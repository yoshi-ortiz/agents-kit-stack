"""tanks: token spend per agent on the full case suite, graded on end state, kept or reverted by a computed verdict.

Ported from homelab-infra cpu/platform/eval/agent-shot (run.py, grade.py, fixture.py). Paid tanks run only with
--paid; every other run costs $0 (the oracle).
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from base import Fail, Module, git, git_out, sh, tail

CASES = "tanks/cases.json"
CARD = "tanks/card.json"
LEDGER = "TANKS.md"
HERE = Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures"
CASE_KEYS = ("id", "fixture", "prompt", "grade", "oracle")
QUOTA = re.compile(r"(hit your (weekly|session|5-hour|usage) limit|usage limit|rate limit|out of extra usage|"
                   r"limit · resets)", re.I)
KEEP_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "USER", "SHELL", "TERM")
LEDGER_HEADER = ("| Date | Change | Tank | Pass before → after | Tokens/pass before → after (± spread) | Verdict |\n"
                 "| --- | --- | --- | --- | --- | --- |\n")
RUN_TIMEOUT = 900


# Adapters ----------------------------------------------------------------------
# Each turns one headless run into the adapter contract:
# {case, rep, tank, pass, input, output, cache_read, cache_write, cost_usd, latency_ms, turns, model}

def claude_command(prompt):
    return ["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits"]


def claude_usage(stdout):
    """`claude -p --output-format json`: one result object (homelab run.py:329 reads the same keys)."""
    data = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
    usage = data.get("usage") or {}
    models = sorted((data.get("modelUsage") or {}).keys())
    return {"input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0),
            "cache_read": usage.get("cache_read_input_tokens", 0),
            "cache_write": usage.get("cache_creation_input_tokens", 0),
            "cost_usd": data.get("total_cost_usd"), "turns": data.get("num_turns", 0),
            "model": ",".join(models), "error": bool(data.get("is_error"))}


# tank -> (binary, command builder, usage parser) or the reason it is unmeasured
ADAPTERS = {
    "claude-code": ("claude", claude_command, claude_usage),
}
UNVERIFIED = {  # flags checked 2026-11-27; the usage fields need one saved real run (spec build step 8)
    "codex": "codex exec --json: usage event unverified",
    "cursor": "cursor-agent -p --output-format json: usage fields unverified",
    "pi": "pi -p --mode json: usage fields unverified",
}
HEADLESS_NONE = {"zed": "no headless agent CLI", "antigravity": "no headless CLI"}


def unmeasured(agents):
    """{tank: reason} for configured agents that cannot produce a measured run yet."""
    reasons = {}
    for agent in agents:
        if agent in ADAPTERS:
            continue
        if agent in UNVERIFIED:
            saved = FIXTURES / f"{agent}.jsonl"
            reasons[agent] = UNVERIFIED[agent] + ("" if saved.is_file() else f"; save one run as {saved.name}")
        else:
            reasons[agent] = HEADLESS_NONE.get(agent, "no adapter")
    return reasons


def tokens(row):
    """Every token the run processed: the context shot comes back as cache reads on each turn, so it counts."""
    return row["input"] + row["cache_write"] + row["cache_read"] + row["output"]


# Hashes and cases --------------------------------------------------------------

def tree_hash(root, paths, skip=()):
    """sha256 over the path and bytes of every tracked or unignored file under paths, as the working tree holds them."""
    digest = hashlib.sha256()
    listing = git_out(root, "ls-files", "-co", "--exclude-standard", "--", *paths) if paths else ""
    for name in sorted(set(listing.splitlines()) - set(skip)):
        path = Path(root) / name
        if path.is_file():
            digest.update(name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def covers(ctx):
    value = (ctx.rail.get("tanks") or {}).get("covers", ["AGENTS.md"])
    return value if isinstance(value, list) else []


def covers_hash(ctx):
    return tree_hash(ctx.root, covers(ctx), skip=(CARD, LEDGER))


def harness(ctx):
    return hashlib.sha256((tree_hash(ctx.root, ["tanks/"], skip=(CARD,)) + hashlib.sha256(HERE.read_bytes()).hexdigest())
                          .encode()).hexdigest()


def settings(ctx):
    t = ctx.rail.get("tanks") if isinstance(ctx.rail.get("tanks"), dict) else {}
    return {"agents": t.get("agents", ["claude-code", "codex"]), "reps": t.get("reps", 3),
            "max_cost_usd": t.get("max_cost_usd", 5.0), "price": t.get("price", {})}


def load_cases(root):
    path = Path(root) / CASES
    if not path.is_file():
        return None, [Fail(f"{CASES} missing", "bigbang (writes a sample case)")]
    try:
        cases = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return None, [Fail(f"{CASES} is not JSON: {error}", f"fix {CASES}")]
    if not isinstance(cases, list) or not cases:
        return None, [Fail(f"{CASES} holds no cases", f"add cases to {CASES}")]
    fails, seen = [], set()
    for n, case in enumerate(cases):
        missing = [k for k in CASE_KEYS if not isinstance(case, dict) or not case.get(k)]
        if missing:
            fails.append(Fail(f"{CASES}[{n}] lacks {', '.join(missing)}", f"give every case {', '.join(CASE_KEYS)}"))
            continue
        if case["id"] in seen:
            fails.append(Fail(f"{CASES}: id {case['id']} repeats", "give each case its own id"))
        seen.add(case["id"])
        for key in ("fixture", "prompt", "oracle"):
            if not (Path(root) / case[key]).is_file():
                fails.append(Fail(f"{CASES}: {case['id']} {key} {case[key]} missing", f"write {case[key]}"))
    return cases, fails


# Card --------------------------------------------------------------------------

def read_card(root):
    path = Path(root) / CARD
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except json.JSONDecodeError:
        return None


def card_fails(ctx, card):
    if card is None:
        return [Fail(f"{CARD} missing or unreadable", "bigbang")]
    fails = []
    if card.get("partial"):
        fails.append(Fail(f"{CARD} is partial ({card.get('stopped') or 'a subset ran'})", "bigbang --paid"))
    if card.get("covers") != covers_hash(ctx):
        fails.append(Fail(f"{CARD} is stale: covered files changed", "bigbang (and --paid for paid tanks)"))
    if card.get("harness") != harness(ctx):
        fails.append(Fail(f"{CARD} is stale: cases or runner changed", "bigbang (and --paid)"))
    agents = settings(ctx)["agents"]
    missing = [a for a in agents if a not in card.get("tanks", {}) and a not in card.get("unmeasured", {})]
    if missing:
        fails.append(Fail(f"{CARD} has no run for {', '.join(missing)}", "bigbang --paid"))
    return fails


def card_stale(ctx):
    """Gate rule 5: one Fail when the card does not hold for the current covered files, else None."""
    card = read_card(ctx.root)
    if card is None or card.get("covers") != covers_hash(ctx):
        return Fail(f"{CARD} is stale for the covered files", "bigbang --paid")
    return None


def summarize(rows, reps):
    by_case, per_rep = {}, {}
    for r in rows:
        c = by_case.setdefault(r["case"], {"pass": 0, "runs": 0, "input": 0, "output": 0, "cache_read": 0,
                                           "cache_write": 0})
        c["runs"] += 1
        c["pass"] += int(r["pass"])
        for k in ("input", "output", "cache_read", "cache_write"):
            c[k] += r[k]
        rep = per_rep.setdefault(r["rep"], {"tokens": 0, "passes": 0})
        rep["tokens"] += tokens(r)
        rep["passes"] += int(r["pass"])
    passes = sum(int(r["pass"]) for r in rows)
    total = sum(tokens(r) for r in rows)
    per_pass = [v["tokens"] / v["passes"] for v in per_rep.values() if v["passes"]]
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    return {"runs": len(rows), "reps": reps, "pass_rate": round(passes / len(rows), 4) if rows else 0.0,
            "tokens_per_pass": round(total / passes) if passes else None,
            "tokens_per_pass_spread": round(max(per_pass) - min(per_pass)) if len(per_pass) > 1 else 0,
            "cache_read_per_pass": round(sum(r["cache_read"] for r in rows) / passes) if passes else None,
            "cost_usd": round(sum(costs), 4) if costs else (0.0 if all(r["tank"] == "oracle" for r in rows)
                                                            else None),
            "by_case": by_case}


# Runs --------------------------------------------------------------------------

def tank_env(tank):
    env = {k: v for k, v in os.environ.items() if k in KEEP_ENV}
    if tank == "claude-code":
        env.update({k: v for k, v in os.environ.items() if k.startswith(("ANTHROPIC_", "CLAUDE_CODE_"))})
    env.update(GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="tank", GIT_AUTHOR_EMAIL="tank@example.invalid",
               GIT_COMMITTER_NAME="tank", GIT_COMMITTER_EMAIL="tank@example.invalid")
    return env


def run_one(root, case, tank, rep, runner=None):
    """One case × rep × tank in a throwaway repo; graded on what the repo holds afterwards."""
    root = Path(root)
    work = Path(tempfile.mkdtemp(prefix=f"tank-{case['id']}-"))
    row = {"case": case["id"], "rep": rep, "tank": tank, "pass": False, "input": 0, "output": 0, "cache_read": 0,
           "cache_write": 0, "cost_usd": 0.0 if tank == "oracle" else None, "latency_ms": 0, "turns": 0,
           "model": "oracle" if tank == "oracle" else "", "quota": False, "detail": ""}
    try:
        env = tank_env(tank)
        built = sh(["sh", str(root / case["fixture"])], work, env=env)
        if built.returncode:
            row["detail"] = f"fixture exited {built.returncode}: {tail(built.stderr, 3)}"
            return row
        started = time.time()
        if tank == "oracle":
            done = sh(["sh", str(root / case["oracle"])], work, env=env)
            if done.returncode:
                row["detail"] = f"oracle exited {done.returncode}: {tail(done.stderr, 3)}"
        else:
            binary, command, usage = ADAPTERS[tank]
            prompt = (root / case["prompt"]).read_text()
            done = (runner or sh)(command(prompt), work, env=env, timeout=RUN_TIMEOUT)
            row["quota"] = bool(QUOTA.search((done.stdout or "") + (done.stderr or "")))
            try:
                row.update({k: v for k, v in usage(done.stdout or "").items() if k != "error"})
            except (json.JSONDecodeError, IndexError, AttributeError) as error:
                row["detail"] = f"unreadable output: {error}"
        row["latency_ms"] = round((time.time() - started) * 1000)
        graded = sh(case["grade"], work, shell=True, env=env)
        row["pass"] = graded.returncode == 0
        return row
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_suite(ctx, tanks, runner=None):
    """Every case × rep for each tank, stopping at the cost cap or a quota message. Returns the new card."""
    cases, fails = load_cases(ctx.root)
    if fails:
        raise RuntimeError("; ".join(f.problem for f in fails))
    s = settings(ctx)
    picked = [c for c in cases if not ctx.cases or c["id"] in ctx.cases]
    reps = s["reps"]
    rows, spent, stopped = [], 0.0, None
    for tank in tanks:
        for rep in range(1 if tank == "oracle" else reps):
            for case in picked:
                if stopped:
                    break
                row = run_one(ctx.root, case, tank, rep, runner)
                rows.append(row)
                if row["cost_usd"] is None and tank != "oracle":
                    price = s["price"].get(tank) or {}
                    if price:
                        row["cost_usd"] = (tokens(row) - row["output"]) * price.get("input", 0) / 1e6 + \
                            row["output"] * price.get("output", 0) / 1e6
                spent += row["cost_usd"] or 0
                if row["quota"]:
                    stopped = f"quota message from {tank}"
                elif spent >= s["max_cost_usd"]:
                    stopped = f"cost cap ${s['max_cost_usd']} reached"
    summaries = {t: summarize([r for r in rows if r["tank"] == t], 1 if t == "oracle" else reps) for t in tanks}
    against_shots(ctx, rows, summaries)
    expected = {t: len(picked) * (1 if t == "oracle" else reps) for t in tanks}
    ran = {t: sum(1 for r in rows if r["tank"] == t) for t in tanks}
    complete = not stopped and len(picked) == len(cases) and ran == expected
    return {"complete": complete, "partial": not complete, "stopped": stopped or (
                None if len(picked) == len(cases) else f"--cases ran {len(picked)}/{len(cases)}"),
            "covers": covers_hash(ctx), "harness": harness(ctx), "cases": len(cases), "reps": reps,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "unmeasured": unmeasured(s["agents"]),
            "tanks": summaries}


def against_shots(ctx, rows, summaries):
    """Each paid tank's context shot and the share of its spend that re-reads it, plus the cached model spec."""
    import shots
    latest = shots.last_rows(ctx.root)
    for tank, summary in summaries.items():
        if tank == "oracle":
            continue
        mine = [r for r in rows if r["tank"] == tank]
        shot = (latest.get(tank) or {}).get("total")
        turns, total = sum(r["turns"] for r in mine), sum(tokens(r) for r in mine)
        summary["shot_tokens"] = shot
        summary["shot_share"] = round(min(1.0, shot * turns / total), 3) if shot and total else None
        if getattr(ctx, "kit", None) is not None:
            summary["model_spec"] = shots.model_spec(ctx.kit, tank)


