"""The guardrail (guardrail.toml, HALLUCINATIONS.md, owner-owned paths, hooks) and the evidence gate."""
import fnmatch
import json
import os
import re
from pathlib import Path

from base import (RAIL, STATE, ZERO_SHA, Fail, Module, branch_sha, current_branch, git, git_out, owner_owned, sh,
                  tail, template, worktree_at, write_new)

HOOKS = f"{STATE}/hooks"
HOOK_NAMES = ("pre-merge-commit", "pre-push")
MANIFESTS = [  # (file or glob, test, select): the first one present wins
    ("package.json", "npm test", "npm test -- -t '^{id}: '"),
    ("Cargo.toml", "cargo test", "cargo test _{lid}_"),
    ("go.mod", "go test ./...", "go test ./... -run '_{tid}_'"),
    ("pyproject.toml", "pytest", "pytest -q -k '_{tid}_'"),
    ("pytest.ini", "pytest", "pytest -q -k '_{tid}_'"),
    ("setup.py", "pytest", "pytest -q -k '_{tid}_'"),
    ("*.sln", "dotnet test", "dotnet test --filter 'Name~_{tid}_'"),
    ("*.csproj", "dotnet test", "dotnet test --filter 'Name~_{tid}_'"),
]
DEFAULT_SELECT = "pytest -q -k '_{tid}_'"
PLACEHOLDER = re.compile(r"\{(?:id|tid|lid)\}")

STR, INT, NUM, STRS, BOOL = "a string", "an integer", "a number", "a list of strings", "true or false"
# key -> (expected, required, extra check or None)
SCHEMA = {
    "domains": (STRS, True, "domains"), "compass": (STRS, True, "compass"),
    "base": (STR, True, None), "test": (STR, True, None), "spec": (STR, True, None),
    "limits": ("a table of strings", False, None),
    "ids": ("a table", True, None),
    "ids.pattern": (STR, True, "regex"), "ids.url": (STR, False, "placeholder"), "ids.export": (STR, False, None),
    "burndown": ("a table", True, None),
    "burndown.select": (STR, True, "placeholder"), "burndown.tests": (STRS, True, None),
    "evidence": ("a table of strings", False, None),
    "loop": ("a table", False, None),
    "loop.max_steps": (INT, False, ">=1"), "loop.stale_hours": (NUM, False, ">0"),
    "tanks": ("a table", False, None),
    "tanks.agents": (STRS, False, "agents"), "tanks.reps": (INT, False, ">=2"),
    "tanks.max_cost_usd": (NUM, False, ">0"), "tanks.covers": (STRS, False, None),
    "tanks.price": ("a table of tables", False, None),
    "shots": ("a table", False, None),
    "shots.budget": ("a table of integers", False, None), "shots.memory_budget": (INT, False, ">=1"),
    "scaffold": ("a table", False, None), "scaffold.cooldown_days": (INT, False, ">=1"),
    "receipts": ("a table", False, None), "receipts.dir": (STR, False, None), "receipts.required": (BOOL, False, None),
}
DEFAULTS = {"loop": {"max_steps": 5, "stale_hours": 3},
            "tanks": {"agents": ["claude-code", "codex"], "reps": 3, "max_cost_usd": 5.0,
                      "covers": ["skills/", "AGENTS.md"]}}


def setting(rail, dotted):
    section, _, key = dotted.partition(".")
    value = rail.get(section, {}) if key else rail.get(section)
    if key:
        value = value.get(key) if isinstance(value, dict) else None
        if value is None:
            value = DEFAULTS.get(section, {}).get(key)
    return value


def kind_ok(expected, value):
    if expected == STR:
        return isinstance(value, str)
    if expected == BOOL:
        return isinstance(value, bool)
    if expected == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == NUM:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if expected == "a table":
        return isinstance(value, dict)
    if expected == "a table of strings":
        return isinstance(value, dict) and all(isinstance(v, str) for v in value.values())
    if expected == "a table of integers":
        return isinstance(value, dict) and all(isinstance(v, int) and not isinstance(v, bool) for v in value.values())
    if expected == "a table of tables":
        return isinstance(value, dict) and all(isinstance(v, dict) for v in value.values())
    return False


