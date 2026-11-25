#!/usr/bin/env python3
"""kit: install only the skills a project calls for, from the PACK.md catalog, or fail.

  packages.py                          verify: gate both scopes, install nothing
  packages.py kit-starter-pack         index the catalog and publish explicit-only plugins
  packages.py bigbang [<domain>...]    initialize Git if needed, index the catalog, configure domains (default core), `mise run stage0`
                                       (or `mise install`), start every stdio MCP server once, then verify
  packages.py verify --strict-projection  also fail on nonzero Claude plugin token estimates
  packages.py prune [<plugin>...]      list unused @kit plugins; turn off only the ones named, in ~/.claude/settings.json
  packages.py portable                refresh shared skill commands from the published catalog
  packages.py dev-sync [--allow-main] [--local-only]  sync repo and catalog skills
  packages.py use <skill>...           print a catalog skill from the index, so it enters the context only when called
  packages.py tag [<tag>...]           list declared PACK.md tags or filter catalog skills by one or more tags
  packages.py tools                    deny PACK.md `# Tools` in ~/.claude/settings.json, so no session loads them
  packages.py domain <domain>...       add the domain's MCP servers to this project and list its /publisher:skill commands
  packages.py <token>... [-g]          install into this project, or globally with -g.
                                       A token is a domain, a skill, owner/repo:skill, or owner/repo.
  packages.py add owner/repo [--skill a b]   add a catalog row; installs nothing
  packages.py remove <skill>... [-g]   uninstall from this project, or globally
  packages.py list [-g]                passed to `skills list`
  packages.py stamp                    write publisher metadata and a `publisher:` description prefix into every installed SKILL.md
  packages.py export <skill>... [-g]   zip skills for ChatGPT web upload, which has no scripted route
  --dry-run                            run every gate and print the installs; change nothing

Every check is a hard gate: one problem stops the run with exit code 1.

CLI reference: https://github.com/vercel-labs/skills/blob/main/docs/commands.md
Discovery rules: https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CLI_VERSION = "1.7.4"  # npm `skills`, published 2026-10-19. Pin, never `latest`.
CLI = ["npx", "--yes", f"skills@{CLI_VERSION}"]
MAX_SKILLS = 40  # per session: global plus this project
MAX_LISTING_BYTES = 12000  # sum of descriptions: what every session pays to list them
TIMEOUT = 600  # seconds per command
SLASH = Path.home() / ".claude/skills"  # where the earlier layout wrote stubs
MARKET = Path.home() / ".cache/kit/marketplace"
MARKET_NAME = "kit"
SETTINGS = Path.home() / ".claude/settings.json"
CLAUDE_STATE = Path.home() / ".claude.json"  # Claude Code's own usage counters (skillUsage, pluginUsage)
TOOLS_OWNED = Path.home() / ".cache/kit/tools.json"  # deny rules kit added, so it never removes yours
TOOL = re.compile(r"[\w.*-]+")

HOME = Path.home()
PACK = Path(__file__).with_name("PACK.md")
CACHE = HOME / ".cache/kit"
INDEX = CACHE / "index.json"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
if os.environ.get("KIT_TELEMETRY") != "1":
    ENV.update(DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")  # also skips the CLI's audit requests

ROW = re.compile(
    r"^\s*[*-]\s+(?:<img[^>]*>\s*)?\[[^\]]+\]\(https://github\.com/([\w.-]+/[\w.-]+?)/?\)\s*(?::\s*(.*))?$"
)
LINK = re.compile(r"\[([^\]]+)\]\(https://github\.com/([\w.-]+/[\w.-]+?)/?\)")
BULLET = re.compile(r"^\s*[*-]\s")
NAME = re.compile(r"\[([^\]]+)\]\(https://github\.com/")
ITEM = re.compile(r"^\s*\d+\.\s+(\S+)")
REPO = re.compile(r"[\w.-]+/[\w.-]+")
TAG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TAGS_LINE = re.compile(r"^\s*Tags:\s*(.+)$", re.IGNORECASE)


def gate(problems, hint=""):
    if not problems:
        return
    print(f"\nFAIL: {len(problems)} problem(s)")
    for p in problems[:20]:
        print("  - " + p)
    if len(problems) > 20:
        print(f"  ... and {len(problems) - 20} more")
    if hint:
        print(hint)
    sys.exit(1)


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, stdin=subprocess.DEVNULL, timeout=TIMEOUT, env=ENV, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"timed out after {TIMEOUT}s")


# PACK.md -----------------------------------------------------------------

class Pack:
    def __init__(self, text):
        self.text, self.rows, self.domains, self.agents, problems = text, {}, {}, [], []
        self.owned, self.publisher, self.tools, self.mcp = set(), {}, [], {}
        self.tags, self.repo_tags, self.domain_tags, used_tags = [], {}, {}, []
        section = domain = last_repo = ""
        for n, line in enumerate(text.splitlines(), 1):
            if line.startswith("# "):
                section, domain, last_repo = line[2:].strip().lower(), "", ""
            elif line.startswith("## ") and section == "domains":
                domain = line[3:].strip().lower()
                if domain in self.domains:
                    problems.append(f"PACK.md:{n} repeats domain {domain}")
                self.domains[domain] = []
                self.domain_tags[domain] = set()
            elif (tm := TAGS_LINE.match(line)) and section in ("batteries included", "domains"):
                tags = [t.strip() for t in re.split(r"[,\s]+", tm.group(1)) if t.strip()]
                if section == "batteries included" and last_repo:
                    self.repo_tags[last_repo] |= set(tags)
                    used_tags.extend((n, t) for t in tags)
                elif section == "domains" and domain:
                    self.domain_tags[domain] |= set(tags)
                    used_tags.extend((n, t) for t in tags)
                else:
                    problems.append(f"PACK.md:{n} `Tags:` line has no preceding entry")
            elif section == "batteries included" and line.lstrip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and (cells[0].lower() == "source" or all(re.fullmatch(r":?-{2,}:?", c) for c in cells)):
                    continue
                m = LINK.search(cells[0]) if len(cells) == 3 else None
                if not m:
                    problems.append(f"PACK.md:{n} is not `| [Name](https://github.com/owner/repo) | skills | tags |`")
                elif m.group(2).lower() in self.rows:
                    problems.append(f"PACK.md:{n} repeats {m.group(2)}")
                else:
                    names = [] if cells[1].lower() in ("", "-", "all") else [s for s in re.split(r"[,\s]+", cells[1]) if s]
                    tags = [] if cells[2] in ("", "-") else [t for t in re.split(r"[,\s]+", cells[2]) if t]
                    last_repo = m.group(2).lower()
                    self.rows[last_repo] = (m.group(2), names)
                    self.publisher[last_repo] = m.group(1)
                    self.repo_tags[last_repo] = set(tags)
                    used_tags.extend((n, t) for t in tags)
            elif section == "batteries included" and BULLET.match(line):
                m = ROW.match(line)
                if not m:
                    problems.append(f"PACK.md:{n} is not `* [Name](https://github.com/owner/repo): skills`")
                elif m.group(1).lower() in self.rows:
                    problems.append(f"PACK.md:{n} repeats {m.group(1)}")
                else:
                    names = [s for s in re.split(r"[,\s]+", m.group(2) or "") if s]
                    last_repo = m.group(1).lower()
                    self.rows[last_repo] = (m.group(1), names)
                    self.publisher[last_repo] = NAME.search(line).group(1)
                    self.repo_tags[last_repo] = set()
            elif section == "mcp servers" and re.match(r"^\s*\d+\.", line):
                m = re.match(r"^\s*\d+\.\s+`?([\w-]+)`?\s+`?(.+?)`?\s*$", line)
                if not m:
                    problems.append(f"PACK.md:{n} is not `1. name https://url` or `1. name command args`")
                else:
                    self.mcp[m.group(1)] = m.group(2)
            elif section in ("agents", "agent-owned", "tools", "tags", "domains") and re.match(r"^\s*\d+\.", line):
                m = ITEM.match(line)
                if not m:
                    problems.append(f"PACK.md:{n} is an empty list item")
                elif section == "agents":
                    if m.group(1) == "*":
                        problems.append(f"PACK.md:{n} `*` links every agent, and some get copies. Name agents.")
                    self.agents.append(m.group(1))
                elif section == "agent-owned":
                    self.owned.add(m.group(1))
                elif section == "tools":
                    rule = m.group(1).strip("`")
                    if not TOOL.fullmatch(rule):
                        problems.append(f"PACK.md:{n} `{rule}` is scoped; only a bare name or glob leaves a tool out of context")
                    self.tools.append(rule)
                elif section == "tags":
                    tag = m.group(1)
                    if not TAG.fullmatch(tag):
                        problems.append(f"PACK.md:{n} invalid tag `{tag}`; use lowercase letters, digits, and hyphens")
                    elif tag in self.tags:
                        problems.append(f"PACK.md:{n} repeats tag `{tag}`")
                    else:
                        self.tags.append(tag)
                elif not domain:
                    problems.append(f"PACK.md:{n} is a list item outside a `## domain`")
                else:
                    body = re.sub(r"^\s*\d+\.\s+", "", line).strip()
                    if ": " in body:
                        prefix, rest = body.split(":", 1)
                        self.domains[domain].extend(f"{prefix.strip()}:{s}" for s in re.split(r"[,\s]+", rest) if s)
                    else:
                        self.domains[domain].append(m.group(1))
        declared = set(self.tags)
        for n, t in used_tags:
            if not TAG.fullmatch(t):
                problems.append(f"PACK.md:{n} invalid tag `{t}`; use lowercase letters, digits, and hyphens")
            elif t not in declared:
                problems.append(f"PACK.md:{n} uses undeclared tag `{t}`; declare it under `# Tags`")
        if not self.rows:
            problems.append("PACK.md has no rows under `# Batteries included`")
        if not self.agents:
            problems.append("PACK.md has no agents under `# Agents`")
        gate(problems)

    def repo(self, name):
        return self.rows.get(name.lower(), (None, None))[0]


# Sources -----------------------------------------------------------------

def frontmatter(path):
    lines = path.read_text(errors="ignore").splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None, False
    fm = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm.append(line)
    name = desc = None
    for i, line in enumerate(fm):
        if line.startswith("name:"):
            name = line[5:].strip().strip("'\"")
        elif line.startswith("description:"):
            desc = line[12:].strip()
            if desc in ("", ">", "|", ">-", "|-"):
                desc = " ".join(x.strip() for x in fm[i + 1:] if x[:1] in (" ", "\t")).strip()
            desc = desc.strip("'\"")
    return name, desc, any(re.match(r"^\s+internal:\s*true\b", x) for x in fm)


def discover(root):
    return {n: len((frontmatter(f)[1] or "").encode()) for n, f in discover_paths(root).items()}


def discover_paths(root):
    """Approximates the CLI's discovery rules; the post-install gates catch any disagreement."""
    if (root / "SKILL.md").is_file():
        files = [root / "SKILL.md"]
    else:
        containers = [d for d in [root / "skills", *root.glob(".*/skills")] if d.is_dir()]
        files = [f for c in containers for f in c.rglob("SKILL.md") if len(f.relative_to(c).parts) <= 4]
        if not files:
            files = [f for f in root.rglob("SKILL.md") if not {".git", "node_modules"} & set(f.parts)]
    dirs, found = {f.parent for f in files}, {}
    for f in sorted(files, key=lambda f: len(f.parts)):
        if any(p in dirs for p in f.parent.parents):
            continue  # a shallower SKILL.md shadows this one
        name, desc, internal = frontmatter(f)
        if name and desc and not internal:
            found.setdefault(name, f)
    return found