def verdict(before, after):
    """keep only when pass rate holds or rises and tokens/pass drops by more than the spread."""
    if not before or before.get("tokens_per_pass") is None or after.get("tokens_per_pass") is None:
        return "baseline"
    spread = max(before.get("tokens_per_pass_spread", 0), after.get("tokens_per_pass_spread", 0))
    if after["pass_rate"] >= before["pass_rate"] and after["tokens_per_pass"] < before["tokens_per_pass"] - spread:
        return "keep"
    return "revert"


def ledger_rows(ctx, card):
    base = ctx.rail.get("base", "dev")
    shown = git(ctx.root, "show", f"{base}:{CARD}")
    try:
        previous = json.loads(shown.stdout) if shown.returncode == 0 else {}
    except json.JSONDecodeError:
        previous = {}
    change = git_out(ctx.root, "log", "-1", "--format=%h %s") or "uncommitted"
    rows = []
    for tank, after in card["tanks"].items():
        if tank == "oracle":
            continue
        before = previous.get("tanks", {}).get(tank, {})
        fmt = lambda v: "—" if v is None else str(v)  # noqa: E731
        rows.append(f"| {card['ts'][:10]} | {change.replace('|', '/')} | {tank} | "
                    f"{fmt(before.get('pass_rate'))} → {after['pass_rate']} | "
                    f"{fmt(before.get('tokens_per_pass'))} → {fmt(after['tokens_per_pass'])} "
                    f"(± {after['tokens_per_pass_spread']}) | {verdict(before, after)} |")
    return rows