def validate(rail, root, agents, pack=None):
    """Schema fails for an guardrail.toml: each names the key, the value found, and the form expected."""
    if "__error__" in rail:
        return [Fail(f"{RAIL} is not TOML: {rail['__error__']}", f"fix the syntax in {RAIL}")]
    fails = []
    tables = {k for k in SCHEMA if "." not in k}
    for key in rail:
        if key not in tables:
            fails.append(Fail(f"{RAIL}: unknown key `{key}`", f"remove `{key}` or fix its spelling"))
    for key, section in rail.items():
        if isinstance(section, dict) and key in ("ids", "burndown", "loop", "tanks", "shots", "scaffold", "receipts"):
            for sub in section:
                if f"{key}.{sub}" not in SCHEMA:
                    fails.append(Fail(f"{RAIL}: unknown key `{key}.{sub}`", f"remove `{sub}` from [{key}]"))
    for key, (expected, required, check) in SCHEMA.items():
        section, _, sub = key.partition(".")
        container, name = (rail.get(section), sub) if sub else (rail, section)
        if not isinstance(container, dict) or name not in container:
            if required and (not sub or isinstance(rail.get(section), dict)):
                fails.append(Fail(f"{RAIL}: `{key}` is missing", f"set `{key}` ({expected}) in {RAIL}"))
            continue
        value = container[name]
        if not kind_ok(expected, value):
            fails.append(Fail(f"{RAIL}: `{key}` is {value!r}, expected {expected}", f"set `{key}` to {expected}"))
            continue
        if check == "regex":
            try:
                pattern = re.compile(value)
            except re.error as error:
                fails.append(Fail(f"{RAIL}: `{key}` does not compile: {error}", f"fix the regex in `{key}`"))
                continue
            clash = [s for s in ("R1", "R1.1", "D1") if pattern.fullmatch(s)]
            if clash:
                fails.append(Fail(f"{RAIL}: `{key}` matches requirement ids {', '.join(clash)}",
                                  f"narrow `{key}` so requirement and decision ids stay apart"))
        elif check == "placeholder" and key == "burndown.select" and not PLACEHOLDER.search(value):
            fails.append(Fail(f"{RAIL}: `{key}` has no {{id}}, {{tid}} or {{lid}}", f"add the ticket id to `{key}`"))
        elif check == ">=1" and value < 1 or check == ">=2" and value < 2 or check == ">0" and value <= 0:
            fails.append(Fail(f"{RAIL}: `{key}` is {value!r}, expected {expected} {check}", f"raise `{key}`"))
        elif check == "domains" and pack is not None:
            unknown = [d for d in value if d not in pack.domains]
            if unknown:
                fails.append(Fail(f"{RAIL}: `domains` names {', '.join(unknown)}, not in PACK.md # Domains",
                                  f"use names from: {', '.join(pack.domains)}"))
        elif check == "compass" and pack is not None:
            unknown = [c for c in value if c not in pack.compass or c == "core"]
            if unknown:
                fails.append(Fail(f"{RAIL}: `compass` names {', '.join(unknown)}, not an optional compass layer",
                                  f"use names from: {', '.join(c for c in pack.compass if c != 'core')}"))
        elif check == "agents":
            unknown = [a for a in value if a not in agents]
            if unknown:
                fails.append(Fail(f"{RAIL}: `{key}` names {', '.join(unknown)}, not in PACK.md # Agents",
                                  f"use names from: {', '.join(agents)}"))
    if isinstance(rail.get("base"), str) and rail["base"]:
        base = rail["base"]
        if not branch_sha(root, base) and current_branch(root) != base:
            fails.append(Fail(f"{RAIL}: `base` names branch `{base}`, which does not exist",
                              f"set base in {RAIL} or git branch {base}"))
    if isinstance(rail.get("spec"), str) and not (Path(root) / rail["spec"]).is_dir():
        fails.append(Fail(f"{RAIL}: `spec` names {rail['spec']}, which is not a directory",
                          f"mkdir -p {rail['spec']} or set spec in {RAIL}"))
    return fails