def repository_skills():
    """First-party packages have one entrypoint per directory under skills/."""
    root = Path(__file__).resolve().parent.parent
    found = {}
    for manifest in sorted(root.glob("*/SKILL.md")):
        text = manifest.read_text(errors="ignore")
        name, description, internal = frontmatter(manifest)
        if internal:
            continue
        policy = manifest.parent / "agents/openai.yaml"
        hidden = (re.search(r"^disable-model-invocation:\s*true\s*$", text, re.MULTILINE)
                  or (policy.is_file() and re.search(r"^\s*allow_implicit_invocation:\s*false\s*$",
                                                     policy.read_text(errors="ignore"), re.MULTILINE)))
        gate([f"{manifest}: expected a model-invocable local skill named {manifest.parent.name} with a description"]
             if (manifest.is_symlink() or manifest.parent.is_symlink() or not name or not description
                 or name != manifest.parent.name or name != slug(name) or hidden) else [])
        found[name] = manifest.parent
    return found


def index_one(repo, cached):
    url = f"https://github.com/{repo}.git"
    head = run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True)
    sha = head.stdout.split()[0] if head.returncode == 0 and head.stdout else None
    if not sha:
        return repo, None, f"{repo}: does not resolve at {url}"
    if cached.get("sha") == sha:
        return repo, cached, None
    dest = CACHE / repo.replace("/", "@")
    if (dest / ".git").is_dir():
        steps = [["git", "-C", str(dest), "fetch", "--depth", "1", "--quiet", "origin", "HEAD"],
                 ["git", "-C", str(dest), "reset", "--hard", "--quiet", "FETCH_HEAD"]]
    else:
        steps = [["git", "clone", "--depth", "1", "--quiet", url, str(dest)]]
    for step in steps:
        if run(step, capture_output=True).returncode:
            return repo, None, f"{repo}: does not clone from {url}"
    return repo, {"sha": sha, "skills": discover(dest)}, None


def index(pack, repos, offline=False):
    try:
        idx = json.loads(INDEX.read_text())
    except (FileNotFoundError, ValueError):
        idx = {}
    if offline:
        gate([f"{r}: missing from the local index. Run: python3 packages.py kit-starter-pack"
              for r in repos if r not in idx])
        results = [(r, idx[r], None) for r in repos]
    else:
        CACHE.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda r: index_one(r, idx.get(r, {})), repos))
    problems = [err for _, _, err in results if err]
    for repo, entry, _ in results:
        if entry:
            idx[repo] = entry
            offered = pack.rows[repo.lower()][1]
            problems += [f"{repo}: catalog offers {n}, which the repo does not have"
                         for n in offered if n not in entry["skills"]]
    gate(problems)
    if not offline:
        INDEX.write_text(json.dumps(idx, indent=1, sort_keys=True))
    return {r: {n: b for n, b in idx[r]["skills"].items() if not pack.rows[r.lower()][1]
                or n in pack.rows[r.lower()][1]} for r in repos}


def resolve(pack, tokens, offline=False):
    """Map tokens to {skill: (repo, description bytes)}."""
    items = []
    for t in tokens:
        items += pack.domains[t.lower()] if t.lower() in pack.domains else [t]
    items = [i for i in items if not i.startswith("mcp:")]  # servers, not skills: see domain()
    aliases = {slug(p): pack.repo(r) for r, p in pack.publisher.items()}

    def source(prefix):
        return pack.repo(prefix) or aliases.get(prefix.lower())

    needed = {source(i.split(":", 1)[0]) if ":" in i else pack.repo(i) for i in items}
    if None in needed:
        needed = {repo for repo, _ in pack.rows.values()}  # a bare name: search the catalog
    offered = index(pack, sorted(needed), offline)
    picks, problems = {}, []
    for item in items:
        repo_part, _, name = item.partition(":")
        repo = source(repo_part) if name else pack.repo(repo_part)
        if repo and name:
            hits = [repo] if name in offered[repo] else []
        elif repo:
            for n in offered[repo]:
                picks.setdefault(n, (repo, offered[repo][n]))
            continue
        elif REPO.fullmatch(item):
            problems.append(f"{item}: not in the catalog. Add it: packages.py add {item}")
            continue
        else:
            name = item
            hits = [r for r in offered if name in offered[r]]
        if not hits:
            problems.append(f"{item}: no catalog source offers this skill")
        elif len(hits) > 1:
            problems.append(f"{item}: offered by {', '.join(hits)}. Write it as owner/repo:{name}")
        elif name in picks and picks[name][0] != hits[0]:
            problems.append(f"{name}: picked from both {picks[name][0]} and {hits[0]}")
        else:
            picks[name] = (hits[0], offered[hits[0]][name])
    problems += [f"{n}: an agent already ships a skill named {n} (PACK.md # Agent-owned)" for n in picks if n in pack.owned]
    gate(problems)
    return picks


# Scopes ------------------------------------------------------------------

