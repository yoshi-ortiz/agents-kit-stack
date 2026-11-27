"""bigbang: one command that makes a checkout ready, guarded, and audited.

Each module probes real state, applies what is missing, and probes again. See docs/specs/bigbang.md.

  bigbang [domain...] [--dry-run] [--paid] [--sync] [--only <module>] [--cases <id,...>]
  bigbang ledger start <role> <name> <session-id> | end <name> <sha> | park <name>
  bigbang goals <quote-file>
  bigbang brief
"""
import contextlib
import io
import os
import json
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))

from base import Ctx, Fail, Module, git, read_rail, sh, tail  # noqa: E402
import burndown as burndown_mod  # noqa: E402
import verbatim as goals_mod  # noqa: E402
import loop as loop_mod  # noqa: E402
import guardrail as rail_mod  # noqa: E402
import tokens as tanks_mod  # noqa: E402
import index as index_mod  # noqa: E402
import scaffold as scaffold_mod  # noqa: E402
import shots as shots_mod  # noqa: E402


def contained(fn, *args, **kw):
    """Run a packages.py function; return (stdout lines, problem lines). gate()'s SystemExit becomes problems."""
    buffer = io.StringIO()
    problems = []
    with contextlib.redirect_stdout(buffer):
        try:
            code = fn(*args, **kw)
            if code not in (0, None):
                problems.append(f"exited {code}")
        except SystemExit as stop:
            if stop.code not in (0, None):
                problems.append(f"exited {stop.code}")
    lines = buffer.getvalue().splitlines()
    gated = [line[4:] for line in lines if line.startswith("  - ")]
    rest = [line for line in lines if not line.startswith("  - ") and not line.startswith("FAIL:") and line.strip()]
    return rest, gated or problems


# Setup modules ---------------------------------------------------------------

class GitModule(Module):
    name, stops, always = "git", True, True

    def probe(self, ctx):
        top = git(ctx.root, "rev-parse", "--show-toplevel")
        if top.returncode == 0:
            ctx.root = Path(top.stdout.strip())
            return []
        if any((p / ".git").exists() for p in (ctx.root, *ctx.root.parents)):
            return [Fail(f"could not open the Git repository: {tail(top.stderr, 1)}", "repair or remove the broken .git")]
        return [Fail(f"{ctx.root} is not a Git repository", "git init")]

    def apply(self, ctx):
        if any((p / ".git").exists() for p in (ctx.root, *ctx.root.parents)):
            return []
        return [(f"git init in {ctx.root}", lambda: git(ctx.root, "init", "--quiet"))]


class CatalogModule(Module):
    name, stops, always = "catalog", True, True

    def probe(self, ctx):
        return [] if ctx.kit.INDEX.exists() else [Fail("the Kit catalog is not indexed", "kit kit-starter-pack")]

    def apply(self, ctx):
        def index():
            _, problems = contained(ctx.kit.main, ["kit-starter-pack"])
            for p in problems:
                ctx.out(f"catalog: {p}")
        return [("index the Kit catalog (kit-starter-pack)", index)]


def domain_servers(ctx):
    return list(dict.fromkeys(i.name for i in ctx.items if i.kind == "mcp"))


class DomainsModule(Module):
    name, stops, always = "domains", True, True

    def probe(self, ctx):
        servers = domain_servers(ctx)
        fails = [Fail(f"mcp:{s} is not under PACK.md # MCP servers", "add it to PACK.md # MCP servers")
                 for s in servers if s not in ctx.pack.mcp]
        toml = ctx.root / ".codex/config.toml"
        codex = toml.read_text() if toml.is_file() else ""
        mcp_json = ctx.root / ".mcp.json"
        claude = json.loads(mcp_json.read_text()).get("mcpServers", {}) if mcp_json.is_file() else {}
        for s in servers:
            if s not in ctx.pack.mcp:
                continue
            if f"[mcp_servers.{s}]" not in codex:
                fails.append(Fail(f"MCP {s} missing from .codex/config.toml", f"kit domain {' '.join(ctx.domains)}"))
            if shutil.which("claude") and s not in claude:
                fails.append(Fail(f"MCP {s} missing from .mcp.json", f"kit domain {' '.join(ctx.domains)}"))
        return fails

    def apply(self, ctx):
        if any(s not in ctx.pack.mcp for s in domain_servers(ctx)):
            return []

        def configure():
            lines, problems = contained(ctx.kit.domain, ctx.pack, ctx.domains, False, root=ctx.root)
            for p in problems:
                ctx.out(f"domains: {p}")
        return [(f"configure MCP servers {', '.join(domain_servers(ctx))}", configure)]

    def report(self, ctx):
        servers = domain_servers(ctx)
        return [f"domains: {', '.join(ctx.domains)} · {len(servers)} MCP server(s): {', '.join(servers) or 'none'}"]


