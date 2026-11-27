"""shots: each vendor harness's context shot (what it loads before the first prompt), measured at $0, with its leaks.

Also keeps each vendor's model spec and prompting docs cached (vendors.toml), which tanks read to price and
label runs.
"""
import json
import re
import shlex
import shutil
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from base import HERE, STATE, Fail, Module, append_jsonl, ignore_action, jsonl, sh

VENDORS = HERE / "vendors.toml"
HISTORY = f"{STATE}/shots.jsonl"
MEMORY_BUDGET = 3000
AGENT = "kit-bigbang"
CLAUDE = ["claude", "-p", "/context", "--output-format", "json", "--no-session-persistence"]
CODEX = ["codex", "debug", "prompt-input", "hello"]
EXPLICIT = re.compile(r"^disable-model-invocation:\s*true\s*$", re.M)
SIZE = re.compile(r"^([\d.]+)\s*([km]?)$", re.I)
LOADED = ("System prompt", "System tools", "MCP tools", "MCP server instructions", "Memory files", "Skills",
          "Custom agents", "Messages")


def tokens_of(text):
    m = SIZE.match(text.strip().lstrip("~"))
    if not m:
        return 0
    return round(float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6}[m.group(2).lower()])


def table(markdown, heading):
    """Rows of the pipe table under `### heading`, as lists of cells."""
    if f"### {heading}\n" not in markdown:
        return []
    section = markdown.split(f"### {heading}\n", 1)[1].split("\n### ", 1)[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines() if line.startswith("|")]
    return [r for r in rows[2:] if r]


# Probes ------------------------------------------------------------------------

def probe_claude(root):
    result = sh(CLAUDE, root, timeout=120)
    data = json.loads(result.stdout)
    if result.returncode or data.get("total_cost_usd"):
        raise ValueError("the /context dump failed or was billed")
    report = data["result"]
    categories = {r[0]: tokens_of(r[1]) for r in table(report, "Estimated usage by category") if r[0] in LOADED}
    model = re.search(r"\*\*Model:\*\*\s*(\S+)", report)
    window = re.search(r"\*\*Tokens:\*\*\s*\S+\s*/\s*(\S+)", report)
    if not categories:
        raise ValueError("no category table in the /context dump")
    return {"method": "measured", "total": sum(categories.values()), "categories": categories,
            "model": model.group(1) if model else "", "window": tokens_of(window.group(1)) if window else 0,
            "skills": [r[0] for r in table(report, "Skills")],
            "mcp": sorted({r[1] for r in table(report, "MCP Tools") if len(r) > 1})}


def probe_codex(root):
    result = sh(CODEX, root, timeout=120)
    items = json.loads(result.stdout)
    if result.returncode or not isinstance(items, list):
        raise ValueError("the prompt-input dump failed")
    categories, skills = {}, []
    for n, item in enumerate(items):
        text = "".join(c.get("text", "") for c in item.get("content") or [] if isinstance(c, dict))
        if item.get("type") != "message" or not text:
            name = "Tools" if item.get("type") != "message" else None
        elif item.get("role") == "user" and text.startswith("# AGENTS.md"):
            name = "Memory files"
        elif item.get("role") == "user":
            name = "Messages"
        elif "<skills_instructions>" in text:
            name = "Skills"
            skills = re.findall(r"^- ([\w:-]+): ", text, re.M)
        elif n == 0 or not categories:
            name = "System prompt"
        else:
            name = "Instructions"
        if name:
            categories[name] = categories.get(name, 0) + len(json.dumps(item) if name == "Tools" else text) // 4
    return {"method": "estimated (prompt text ÷ 4)", "total": sum(categories.values()), "categories": categories,
            "model": "", "window": 0, "skills": skills, "mcp": []}