def prefix_description(fm, tag):
    """Prefix `description:` with `tag` in place: every agent lists it, and names cannot carry a colon."""
    d = next((k for k, x in enumerate(fm) if x.startswith("description:")), None)
    if d is None:
        return False
    val = fm[d][12:].strip()
    if val[:1] in (">", "|"):  # block scalar: a colon is safe in its content
        if d + 1 >= len(fm) or not fm[d + 1].strip():
            return False
        body = fm[d + 1].lstrip()
        if not body.startswith(tag + " "):
            fm[d + 1] = fm[d + 1][:len(fm[d + 1]) - len(body)] + tag + " " + body
    elif not val:
        return False  # plain multi-line scalar: a colon would break it
    elif val[0] in "'\"":
        if not val[1:].startswith(tag + " "):
            fm[d] = f"description: {val[0]}{tag} {val[1:]}"
    elif not val.startswith(tag + " "):
        fm[d] = "description: " + json.dumps(f"{tag} {val}")
    return True


def stamp(skill, want, write):
    """Put `want` in the SKILL.md frontmatter `metadata:` map (agentskills.io spec). ok, changed or cannot."""
    lines = skill.read_text().split("\n")
    try:
        end = lines.index("---", 1)
    except ValueError:
        return "cannot"
    fm = lines[1:end]
    i = next((k for k, x in enumerate(fm) if x.startswith("metadata:")), None)
    if i is None:
        fm.append("metadata:")
        i = len(fm) - 1
    elif fm[i].strip() != "metadata:":
        return "cannot"  # an inline map is not safely editable
    j = i + 1
    while j < len(fm) and fm[j][:1] in (" ", "\t"):
        j += 1
    block = fm[i + 1:j]
    for k, v in want.items():
        line = f"  {k}: {json.dumps(v)}"
        old = [x for x in block if x.split(":", 1)[0].strip() == k]
        if old != [line]:
            block = [x for x in block if x not in old] + [line]
    fm = fm[:i + 1] + block + fm[j:]
    if not prefix_description(fm, re.sub(r"[^a-z0-9]+", "-", want["publisher"].lower()).strip("-") + ":"):
        return "cannot"
    new = lines[:1] + fm + lines[end:]
    if new == lines:
        return "ok"
    if write:
        skill.write_text("\n".join(new))
    return "changed"


class Scope:
    def __init__(self, is_global):
        self.is_global = is_global
        if is_global:
            self.root, self.lock, self.name, self.tracked = HOME, HOME / ".agents/.skill-lock.json", "global", set()
        else:
            top = run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
            if top.returncode:
                gate(["not inside a git project. Pass -g to install globally."])
            self.root = Path(top.stdout.strip())
            self.lock, self.name = self.root / "skills-lock.json", "project"
            files = run(["git", "-C", str(self.root), "ls-files"], capture_output=True, text=True).stdout
            self.tracked = {str(p) for f in files.splitlines() for p in [Path(f), *Path(f).parents]}
        self.store = self.root / ".agents/skills"

    def locked(self):
        try:
            return json.loads(self.lock.read_text()).get("skills", {})
        except FileNotFoundError:
            return {}

    def folders(self):
        found = [*self.root.glob(".*/skills"), *self.root.glob(".config/*/skills"),
                 self.root / ".pi/agent/skills", self.root / ".gemini/config/skills"]
        if not self.is_global:
            found += self.root.glob("*/skills")
        return [f for f in dict.fromkeys(found) if f.is_dir()]  # Python 3.14 globs match dot names with `*`

    def listing(self, names):
        return sum(len((frontmatter(self.store / n / "SKILL.md")[1] or "").encode())
                   for n in names if (self.store / n / "SKILL.md").is_file())

    def stamps(self, pack, write):
        """Every installed skill carries its catalog publisher. Write fixes; otherwise report."""
        bad = []
        for name, entry in self.locked().items():
            src, skill = entry.get("source", ""), self.store / name / "SKILL.md"
            if src.lower() not in pack.publisher or not skill.is_file():
                continue  # drift() reports these
            want = {"publisher": pack.publisher[src.lower()], "source": src, "source-url": f"https://github.com/{src}"}
            res = stamp(skill, want, write)
            if res == "cannot":
                bad.append(f"cannot stamp {skill}: inline `metadata:` or no frontmatter")
            elif res == "changed" and not write:
                bad.append(f"{self.name}: {name} has no publisher stamp. Run: python3 packages.py stamp")
        return bad

    def drift(self, pack):
        lock, problems = self.locked(), []
        own = {"kit-starter-pack", *repository_skills()}
        for name, entry in lock.items():
            if name not in own and not pack.repo(entry.get("source", "")):
                problems.append(f"{self.name}: {name} comes from {entry.get('source')}, not from the catalog")
            if not (self.store / name / "SKILL.md").is_file():
                problems.append(f"{self.name}: {name} is in the lock but not in {self.store}")
            elif name not in own and not re.search(r"^disable-model-invocation:\s*true\s*$",
                                                    (self.store / name / "SKILL.md").read_text(), re.MULTILINE):
                # kit serves catalog skills on demand; a model-visible install loads its description into every window
                problems.append(f"{self.name}: {name} loads into every session; it is already on demand from kit. "
                                f"Run: python3 packages.py remove {name}{' -g' if self.is_global else ''}")
        for folder in self.folders():
            for p in sorted(folder.iterdir()):
                if p.is_symlink() and not p.exists():
                    problems.append(f"broken link: {p}")
                    continue
                if (p.name.startswith(".") or p.name in pack.owned or p.name in own or (p / ".kit-stub").is_file()
                        or str(p.relative_to(self.root)) in self.tracked):
                    continue
                if p.name not in lock:
                    problems.append(f"foreign entry: {p}")
                elif folder != self.store and p.resolve() != (self.store / p.name).resolve():
                    problems.append(f"a copy, not a link: {p}")
                elif folder not in (self.store, self.root / ".claude/skills",
                                    self.root / ".cursor/skills", self.root / ".gemini/config/skills"):
                    problems.append(f"{p.name} is listed twice for the agents reading {folder}: it is already in {self.store}")
        return problems


def scopes():
    inside = run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).returncode == 0
    return [Scope(True)] + ([Scope(False)] if inside else [])


def twice():
    """A skill in both the global and the project store is listed twice in every session."""
    seen, problems = {}, []
    for s in scopes():
        for n in s.locked():
            if n in seen:
                problems.append(f"{n}: installed in {seen[n]} and {s.name}; each session lists it twice")
            seen[n] = s.name
    return problems


def budget(pack, extra=None):
    names, listing = set(), 0
    for s in scopes():
        names |= set(s.locked())
        listing += s.listing(s.locked())
    for n, (_, size) in (extra or {}).items():
        if n not in names:
            names.add(n)
            listing += size
    problems = []
    if len(names) > MAX_SKILLS:
        problems.append(f"{len(names)} skills per session, over the {MAX_SKILLS} cap")
    if listing > MAX_LISTING_BYTES:
        problems.append(f"{listing} description bytes per session, over the {MAX_LISTING_BYTES} cap")
    return problems, len(names), listing


# Commands ----------------------------------------------------------------

def install(pack, tokens, is_global, dry):
    scope = Scope(is_global)
    gate(scope.drift(pack), f"Clean {scope.root} first: every installed skill must come from the catalog.")
    picks = resolve(pack, tokens)
    lock = scope.locked()
    clash = [f"{n}: installed from {lock[n].get('source')}, picked from {repo}"
             for n, (repo, _) in picks.items() if n in lock and lock[n].get("source", "").lower() != repo.lower()]
    gate(clash)
    gate([f"{n}: already installed in {s.name}; each session would list it twice"
          for s in scopes() if s.is_global != is_global for n in picks if n in s.locked()])
    new = {n: v for n, v in picks.items() if n not in lock}
    problems, count, listing = budget(pack, new)
    gate(problems, "Install fewer skills, or remove some first.")
    by_repo = {}
    for n, (repo, _) in sorted(new.items()):
        by_repo.setdefault(repo, []).append(n)
    agents = [x for a in pack.agents for x in ("-a", a)]
    cmds = [CLI + ["add", repo, *(["-g"] if is_global else []), "-y", *agents, "--skill", *names]
            for repo, names in by_repo.items()]
    print(f"{scope.name}: {len(new)} new skill(s), {len(picks) - len(new)} already installed; "
          f"session after install: {count} skills, {listing} description bytes")
    for cmd in cmds:
        print("$ " + shlex.join(cmd))
    if dry or not cmds:
        print("dry run: nothing changed" if dry else "nothing to install")
        return 0
    if scope.lock.is_file():
        backup = CACHE / f"{scope.name}-lock-{time.strftime('%Y%m%d-%H%M%S')}.json"
        shutil.copy2(scope.lock, backup)
        print(f"lock backed up: {backup}")
    before = {p.name for p in scope.root.iterdir()}
    for cmd in cmds:
        if run(cmd, cwd=scope.root).returncode:
            gate([f"install failed: {shlex.join(cmd)}"], "Fix it and run again; installs are idempotent.")
    lock, problems = scope.locked(), scope.drift(pack)
    problems += [f"not in lock after install: {n}" for n in new if n not in lock]
    if not scope.is_global:
        problems += [f"install created {scope.root / p} in the project root"
                     for p in sorted({p.name for p in scope.root.iterdir()} - before)
                     if not p.startswith(".") and p != "skills-lock.json"]
    problems += scope.stamps(pack, True)
    problems += budget(pack)[0]
    gate(problems, "Installed, but not as declared. Lock backup is in ~/.cache/kit.")
    print(f"ok: {len(new)} installed into {scope.name}")
    return 0