def mise_config(root):
    return next((root / n for n in ("mise.toml", ".mise.toml") if (root / n).is_file()), None)


class Stage0Module(Module):
    name, stops, always, runs = "stage0", True, True, True

    def selected(self, ctx):
        return mise_config(ctx.root) is not None

    def command(self, ctx):
        import tomllib
        tasks = tomllib.loads(mise_config(ctx.root).read_text()).get("tasks", {})
        return ["mise", "run", "stage0"] if "stage0" in tasks else ["mise", "install"]

    def probe(self, ctx):
        cmd = self.command(ctx)
        if not shutil.which("mise"):
            return [Fail("mise not found; bigbang does not install runtimes", "install mise")]
        result = sh(cmd, ctx.root)
        return [] if result.returncode == 0 else [Fail(f"{shlex.join(cmd)} exited {result.returncode}: "
                                                       f"{tail(result.stderr or result.stdout, 3)}", shlex.join(cmd))]


class McpModule(Module):
    name, stops, always, runs = "mcp", True, True, True

    def stdio(self, ctx):
        config = ctx.root / ".mcp.json"
        servers = json.loads(config.read_text()).get("mcpServers", {}) if config.is_file() else {}
        return {n: s for n, s in servers.items() if s.get("command")}

    def probe(self, ctx):
        return [Fail(f"MCP {n} does not start: {why}", f"fix the {n} command in .mcp.json or PACK.md")
                for n, s in self.stdio(ctx).items() if (why := ctx.kit.mcp_starts(s, cwd=ctx.root))]

    def report(self, ctx):
        servers = self.stdio(ctx)
        return [f"mcp: {len(servers)} stdio server(s) start: {', '.join(servers) or 'none'}"]


class VerifyModule(Module):
    name, always, runs = "verify", True, True

    def probe(self, ctx):
        self.lines, problems = contained(ctx.kit.verify, ctx.pack)
        return [Fail(p, "python3 skills/kit/packages.py (Kit verify names each fix)") for p in problems]

    def report(self, ctx):
        return [f"verify: {line.removeprefix('ok: ')}" for line in getattr(self, "lines", []) if line.startswith("ok:")]


MODULES = [GitModule(), CatalogModule(), DomainsModule(), scaffold_mod.Scaffold(), Stage0Module(), McpModule(),
           rail_mod.Guardrail(), goals_mod.Goals(), rail_mod.Gate(), burndown_mod.Burndown(),
           loop_mod.Loop(), loop_mod.Babysitter(), tanks_mod.Tanks(), index_mod.Index(), shots_mod.Shots(),
           VerifyModule()]
NAMES = [m.name for m in MODULES]


def check_names(kit):
    """packages.py lists the selectable modules without importing this file; both lists must agree."""
    selectable = {m.name for m in MODULES if not m.always}
    return [] if set(kit.BIGBANG_MODULES) == selectable else [
        f"packages.BIGBANG_MODULES {kit.BIGBANG_MODULES} differs from modules.py {selectable}"]


# Runner ----------------------------------------------------------------------

def guarded(ctx, module, step, *args):
    """Call a module step; an exception becomes one Fail naming the module, so one broken module never hides the rest
    of the report. BIGBANG_DEBUG=1 re-raises for the traceback."""
    try:
        return getattr(module, step)(ctx, *args), None
    except Exception as error:  # noqa: BLE001 - every module error must reach the report
        if os.environ.get("BIGBANG_DEBUG"):
            raise
        return None, Fail(f"{module.name} {step} crashed: {type(error).__name__}: {error}",
                          "BIGBANG_DEBUG=1 bigbang (prints the traceback); fix the file the error names")


def run(ctx, modules=None):
    """Probe, apply, probe again, per selected module. 0 when every module ends with an empty probe."""
    modules = MODULES if modules is None else modules
    failed = False
    for module in modules:
        if ctx.only and module.name not in (ctx.only, "git"):
            continue
        if not module.selected(ctx):
            continue
        if module.name != "git":
            ctx.rail = read_rail(ctx.root)
        if ctx.dry and module.runs:
            ctx.out(f"would: {module.name}: run its checks")
            continue
        fails, crash = guarded(ctx, module, "probe")
        if crash:
            fails = [crash]
        if fails and not crash:
            actions, crash = guarded(ctx, module, "apply")
            actions = actions or []
            if crash:
                fails = fails + [crash]
            if ctx.dry:
                for text, _ in actions:
                    ctx.out(f"would: {module.name}: {text}")
                if not actions:
                    failed = True
                    for f in fails:
                        ctx.out(f.line(module.name))
                continue
            for text, do in actions:
                try:
                    do()
                    ctx.out(f"done: {module.name}: {text}")
                except Exception as error:  # noqa: BLE001
                    if os.environ.get("BIGBANG_DEBUG"):
                        raise
                    ctx.out(f"{module.name}: {text} failed: {type(error).__name__}: {error}")
            if actions and not crash:
                if module.name != "git":
                    ctx.rail = read_rail(ctx.root)
                fails, crash = guarded(ctx, module, "probe")
                fails = [crash] if crash else fails
        if not fails:
            ctx.out(f"ok: {module.name}")
        lines, crash = guarded(ctx, module, "report")
        for line in lines or []:
            ctx.out(line)
        if crash:
            fails = fails + [crash]
        for f in fails:
            ctx.out(f.line(module.name))
        if fails:
            failed = True
            if module.stops:
                return 1
    return int(failed)