def probe_files(root, kit, agent):
    """Hosts with no prompt dump: estimate from the files they load (memory files, global skill listing)."""
    root = Path(root)
    memory = sum(len((root / f).read_text(errors="ignore")) for f in ("AGENTS.md", "GEMINI.md") if (root / f).is_file())
    skills, names, explicit = 0, [], 0
    folder = kit.agent_global_dir(agent) if hasattr(kit, "agent_global_dir") else None
    if folder and Path(folder).is_dir():
        for manifest in sorted(Path(folder).glob("*/SKILL.md")):
            try:
                text = manifest.read_text(errors="ignore")
                name, description, _ = kit.frontmatter(manifest)
            except (OSError, ValueError, TypeError):
                continue
            if EXPLICIT.search(text.split("\n---", 1)[0]):
                explicit += 1  # an explicit-only skill stays out of the listing on a host that honors the flag
                continue
            names.append(name or manifest.parent.name)
            skills += len(f"- {name}: {description}")
    categories = {"Memory files": memory // 4, "Skills": skills // 4}
    method = "estimated (loaded files ÷ 4" + (f"; {explicit} explicit-only skills assumed unlisted" if explicit else "") + ")"
    return {"method": method, "total": sum(categories.values()), "categories": categories,
            "model": "", "window": 0, "skills": names, "mcp": []}


PROBES = {"claude-code": probe_claude, "codex": probe_codex}


CLIS = {"claude-code": "claude", "codex": "codex"}


def measure(ctx, agent):
    probe = PROBES.get(agent)
    if probe and (agent not in CLIS or shutil.which(CLIS[agent])):
        return probe(ctx.root)
    shot = probe_files(ctx.root, ctx.kit, agent)
    if probe:
        shot["method"] = f"{CLIS[agent]} CLI not installed; " + shot["method"]
    return shot


# Vendor docs and model specs ---------------------------------------------------

def vendors():
    return tomllib.loads(VENDORS.read_text())


def vendor_of(agent):
    return next((name for name, v in vendors().items() if isinstance(v, dict) and agent in v.get("agents", [])), None)


def cache_dir(kit, vendor):
    return Path(kit.CACHE) / "vendors" / vendor


def cache_stale(kit, vendor, max_age_days):
    meta = cache_dir(kit, vendor) / "meta.json"
    try:
        return time.time() - json.loads(meta.read_text())["fetched"] > max_age_days * 86400
    except (OSError, ValueError, KeyError):
        return True


def fetch_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


RETRY_DAYS = 1  # a vendor refresh that failed is tried again after this, not after max_age_days


def refresh_vendor(kit, vendor, spec, root, max_age_days=7):
    """Cache the vendor's model catalog (its own free dump) and its llms.txt docs; returns problem lines."""
    folder = cache_dir(kit, vendor)
    folder.mkdir(parents=True, exist_ok=True)
    problems, meta = [], {"fetched": time.time(), "vendor": vendor}
    if spec.get("models"):
        result = sh(shlex.split(spec["models"]), root, timeout=120)
        if result.returncode:
            problems.append(f"{vendor}: `{spec['models']}` exited {result.returncode}")
        else:
            (folder / "models.raw").write_text(result.stdout)
            meta["models"] = summarize_models(vendor, result.stdout)
            if vendor == "openai":  # the vendor's own instructions per model: its prompting practice, verbatim
                try:
                    for m in json.loads(result.stdout).get("models", []):
                        template = (m.get("model_messages") or {}).get("instructions_template")
                        if template and m.get("visibility") == "list":
                            (folder / f"prompting-{m['slug']}.md").write_text(template)
                except ValueError:
                    pass
    if spec.get("docs"):
        try:
            (folder / "docs.txt").write_text(fetch_text(spec["docs"]))
            meta["docs"] = spec["docs"]
        except (urllib.error.URLError, OSError) as error:
            problems.append(f"{vendor}: docs {spec['docs']}: {error}")
    if problems:  # keep what was cached, and come back sooner
        meta["fetched"] -= max(0, max_age_days - RETRY_DAYS) * 86400
        meta["errors"] = problems
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))
    return problems