def claude_projection():
    if not shutil.which("claude"):
        return ["Claude Code is required to check plugin token projections"]
    result = run(["claude", "plugin", "list", "--json"], capture_output=True, text=True)
    try:
        plugins = [p["id"] for p in json.loads(result.stdout) if p["id"].endswith("@kit") and p.get("enabled")]
    except (ValueError, TypeError, KeyError):
        plugins = []
    if result.returncode or not plugins:
        return ["Could not read any enabled @kit plugins from Claude Code"]
    problems = []
    for plugin in plugins:
        details = run(["claude", "plugin", "details", plugin], capture_output=True, text=True)
        cost = re.search(r"^\s*Always-on:\s*(.+)$", details.stdout, re.MULTILINE)
        if details.returncode or not cost:
            problems.append(f"{plugin}: could not read the always-on token projection")
        elif not re.match(r"^~?0\s+tok\b", cost[1]):
            problems.append(f"{plugin}: Claude Code projects {cost[1].strip()}")
    return problems


def disabled_plugins():
    return {k for k, v in read_settings().get("enabledPlugins", {}).items() if v is False and k.endswith("@" + MARKET_NAME)}


def source_drift():
    """Kit edits itself (`kit add` writes PACK.md). When it runs from a copy, or its source has uncommitted changes,
    those edits never reach git: the 2026-11-12 incident lost a PACK.md row and a whole packages.py that way."""
    here = Path(__file__).resolve().parent
    top = run(["git", "-C", str(here), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode:
        return [f"kit runs from a copy at {here}, not a git checkout. Link it: "
                f"ln -sfn <agents-kit-stack>/skills/kit {Path(__file__).parent}"]
    dirty = run(["git", "-C", str(here), "status", "--porcelain", "--", str(here)], capture_output=True, text=True).stdout
    return [f"uncommitted kit change: {line[3:]}. Commit it on the dev branch" for line in dirty.splitlines()]


def usage():
    try:
        state = json.loads(CLAUDE_STATE.read_text())
    except (FileNotFoundError, ValueError):
        return None
    return state.get("pluginUsage", {}), state.get("skillUsage", {})


def unused_plugins():
    """Enabled @kit plugins with no recorded use: zero plugin dispatches and no skill of theirs ever called."""
    counts = usage()
    if counts is None:
        return []
    plugins, skills = counts
    enabled = {k for k, v in read_settings().get("enabledPlugins", {}).items() if v is True and k.endswith("@" + MARKET_NAME)}
    return sorted(k for k in enabled
                  if not plugins.get(k, {}).get("usageCount") and not any(s.startswith(k.split("@")[0] + ":") for s in skills))


def prune(dry, picked=()):
    """Turn off the named unused @kit plugins; bare prune only lists them (never a bulk disable). Undo: /plugin."""
    unused = unused_plugins()
    print(f"prune: {len(unused)} unused plugin(s): {', '.join(unused) or 'none'}")
    names = [n if "@" in n else f"{n}@{MARKET_NAME}" for n in picked]
    gate([f"{n} is not an unused @kit plugin" for n in names if n not in unused])
    if not names:
        if unused:
            print("ask the owner which to turn off, then: python3 packages.py prune <plugin>...")
        return 0
    if dry:
        print(f"would turn off: {', '.join(names)}")
        return 0
    settings = read_settings()
    CACHE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SETTINGS, CACHE / f"settings-{time.strftime('%Y%m%d-%H%M%S')}.json")
    for name in names:
        settings.setdefault("enabledPlugins", {})[name] = False
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    print("ok: turned off; kit-starter-pack keeps them off")
    return 0


def agent_global_dir(agent):
    """Global skill directory each supported agent actually reads."""
    return {
        "claude-code": HOME / ".claude/skills",
        "cursor": HOME / ".cursor/skills",
        "antigravity": HOME / ".gemini/config/skills",
    }.get(agent, HOME / ".agents/skills")


def agent_coverage(pack):
    """Verify every configured agent has all core repository skills and catalog access."""
    sources = repository_skills()
    manifest = MARKET / ".claude-plugin/marketplace.json"
    plugins_meta = json.loads(manifest.read_text()).get("plugins", []) if manifest.is_file() else []
    catalog = [
        f"{plugin['name']}-{skill.parent.name}"
        for plugin in plugins_meta
        for skill in sorted((MARKET / plugin["source"] / "skills").glob("*/SKILL.md"))
    ]
    problems, summary = [], []
    if manifest.is_file() and INDEX.is_file() and isinstance(getattr(pack, "rows", None), dict):
        try:
            idx = json.loads(INDEX.read_text())
        except ValueError:
            idx = {}
        published = set(catalog)
        unpublished = [
            f"{slug(pack.publisher[k])}:{n}"
            for k, (repo, offered_names) in sorted(pack.rows.items())
            if repo in idx
            for n in sorted(idx[repo].get("skills", {}))
            if (not offered_names or n in offered_names) and f"{slug(pack.publisher[k])}-{n}" not in published
        ]
        if unpublished:
            sample = ", ".join(unpublished[:5]) + (f", +{len(unpublished) - 5} more" if len(unpublished) > 5 else "")
            problems.append(f"catalog: PACK.md offers {len(unpublished)} unpublished skill(s) ({sample}). "
                            "Run: python3 packages.py kit-starter-pack")
    for agent in pack.agents:
        root = agent_global_dir(agent)
        missing_core = [n for n in sources if not (root / n / "SKILL.md").is_file()]
        if missing_core:
            problems.append(f"{agent}: missing core skill(s) in {root}: {', '.join(missing_core)}. "
                            "Run: python3 packages.py dev-sync --local-only")
        if catalog:
            if agent == "claude-code" and shutil.which("claude"):
                installed = HOME / ".claude/plugins/installed_plugins.json"
                try:
                    plugins = set(json.loads(installed.read_text()).get("plugins", {}))
                except (FileNotFoundError, ValueError):
                    plugins = set()
                want = {f"{p['name']}@{MARKET_NAME}" for p in plugins_meta} - disabled_plugins()
                missing_p = sorted(want - plugins)
                if missing_p:
                    problems.append(f"claude-code: missing @kit plugins: {', '.join(missing_p)}. "
                                    "Run: python3 packages.py kit-starter-pack")
                cat_note = f"{len(want) - len(missing_p)}/{len(want)} plugins"
            elif agent == "codex" and shutil.which("codex"):
                import tomllib

                cfg = Path(os.environ.get("CODEX_HOME") or HOME / ".codex") / "config.toml"
                try:
                    data = tomllib.loads(cfg.read_text()) if cfg.is_file() else {}
                except ValueError:
                    data = {}
                enabled = {k for k, v in data.get("plugins", {}).items()
                           if v.get("enabled") is True and k.endswith("@" + MARKET_NAME)}
                want = {f"{p['name']}@{MARKET_NAME}" for p in plugins_meta}
                missing_p = sorted(want - enabled)
                if missing_p:
                    problems.append(f"codex: missing @kit plugins in {cfg}: {', '.join(missing_p)}. "
                                    "Run: python3 packages.py kit-starter-pack")
                codex_cache = Path(os.environ.get("CODEX_HOME") or HOME / ".codex") / "plugins/cache" / MARKET_NAME
                leaked_codex = [
                    p for p in codex_cache.glob("*/*/skills/*/agents/openai.yaml")
                    if not re.search(r"^\s*allow_implicit_invocation:\s*false\s*$",
                                     p.read_text(errors="ignore"), re.MULTILINE)
                ] if codex_cache.is_dir() else []
                if leaked_codex:
                    problems.append(f"codex: {len(leaked_codex)} cached @kit skills are not explicit-only "
                                    "(allow_implicit_invocation: false). Run: python3 packages.py kit-starter-pack")
                cat_note = f"{len(want) - len(missing_p)}/{len(want)} plugins"
            else:
                missing_c = [n for n in catalog if not (root / n / "SKILL.md").is_file()]
                if missing_c:
                    problems.append(f"{agent}: missing {len(missing_c)}/{len(catalog)} catalog aliases in {root}. "
                                    "Run: python3 packages.py portable")
                leaked_c = [
                    n for n in catalog
                    if (root / n / "SKILL.md").is_file()
                    and not re.search(r"^disable-model-invocation:\s*true\s*$",
                                      (root / n / "SKILL.md").read_text(errors="ignore"), re.MULTILINE)
                ]
                if leaked_c:
                    problems.append(f"{agent}: {len(leaked_c)}/{len(catalog)} catalog aliases in {root} are not "
                                    "explicit-only (disable-model-invocation: true). Run: python3 packages.py portable")
                cat_note = f"{len(catalog) - len(missing_c)}/{len(catalog)} aliases"
        else:
            cat_note = "catalog not indexed"
        summary.append(f"{agent}={len(sources) - len(missing_core)}/{len(sources)} core, {cat_note}")
    return problems, summary


def verify(pack, strict_projection=False):
    problems = [p for s in scopes() for p in s.drift(pack) + s.stamps(pack, False)] + twice()
    budget_problems, count, listing = budget(pack)
    cov_problems, cov_summary = agent_coverage(pack)
    gate(problems + budget_problems + cov_problems + source_drift() + (tool_drift(pack) if INDEX.exists() else []))
    if strict_projection:
        gate(claude_projection(), "Plugin projections are estimates. Measure startup context separately.")
    print(f"ok: skills CLI locks contain {count} skills and {listing} description bytes")
    print("ok: agents: " + "; ".join(cov_summary))
    idle = unused_plugins()
    if idle:
        print(f"hint: {len(idle)} enabled plugin(s) never used: {', '.join(idle)}. Ask the owner, then: python3 packages.py prune <plugin>...")
    if not INDEX.exists():
        print("first run: the catalog is not indexed. Index every skill, loading none: "
              "python3 packages.py kit-starter-pack")
    return 0


def remove(names, is_global, dry):
    scope = Scope(is_global)
    lock = scope.locked()
    gate([f"{n}: not installed in {scope.name}" for n in names if n not in lock] or
         ([] if names else ["name the skills to remove"]))
    cmd = CLI + ["remove", *(["-g"] if is_global else []), "-y", "--skill", *names]
    print("$ " + shlex.join(cmd))
    if dry:
        return 0
    gate([f"remove failed: {shlex.join(cmd)}"] if run(cmd, cwd=scope.root).returncode else [])
    gate([f"still installed: {n}" for n in names if n in scope.locked()])
    print(f"ok: removed {len(names)} from {scope.name}")
    return 0


def add_row(pack, rest):
    url = re.match(r"(?:https?://)?(?:www\.)?github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?(?:[/#?].*)?$", rest[0]) if rest else None
    repo = url.group(1) if url else (rest[0] if rest else "")
    if not REPO.fullmatch(repo) or (rest[1:] and rest[1] not in ("-s", "--skill")):
        sys.exit("usage: packages.py add <owner/repo or any github.com URL> [--skill a b]. "
                 "Not on GitHub, or an MCP server? Add it to PACK.md # MCP servers as `1. name url-or-command`.")
    names = rest[2:]
    gate([f"already in the catalog: {repo}"] if pack.repo(repo) else [])
    lines = pack.text.splitlines()
    start = lines.index("# Batteries included")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("# ")), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    is_table = any(l.lstrip().startswith("|") for l in lines[start:end])
    row = (f"| [{repo}](https://github.com/{repo}) | {', '.join(names) if names else 'all'} | |"
           if is_table else f"* [{repo}](https://github.com/{repo})" + (": " + ", ".join(names) if names else ""))
    lines.insert(end, row)
    new = Pack("\n".join(lines) + "\n")
    index(new, [repo])  # gates: resolves, clones, offers only skills it has
    PACK.write_text(new.text)
    print(f"catalog row added: {row}")
    return 0


