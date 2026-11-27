"""burndown: ticket states computed from tagged tests and evidence on base, never from a Status line or a tracker."""
import hashlib
import json
import re
import time
from pathlib import Path

from base import (DECISION_PATTERN, REQ_PATTERN, STATE, WORKTREE, Fail, Module, append_jsonl, branch_sha, fill,
                  git, id_forms, ignore_action, jsonl, load_determdinistic, sh, tail, template, worktree_at, write_new)

ROADMAP = "ROADMAP.md"
CACHE = f"{STATE}/burndown.jsonl"
IGNORED = [f"{WORKTREE}/", CACHE, f"{STATE}/sessions.jsonl", f"{STATE}/status/"]
STATUS = f"{STATE}/status"          # per-shot project status screenshots: attached to the brief, never committed
SHOTS_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4")
REQUIRED = ("entry", "visible")  # `req:` is required only with the goals layer
BARS = "▁▂▃▄▅▆▇█"
WORKING = ("open", "red", "green")  # states `next:` may pick
DEFAULT_TESTS = ["tests/**", "**/*_test.*", "**/test_*.*", "**/*.test.*", "**/*_test.go"]


def ids_pattern(rail):
    pattern = (rail.get("ids") or {}).get("pattern") if isinstance(rail.get("ids"), dict) else None
    try:
        return re.compile(pattern or r"[A-Z][A-Z0-9]*-[0-9]+")
    except re.error:
        return re.compile(r"[A-Z][A-Z0-9]*-[0-9]+")


class Roadmap:
    """ROADMAP.md read through determdinistic's ticket index: the epic, its steps, the goals, and many-to-many links."""

    def __init__(self, text, rail):
        self.text, self.pattern = text, ids_pattern(rail)
        dm = load_determdinistic()
        self.index = dm.tickets(text, [self.pattern, re.compile(REQ_PATTERN), re.compile(DECISION_PATTERN)], ROADMAP)
        tickets = self.index["tickets"]
        self.epic = next((t for t in tickets if t["kind"] == "heading" and t["label"].lower() == "epic"
                          and self.pattern.fullmatch(t["id"])), None)
        epic_title = None
        if self.epic:
            heading = dm.HEADING.match(self.text.splitlines()[self.epic["line"] - 1])
            epic_title = dm.heading_title(heading)

        def under(t, name):
            return bool(t["heading"]) and t["heading"][-1] == name

        self.steps = [t for t in tickets if t["kind"] == "item" and epic_title and under(t, epic_title)
                      and self.pattern.fullmatch(t["id"])]
        self.goals = [t for t in tickets if t["kind"] == "item" and under(t, "Goals")
                      and self.pattern.fullmatch(t["id"])]
        self.by_id = {t["id"]: t for t in self.steps}
        listed = [i for i in dm.ticket_ids((self.epic or {}).get("fields", {}).get("Order", ""), [self.pattern])
                  if i in self.by_id]
        self.order = listed + [t["id"] for t in self.steps if t["id"] not in listed]
        self.epic_title = epic_title
        self.links = self.index["links"]

    def fails(self, rail):
        fails = []
        if not self.epic:
            return [Fail(f"{ROADMAP} has no `## Epic: <ticket id> · <name> · benchmark: …` heading",
                         f"add the epic heading to {ROADMAP}")]
        step_lines = {t["line"] for t in self.steps} | {t["line"] for t in self.goals}
        dm = load_determdinistic()
        section = None
        for number, line in enumerate(self.text.splitlines(), 1):
            if heading := dm.HEADING.match(line):
                section = dm.heading_title(heading)
                continue
            if section in (self.epic_title, "Goals") and re.match(r"^[-+*]\s+\S+\s+·", line) and \
                    number not in step_lines:
                token = line.split()[1]
                fails.append(Fail(f"{ROADMAP}:{number}: `{token}` does not match [ids] pattern "
                                  f"`{self.pattern.pattern}`", "fix the id, or [ids] pattern in guardrail.toml"))
        for d in self.index["diagnostics"]:
            fails.append(Fail(f"{ROADMAP}:{d['line']}: {d['code'].replace('_', ' ')} {d.get('key', '')}".rstrip(),
                              "give each ticket one line and each field one value"))
        limits = rail.get("limits") or {}
        for t in self.steps:
            missing = [f for f in REQUIRED if not t["fields"].get(f)]
            if missing:
                fails.append(Fail(f"{ROADMAP}:{t['line']}: {t['id']} lacks {', '.join(missing)}",
                                  f"add `· {missing[0]}: …` to {t['id']}"))
            limit = t["fields"].get("limit")
            if limit and limit not in limits:
                fails.append(Fail(f"{ROADMAP}:{t['line']}: {t['id']} names limit `{limit}`, not under [limits]",
                                  "add it to [limits] in guardrail.toml or fix the name"))
        for g in self.goals:
            unknown = [e["to"] for e in self.links if e["from"] == g["id"] and e["field"] == "steps"
                       and e["to"] not in self.by_id]
            if unknown:
                fails.append(Fail(f"{ROADMAP}:{g['line']}: goal {g['id']} names unknown steps {', '.join(unknown)}",
                                  "name steps listed under the epic"))
        return fails