def summarize_models(vendor, raw):
    try:
        if vendor == "anthropic":
            report = json.loads(raw)["result"]
            model = re.search(r"\*\*Model:\*\*\s*(\S+)", report)
            window = re.search(r"\*\*Tokens:\*\*\s*\S+\s*/\s*(\S+)", report)
            return [{"id": model.group(1), "context_window": tokens_of(window.group(1)) if window else 0}] if model else []
        if vendor == "openai":
            return [{"id": m["slug"], "context_window": m.get("context_window")}
                    for m in json.loads(raw).get("models", []) if m.get("visibility") == "list"]
    except (ValueError, KeyError, TypeError):
        return []
    return [{"id": line.split()[0]} for line in raw.splitlines() if line.strip()][:50]


def model_spec(kit, agent):
    vendor = vendor_of(agent)
    try:
        meta = json.loads((cache_dir(kit, vendor) / "meta.json").read_text()) if vendor else {}
    except (OSError, ValueError):
        meta = {}
    return {"vendor": vendor, "models": meta.get("models", []), "docs": meta.get("docs")}


# Leaks -------------------------------------------------------------------------

def catalog_names(kit):
    manifest = Path(kit.MARKET) / ".claude-plugin/marketplace.json" if hasattr(kit, "MARKET") else None
    names = set()
    if manifest and manifest.is_file():
        for plugin in json.loads(manifest.read_text()).get("plugins", []):
            for skill in (Path(kit.MARKET) / plugin["source"] / "skills").glob("*/SKILL.md"):
                names.update((f"{plugin['name']}:{skill.parent.name}", f"{plugin['name']}-{skill.parent.name}"))
    return names


def project_servers(root):
    path = Path(root) / ".mcp.json"
    try:
        return set(json.loads(path.read_text()).get("mcpServers", {})) if path.is_file() else set()
    except ValueError:
        return set()


def settings(rail):
    s = rail.get("shots") if isinstance(rail.get("shots"), dict) else {}
    return {"budget": s.get("budget") or {}, "memory_budget": s.get("memory_budget", MEMORY_BUDGET)}


def leaks(ctx, agent, shot):
    fails, s = [], settings(ctx.rail)
    leaked = sorted(set(shot["skills"]) & catalog_names(ctx.kit))
    if leaked:
        fails.append(Fail(f"{agent}: catalog skills in the startup listing: {', '.join(leaked[:5])}",
                          "python3 <kit>/packages.py kit-starter-pack (keeps catalog skills explicit-only)"))
    wanted = {i.name for i in ctx.items if i.kind == "mcp"}
    for server in sorted(project_servers(ctx.root) - wanted):
        fails.append(Fail(f"{agent}: MCP server {server} is in .mcp.json but no selected domain lists it",
                          f"claude mcp remove -s project {server} (or add mcp:{server} to a domain)"))
    memory = shot["categories"].get("Memory files", 0)
    if memory > s["memory_budget"]:
        fails.append(Fail(f"{agent}: memory files load {memory} tokens (budget {s['memory_budget']})",
                          "move reference out of AGENTS.md behind pointers in its index; the owner edits it"))
    budget = s["budget"].get(agent)
    if isinstance(budget, int) and shot["total"] > budget:
        top = sorted(shot["categories"].items(), key=lambda kv: -kv[1])[:3]
        fails.append(Fail(f"{agent}: context shot {shot['total']} tokens over budget {budget} "
                          f"({', '.join(f'{k} {v}' for k, v in top)})", "cut the largest category, or the owner raises "
                          "[shots] budget in guardrail.toml"))
    return fails


def last_rows(root):
    latest = {}
    for row in jsonl(Path(root) / HISTORY):
        latest[row.get("agent")] = row
    return latest


JITTER = 0.02  # a vendor's own count moves a little between identical starts; under 2% is the same shot


def same(row, shot):
    if not row or set(row.get("categories", {})) != set(shot["categories"]):
        return False
    return abs(row.get("total", 0) - shot["total"]) <= JITTER * max(shot["total"], 1)