def read_settings():
    try:
        return json.loads(SETTINGS.read_text())
    except FileNotFoundError:
        return {}
    except ValueError:
        gate([f"{SETTINGS} is not valid JSON; kit will not edit it"])


def tool_drift(pack):
    deny = read_settings().get("permissions", {}).get("deny", [])
    return [f"PACK.md removes {r} from sessions, but {SETTINGS} does not deny it. Run: python3 packages.py tools"
            for r in pack.tools if r not in deny]


def tools(pack, dry):
    """Write PACK.md `# Tools` as bare-name deny rules, which leave those tools out of every Claude Code
    session's context: https://code.claude.com/docs/en/permissions. Rules you wrote are never touched."""
    settings = read_settings()
    deny = settings.get("permissions", {}).get("deny", [])
    try:
        mine = set(json.loads(TOOLS_OWNED.read_text()))
    except (FileNotFoundError, ValueError):
        mine = set()
    added = [r for r in pack.tools if r not in deny]
    new = [r for r in deny if r not in mine or r in pack.tools] + added
    print(f"tools: {len(pack.tools)} left out of every session; {len(added)} new, {len(deny) + len(added) - len(new)} given back")
    if dry:
        return 0
    CACHE.mkdir(parents=True, exist_ok=True)
    if new != deny:
        if SETTINGS.exists():
            shutil.copy2(SETTINGS, CACHE / f"settings-{time.strftime('%Y%m%d-%H%M%S')}.json")
        settings.setdefault("permissions", {})["deny"] = new
        SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")
    TOOLS_OWNED.write_text(json.dumps(sorted((mine & set(pack.tools)) | set(added))))
    gate(tool_drift(pack))
    return 0


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def explicit_policy(path, implicit=False):
    flag = "true" if implicit else "false"
    yaml = path.read_text() if path.exists() else ""
    block = re.search(r"^policy:[ \t]*(?:#[^\n]*)?\n(?:[ \t]+[^\n]*\n?)*", yaml, re.MULTILINE)
    if block:
        text = block[0].rstrip("\n")
        key = r"^([ \t]+)allow_implicit_invocation:.*$"
        if re.search(key, text, re.MULTILINE):
            text = re.sub(key, r"\1allow_implicit_invocation: " + flag, text, flags=re.MULTILINE)
        else:
            indent = re.search(r"^[ \t]+(?=\w)", text, re.MULTILINE)
            text += "\n" + (indent[0] if indent else "  ") + "allow_implicit_invocation: " + flag
        yaml = yaml[:block.start()] + text + "\n" + yaml[block.end():]
    else:
        gate([f"{path}: expected a block-style policy"] if re.search(r"^policy:", yaml, re.MULTILINE) else [])
        yaml = (yaml.rstrip("\n") + "\n" if yaml else "") + f"policy:\n  allow_implicit_invocation: {flag}\n"
    path.write_text(yaml)


def write_skill(d, src, publisher, repo):
    """Package a skill with explicit-only invocation policies for both plugin hosts.
    Claude Code: `disable-model-invocation: true` keeps /publisher:skill at ~0 startup tokens.
    Codex: agents/openai.yaml `policy.allow_implicit_invocation: false` keeps $publisher:skill at 0 startup tokens."""
    lines = src.read_text(errors="ignore").split("\n")
    if "---" not in lines[1:]:
        return False
    end = lines.index("---", 1)
    fm = [x for x in lines[1:end] if not x.startswith("disable-model-invocation:")]
    d.mkdir(parents=True)
    for item in src.parent.iterdir():
        if item.name in ("SKILL.md", ".git"):
            continue
        # Both plugin caches discard symlinks into the external source checkout.
        if item.is_dir():
            shutil.copytree(item, d / item.name, symlinks=True)
        else:
            shutil.copy2(item, d / item.name, follow_symlinks=False)
    agents = d / "agents"
    agents.mkdir(exist_ok=True)
    policy = agents / "openai.yaml"
    gate([f"{policy}: expected a regular file"] if policy.is_symlink() else [])
    explicit_policy(policy, implicit=False)
    skill = d / "SKILL.md"
    skill.write_text("\n".join(["---", "disable-model-invocation: true", *fm, *lines[end:]]))
    stamp(skill, {"publisher": publisher, "source": repo, "source-url": f"https://github.com/{repo}"}, True)
    return True