def read_roadmap(ctx):
    path = ctx.root / ROADMAP
    return Roadmap(path.read_text(), ctx.rail) if path.is_file() else None


def roadmap_hash(ctx):
    path = ctx.root / ROADMAP
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def tagged(ctx, sha, ticket):
    """True when a test file at sha carries the ticket's tag: _{tid}_, _{lid}_ or `{id}: `."""
    forms = id_forms(ticket)
    globs = (ctx.rail.get("burndown") or {}).get("tests") or DEFAULT_TESTS
    result = git(ctx.root, "grep", "-l", "-F", "-e", f"_{forms['tid']}_", "-e", f"_{forms['lid']}_",
                 "-e", f"{ticket}: ", sha, "--", *[f":(glob){g}" for g in globs])
    return result.returncode == 0 and bool(result.stdout.strip())


def receipts_conf(rail):
    conf = rail.get("receipts") if isinstance(rail.get("receipts"), dict) else {}
    return conf.get("dir", "receipts"), conf.get("required", True)


def receipt_files(ctx, sha, ticket):
    """Files committed under <receipts dir>/<ticket>/ at sha: the closing receipt (journey report, screenshots)."""
    folder, _ = receipts_conf(ctx.rail)
    listed = git(ctx.root, "ls-tree", "-r", "--name-only", sha, "--", f"{folder}/{ticket}/")
    return sorted(filter(None, listed.stdout.splitlines())) if listed.returncode == 0 else []


def compute(ctx, roadmap, sha):
    """({ticket: state}, {ticket: why}) for every step at base sha. Runs the tests in a detached worktree."""
    states, why, rail = {}, {}, ctx.rail
    folder, required = receipts_conf(rail)
    select = (rail.get("burndown") or {}).get("select", "")
    evidence = rail.get("evidence") or {}
    work = None
    for ticket in roadmap.order:
        step = roadmap.by_id[ticket]
        if step["fields"].get("parked"):
            states[ticket] = "parked"
            continue
        if not tagged(ctx, sha, ticket):
            states[ticket] = "open"
            continue
        if work is None:
            work, error = worktree_at(ctx.root, sha)
            if error:
                raise RuntimeError(f"could not check out base at {sha[:7]}: {error}")
        if sh(fill(select, ticket), work, shell=True).returncode:
            states[ticket] = "red"
            continue
        check = evidence.get(ticket)
        if check and sh(check, work, shell=True).returncode:
            states[ticket], why[ticket] = "green", f"evidence `{check}` fails"
        elif required and not receipt_files(ctx, sha, ticket):
            states[ticket], why[ticket] = "green", f"no receipt in {folder}/{ticket}/"
        elif step["fields"].get("limit"):
            states[ticket] = "blocked"
        else:
            states[ticket] = "live"
    return states, why