def parse(argv):
    opts = {"domains": [], "compass": None, "paid": False, "sync": False, "only": None, "cases": None, "dry": False}
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--dry-run":
            opts["dry"] = True
        elif arg == "--paid":
            opts["paid"] = True
        elif arg == "--sync":
            opts["sync"] = True
        elif arg == "--only" and args:
            opts["only"] = args.pop(0)
        elif arg == "--cases" and args:
            opts["cases"] = [c for c in args.pop(0).split(",") if c]
        elif arg == "--compass" and args:
            opts["compass"] = [c.strip().lower() for c in args.pop(0).split(",") if c.strip()]
        elif arg.startswith("-"):
            raise ValueError(f"unknown flag {arg}")
        else:
            opts["domains"].append(arg.lower())
    return opts


def selection(pack, opts, rail):
    """(domains, compass layers, problems): from the command, else from guardrail.toml. `core` is always on."""
    problems = []
    saved_domains = rail.get("domains") if isinstance(rail.get("domains"), list) else []
    saved_compass = rail.get("compass") if isinstance(rail.get("compass"), list) else []
    domains = opts["domains"] or saved_domains
    compass = opts["compass"] if opts["compass"] is not None else saved_compass
    if not domains:
        problems.append(("no domain named and guardrail.toml names none",
                         f"bigbang <domain> (one of: {', '.join(pack.domains)}), or bigbang sketch to brief first"))
    problems += [(f"{d}: not a domain", f"use one of: {', '.join(pack.domains)}") for d in domains if d not in pack.domains]
    problems += [(f"{c}: not a context compass layer", f"use: {', '.join(l for l in pack.compass if l != 'core')}")
                 for c in compass if c not in pack.compass or c == "core"]
    return domains, ["core"] + [c for c in compass if c != "core"], problems


def brief_main(kit, pack, out):
    """`bigbang brief`: the shot brief (burndown, receipts, status screenshots) as Markdown, from the last run's rows."""
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").stdout.strip() or Path.cwd())
    rail = read_rail(root)
    ctx = Ctx(root=root, pack=pack, kit=kit, domains=rail.get("domains") or [], items=[], rail=rail, out=out)
    text, problems = burndown_mod.brief(ctx)
    for problem in problems:
        out(f"FAIL: brief: {problem}")
    if text:
        (root / ".bigbang").mkdir(exist_ok=True)
        (root / ".bigbang/brief.md").write_text(text)
        out(text.rstrip("\n"))
    return int(bool(problems))


def main(kit, pack, argv, dry=False, out=print):
    """Entry point from packages.py: `bigbang ...` arguments after the verb."""
    if argv[:1] == ["ledger"]:
        return loop_mod.ledger_main(Path.cwd(), argv[1:], out)
    if argv[:1] == ["brief"]:
        return brief_main(kit, pack, out)
    if argv[:1] == ["goals"]:
        return goals_mod.goals_main(Path.cwd(), argv[1:], out)
    try:
        opts = parse(argv)
    except ValueError as error:
        out(f"FAIL: bigbang: {error} · fix: {__doc__.splitlines()[4].strip()}")
        return 1
    root = Path.cwd().resolve()
    top = git(root, "rev-parse", "--show-toplevel")
    rail = read_rail(Path(top.stdout.strip()) if top.returncode == 0 else root)
    domains, compass, problems = selection(pack, opts, rail)
    problems += [(p, "align packages.BIGBANG_MODULES with modules.py") for p in check_names(kit)]
    if opts["only"] and opts["only"] not in NAMES:
        problems.append((f"--only {opts['only']}: not a module", f"use one of: {', '.join(NAMES)}"))
    if problems:
        for problem, fix in problems:
            out(Fail(problem, fix).line("bigbang"))
        return 1
    items = [i for d in domains for i in pack.items.get(d, [])] + [i for c in compass for i in pack.compass.get(c, [])]
    if opts["only"] and opts["only"] not in {i.name for i in items if i.kind == "module"}:
        items.append(kit.Item("module", opts["only"]))
    ctx = Ctx(root=root, pack=pack, kit=kit, domains=domains, items=items, compass=compass,
              asked_domains=opts["domains"], asked_compass=opts["compass"],
              dry=dry or opts["dry"], paid=opts["paid"], sync=opts["sync"], only=opts["only"], cases=opts["cases"],
              out=out)
    return run(ctx)