def detect(root):
    root = Path(root)
    for name, test, select in MANIFESTS:
        if any(root.glob(name)):
            return test, select
    return "", DEFAULT_SELECT


def default_base(root):
    """dev, then main, then master; a checkout with none of them (or none yet) uses its current branch."""
    for name in ("dev", "main", "master"):
        if branch_sha(root, name):
            return name
    return current_branch(root) or "main"


def manifest_seeds(domains):
    """[guardrail] test/select from the first selected domain manifest that declares them."""
    import scaffold
    for d in domains:
        seed = (scaffold.load_manifest(d) or {}).get("guardrail") or {}
        if seed.get("test"):
            return seed["test"], seed.get("select", DEFAULT_SELECT)
    return None


def rail_text(root, agents=(), domains=(), compass=()):
    test, select = manifest_seeds(domains) or detect(root)
    tanks = [a for a in ("claude-code", "codex") if a in agents]
    return (template("guardrail.toml").replace("@DOMAINS@", json.dumps(list(domains)))
            .replace("@COMPASS@", json.dumps([c for c in compass if c != "core"]))
            .replace("@BASE@", default_base(root)).replace("@AGENTS@", json.dumps(tanks))
            .replace("@TEST@", test).replace("@SELECT@", select.replace("\\", "\\\\").replace('"', '\\"')))


def hook_text(name):
    return template(f"hooks/{name}")


def hooks_state(root):
    path = git_out(root, "config", "--get", "core.hooksPath")
    missing = [n for n in HOOK_NAMES if not os.access(Path(root) / HOOKS / n, os.X_OK)]
    return path, missing


CLAUDE_SETTINGS = ".claude/settings.json"


def ask_rules(ctx):
    return [f"{tool}({p})" for p in owner_owned(ctx) for tool in ("Edit", "Write")]


def claude_ask_missing(ctx):
    path = ctx.root / CLAUDE_SETTINGS
    if not path.is_file():
        return ask_rules(ctx), False
    try:
        have = json.loads(path.read_text()).get("permissions", {}).get("ask", [])
    except (json.JSONDecodeError, AttributeError):
        return ask_rules(ctx), True
    return [r for r in ask_rules(ctx) if r not in have], True