def base_sha(ctx):
    return branch_sha(ctx.root, ctx.rail.get("base", "dev"))


def rows(ctx):
    return jsonl(ctx.root / CACHE)


def fresh(ctx, sha):
    history = rows(ctx)
    return bool(history) and history[-1].get("sha") == sha and history[-1].get("roadmap") == roadmap_hash(ctx)


class Burndown(Module):
    name = "burndown"

    def probe(self, ctx):
        if not (ctx.root / ROADMAP).is_file():
            return [Fail(f"{ROADMAP} missing", "bigbang (writes the template)")]
        roadmap = read_roadmap(ctx)
        fails = roadmap.fails(ctx.rail)
        if fails:
            return fails
        sha = base_sha(ctx)
        if sha and not fresh(ctx, sha):
            fails.append(Fail(f"no burndown row for base {sha[:7]}", "bigbang (computes it)"))
        from base import ignore_lines
        if ignore_lines(ctx.root, IGNORED):
            fails.append(Fail("bigbang state is not ignored by git", "bigbang (adds it to .gitignore)"))
        return fails

    def apply(self, ctx):
        root = ctx.root
        actions = ignore_action(root, IGNORED)
        if not (root / ROADMAP).is_file():
            return actions + [(f"write {ROADMAP}", lambda: write_new(root / ROADMAP, template("ROADMAP.md")))]
        roadmap = read_roadmap(ctx)
        sha = base_sha(ctx)
        if roadmap.fails(ctx.rail) or not sha or fresh(ctx, sha):
            return actions

        def append():
            try:
                states, why = compute(ctx, roadmap, sha)
            except RuntimeError as error:
                ctx.out(f"burndown: {error}")
                return
            row = {"sha": sha, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "roadmap": roadmap_hash(ctx), "states": states, "why": why}
            append_jsonl(root / CACHE, row)
            export = (ctx.rail.get("ids") or {}).get("export")
            if ctx.sync and export:
                result = sh(export, root, shell=True, input=json.dumps(row))
                ctx.out(f"burndown: export exited {result.returncode}"
                        + (f": {tail(result.stderr, 2)}" if result.returncode else ""))
        actions.append((f"test {len(roadmap.steps)} ticket(s) at base {sha[:7]} and append the burndown row", append))
        return actions

    def report(self, ctx):
        roadmap = read_roadmap(ctx)
        if roadmap is None or not roadmap.epic:
            return []
        if not base_sha(ctx):
            return [f"burndown: Epic {roadmap.epic['id']} · base `{ctx.rail.get('base')}` has no commits yet"]
        return summary(ctx, roadmap, rows(ctx))


def link(ctx, ticket):
    url = (ctx.rail.get("ids") or {}).get("url")
    return f"[{ticket}]({fill(url, ticket)})" if url else ticket


