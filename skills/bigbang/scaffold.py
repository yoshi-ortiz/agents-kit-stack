"""scaffold: a domain manifest becomes a goldfish-ready plan, pinned to the latest breach-safe versions.

bigbang resolves versions and copies the manifest's files; a small-model session (the goldfish) runs the plan's
steps, because they install third-party code and belong under the host's permission prompts.
"""
import json
import re
import shutil
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from base import DETERMDINISTIC, HERE, STATE, Fail, Module, ignore_action, load_determdinistic, sh, tail

DOMAINS = HERE.parent / "kit" / "domains"
FILES = DOMAINS / "files"
LOCK = "scaffold.lock"
PLAN = f"{STATE}/scaffold-plan.md"
LOCK_DAYS = 30            # an advisory check older than this is re-run
COOLDOWN_DAYS = 7         # default for [scaffold] cooldown_days
AGENT = "kit-bigbang"     # generic User-Agent; registries ask clients to name themselves
OSV = "https://api.osv.dev/v1/query"
ECOSYSTEMS = {"npm": "npm", "pypi": "PyPI", "crates": "crates.io"}
REQUIRED = ("name", "kind", "summary")
PLACEHOLDER = re.compile(r"\{([a-z]+:[^}]+)\}")
STABLE = re.compile(r"^\d+(\.\d+)*$")


def load_manifest(domain):
    path = DOMAINS / f"{domain}.toml"
    if not path.is_file():
        return None
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        return {"__error__": str(error)}


def manifest_fails(domain, manifest):
    if "__error__" in manifest:
        return [Fail(f"domains/{domain}.toml is not TOML: {manifest['__error__']}", f"fix skills/kit/domains/{domain}.toml")]
    fails = [Fail(f"domains/{domain}.toml lacks `{k}`", f"add `{k}`") for k in REQUIRED if not manifest.get(k)]
    scaffold = manifest.get("scaffold") or {}
    if not scaffold.get("check"):
        fails.append(Fail(f"domains/{domain}.toml lacks `scaffold.check`", "add the command whose exit 0 proves it"))
    packages = manifest.get("packages") or {}
    for step in scaffold.get("steps", []):
        for name in PLACEHOLDER.findall(step):
            if name not in packages:
                fails.append(Fail(f"domains/{domain}.toml step uses {{{name}}} with no [packages] entry",
                                  f"add \"{name}\" = \"latest-safe\" to [packages]"))
    for target, source in (scaffold.get("files") or {}).items():
        if not (FILES / source).is_file():
            fails.append(Fail(f"domains/{domain}.toml file source {source} missing", f"write skills/kit/domains/files/{source}"))
    return fails


# Tools a manifest requires ---------------------------------------------------

def version_tuple(text):
    return tuple(int(p) for p in re.findall(r"\d+", text)[:4])


def requires_fails(manifest, root):
    fails = []
    for need in manifest.get("requires", []):
        m = re.match(r"^([\w.+-]+)\s*(?:>=\s*([\d.]+))?$", need.strip())
        if not m:
            fails.append(Fail(f"requires `{need}` does not parse", "write `tool` or `tool>=1.2`"))
            continue
        tool, minimum = m.groups()
        result = sh([tool, "--version"], root, timeout=30)
        if result.returncode:
            fails.append(Fail(f"{tool} not found", f"install {tool}{' ' + minimum + '+' if minimum else ''}"))
            continue
        found = re.search(r"\d+(?:\.\d+)+", result.stdout + result.stderr)
        if minimum and (not found or version_tuple(found.group()) < version_tuple(minimum)):
            fails.append(Fail(f"{tool} {found.group() if found else '?'} is older than {minimum}", f"upgrade {tool}"))
    return fails


# Breach-safe resolver ---------------------------------------------------------