def build_market(pack, offered):
    """One plugin per publisher, so every skill is /publisher:skill in Claude Code and $publisher:skill in Codex."""
    if MARKET.exists():
        shutil.rmtree(MARKET)
    plugins = []
    for repo, skills in sorted(offered.items()):
        publisher = pack.publisher[repo.lower()]
        name, paths = slug(publisher), discover_paths(CACHE / repo.replace("/", "@"))
        base = MARKET / "plugins" / name
        made = sum(write_skill(base / "skills" / n, paths[n], publisher, repo) for n in sorted(skills) if n in paths)
        if not made:
            continue
        meta = {"name": name, "version": "1.0.0",
                "description": f"{made} explicit-only {publisher} skills from github.com/{repo}.",
                "author": {"name": publisher}, "repository": f"https://github.com/{repo}"}
        (base / ".claude-plugin").mkdir(parents=True)
        (base / ".claude-plugin/plugin.json").write_text(json.dumps(meta, indent=2))
        (base / ".codex-plugin").mkdir()
        (base / ".codex-plugin/plugin.json").write_text(json.dumps({**meta, "skills": "./skills"}, indent=2))
        plugins.append({"name": name, "source": f"./plugins/{name}", "description": meta["description"], "_count": made})
    (MARKET / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (MARKET / ".claude-plugin/marketplace.json").write_text(json.dumps(
        {"name": MARKET_NAME, "owner": {"name": "kit"}, "description": "The kit catalog, one plugin per publisher.",
         "plugins": [{k: v for k, v in p.items() if k != "_count"} for p in plugins]}, indent=2))
    return plugins


def portable():
    """Publish explicit aliases in the shared skill root and one Antigravity router."""
    manifest = MARKET / ".claude-plugin/marketplace.json"
    gate([f"{manifest} is missing. Run kit-starter-pack first."] if not manifest.is_file() else [])
    shared = HOME / ".agents/skills"
    commands = {}
    for plugin in json.loads(manifest.read_text())["plugins"]:
        publisher = plugin["name"]
        for skill in sorted((MARKET / plugin["source"] / "skills").glob("*/SKILL.md")):
            name = f"{publisher}-{skill.parent.name}"
            gate([f"{name}: duplicate or invalid portable command name"]
                 if name in commands or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64 else [])
            path = skill.relative_to(HOME)
            commands[name] = (
                f"Open `~/{path}` and follow that skill for the user's request. "
                "Resolve its relative paths from that skill's directory."
            )

    router = HOME / ".gemini/config/skills/kit"
    install = {shared / name: (body, True) for name, body in commands.items()}
    if not (router.is_symlink() and router.resolve() == (shared / "kit").resolve()):
        install[router] = (
            "Open `~/.agents/skills/kit/SKILL.md` and follow its command table. "
            "Run `packages.py` from that skill's directory using its absolute path.",
            False,
        )
    marker = "kit-portable-v1\n"

    def owned(folder):
        stamp = folder / ".kit-stub"
        return not folder.is_symlink() and stamp.is_file() and stamp.read_text() == marker

    gate([f"{folder}: another skill already owns this path"
          for folder in install if (folder.exists() or folder.is_symlink()) and not owned(folder)])
    for folder, (body, explicit) in install.items():
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".kit-stub").write_text(marker)
        (folder / "SKILL.md").write_text(
            f"---\nname: {folder.name}\ndescription: Open the Kit skill {folder.name}.\n"
            + ("disable-model-invocation: true\n" if explicit else "")
            + f"---\n\n{body}\n"
        )
        agents = folder / "agents"
        agents.mkdir(exist_ok=True)
        explicit_policy(agents / "openai.yaml", implicit=not explicit)
    for folder in shared.iterdir():
        if folder not in install and owned(folder):
            shutil.rmtree(folder)
    for mirror in (HOME / ".cursor/skills", HOME / ".gemini/config/skills"):
        mirror.mkdir(parents=True, exist_ok=True)
        mirror_links = {mirror / name: shared / name for name in commands}
        gate([f"{link}: another skill already owns this path"
              for link, target in mirror_links.items()
              if (link.exists() or link.is_symlink())
              and not (link.is_symlink() and link.resolve() == target.resolve())])
        for link, target in mirror_links.items():
            if not link.is_symlink():
                link.symlink_to(target, target_is_directory=True)
        for entry in list(mirror.iterdir()):
            if entry.is_symlink() and entry not in mirror_links:
                target = Path(os.readlink(entry))
                if not target.is_absolute():
                    target = entry.parent / target
                if target.parent == shared and (not entry.exists() or owned(target)):
                    entry.unlink()
    print(f"shared: {len(commands)} catalog aliases synced to ~/.agents/skills, ~/.cursor/skills, and ~/.gemini/config/skills")
    dedupe_codex()