def summary(ctx, roadmap, history):
    """At most 8 lines: totals, what changed since the previous base row, the graph, and next."""
    if not history:
        return []
    latest = history[-1]
    previous = next((r for r in reversed(history[:-1]) if r.get("sha") != latest.get("sha")), None)
    states = {t: latest["states"].get(t, "open") for t in roadmap.order}
    counts = {s: sum(1 for v in states.values() if v == s) for s in ("live", "green", "red", "open", "blocked",
                                                                    "parked")}
    total = len(states)
    was = ""
    if previous:
        prior = sum(1 for t in roadmap.order if previous["states"].get(t) == "live")
        was = f" (was live {prior}/{total} at {previous['sha'][:7]})"
    lines = [f"burndown: Epic {roadmap.epic['id']} · live {counts['live']}/{total}, green {counts['green']}, "
             f"red {counts['red']}, open {counts['open']}, blocked {counts['blocked']}, "
             f"parked {counts['parked']}{was}"]
    changed = []
    for t in roadmap.order:
        before = previous["states"].get(t) if previous else None
        if before != states[t]:
            changed.append((t, states[t], f"was {before} at {previous['sha'][:7]}" if before else "first seen"))
    if changed:
        lines.append("| Ticket | State | Changed |")
        lines += [f"| {link(ctx, t)} | {s} | {c} |" for t, s, c in changed[:3]]
        if len(changed) > 3:
            lines.append(f"… and {len(changed) - 3} more")
    by_sha = []
    for r in history:
        if not by_sha or by_sha[-1]["sha"] != r["sha"]:
            by_sha.append(r)
        else:
            by_sha[-1] = r
    live = [sum(1 for t in roadmap.order if r["states"].get(t) == "live") for r in by_sha[-5:]]
    bars = "".join(BARS[min(len(BARS) - 1, (n * (len(BARS) - 1)) // total)] if total else BARS[0] for n in live)
    lines.append(f"graph: live {bars} (last {len(live)} base commits)")
    pick = next((t for t in roadmap.order if states[t] in WORKING), None)
    if pick:
        f = roadmap.by_id[pick]["fields"]
        needs = (latest.get("why") or {}).get(pick)
        lines.append(f"next: {link(ctx, pick)} · {states[pick]}" + (f" ({needs})" if needs else "")
                     + f" · entry: {f.get('entry')} · visible: {f.get('visible')}")
    else:
        lines.append("next: none · push brief due")
    held = [t for t in roadmap.order if states[t] in ("blocked", "parked")]
    if held:
        lines.append("held: " + ", ".join(f"{t} ({states[t]})" for t in held))
    return lines[:8]


# Brief: what the agent posts at the end of each shot ------------------------

def status_shots(root, limit=3):
    folder = Path(root) / STATUS
    files = [p for p in folder.glob("*") if p.suffix.lower() in SHOTS_EXT] if folder.is_dir() else []
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def receipt_cell(ctx, sha, ticket):
    files = receipt_files(ctx, sha, ticket)
    journeys = [f for f in files if f.lower().endswith(".md")]
    images = [f for f in files if f.lower().endswith(SHOTS_EXT)]
    parts = [f"[journey]({j})" for j in journeys[:1]] + [f"![{Path(i).stem}]({i})" for i in images[:2]]
    return " · ".join(parts) or "—"


def brief(ctx):
    """The shot brief in Markdown: burndown, a receipt per ticket, status screenshots, next and held."""
    roadmap = read_roadmap(ctx)
    if roadmap is None or not roadmap.epic:
        return None, [f"{ROADMAP} missing or without an epic · fix: bigbang"]
    sha, history = base_sha(ctx), rows(ctx)
    if not sha:
        return None, [f"base `{ctx.rail.get('base')}` has no commits yet · fix: commit, then bigbang"]
    if not history or history[-1].get("sha") != sha:
        return None, ["no burndown row for the current base · fix: bigbang (computes it first)"]
    latest = history[-1]
    states = {t: latest["states"].get(t, "open") for t in roadmap.order}
    why = latest.get("why") or {}
    lines = [f"# Shot brief · Epic {link(ctx, roadmap.epic['id'])} · base {sha[:7]} · {latest['ts'][:10]}", ""]
    report = summary(ctx, roadmap, history)
    lines += [line for line in report if line.startswith(("burndown:", "graph:"))]
    shots = status_shots(ctx.root)
    lines += ["", "## Status"]
    lines += [f"![status]({p})" for p in shots] or [f"No status screenshot for this shot: capture the project as it "
                                                   f"stands into {STATUS}/ and run `bigbang brief` again."]
    lines += ["", "## Backlog", "", "| Ticket | State | Receipt |", "| --- | --- | --- |"]
    for ticket in roadmap.order:
        state = states[ticket] + (f" ({why[ticket]})" if ticket in why else "")
        lines.append(f"| {link(ctx, ticket)} | {state} | {receipt_cell(ctx, sha, ticket)} |")
    lines += [""] + [line for line in report if line.startswith(("next:", "held:"))]
    return "\n".join(lines) + "\n", []