def fetch_json(url, data=None):
    """GET (or POST JSON) and parse; the one network call site, so tests replace it."""
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers={"User-Agent": AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def releases(ecosystem, name):
    """[(version, published datetime, withdrawn bool)] for stable versions, newest first."""
    quoted = urllib.parse.quote(name, safe="@")
    found = []
    if ecosystem == "npm":
        data = fetch_json(f"https://registry.npmjs.org/{quoted.replace('/', '%2F')}")
        for version, meta in data.get("versions", {}).items():
            if STABLE.match(version) and version in data.get("time", {}):
                found.append((version, parse_time(data["time"][version]), bool(meta.get("deprecated"))))
    elif ecosystem == "pypi":
        data = fetch_json(f"https://pypi.org/pypi/{quoted}/json")
        for version, files in data.get("releases", {}).items():
            if STABLE.match(version) and files:
                found.append((version, min(parse_time(f["upload_time_iso_8601"]) for f in files),
                              all(f.get("yanked") for f in files)))
    elif ecosystem == "crates":
        data = fetch_json(f"https://crates.io/api/v1/crates/{quoted}/versions")
        for v in data.get("versions", []):
            if STABLE.match(v["num"]):
                found.append((v["num"], parse_time(v["created_at"]), bool(v.get("yanked"))))
    else:
        raise ValueError(f"ecosystem {ecosystem} has no resolver")
    return sorted(found, key=lambda r: version_tuple(r[0]), reverse=True)


def advisories(ecosystem, name, version):
    data = fetch_json(OSV, {"package": {"name": name, "ecosystem": ECOSYSTEMS[ecosystem]}, "version": version})
    return [v["id"] for v in data.get("vulns", [])]


def resolve(package_id, want, cooldown_days, now=None):
    """The lock entry for one package: newest stable version past the cooldown, not withdrawn, with no OSV advisory."""
    now = now or datetime.now(timezone.utc)
    ecosystem, _, name = package_id.partition(":")
    if ecosystem not in ECOSYSTEMS:
        raise ValueError(f"{package_id}: ecosystem {ecosystem} has no resolver ({', '.join(ECOSYSTEMS)})")
    cutoff = now - timedelta(days=cooldown_days)
    skipped = []
    for version, published, withdrawn in releases(ecosystem, name):
        if want != "latest-safe" and not version_matches(version, want):
            continue
        if published > cutoff or withdrawn:
            continue
        found = advisories(ecosystem, name, version)
        if found:
            skipped.append(f"{version}: {', '.join(found)}")
            continue
        return {"id": package_id, "version": version, "published": published.date().isoformat(),
                "osv_checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "advisories": [], "skipped": skipped[:5]}
    raise ValueError(f"{package_id}: no version is past the {cooldown_days}-day cooldown and free of advisories"
                     + (f" (skipped {'; '.join(skipped[:3])})" if skipped else ""))


def version_matches(version, want):
    """`want` is an exact version or a major/minor prefix such as `5` or `5.4`."""
    return version == want or version.startswith(want.rstrip(".") + ".")


def read_lock(root):
    path = Path(root) / LOCK
    if not path.is_file():
        return {}
    try:
        return {p["id"]: p for p in tomllib.loads(path.read_text()).get("package", [])}
    except (tomllib.TOMLDecodeError, KeyError):
        return {}


def write_lock(root, entries):
    lines = ["# Written by bigbang: the latest breach-safe versions the domain manifests asked for.", ""]
    for entry in sorted(entries.values(), key=lambda e: e["id"]):
        lines += ["[[package]]", f"id = {json.dumps(entry['id'])}", f"version = {json.dumps(entry['version'])}",
                  f"published = {json.dumps(entry['published'])}", f"osv_checked = {json.dumps(entry['osv_checked'])}",
                  f"advisories = {json.dumps(entry['advisories'])}", f"skipped = {json.dumps(entry.get('skipped', []))}", ""]
    (Path(root) / LOCK).write_text("\n".join(lines))


def stale(entry, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        return now - parse_time(entry["osv_checked"]) > timedelta(days=LOCK_DAYS)
    except (KeyError, ValueError):
        return True


# Plan ------------------------------------------------------------------------

def fill_step(text, lock):
    text = text.replace("{determdinistic}", str(DETERMDINISTIC))
    return PLACEHOLDER.sub(lambda m: lock[m.group(1)]["version"] if m.group(1) in lock else m.group(0), text)


def plan_text(domain, manifest, lock):
    scaffold = manifest.get("scaffold") or {}
    lines = [f"# Scaffold plan: {domain} ({manifest.get('summary', '')})", "",
             "Run each step from the project root, in order. Stop at the first non-zero exit and report it.", ""]
    lines += [f"{n}. `{fill_step(step, lock)}`" for n, step in enumerate(scaffold.get("steps", []), 1)] or ["(no steps)"]
    lines += ["", f"Done when `{fill_step(scaffold['check'], lock)}` exits 0.",
              "Report: each step's exit code, then `git status --short`.", ""]
    return "\n".join(lines)


def brief_domain(root):
    """The **Domain** field of sketch/BRIEF.md, read with determdinistic's field audit."""
    path = Path(root) / "sketch/BRIEF.md"
    if not path.is_file():
        return ""
    report, _ = load_determdinistic().audit(path.read_text())
    for section in report["sections"]:
        if "Domain" in section["values"]:
            return section["values"]["Domain"].strip().strip("`").lower()
    return ""


class Scaffold(Module):
    name, stops, always, runs = "scaffold", True, True, True

    def manifests(self, ctx):
        return {d: m for d in ctx.domains if (m := load_manifest(d)) is not None}

    def selected(self, ctx):
        return bool(self.manifests(ctx))

    def probe(self, ctx):
        self.notes, fails = [], []
        lock = read_lock(ctx.root)
        for domain, manifest in self.manifests(ctx).items():
            bad = manifest_fails(domain, manifest)
            if bad:
                fails += bad
                continue
            fails += requires_fails(manifest, ctx.root)
            for package_id in manifest.get("packages") or {}:
                if package_id not in lock or stale(lock[package_id]):
                    fails.append(Fail(f"{package_id} not resolved in {LOCK} (or its advisory check is stale)",
                                      f"bigbang {domain} (resolves the latest breach-safe version)"))
            scaffold = manifest["scaffold"]
            for target in (scaffold.get("files") or {}):
                if not (ctx.root / target).exists():
                    fails.append(Fail(f"{target} missing", f"bigbang {domain} (copies it from the manifest)"))
            if fails:
                continue
            check = fill_step(scaffold["check"], lock)
            result = sh(check, ctx.root, shell=True)
            if result.returncode and manifest["kind"] == "sketch":
                empty = sorted({d.get("key", "") for d in json.loads(result.stdout or "{}").get("diagnostics", [])}
                               - {""}) if result.stdout.strip().startswith("{") else []
                fails.append(Fail(f"sketch/BRIEF.md is not filled in ({', '.join(empty) or 'see its diagnostics'})",
                                  "write the brief and the prototype from the owner's words, show both, "
                                  "and fill **Domain:** when the owner approves a stack"))
                continue
            if result.returncode:
                fails.append(Fail(f"{domain}: `{check}` exited {result.returncode}: {tail(result.stdout + result.stderr, 2)}",
                                  f"hand {PLAN} to a goldfish (a fresh small-model session), then run bigbang"))
                continue
            if manifest["kind"] == "sketch":
                chosen = brief_domain(ctx.root)
                if chosen not in ctx.pack.domains or chosen == "sketch":
                    fails.append(Fail(f"sketch/BRIEF.md names domain `{chosen}`, not an approved stack in PACK.md",
                                      f"show the brief and prototype to the owner; on approval set **Domain:** to one of "
                                      f"{', '.join(d for d in ctx.pack.domains if d != 'sketch')}"))
                else:  # the sketch's job is done; the stack takes over, so the sketch run stops here on purpose
                    rail = (ctx.root / "guardrail.toml").is_file()
                    fails.append(Fail(f"sketch approved for `{chosen}`; the sketch domain stops here",
                                      (f"the owner sets domains = [\"{chosen}\"] in guardrail.toml, then " if rail else "")
                                      + f"bigbang {chosen}"))
            else:
                pinned = [f"{p} {lock[p]['version']}" for p in manifest.get("packages") or {}]
                self.notes.append(f"scaffold: {domain} holds · `{check}` passed" + (f" · {', '.join(pinned)}" if pinned else ""))
        return fails

    def apply(self, ctx):
        root, actions = ctx.root, []
        lock = read_lock(root)
        cooldown = (ctx.rail.get("scaffold") or {}).get("cooldown_days", COOLDOWN_DAYS) \
            if isinstance(ctx.rail.get("scaffold"), dict) else COOLDOWN_DAYS
        for domain, manifest in self.manifests(ctx).items():
            if manifest_fails(domain, manifest):
                continue
            wanted = {p: w for p, w in (manifest.get("packages") or {}).items() if p not in lock or stale(lock[p])}
            if wanted:
                def resolve_all(wanted=wanted):
                    current = read_lock(root)
                    for package_id, want in wanted.items():
                        try:
                            current[package_id] = resolve(package_id, want, cooldown)
                        except (ValueError, urllib.error.URLError, OSError, KeyError) as error:
                            ctx.out(f"scaffold: {error}")
                    write_lock(root, current)
                actions.append((f"resolve {', '.join(wanted)} to the latest breach-safe versions ({LOCK})", resolve_all))
            scaffold = manifest["scaffold"]
            for target, source in (scaffold.get("files") or {}).items():
                if not (root / target).exists():
                    def copy(target=target, source=source):
                        (root / target).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(FILES / source, root / target)
                    actions.append((f"copy {target}", copy))
            actions += ignore_action(root, scaffold.get("ignore", []) + [PLAN])
            if manifest["kind"] == "sketch" or not scaffold.get("steps"):
                continue

            def plan(domain=domain, manifest=manifest):
                (root / PLAN).parent.mkdir(parents=True, exist_ok=True)
                (root / PLAN).write_text(plan_text(domain, manifest, read_lock(root)))
            if not (root / PLAN).is_file() or (root / PLAN).read_text() != plan_text(domain, manifest, lock):
                actions.append((f"write {PLAN} for a goldfish", plan))
        return actions

    def report(self, ctx):
        return getattr(self, "notes", [])