def dedupe_codex():
    """Hide only Kit's shared shortcuts that have an enabled native Codex equivalent."""
    if not shutil.which("codex"):
        return
    import tomllib

    config = Path(os.environ.get("CODEX_HOME") or HOME / ".codex") / "config.toml"
    if not config.is_file():
        return
    original = config.read_text()
    start, end = "# BEGIN kit portable duplicates", "# END kit portable duplicates"
    managed = re.compile(rf"(?m)^{re.escape(start)}\n.*?^{re.escape(end)}\n?", re.DOTALL)
    base, blocks = managed.subn("", original)
    gate([f"{config}: invalid Kit block; no settings were changed"]
         if blocks > 1 or start in base or end in base else [])
    settings = tomllib.loads(base)
    manual = {Path(item["path"]).expanduser() for item in settings.get("skills", {}).get("config", [])
              if "path" in item}
    market = settings.get("marketplaces", {}).get(MARKET_NAME, {})
    duplicates = set()
    if market.get("source") == str(MARKET) and market.get("source_type") == "local":
        for key, plugin in settings.get("plugins", {}).items():
            publisher, _, marketplace = key.partition("@")
            if marketplace != MARKET_NAME or publisher != slug(publisher) or plugin.get("enabled") is not True:
                continue
            for skill in (MARKET / "plugins" / publisher / "skills").glob("*/SKILL.md"):
                folder = HOME / ".agents/skills" / f"{publisher}-{skill.parent.name}"
                marker, shortcut = folder / ".kit-stub", folder / "SKILL.md"
                if (not folder.is_symlink() and marker.is_file() and marker.read_text() == "kit-portable-v1\n"
                        and shortcut.is_file() and shortcut not in manual
                        and f"`~/{skill.relative_to(HOME)}`" in shortcut.read_text()):
                    duplicates.add(shortcut)
    block = "".join(f"[[skills.config]]\npath = {json.dumps(str(path), ensure_ascii=False)}\nenabled = false\n\n"
                    for path in sorted(duplicates))
    updated = base
    if block:
        updated += ("" if not base or base.endswith("\n\n") else "\n" if base.endswith("\n") else "\n\n")
        updated += f"{start}\n{block}{end}\n"
    if updated != original:
        tomllib.loads(updated)
        with tempfile.NamedTemporaryFile(mode="w", dir=config.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            try:
                tmp.write(updated)
                tmp.close()
                gate([f"{config} changed during refresh; retry"] if config.read_text() != original else [])
                temp_path.replace(config)
            finally:
                temp_path.unlink(missing_ok=True)
    print(f"Codex: hid {len(duplicates)} duplicate Kit shortcuts")


def publish(pack, offered):
    """Install the marketplace into every agent with a plugin CLI. A missing CLI is skipped, a failed command fails."""
    for old in SLASH.glob("*/.kit-stub"):  # stubs from the earlier layout would list each skill twice
        shutil.rmtree(old.parent)
    plugins = build_market(pack, offered)
    agents = [("claude", ["plugin", "marketplace", "remove", MARKET_NAME], ["plugin", "marketplace", "add", str(MARKET)],
               ["plugin", "uninstall"], ["plugin", "install"]),
              ("codex", ["plugin", "marketplace", "remove", MARKET_NAME], ["plugin", "marketplace", "add", str(MARKET)],
               ["plugin", "remove"], ["plugin", "add"])]
    off = disabled_plugins()  # the owner turned these off (doctor, /plugin, prune): a refresh must not turn them back on
    done = []
    for cli, remove_market, add_market, uninstall, install_cmd in agents:
        if not shutil.which(cli):
            print(f"skipped {cli}: not on PATH")
            continue
        for p in plugins:
            run([cli, *uninstall, f"{p['name']}@{MARKET_NAME}"], capture_output=True)
        run([cli, *remove_market], capture_output=True)
        keep = [p for p in plugins if cli != "claude" or f"{p['name']}@{MARKET_NAME}" not in off]
        steps = [[cli, *add_market]] + [[cli, *install_cmd, f"{p['name']}@{MARKET_NAME}"] for p in keep]
        for step in steps:
            res = run(step, capture_output=True, text=True)
            if res.returncode:
                gate([f"{shlex.join(step)} failed: {(res.stderr or res.stdout).strip().splitlines()[-1:]}"])
        done.append(cli)
    total = sum(p["_count"] for p in plugins)
    print(f"plugins: {len(plugins)} publishers, {total} skills, installed into {', '.join(done) or 'no agent'}"
          + (f"; left off in Claude Code: {', '.join(sorted(off))}" if off else ""))
    portable()
    return plugins


def domain(pack, names, dry, *, root=None):
    """Add a domain's MCP servers to this project, for Claude Code (.mcp.json) and Codex (.codex/config.toml),
    and list its skills. The project configuration scopes the servers to this project."""
    gate([f"{n}: not a domain. Domains: {', '.join(pack.domains)}" for n in names if n.lower() not in pack.domains]
         or ([] if names else [f"name a domain: {', '.join(pack.domains)}"]))
    items = [i for n in names for i in pack.domains[n.lower()]]
    servers = list(dict.fromkeys(i[4:] for i in items if i.startswith("mcp:")))
    gate([f"mcp:{s} is not under PACK.md # MCP servers" for s in servers if s not in pack.mcp])
    if dry and not INDEX.exists():
        print("would list domain skills after indexing the catalog")
        skills = {}
    else:
        skills = resolve(pack, [i for i in items if not i.startswith("mcp:")], offline=True)
    root = root if root is not None else Scope(False).root
    toml = root / ".codex/config.toml"
    for s in servers:
        spec = pack.mcp[s]
        is_url = spec.startswith(("http://", "https://"))
        claude = ["claude", "mcp", "add", "-s", "project", s] + (["--transport", "http", spec] if is_url else ["--", *shlex.split(spec)])
        print("$ " + shlex.join(claude))
        section = f"[mcp_servers.{s}]\n" + (f"url = {json.dumps(spec)}\n" if is_url else
                  f"command = {json.dumps(shlex.split(spec)[0])}\nargs = {json.dumps(shlex.split(spec)[1:])}\n")
        if dry:
            continue
        if shutil.which("claude"):
            run(["claude", "mcp", "remove", "-s", "project", s], capture_output=True, cwd=root)
            res = run(claude, capture_output=True, text=True, cwd=root)
            gate([f"claude mcp add {s} failed: {(res.stderr or res.stdout).strip()[-200:]}"] if res.returncode else [])
        old = toml.read_text() if toml.exists() else ""
        if f"[mcp_servers.{s}]" not in old:
            toml.parent.mkdir(exist_ok=True)
            toml.write_text(old + ("\n" if old and not old.endswith("\n") else "") + section)
    if not dry and servers:
        mcp_config = root / ".mcp.json"
        mcp_json = json.loads(mcp_config.read_text()).get("mcpServers", {}) if mcp_config.exists() else {}
        gate([f"{s}: not in {mcp_config} after install" for s in servers
              if shutil.which("claude") and s not in mcp_json] +
             [f"{s}: not in {toml}" for s in servers if f"[mcp_servers.{s}]" not in toml.read_text()])
        print(f"ok: {len(servers)} MCP server(s) for this project: {', '.join(servers)}")
    for name, (repo, _) in skills.items():
        print(f"  /{slug(pack.publisher[repo.lower()])}:{name}")
    return 0


def mcp_starts(spec, timeout=60, *, cwd=None):
    """'' if the stdio server answers an MCP initialize, else the reason (last stderr line)."""
    hello = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "kit", "version": "1"}}}) + "\n"
    argv = [spec["command"], *spec.get("args", [])]
    try:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             cwd=cwd, env={**os.environ, **spec.get("env", {})})
    except OSError as e:
        return str(e)
    try:
        out, err = p.communicate(hello, timeout=timeout)
    except subprocess.TimeoutExpired:  # still serving after stdin closed is fine only if it answered
        p.kill()
        out, err = p.communicate()
    if '"id":1' in out.replace(" ", "") and '"result"' in out:
        return ""
    return (err.strip().splitlines() or ["no initialize reply"])[-1][:300]


def bigbang(pack, names, dry):
    """One command per checkout: catalog, domains, the project's stage 0, then proof that its MCP servers start."""
    names = names or ["core"]
    gate([f"{n}: not a domain. Domains: {', '.join(pack.domains)}" for n in names if n.lower() not in pack.domains])
    top = run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = Path(top.stdout.strip()) if top.returncode == 0 else Path.cwd()
    if top.returncode:
        gate([f"could not open existing Git repository: {top.stderr.strip()}"]
             if any((p / ".git").exists() or (p / ".git").is_symlink() for p in (root, *root.parents)) else [])
        if dry:
            print(f"would initialize Git in {root}")
        else:
            result = run(["git", "init", "--quiet"], cwd=root, capture_output=True, text=True)
            gate([f"could not initialize Git in {root}: {result.stderr.strip()}"] if result.returncode else [])
            print(f"ok: initialized Git in {root}")
    if not INDEX.exists():
        main(["kit-starter-pack"] + (["--dry-run"] if dry else []))
    domain(pack, names, dry, root=root)
    mise = next((root / n for n in ("mise.toml", ".mise.toml") if (root / n).is_file()), None)
    if mise:
        import tomllib
        cmd = ["mise", "run", "stage0"] if "stage0" in tomllib.loads(mise.read_text()).get("tasks", {}) else ["mise", "install"]
        print("$ " + shlex.join(cmd))
        if not dry:
            gate([] if shutil.which("mise") else ["mise not found; kit does not install runtimes"])
            gate([f"{shlex.join(cmd)} failed"] if run(cmd, cwd=root).returncode else [])
    if dry:
        print("would check configured stdio MCP servers and run Kit verification")
        return 0
    config = root / ".mcp.json"
    servers = json.loads(config.read_text()).get("mcpServers", {}) if config.exists() else {}
    stdio = {n: s for n, s in servers.items() if s.get("command")}
    gate([f"MCP {n} does not start: {why}" for n, s in stdio.items() if (why := mcp_starts(s, cwd=root))])
    print(f"ok: {len(stdio)} stdio MCP server(s) start: {', '.join(stdio) or 'none'}")
    return verify(pack)


def skill_tags(pack, offered):
    """Return {(repo, skill): set(tags)} across all offered catalog skills."""
    by_skill = {(repo, name): set(pack.repo_tags.get(repo.lower(), ()))
                for repo, skills in offered.items() for name in skills}
    aliases = {slug(p): pack.repo(r) for r, p in pack.publisher.items()}
    for d, items in pack.domains.items():
        dtags = set(pack.domain_tags.get(d, ())) | ({d} if d in pack.tags else set())
        for item in items:
            if item.startswith("mcp:"):
                continue
            repo_part, _, name = item.partition(":")
            repo = (pack.repo(repo_part) or aliases.get(repo_part.lower())) if name else pack.repo(repo_part)
            if repo and name and (repo, name) in by_skill:
                by_skill[(repo, name)] |= dtags
            elif repo:
                for n in offered.get(repo, ()):
                    by_skill[(repo, n)] |= dtags
            else:
                for r in offered:
                    if item in offered[r]:
                        by_skill[(r, item)] |= dtags
    return by_skill


