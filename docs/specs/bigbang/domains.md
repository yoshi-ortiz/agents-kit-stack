# Domains, scaffolds and sketch first

Reached from [bigbang.md](../bigbang.md) build steps 13 and 14.

A **domain** is the stack of a filesystem project: what it is built with and how it is checked. A codebase is one kind; a book, a video edit, a dataset, a homelab or a design library are others. The context compass ([bigbang.md](../bigbang.md) "Taxonomy") is a separate list and never appears here.

## Where a domain lives

- `PACK.md # Domains` keeps what it has today: the domain's skills and `mcp:` servers, loaded through Kit on demand.
- `skills/kit/domains/<name>.toml` holds the **manifest**: the scaffold a goldfish builds. A domain without a manifest still works (skills and MCP only); `bigbang` then reports `scaffold: none declared`.

## Manifest

```toml
name = "astro"
kind = "code"                          # code | docs | media | data | infra | sketch | any word
summary = "Astro static website"
names = ["astro", "static site"]       # words that name this stack in a prompt (skill routing)
requires = ["node>=22"]                # tools that must already exist; probed with `<tool> --version`

[packages]                             # "<ecosystem>:<name>" = "latest-safe" or a range
"npm:create-astro" = "latest-safe"
"npm:astro" = "latest-safe"

[scaffold]
steps = [                              # run in order from the project root; {<ecosystem>:<name>} is the locked version
  "npm create astro@{npm:create-astro} . -- --template minimal --no-install --no-git --yes",
  "npm install astro@{npm:astro} --save-exact",
]
files = { "README.md" = "astro/README.md" }   # copied from skills/kit/domains/files/ when missing
check = "npm run build"                # exit 0 = the scaffold holds
ignore = ["node_modules/", "dist/", ".astro/"]

[guardrail]                            # seeds guardrail.toml for this stack
test = "npm test"
select = "npm test -- -t '^{id}: '"
```

A non-code manifest has the same shape:

```toml
name = "book"
kind = "docs"
summary = "A book written in Markdown, built to HTML and EPUB"
names = ["book", "novel", "manuscript"]
requires = ["pandoc>=3"]

[scaffold]
steps = ["mkdir -p chapters dist"]
files = { "book.md" = "book/book.md", "chapters/01.md" = "book/01.md" }
check = "pandoc book.md chapters/*.md -o dist/book.html"
ignore = ["dist/"]

[guardrail]
test = "pandoc book.md chapters/*.md -o dist/book.epub"
select = "grep -l '{id}' chapters/*.md"
```

Probe fails on: a missing required key (`name`, `kind`, `summary`, `scaffold.check`), a `{…}` placeholder with no `[packages]` entry, a `files` source that does not exist, a `requires` tool that is absent or too old.

## Breach-safe versions

`latest-safe` resolves, per package, to the newest version that:

1. was published at least `[scaffold] cooldown_days` ago (default 7, in `guardrail.toml`): a fresh release has had time for a compromised publish to be caught;
2. has no advisory in OSV (`https://api.osv.dev/v1/query`, by ecosystem, name and version);
3. is not yanked or deprecated in its registry.

Registries: npm (`registry.npmjs.org/<name>`, `time`, `deprecated`), PyPI (`pypi.org/pypi/<name>/json`, `upload_time_iso_8601`, `yanked`), crates.io (`/api/v1/crates/<name>/versions`). Pre-releases are skipped. Any other ecosystem (Go included, for now) fails with its name, never a guess. A version prefix (`"5"`, `"5.4"`) narrows `latest-safe` to that line.

Resolution needs the network, so it runs in `apply` and writes **`scaffold.lock`** (versioned):

```toml
[[package]]
id = "npm:astro"
version = "5.4.1"
published = "2026-11-12"
osv_checked = "2026-11-27T10:00:00Z"
advisories = []
```

The probe reads the lock alone ($0, offline). A lock entry older than 30 days, or a manifest package missing from the lock, fails with `fix: bigbang <domain>` (re-resolve). A newer safe version only shows as a report line (`scaffold: astro 5.5.0 is now safe; bigbang <domain> --upgrade`), because changing versions is the owner's call.

## The scaffold module and the goldfish

`scaffold` (`stops = True`, runs before `stage0`) for each selected domain with a manifest:

1. Probe: `requires` present; lock fresh; `check` exits 0. A project whose `check` already passes (an existing codebase) is `ok` without scaffolding.
2. Apply: resolve the lock, then write `.bigbang/scaffold-plan.md`: the goldfish's whole brief.

```markdown
# Scaffold plan: astro (summary)
Run each step from the project root, in order. Stop at the first non-zero exit and report it.
1. `npm create astro@4.11.0 . -- --template minimal --no-install --no-git --yes`
2. `npm install astro@5.4.1 --save-exact`
Copy when missing: README.md ← skills/kit/domains/files/astro/README.md
Done when `npm run build` exits 0. Report: each step's exit code, then `git status --short`.
```

3. Copy the manifest's `files` and write the plan. The agent hands the plan to a goldfish: a fresh small-model session (Haiku class) with the plan and nothing else. The plan is complete enough that the goldfish needs no reasoning about the stack. On a host with no session tool, the agent runs the plan itself.
4. `bigbang` runs again; `scaffold` probes `check`. `ignore` entries are appended to `.gitignore`; `[guardrail]` seeds `guardrail.toml` when that file does not exist yet.

`bigbang` copies the manifest's `files` itself (they come from Kit, not a registry) and never runs scaffold steps: they install third-party code, so a step runs in an agent session where the host's permission prompts apply.

## Sketch first

Routing, in the skill:

- The prompt names a stack (a domain's `names` word, or an explicit tool such as "Godot") → `bigbang <domain>`. No domain declares it → the agent drafts a manifest for the owner to approve, then runs it.
- Otherwise → `bigbang sketch`. No stack is chosen before the owner approves a sketch.

`sketch` is a domain like any other, with no packages:

```toml
name = "sketch"
kind = "sketch"
summary = "A brief and a prototype the owner can open, before any stack"
names = ["idea", "prototype", "brainstorm"]

[scaffold]
steps = ["mkdir -p sketch/prototype"]
files = { "sketch/BRIEF.md" = "sketch/BRIEF.md", "sketch/prototype/index.html" = "sketch/index.html" }
check = "python3 {determdinistic} sketch/BRIEF.md"   # every field filled; see below
```

`sketch/BRIEF.md` template, read with determdinistic's field audit:

```markdown
# Brief
- **Goal:** <one sentence: what exists when this is done>
- **For:** <who uses it>
- **Owner words:** <the prompt, verbatim>
- **Constraints:** <budget, platform, deadline>
- **Domain:** <empty until the owner approves; then a domain name>
```

- The prototype is a single static page the owner opens with no build: an HTML mock for an app or site, a diagram for a system, an outline or storyboard for a book or video.
- `check` fails while any field is empty, so `scaffold` stays red until the brief is complete. Once **Domain** names an approved stack, `scaffold` still stops the sketch run on purpose, with `fix: bigbang <domain>`: the compass is installed for the real stack, never for the sketch.
- `PACK.md ## sketch` lists the sketch tooling, loaded on demand: a frontend-design skill for HTML mocks, a diagramming skill, research. On Claude Code the agent may also publish the prototype as an artifact for the owner to open.
- When the owner approves, the agent fills **Domain** and runs `bigbang <domain>`; `sketch/` stays as the project's first design record.