class Guardrail(Module):
    name, stops = "guardrail", True

    def probe(self, ctx):
        root = ctx.root
        fails = []
        if not (root / RAIL).is_file():
            fails.append(Fail(f"{RAIL} missing", "bigbang (writes it from the template)"))
        else:
            fails += validate(ctx.rail, root, ctx.pack.agents, ctx.pack)
            saved = ctx.rail.get("domains")
            if ctx.asked_domains and isinstance(saved, list) and set(ctx.asked_domains) != set(saved):
                fails.append(Fail(f"{RAIL} names domains {saved}; this command names {ctx.asked_domains}",
                                  f"the owner sets `domains = {json.dumps(ctx.asked_domains)}` in {RAIL} "
                                  "(Owner-Approved commit), e.g. after approving the sketch"))
            saved = ctx.rail.get("compass")
            asked = [c for c in (ctx.asked_compass or []) if c != "core"]
            if ctx.asked_compass is not None and isinstance(saved, list) and set(asked) != set(saved):
                fails.append(Fail(f"{RAIL} names compass {saved}; this command names {asked}",
                                  f"the owner sets `compass = {json.dumps(asked)}` in {RAIL} (Owner-Approved commit)"))
            if ctx.rail.get("test") == "" and detect(root)[0]:
                fails.append(Fail(f"{RAIL}: `test` is empty but {detect(root)[0]!r} fits this project",
                                  f"set test in {RAIL}"))
        if not (root / "HALLUCINATIONS.md").is_file():
            fails.append(Fail("HALLUCINATIONS.md missing", "bigbang (writes it from the template)"))
        hooks_path, missing = hooks_state(root)
        if hooks_path and hooks_path != HOOKS:
            pass  # another hook manager owns the hooks: report() names the two calls to add, the run goes on
        elif hooks_path != HOOKS or missing:
            fails.append(Fail(f"gate hooks not installed ({', '.join(missing) or 'core.hooksPath unset'})",
                              "bigbang (installs them)"))
        return fails

    def apply(self, ctx):
        root, actions = ctx.root, []
        if not (root / RAIL).is_file():
            actions.append((f"write {RAIL}", lambda: write_new(root / RAIL, rail_text(root, ctx.pack.agents, ctx.domains, ctx.compass))))
            spec = "docs/specs"
            if not (root / spec).is_dir():
                actions.append((f"mkdir {spec}", lambda: (root / spec).mkdir(parents=True, exist_ok=True)))
        if not (root / "HALLUCINATIONS.md").is_file():
            actions.append(("write HALLUCINATIONS.md",
                            lambda: write_new(root / "HALLUCINATIONS.md", template("HALLUCINATIONS.md"))))
        hooks_path, missing = hooks_state(root)
        if hooks_path in ("", HOOKS):
            for n in missing:
                actions.append((f"write {HOOKS}/{n}", lambda n=n: write_new(root / HOOKS / n, hook_text(n), 0o755)))
            if not hooks_path:
                actions.append((f"git config core.hooksPath {HOOKS}",
                                lambda: git(root, "config", "core.hooksPath", HOOKS)))
        missing_rules, exists = claude_ask_missing(ctx)
        if missing_rules and not exists:
            settings = {"permissions": {"ask": ask_rules(ctx)}}
            actions.append((f"write {CLAUDE_SETTINGS} with ask rules for the owner-owned paths",
                            lambda: write_new(root / CLAUDE_SETTINGS, json.dumps(settings, indent=2) + "\n")))
        return actions

    def report(self, ctx):
        lines = []
        missing_rules, exists = claude_ask_missing(ctx)
        if missing_rules:
            lines.append(f"guardrail: ask unenforced on claude-code: add {json.dumps(missing_rules)} to "
                         f"permissions.ask in {CLAUDE_SETTINGS}")
        others = [a for a in ctx.pack.agents if a != "claude-code"]
        if others:
            lines.append(f"guardrail: ask unenforced on {', '.join(others)}: no project-level ask rule known; "
                         "the Owner-Approved trailer is the only record")
        hooks_path, _ = hooks_state(ctx.root)
        if hooks_path and hooks_path != HOOKS:
            lines.append(f"guardrail: gate hooks not enforced: core.hooksPath is {hooks_path}; add "
                         f"`{HOOKS}/pre-merge-commit` and `{HOOKS}/pre-push` to its hooks")
        if ctx.rail.get("test") == "":
            lines.append(f"guardrail: test unset (no manifest found); set test in {RAIL} once tests exist")
        return lines


# Gate ------------------------------------------------------------------------

def limit_hit(path, pattern):
    pattern = pattern.rstrip("/")
    return path == pattern or path.startswith(pattern + "/") or fnmatch.fnmatch(path, pattern)


def gate_range(ctx):
    """(mode, lo, hi, test_at): which commits the gate judges. test_at is a sha to test in a worktree, or None."""
    base = ctx.rail.get("base", "dev")
    push = os.environ.get("BIGBANG_PUSH", "").split()
    if len(push) == 3:
        remote_ref, remote_sha, local_sha = push
        if remote_ref != f"refs/heads/{base}" or local_sha == ZERO_SHA:
            return ("skip", None, None, None)
        lo = remote_sha if remote_sha != ZERO_SHA else ""
        return ("push", lo, local_sha, local_sha)
    merge = git_out(ctx.root, "rev-parse", "--quiet", "--verify", "MERGE_HEAD")
    head = git_out(ctx.root, "rev-parse", "--quiet", "--verify", "HEAD")
    if merge and head:
        return ("merge", head, merge, None)
    if not head or current_branch(ctx.root) == base:
        return ("base", None, None, None)
    return ("branch", base, "HEAD", None)