def filter_tags(pack, tokens):
    """List declared tags or filter catalog skills by one or more tags (AND)."""
    gate(["PACK.md has no tags under `# Tags`"] if not pack.tags else [])
    want = [t.lstrip("#").lower() for t in tokens]
    gate([f"{t}: not a tag. Tags: {', '.join(pack.tags)}" for t in want if t not in pack.tags])
    offered = index(pack, sorted(r for r, _ in pack.rows.values()), offline=True)
    tagged = skill_tags(pack, offered)
    if not want:
        print(f"tags ({len(pack.tags)}):")
        for t in pack.tags:
            count = sum(1 for ts in tagged.values() if t in ts)
            doms = [d for d in pack.domains if t in pack.domain_tags.get(d, ()) or d == t]
            suffix = f"  domains: {', '.join(doms)}" if doms else ""
            print(f"  {t} ({count}){suffix}")
        return 0
    want_set = set(want)
    hits = sorted((slug(pack.publisher[r.lower()]), n, sorted(ts))
                  for (r, n), ts in tagged.items() if want_set <= ts)
    doms = [d for d in pack.domains if want_set <= (pack.domain_tags.get(d, set()) | {d})]
    if doms:
        print(f"domains: {', '.join(doms)}")
    label = ", ".join(want)
    if not hits:
        print(f"no skills match: {label}")
        return 0
    print(f"skills ({len(hits)}) for {label}:")
    for pub, name, ts in hits:
        print(f"  /{pub}:{name}  [{', '.join(ts)}]")
    return 0


def use(pack, tokens):
    """Print a catalog skill from the cache: it enters the context only now, when called."""
    gate([] if tokens else ["name a skill: packages.py use <skill>"])
    if pack.tags and all(t.lstrip("#").lower() in pack.tags for t in tokens):
        offered = index(pack, sorted(r for r, _ in pack.rows.values()), offline=True)
        if not any(t.lower() in pack.domains or pack.repo(t) or any(t in s for s in offered.values()) for t in tokens):
            return filter_tags(pack, tokens)
    for name, (repo, _) in resolve(pack, tokens, offline=True).items():
        root = CACHE / repo.replace("/", "@")
        skill = discover_paths(root).get(name)
        gate([] if skill else [f"{name}: not in {root}. Run: python3 packages.py kit-starter-pack"])
        print(f'<skill name="{name}" publisher="{pack.publisher[repo.lower()]}" source="{repo}" dir="{skill.parent}">')
        print(skill.read_text().rstrip())
        print("</skill>")
    return 0


def export(pack, names, is_global):
    """Zip stamped skills for ChatGPT web, which only takes uploads. Modes are normalized to 644/755."""
    scope = Scope(is_global)
    gate([f"{n}: not installed in {scope.name}" for n in names if n not in scope.locked()] or
         ([] if names else ["name the skills to export"]))
    gate(scope.stamps(pack, False))
    for n in names:
        out = Path.cwd() / f"{n}.zip"
        with zipfile.ZipFile(out, "w") as z:
            for f in sorted((scope.store / n).rglob("*")):
                if f.is_file() and not f.is_symlink():
                    info = zipfile.ZipInfo(f"{n}/{f.relative_to(scope.store / n).as_posix()}", (2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = (0o755 if os.access(f, os.X_OK) else 0o644) << 16
                    z.writestr(info, f.read_bytes())
        print(f"wrote {out}. Upload: ChatGPT > Skills > Create > Upload from your computer")
    return 0


def dev_sync(args, dry):
    flags = set(args)
    gate(["usage: packages.py dev-sync [--allow-main] [--local-only] [--dry-run]"]
         if flags - {"--allow-main", "--local-only"} or len(flags) != len(args) else [])
    local_only = "--local-only" in flags
    skills = Path(__file__).resolve().parent.parent
    git = ["git", "-C", str(skills.parent)]
    top = run([*git, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    gate(["dev-sync must run from the source checkout"]
         if top.returncode or Path(top.stdout.strip()).resolve() != skills.parent else [])
    branch = run([*git, "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    gate(["dev-sync requires dev, or main with --allow-main"]
         if branch != "dev" and not (branch == "main" and "--allow-main" in flags) else [])

    shared = HOME / ".agents/skills"
    extra_roots = [HOME / ".claude/skills", HOME / ".cursor/skills", HOME / ".gemini/config/skills"]
    links = {}
    sources = repository_skills()
    gate(["no first-party skill packages found"] if not sources else [])
    for name, source in sources.items():
        links[shared / name] = source
        for root in extra_roots:
            links[root / name] = shared / name
    marker = "kit-portable-v1\n"

    def stub(folder):
        stamp = folder / ".kit-stub"
        return not folder.is_symlink() and stamp.is_file() and stamp.read_text() == marker

    gate([f"{link}: existing skill is not linked to {target}"
          for link, target in links.items() if (link.exists() or link.is_symlink())
          and not stub(link)
          and not (link.is_symlink() and link.resolve() == target.resolve())])
    if dry:
        if not local_only:
            print(f"would push committed {branch} to origin/{branch}")
        print(f"would link {', '.join(sources)} and refresh the Kit catalog")
        return 0

    if not local_only:
        status = run([*git, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True)
        new_skill_files = run([*git, "ls-files", "--others", "--exclude-standard", "--",
                               *(str(p.relative_to(skills.parent)) for p in sources.values())],
                              capture_output=True, text=True)
        gate(["commit tracked changes and new files in skill packages, or use --local-only"]
             if status.returncode or new_skill_files.returncode or status.stdout or new_skill_files.stdout else [])
        commit = run([*git, "rev-parse", "--verify", "HEAD"], capture_output=True, text=True)
        gate(["could not resolve the current commit"] if commit.returncode else [])
        push = run([*git, "push", "--no-follow-tags", "origin", f"{commit.stdout.strip()}:refs/heads/{branch}"])
        gate([f"push to origin/{branch} failed; use --local-only to update this machine"] if push.returncode else [])
        print(f"ok: pushed origin/{branch}", flush=True)
    for root in (shared, *extra_roots):
        if root.is_dir():
            for entry in sorted(root.iterdir()):
                if entry.is_symlink() and not entry.exists():
                    entry.unlink()
    for link, target in links.items():
        if stub(link):
            shutil.rmtree(link)
        if not link.is_symlink():
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target, target_is_directory=True)
    print(f"ok: linked {len(sources)} local skills: {', '.join(sources)}", flush=True)
    return main(["kit-starter-pack"])


def main(argv):
    dry, is_global = "--dry-run" in argv, "-g" in argv or "--global" in argv
    argv = [a for a in argv if a not in ("--dry-run", "-g", "--global")]
    gate([f"{t} not found; kit does not install runtimes" for t in ("npx", "git") if not shutil.which(t)])
    pack = Pack(PACK.read_text())
    if not argv or argv in (["verify"], ["verify", "--strict-projection"]):
        return verify(pack, strict_projection="--strict-projection" in argv)
    verb, rest = argv[0], argv[1:]
    if verb == "dev-sync":
        return dev_sync(rest, dry)
    if verb == "kit-starter-pack":
        repos = [r for r, _ in pack.rows.values()]
        if dry:
            print(f"would index {len(repos)} sources, publish explicit-only plugins, and apply {len(pack.tools)} Claude tool rules")
            return 0
        offered = index(pack, repos)
        plugins = publish(pack, offered)
        tools(pack, False)
        print(f"ok: packaged {sum(p['_count'] for p in plugins)} explicit-only skills from {len(repos)} sources. "
              "Use /<publisher>:<skill> in Claude Code, $<publisher>:<skill> in Codex, "
              "or kit <publisher>:<skill> to read it from the local catalog.")
        return 0
    if verb == "domain":
        return domain(pack, rest, dry)
    if verb == "bigbang":
        return bigbang(pack, rest, dry)
    if argv == ["portable"]:
        if dry:
            print("would refresh shared skill commands and the Antigravity router")
        else:
            portable()
        return 0
    if verb == "use":
        return use(pack, rest)
    if verb in ("tag", "tags"):
        return filter_tags(pack, rest)
    if verb == "prune":
        return prune(dry, rest)
    if verb == "tools":
        return tools(pack, dry)
    if verb == "stamp":
        gate([p for s in scopes() for p in s.stamps(pack, True)])
        print("ok: every installed skill carries its publisher")
        return 0
    if verb == "export":
        return export(pack, rest, is_global)
    if verb == "add":
        return add_row(pack, rest)
    if verb in ("remove", "rm"):
        return remove(rest, is_global, dry)
    if verb in ("list", "ls"):
        return subprocess.call(CLI + ["list", *(["-g"] if is_global else []), *rest], env=ENV)
    return install(pack, argv, is_global, dry)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