def k(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


class Shots(Module):
    name, runs = "shots", True

    def probe(self, ctx):
        self.lines, fails = [], []
        spec = vendors()
        age = spec.get("max_age_days", 7)
        if getattr(self, "measured_for", None) is not ctx:  # one measurement per run; the re-probe reuses it
            self.shots, self.measured_for = {}, ctx
        for agent in ctx.pack.agents:
            try:
                shot = self.shots.get(agent) or measure(ctx, agent)
            except (ValueError, KeyError, TypeError, OSError) as error:
                fails.append(Fail(f"{agent}: context shot probe failed: {error}", "run the vendor CLI by hand; "
                                  "a failed probe never counts as zero"))
                continue
            self.shots[agent] = shot
            fails += leaks(ctx, agent, shot)
        latest = last_rows(ctx.root)
        unrecorded = [a for a, s in self.shots.items() if not same(latest.get(a), s)]
        if unrecorded:
            fails.append(Fail(f"context shot changed for {', '.join(unrecorded)}; not recorded", "bigbang (records it)"))
        stale = [v for v, s in spec.items() if isinstance(s, dict) and set(s.get("agents", [])) & set(ctx.pack.agents)
                 and (s.get("models") or s.get("docs")) and cache_stale(ctx.kit, v, age)]
        if stale:
            fails.append(Fail(f"vendor model specs and docs not cached (or older than {age} days): {', '.join(stale)}",
                              "bigbang (refreshes ~/.cache/kit/vendors)"))
        from base import ignore_lines
        if ignore_lines(ctx.root, [HISTORY]):
            fails.append(Fail(f"{HISTORY} is not ignored by git", "bigbang (adds it to .gitignore)"))
        return fails

    def apply(self, ctx):
        actions = ignore_action(ctx.root, [HISTORY])
        latest = last_rows(ctx.root)
        changed = {a: s for a, s in getattr(self, "shots", {}).items() if not same(latest.get(a), s)}
        if changed:
            def record():
                stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                for agent, shot in changed.items():
                    append_jsonl(ctx.root / HISTORY, {"ts": stamp, "agent": agent, **shot})
            actions.append((f"record the context shot for {', '.join(changed)}", record))
        spec = vendors()
        age = spec.get("max_age_days", 7)
        for vendor, entry in spec.items():
            if not isinstance(entry, dict) or not set(entry.get("agents", [])) & set(ctx.pack.agents):
                continue
            if (entry.get("models") or entry.get("docs")) and cache_stale(ctx.kit, vendor, age):
                def refresh(vendor=vendor, entry=entry):
                    for problem in refresh_vendor(ctx.kit, vendor, entry, ctx.root, age):
                        ctx.out(f"shots: {problem}")
                actions.append((f"cache {vendor} model spec and docs", refresh))
        return actions

    def report(self, ctx):
        lines = []
        budgets = settings(ctx.rail)["budget"]
        for agent, shot in getattr(self, "shots", {}).items():
            parts = sorted(shot["categories"].items(), key=lambda kv: -kv[1])[:4]
            window = f" of {k(shot['window'])} ({100 * shot['total'] / shot['window']:.1f}%)" if shot.get("window") else ""
            budget = f" · budget {k(budgets[agent])}" if agent in budgets else ""
            approx = "" if shot["method"] == "measured" else "~"
            lines.append(f"shot: {agent} · {approx}{k(shot['total'])} tokens at start{window}{budget} · "
                         + " · ".join(f"{name.lower()} {k(v)}" for name, v in parts)
                         + ("" if shot["method"] == "measured" else f" · {shot['method']}"))
        if hasattr(ctx.kit, "unused_plugins"):
            try:
                idle = ctx.kit.unused_plugins()
            except Exception:  # a hint only; its source is Claude Code's own state file
                idle = []
            if idle:
                lines.append(f"shots: {len(idle)} enabled plugin(s) never used: {', '.join(idle[:5])} · "
                             "kit prune <plugin> (owner confirms)")
        return lines