def approved(trailers):
    return any(v.strip() for v in trailers.split(","))


class Gate(Module):
    name, runs = "gate", True

    def probe(self, ctx):
        self.lines = []
        if not ctx.rail or "__error__" in ctx.rail:
            return [Fail(f"{RAIL} missing or invalid", "bigbang (guardrail writes and checks it)")]
        mode, lo, hi, test_at = gate_range(ctx)
        if mode == "skip":
            self.lines.append("gate: push is not to base; nothing to judge")
            return []
        root, fails = ctx.root, []
        test = ctx.rail.get("test", "")
        if test:
            cwd = root
            if test_at:
                cwd, error = worktree_at(root, test_at)
                if error:
                    return [Fail(f"could not check out {test_at[:7]}: {error}", "git worktree prune")]
            result = sh(test, cwd, shell=True)
            if result.returncode:
                fails.append(Fail(f"red: `{test}` exited {result.returncode}",
                                  tail(result.stdout + result.stderr).replace("\n", " ⏎ ")[-1500:] or test))
        else:
            self.lines.append("gate: test unset; rule 1 has nothing to run")
        if "tanks" in ctx.modules:
            import tokens
            stale = tokens.card_stale(ctx)
            if stale:
                fails.append(stale)
        if mode in ("base",):
            self.lines.append(f"gate: on base `{ctx.rail.get('base')}`; rules 2–4 judge branches and merges")
        else:
            base = ctx.rail.get("base")
            if mode == "branch" and not git(root, "merge-base", "--is-ancestor", base, "HEAD").returncode == 0:
                fails.append(Fail(f"stale: `{base}` is not an ancestor of HEAD", f"git merge {base}"))
            if mode == "push" and lo and git(root, "merge-base", "--is-ancestor", lo, hi).returncode:
                fails.append(Fail(f"stale: the remote {base} is not an ancestor of the pushed commit",
                                  f"git pull --no-rebase origin {base}"))
            lo = lo or git_out(root, "rev-parse", "--quiet", "--verify", f"refs/remotes/origin/{base}")
            if not lo:
                self.lines.append(f"gate: no remote {base} to compare the push against; rules 3–4 have no range")
                return fails
            spans = (f"{lo}...{hi}", f"{lo}..{hi}")
            changed = git_out(root, "diff", "--name-only", spans[0]).splitlines()
            for name, pattern in (ctx.rail.get("limits") or {}).items():
                hits = [p for p in changed if limit_hit(p, pattern)]
                if hits:
                    fails.append(Fail(f"limit `{name}` touched: {', '.join(hits[:5])}",
                                      f"the owner changes [limits] {name}, or the change moves off {pattern}"))
            log = git_out(root, "log", "--format=%H%x1f%(trailers:key=Owner-Approved,valueonly,separator=%x2C)%x1e",
                          spans[1], "--", *owner_owned(ctx))
            for record in filter(None, (r.strip() for r in log.split("\x1e"))):
                sha, _, trailers = record.partition("\x1f")
                if not approved(trailers):
                    subject = git_out(root, "log", "-1", "--format=%s", sha)
                    fails.append(Fail(f"self-edit: {sha[:7]} `{subject}` changes an owner-owned path without "
                                      "an Owner-Approved trailer", "the owner approves: git commit --amend "
                                      "--trailer 'Owner-Approved: <owner>' (or reverts the change)"))
        if not fails:
            self.lines.append(f"gate: {mode} · evidence holds")
        return fails

    def report(self, ctx):
        return getattr(self, "lines", [])