SAMPLE = ("tanks/cases.json", "tanks/fixtures/gate-red-test.sh", "tanks/prompts/gate-red-test.md",
          "tanks/oracle/gate-red-test.sh")


class Tanks(Module):
    name, runs = "tanks", True

    def probe(self, ctx):
        _, fails = load_cases(ctx.root)
        return fails or card_fails(ctx, read_card(ctx.root))

    def apply(self, ctx):
        from base import template, write_new
        root = ctx.root
        if not (root / CASES).is_file():
            return [("write the sample rail-check case (tanks/)",
                     lambda: [write_new(root / p, template(p), 0o755 if p.endswith(".sh") else None) for p in SAMPLE])]
        _, fails = load_cases(root)
        if fails:
            return []
        card = read_card(root)
        measurable = [a for a in settings(ctx)["agents"] if a in ADAPTERS]
        hold = card and not card.get("partial") and card.get("covers") == covers_hash(ctx) and \
            card.get("harness") == harness(ctx)
        if hold and not ctx.paid:
            return []
        tanks = ["oracle"] + (measurable if ctx.paid else [])

        def run():
            try:
                new = run_suite(ctx, tanks)
            except RuntimeError as error:
                ctx.out(f"tanks: {error}")
                return
            if not ctx.paid and card:  # keep earlier paid results only while they still hold for these files
                for t, v in (card.get("tanks") or {}).items():
                    if t != "oracle" and card.get("covers") == new["covers"] and card.get("harness") == new["harness"]:
                        new["tanks"].setdefault(t, v)
            (root / CARD).parent.mkdir(parents=True, exist_ok=True)
            (root / CARD).write_text(json.dumps(new, indent=2, sort_keys=True) + "\n")
            if ctx.paid:
                path = root / LEDGER
                old = path.read_text() if path.is_file() else "# Tanks\n\n" + LEDGER_HEADER
                path.write_text(old + "".join(r + "\n" for r in ledger_rows(ctx, new)))
        return [(f"run {', '.join(tanks)} on {CASES}" + ("" if ctx.paid else " ($0; paid tanks need --paid)"), run)]

    def report(self, ctx):
        card = read_card(ctx.root)
        if not card:
            return []
        lines = []
        for tank, t in card.get("tanks", {}).items():
            per = "—" if t.get("tokens_per_pass") is None else f"{t['tokens_per_pass']} tokens/pass ± " \
                                                              f"{t.get('tokens_per_pass_spread', 0)}"
            cost = "—" if t.get("cost_usd") is None else f"${t['cost_usd']}"
            share = f" · shot {t['shot_tokens']} = {round(100 * t['shot_share'])}% of spend" \
                if t.get("shot_share") is not None else ""
            lines.append(f"tank: {tank} · pass {t.get('pass_rate')} · {per} · {cost}{share}")
        if card.get("unmeasured"):
            lines.append("tank: unmeasured " + "; ".join(f"{k} ({v})" for k, v in card["unmeasured"].items()))
        return lines
