"""loop: the runbooks an agent follows, and the session ledger that keeps one CTO and one SWE."""
from datetime import datetime, timezone
from pathlib import Path

from base import STATE, Fail, Module, append_jsonl, git, git_out, ignore_action, jsonl, read_rail, template, \
    write_new

LEDGER = f"{STATE}/sessions.jsonl"
SINGLE = ("cto", "swe")  # roles that may have one live session at a time
ROLES = ("ceo", "cto", "swe")


def now():
    return datetime.now(timezone.utc)


def stamp(moment=None):
    return (moment or now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(text):
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def sessions(root, stale_hours, moment=None):
    """{name: {role, id, last, live, stale}} from the ledger rows, in order."""
    moment = moment or now()
    found = {}
    for row in jsonl(Path(root) / LEDGER):
        name, op = row.get("name"), row.get("op")
        if not name:
            continue
        if op == "start":
            found[name] = {"role": row.get("role"), "id": row.get("id"), "last": row.get("ts"), "live": True}
        elif name in found:
            found[name]["last"] = row.get("ts")
            if op in ("end", "park"):
                found[name]["live"] = False
    for entry in found.values():
        last = parse_ts(entry["last"])
        entry["stale"] = entry["live"] and (last is None or (moment - last).total_seconds() > stale_hours * 3600)
    return found


def live(root, stale_hours, moment=None):
    return {n: e for n, e in sessions(root, stale_hours, moment).items() if e["live"] and not e["stale"]}


def stale_hours(rail):
    value = (rail.get("loop") or {}).get("stale_hours", 3) if isinstance(rail.get("loop"), dict) else 3
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else 3


def doubles(root, hours, moment=None):
    by_role = {}
    for name, entry in live(root, hours, moment).items():
        by_role.setdefault(entry["role"], []).append(name)
    return {role: names for role, names in by_role.items() if role in SINGLE and len(names) > 1}


class Loop(Module):
    name = "loop"
    runbooks = ("runbooks/loop.md",)

    def probe(self, ctx):
        fails = [Fail(f"{r} missing", "bigbang (writes it from the template)")
                 for r in self.runbooks if not (ctx.root / r).is_file()]
        from base import ignore_lines
        if ignore_lines(ctx.root, [LEDGER]):
            fails.append(Fail(f"{LEDGER} is not ignored by git", "bigbang (adds it to .gitignore)"))
        return fails

    def apply(self, ctx):
        actions = [(f"write {r}", lambda r=r: write_new(ctx.root / r, template(r)))
                   for r in self.runbooks if not (ctx.root / r).is_file()]
        return actions + ignore_action(ctx.root, [LEDGER])


class Babysitter(Loop):
    name = "babysitter"
    runbooks = ("runbooks/babysitter.md",)

    def probe(self, ctx):
        fails = super().probe(ctx)
        for role, names in doubles(ctx.root, stale_hours(ctx.rail)).items():
            fails.append(Fail(f"{len(names)} live {role} sessions: {', '.join(names)}",
                              f"bigbang ledger end <name> <sha> (or park <name>) for all but one {role}"))
        return fails

    def report(self, ctx):
        running = live(ctx.root, stale_hours(ctx.rail))
        return [f"babysitter: live {', '.join(f'{n} ({e['role']})' for n, e in running.items()) or 'none'}"]


def ledger_main(cwd, args, out=print, moment=None):
    """`bigbang ledger start <role> <name> <session-id> | end <name> <sha> | park <name>`: the one ledger writer."""
    root = Path(git_out(cwd, "rev-parse", "--show-toplevel") or cwd)
    hours = stale_hours(read_rail(root))
    usage = "bigbang ledger start <role> <name> <session-id> | end <name> <sha> | park <name>"
    op, rest = (args[0], args[1:]) if args else ("", [])
    known = sessions(root, hours, moment)
    if op == "start" and len(rest) == 3:
        role, name, session = rest
        if role not in ROLES:
            out(f"FAIL: ledger: role {role} · fix: use one of {', '.join(ROLES)}")
            return 1
        if name in known and known[name]["live"] and not known[name]["stale"]:
            out(f"FAIL: ledger: {name} is already live · fix: pick a new name, or end {name}")
            return 1
        if role in SINGLE:
            busy = [n for n, e in live(root, hours, moment).items() if e["role"] == role]
            if busy:
                out(f"FAIL: ledger: {busy[0]} is the live {role} · fix: bigbang ledger end {busy[0]} <sha> "
                    f"(or park {busy[0]}) first")
                return 1
        row = {"ts": stamp(moment), "op": "start", "role": role, "name": name, "id": session}
    elif op == "end" and len(rest) == 2:
        name, sha = rest
        if name not in known:
            out(f"FAIL: ledger: no session {name} · fix: name a started session")
            return 1
        if git(root, "cat-file", "-e", f"{sha}^{{commit}}").returncode:
            out(f"FAIL: ledger: {sha} is not a commit here · fix: end {name} with the sha it delivered")
            return 1
        row = {"ts": stamp(moment), "op": "end", "name": name, "sha": sha}
    elif op == "park" and len(rest) == 1:
        if rest[0] not in known:
            out(f"FAIL: ledger: no session {rest[0]} · fix: name a started session")
            return 1
        row = {"ts": stamp(moment), "op": "park", "name": rest[0]}
    else:
        out(f"FAIL: ledger: bad arguments · fix: {usage}")
        return 1
    append_jsonl(root / LEDGER, row)
    out(f"ok: ledger: {op} {row['name']}")
    return 0
