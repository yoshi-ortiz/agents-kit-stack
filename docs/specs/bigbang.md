# Bigbang spec

Status: v4, 2026-11-27. Built: steps 1–7 and 9–14 (step 8, paid adapters beyond Claude, is open). Manual acceptance 7 and 24 are not run yet. Sources: [GOAL.md](../../GOAL.md) "Planned skill goals", homelab-infra `drive/docs/agents/shot-lessons.md` (dev 749cead7), and the failures in its `cpu/platform/eval/agent-shot` ([failures.md](bigbang/failures.md)).

This file holds what every build step needs: goals, taxonomy, flow, surface, the module contract, the build steps, acceptance. Each part's rules live in its own file under [bigbang/](bigbang/), reached from the build step that builds it.

## Goals

1. **Shots vs tanks, per vendor.** The first job: audit and fix what each vendor harness (Claude Code, Codex, Antigravity, any agent in `PACK.md # Agents`) loads before the first prompt (its *context shot*), against what it spends to finish real work (its *tank*). A fix is kept only when the tank drops beyond noise at an equal or higher pass rate ([shots-tanks.md](bigbang/shots-tanks.md)).
2. **Brief before stack.** A prompt that names a stack ("make an Astro static website", "make a Godot videogame") goes straight to that domain. Any other prompt starts with a brief and a sketch the owner sees and approves; the stack follows the approved sketch ([domains.md](bigbang/domains.md) "Sketch first").
3. **Domains are projects, not only code.** A domain is the stack of a filesystem project: a codebase, a book, a video, a dataset, a homelab. Each declares a scaffold a goldfish (a small model such as Haiku) can build from the declaration alone, at the latest breach-safe versions ([domains.md](bigbang/domains.md)).
4. **One command.** `bigbang <domain...>` makes the directory a ready, guarded, audited agentic dev environment for that stack.
5. **Re-run is the check.** Every module probes real state, repairs what is missing, probes again. A second run on a ready checkout prints only `ok` lines and writes nothing.
6. **Evidence only.** A result counts only when a command produced it: an exit code, a file hash, a git ancestry check, a token count from the vendor's own output. Agent-written status, prose counts and lockfiles carry zero weight (AGENTS.md rule 4).
7. **Chat first.** A session starts with `@ROADMAP.md`. The owner asks for status, reprioritizes and changes the spec by chat; the agent answers from `bigbang` output and edits `ROADMAP.md` with the owner's approval ([loop.md](bigbang/loop.md) "Chat").
8. **Burndown from evidence.** Roadmap progress is computed from tagged tests and evidence checks on `base`, keyed by the project's own ticket ids ([burndown.md](bigbang/burndown.md)).
9. **Money is explicit.** Every run without `--paid` costs $0. Context shots are $0 probes; tanks are paid.
10. **Parity and zero context.** All agents in `PACK.md # Agents` get the same behaviour. Catalog skills load through `kit use` when a step needs them.

Out of scope: journey GIFs as a gate (a project adds one under `[evidence]`), the homelab state-matrix QA, `next`/`live` as commands (both are lines `bigbang` prints).

## Taxonomy

Two lists that never mix:

| List | Answers | Lives in | Chosen by | Examples |
| --- | --- | --- | --- | --- |
| **Domain** | What is this project built with? | `PACK.md # Domains` plus `skills/kit/domains/<name>.toml` | the prompt or the approved sketch | `sketch`, `astro`, `godot`, `ios`, `cloud`, `book` |
| **Context compass** | How do agents work in it, and what does that cost? | `PACK.md # Context compass` | the owner; `core` is always on | `core`, `goals`, `babysitter`, `tanks` |

| Compass layer | Modules | When |
| --- | --- | --- |
| `core` | guardrail, gate, burndown, loop, index, shots | always |
| `goals` | goals (was `intake`): the owner's words verbatim, `req:` on every ticket | the owner wants the trace |
| `babysitter` | babysitter: CEO > CTO > SWE goldfish, `bigbang ledger` | `shot:` prompts |
| `tanks` | tanks: paid token spend per vendor on the case suite | the owner asks (`--paid`) |

Python files keep their own names: `goals` lives in `verbatim.py`, `tanks` in `tokens.py`, `babysitter` in `loop.py`.

The selection persists in `guardrail.toml` (`domains = [...]`, `compass = [...]`), so a later `bigbang` with no arguments re-checks the same project.

## Flow

1. **Prompt.** Names a stack → step 4 with that domain. Otherwise → step 2.
2. **Brief.** `bigbang sketch` scaffolds `sketch/`: `BRIEF.md` (goal, who it is for, constraints, the owner's words) and a prototype the owner can open (an HTML page, a diagram, a storyboard). The agent fills both and shows them.
3. **Approve.** The owner approves the sketch or changes it by chat. The approval names the domain (the agent proposes one from `PACK.md # Domains`; none fits → it proposes a new domain manifest).
4. **Scaffold.** `bigbang <domain>` resolves the domain's declared versions to the latest breach-safe ones, writes `scaffold.lock`, and prints the scaffold plan. A goldfish runs the plan; `bigbang` probes the domain's `check` command until it passes.
5. **Compass.** `core` (and any chosen layer) installs the guardrail, roadmap, loop, the context index and the first context shot per vendor. The session from here starts with `@ROADMAP.md`.

## Context index (core)

`index` manifests one convention on every project: `AGENTS.md` is the single index every vendor reaches, and it points rather than holds.

- A managed block between `<!-- bigbang:index -->` and `<!-- /bigbang:index -->` lists one pointer per context file that exists (`ROADMAP.md`, `guardrail.toml`, `HALLUCINATIONS.md`, runbooks, `sketch/BRIEF.md`, `docs/specs/`, `GLOSSARY.md`, `TANKS.md`) and every nested `*/AGENTS.md`, each with when to read it. `bigbang` owns only the text between the markers; it appends the block to an existing `AGENTS.md` and rewrites it when stale.
- A host that reads another memory file gets it with `@AGENTS.md`: `CLAUDE.md` (Claude Code) and `GEMINI.md` (Antigravity; that Antigravity honors the import is unverified). An existing memory file without the import fails with the line to add; `bigbang` leaves the file as it is.
- Every pointer resolves. The index stays small because `shots` budgets the memory category it loads into.

## Vendor model specs and prompting docs

`skills/bigbang/vendors.toml` lists each vendor's consumable sources; `shots` caches them under `~/.cache/kit/vendors/<vendor>/` and refreshes them after `max_age_days` (7):

| Vendor | Agents | Model spec ($0, local) | Prompting docs |
| --- | --- | --- | --- |
| anthropic | claude-code | `claude -p /context …`: model id and context window | `https://platform.claude.com/llms.txt` |
| openai | codex | `codex debug models`: every listed model, its context window, and its own instructions template (saved as `prompting-<model>.md`) | `https://learn.chatgpt.com/docs/llms.txt` |
| google | antigravity | none known | `https://aistudio.google.com/llms.txt` |
| pi | pi | `pi --list-models` | none known |
| cursor, zed | — | none known | none known |

Tanks read the cache to label each card with the model spec; agents read `docs.txt` and `prompting-*.md` when writing prompts or skills for that vendor.

## Surface

```
bigbang [domain...] [--compass goals,babysitter,tanks] [--dry-run] [--paid] [--sync] [--only <module>] [--cases <id,...>]
bigbang goals <quote-file>
bigbang brief
bigbang ledger start <role> <name> <session-id> | end <name> <sha> | park <name>
```

| Flag / verb | Effect |
| --- | --- |
| `domain...` | The project's stack(s) from `PACK.md # Domains`. Required on a directory with no `guardrail.toml`; later runs read `domains` from it. |
| `--compass` | Optional context compass layers beside `core`. Persisted as `compass` in `guardrail.toml`. |
| `--dry-run` | Every selected module runs `probe` and prints `would: <action>` for each `apply` it would make. Writes nothing, spends nothing; wins over `--paid`. |
| `--paid` | `tanks` may run paid tanks. Without it `tanks` runs only the oracle. |
| `--sync` | `burndown` pipes a new burndown row to `[ids] export` (a tracker write). Without it nothing leaves the machine. |
| `--only <module>` | Runs that one module (and `git`). The merge hooks use `--only gate`. |
| `--cases` | Passed to `tanks`; any subset makes the card `partial`. |
| `brief` | Prints the shot brief: burndown, a receipt per ticket, status screenshots ([burndown.md](bigbang/burndown.md) "Receipts and the shot brief"). |
| `goals` | Appends the owner's words from a file to the requirements page verbatim, with today's date and the next `R` id ([goals.md](bigbang/goals.md)). |
| `ledger` | The one writer of `.bigbang/sessions.jsonl` ([loop.md](bigbang/loop.md)). |

Entry point: `python3 skills/kit/packages.py bigbang ...`. `packages.py`'s `bigbang()` builds `ctx` and hands control to `skills/bigbang/modules.py`.

**Output.** One line per finding, then exit.

```
ok: git
ok: scaffold: astro 5.x pinned in scaffold.lock · check `npm run build` passed
FAIL: guardrail: guardrail.toml: `base` names branch `develop`, which does not exist · fix: set base in guardrail.toml
shot: claude-code · 18.2k tokens at start · skills 1.1k · mcp 4.0k · memory 2.3k
burndown: Epic … (report lines, see burndown.md)
```

- `ok: <module>`, `done: <module>: <action>` (an apply that ran), `would: <module>: <action>` (dry run), `FAIL: <module>: <problem> · fix: <command or edit>`, and report lines prefixed with the module name.
- Exit 0 when every selected module ends with an empty probe; exit 1 otherwise.

## Module contract

```python
@dataclass(frozen=True)
class Fail:
    problem: str
    fix: str                      # a command or the exact edit; tests assert it is non-empty

@dataclass
class Ctx:
    root: Path                    # git toplevel (or cwd before `git` applies)
    pack: "Pack"                  # parsed PACK.md
    kit: ModuleType               # the running packages.py module: sys.modules[packages.bigbang.__module__]
    domains: list[str]
    items: list["Item"]           # every Item of the selected domains
    dry: bool
    paid: bool
    sync: bool
    only: str | None
    cases: list[str] | None
    rail: dict                    # parsed guardrail.toml, {} until `guardrail` passes

class Module:
    name: str
    stops: bool                   # True: a FAIL stops the run (setup). False: FAIL is reported, the run continues.
    def selected(self, ctx) -> bool: ...
    def probe(self, ctx) -> list[Fail]: ...      # reads real state; [] means ok
    def apply(self, ctx) -> list[Action]: ...     # Action = (text, do); the runner calls `do` only outside --dry-run
    def report(self, ctx) -> list[str]: ...       # optional extra lines (burndown graph, tank card summary); default []
```

```python
MODULES = [git, catalog, domains, scaffold, stage0, mcp, guardrail, goals, gate, burndown, loop, babysitter, tanks, index, shots, verify]  # run order
```

The **guardrail** is what keeps every change honest: `guardrail.toml`, `HALLUCINATIONS.md`, the owner-owned paths and the hooks that hold the gate.

| Module | `stops` | Selected by |
| --- | --- | --- |
| `git`, `catalog`, `domains`, `stage0`, `mcp` | yes | always (`stage0` only with a `mise.toml`/`.mise.toml`) |
| `guardrail` | yes | `module:guardrail` |
| `goals` | no | compass `goals` |
| `scaffold` | yes | a domain with a manifest (v4) |
| `shots` | no | compass `core` (v4) |
| `gate` | no | `module:gate` |
| `burndown` | no | `module:burndown` |
| `loop` | no | `module:loop` |
| `babysitter` | no | `module:babysitter` |
| `tanks` | no | `module:tanks` |
| `verify` | no | always, last |

Setup modules stop the run because later modules read what they create. Report modules continue, so a red gate during a step's skeleton still prints the burndown and `next:` the loop acts on.

**Runner**, per selected module in `MODULES` order:

1. `fails = probe(ctx)`. Empty → print `ok: <name>`, print `report(ctx)`, continue.
2. `dry` → print each `apply` action as a `would:` line without calling it, and continue. A module marked `runs` (its probe runs project commands: `stage0`, `mcp`, `gate`, `tanks`, `verify`) prints `would: <module>: run its checks` instead of probing. A dry run exits 1 only when a failing module has no action to fix it.
3. Otherwise `apply(ctx)`, then `fails = probe(ctx)`, print `report(ctx)`.
4. Print each remaining fail. A `stops` module with fails ends the run with exit 1.

**Wrapping today's functions.** `domain()`, `verify()`, `kit-starter-pack` and `mcp_starts()` report problems through `gate()`, which prints and calls `sys.exit(1)`. Modules call them through one helper:

```python
def contained(fn, *args, **kw) -> tuple[list[str], list[str]]:
    """Run fn; return (stdout lines, problem lines). SystemExit becomes problem lines (the `  - ` lines gate printed)."""
```

It redirects stdout with `contextlib.redirect_stdout`, catches `SystemExit`, and splits `gate()`'s `  - ` lines into problems. `gate()` itself stays unchanged, so every other `packages.py` verb behaves as today.

**Rules every module keeps:**

- **Create, then hand over.** `apply` writes a file only when it is missing. After that the file is the owner's: `probe` checks it against its schema and reports a violation as a `Fail` naming the key, the found value and the expected form.
- **Probe reads real state:** files, git, exit codes. Markers and "installed" ledgers carry zero weight.
- **Idempotent.** The runner calls `apply` only on a failing probe; `apply` twice equals `apply` once.
- **Tight.** Probes run local commands only. Network, paid model calls and full test suites run in `apply` or behind a cache keyed by commit sha.

## Code

| File | Holds |
| --- | --- |
| `skills/kit/packages.py` | `Item`, `Pack.items`, `BIGBANG_MODULES`; `bigbang()` loads `skills/bigbang/modules.py` and calls `main()` |
| `skills/bigbang/base.py` | `Fail`, `Ctx`, `Module`, git and file helpers, ticket id forms, the determdinistic loader |
| `skills/bigbang/modules.py` | the runner, `contained()`, setup modules, `MODULES`, the CLI (`ledger`, `goals`, flags) |
| `skills/bigbang/guardrail.py` | `guardrail` (schema, templates, hooks, ask rules) and `gate` |
| `skills/bigbang/verbatim.py` | the `goals` layer and `bigbang goals` |
| `skills/bigbang/index.py` | `index`: the context indexing convention |
| `skills/bigbang/shots.py` | context-shot probes per vendor, leaks, the vendor cache |
| `skills/bigbang/vendors.toml` | each vendor's model-spec command and docs URL |
| `skills/bigbang/scaffold.py` | domain manifests, breach-safe resolver, `scaffold.lock`, goldfish plan |
| `skills/kit/domains/<name>.toml` | one manifest per domain (`sketch`, `astro`, `book` today) |
| `skills/bigbang/burndown.py` | the roadmap read through determdinistic, states, cache, report |
| `skills/bigbang/loop.py` | `loop`, `babysitter`, `bigbang ledger` |
| `skills/bigbang/tokens.py` | cases, oracle, adapters, card, `TANKS.md` verdicts |
| `skills/bigbang/templates/` | every file a module writes into a project |
| `skills/bigbang/modules_test.py` | the acceptance items as tests against throwaway repos |
| `skills/determdinistic/determdinistic.py` | `tickets`: the ticket index and many-to-many links (DuckDB with `--sql`) |

**Empty projects.** A project with no manifest gets `test = ""`: `guardrail` reports `test unset` and the gate reports that rule 1 has nothing to run. An empty requirements page reports `no requirements yet`. Both are report lines, so acceptance 1 holds on a fresh directory, and each line names what to add.

## Domain items

`PACK.md # Domains` items become typed in the PACK parser (`Pack.__init__`, the `domains` branch near `packages.py:183`):

```python
@dataclass(frozen=True)
class Item:
    kind: Literal["skill", "mcp", "module"]
    name: str            # "owner/repo:skill", "tree-sitter", "guardrail"
```

- `mcp:<name>` → `Item("mcp", name)`; `module:<name>` → `Item("module", name)`; anything else → `Item("skill", text)`. `owner/repo: a, b` grouping keeps working (its prefix is a repo, not a kind).
- `Pack.domains[d]` stays `list[str]` of skill tokens for today's callers; a new `Pack.items[d]: list[Item]` carries all three kinds. The prefix checks at `packages.py:338` (`resolve`), `:1151` (`domain`) and `:1254` (`skill_tags`) read `Pack.items` and filter on `kind`. Without this, `packages.py core` passes `module:guardrail` to `resolve()` as a skill and fails.
- `module:<name>` must name a module in `MODULES`, else the parser reports `PACK.md:<line> module:<name> is not a bigbang module`. The parser holds the names as a constant list (`BIGBANG_MODULES`) so `packages.py` never imports `modules.py` to parse.
- v4: `module:` items leave `# Domains`. A new `PACK.md # Context compass` section lists one `## <layer>` per compass layer (`core`, `goals`, `babysitter`, `tanks`), each with its `module:` items; `Pack.compass[layer]: list[Item]`. A `module:` item under `# Domains` fails parsing: domains name stacks only.

## Build steps

Each step lands as its own commit on `dev`, with its tests, and leaves `python3 -m unittest …` (AGENTS.md command, extended in step 1) and `python3 skills/kit/packages.py` green. Each step reads only the reference files it names.

1. **Items.** Add `Item`, `Pack.items`, `BIGBANG_MODULES`; move the three prefix sites to `kind`; add the `module:` lines to `PACK.md`. Add `skills/bigbang/modules_test.py` to the AGENTS.md test command. *Done when* `packages.py core --dry-run` resolves the same skills as before the change, a `module:nope` line fails parsing with its line number, and the parser tests cover all three kinds.
2. **Runner.** `skills/bigbang/modules.py` with `Fail`, `Ctx`, `Module`, `contained()`, the runner, and the always-on modules (`git`, `catalog`, `domains`, `stage0`, `mcp`, `verify`) ported from today's `bigbang()`. `bigbang()` shrinks to building `Ctx` and calling `modules.run(ctx)`. *Done when* on a fresh empty dir and on this repo, the new `bigbang` prints the same ok/FAIL findings as the old one in the new format (diff the two outputs), a second run writes nothing (`git status --porcelain` unchanged), and `--dry-run` writes nothing.
3. **Guardrail and gate.** [guardrail.md](bigbang/guardrail.md): templates, schema probe, hooks, the five gate rules. *Done when* acceptance 2, 3 and 12 pass as tests against throwaway repos built in `tempfile` dirs.
4. **Goals** (built as `intake`; renamed in step 10). [goals.md](bigbang/goals.md): requirements page, `bigbang goals`, the trace probes. *Done when* acceptance 13 and 14 pass.
5. **Burndown.** [burndown.md](bigbang/burndown.md): ticket ids, step parser, state rules, sha cache, graph, `next:`, `--sync`. *Done when* acceptance 8, 9, 15, 16 and 17 pass.
6. **Loop.** [loop.md](bigbang/loop.md): both runbooks as templates, `bigbang ledger`, the ledger probe. *Done when* acceptance 10 passes and each runbook step ends on a completion criterion a command can check.
7. **Tanks.** [shots-tanks.md](bigbang/shots-tanks.md): runner, adapters, card, ledger, hillclimb verdict. The oracle and claude adapters first. *Done when* acceptance 4 and 5 pass with the oracle alone, at $0.
8. **Adapters.** Before writing each remaining adapter, run one headless case on that CLI by hand and save its raw output as a test fixture under `skills/bigbang/fixtures/<tank>.jsonl`. *Done when* every tank in [shots-tanks.md](bigbang/shots-tanks.md) "Adapters" parses its saved fixture into the adapter contract, or is listed `unmeasured` with its reason.
9. **Skill and docs.** Rewrite `skills/bigbang/SKILL.md` (still short: the command, the flags, "report the ok and FAIL lines", a pointer to `runbooks/loop.md` in the project), update the usage block at the top of `packages.py`, and GOAL.md's Bigbang paragraph. *Done when* all acceptance items pass, `verify --strict-context` passes, and `dev-sync` reaches all six agents.

v4 steps:

10. **Taxonomy.** Split `PACK.md` into `# Domains` (stacks) and `# Context compass` (`core`, `goals`, `babysitter`, `tanks`); rename `intake` → `goals` in code, templates and output; `--compass`; persist `domains` and `compass` in `guardrail.toml`; a directory with no `guardrail.toml` and no domain argument fails naming `bigbang sketch` or a domain. *Done when* acceptance 18 and 19 pass and the v3 tests pass under the new names.
11. **Shots.** [shots-tanks.md](bigbang/shots-tanks.md) "Shots": the `shots` module in `core`, a $0 context-shot probe per vendor, the shot card, the fixes it proposes and applies. *Done when* acceptance 20 and 21 pass.
12. **Shots vs tanks.** Tank rows carry each run's shot share; `TANKS.md` verdicts cover shot fixes. *Done when* acceptance 22 passes.
13. **Domain manifests.** [domains.md](bigbang/domains.md): `skills/kit/domains/<name>.toml`, the breach-safe resolver, `scaffold.lock`, the `scaffold` module, the goldfish brief. Manifests for `sketch` plus one code and one non-code domain. *Done when* acceptance 23 and 24 pass.
14. **Sketch first.** The `sketch` domain's scaffold and tooling; the skill's prompt routing (stack named → domain; else brief). *Done when* acceptance 25 passes.

## Acceptance

Each item is a unit test unless marked *manual*.

1. Fresh empty dir: `bigbang` exits 0; a second run prints only `ok` and report lines and writes nothing (`git status --porcelain` unchanged).
2. `guardrail.toml` with a schema violation (`reps = "three"`): re-run prints a `Fail` naming the key, the value and the expected type, and leaves the file byte-identical. A valid owner edit (`reps = 5`) prints `ok: guardrail`.
3. Each alone makes `gate` fail: branch behind `base`; a red `test`; a changed `[limits]` path; an owner-owned file changed in a commit without `Owner-Approved:`.
4. `bigbang core tanks` without `--paid` spends $0 (oracle only) and fails naming `bigbang core tanks --paid` while a paid tank's card is stale.
5. `--cases` subset, or a cost-cap stop: card `partial: true`, probe fails.
6. `--dry-run` writes nothing and spends nothing, with every flag combination.
7. *Manual:* `python3 skills/kit/packages.py` passes for all six agents; `verify --strict-context` shows every core skill and zero catalog skills at startup.
8. A `Status: live` line in `ROADMAP.md` on a step whose tagged test fails: `burndown` prints `red`.
9. Two runs on the same `base` sha append one burndown row, and both print the same `Changed` column.
10. `bigbang ledger start swe b …` while `swe a` is live fails; an entry older than `stale_hours` does not block.
11. Unit tests green.
12. A merge into `base` with a red test is refused by the hook; the same merge with the test green succeeds.
13. With the `goals` layer: `bigbang goals words.txt` appends the file's bytes unchanged under a new `R` id with today's date; a second identical call appends nothing and prints `ok: goals: already R<n>`.
14. With the `goals` layer, a step with no `req:`, or a `req:` naming an unknown `R` id, fails `goals`; a requirement no step traces to is reported as `uncovered: R<n>`.
15. A red gate on the working branch still prints the burndown and `next:` line.
16. The same roadmap and tests, keyed once by `ENG-12`/`ENG-123` (default pattern) and once by `S1`/`BUG-7` (pattern `(S|BUG)-?[0-9]+`), print the same states; a test tagged `_ENG_12_` never counts for `ENG-123`; an id the pattern rejects fails the probe with its line.
17. A ticket marked Done in the tracker with its tagged test failing prints `red`; without `--sync`, `[ids] export` never runs.
18. `PACK.md` with `module:goals` under `# Domains` fails parsing with its line; `bigbang astro --compass goals` writes `domains = ["astro"]` and `compass = ["goals"]`, and a bare `bigbang` afterwards checks the same selection.
19. An empty directory with no domain argument fails: `name a domain, or start with bigbang sketch`.
20. `shots` on a checkout prints one `shot:` line per agent with a $0 probe (Claude Code, Codex) and `unmeasured` with its reason for the rest; spend stays $0.
21. A seeded leak (a catalog skill made model-visible, or an MCP server outside the project's domains) raises that vendor's shot, fails `shots` naming the leak and its fix, and the fix brings the shot back under budget.
22. A paid tank run records shot tokens beside run tokens per case; a shot fix that lowers tokens/pass beyond the spread gets `keep` in `TANKS.md`, and one that does not gets `revert`.
23. A domain manifest naming a package version younger than the cooldown, or one with a known advisory, resolves to the newest version that is neither; `scaffold.lock` records the resolved versions and the advisory source; a second run resolves nothing and writes nothing.
24. *Manual:* a Haiku-class goldfish given only the printed scaffold plan builds the domain's boilerplate, and the domain's `check` passes (one code domain, one non-code domain).
25. `bigbang sketch` writes `sketch/BRIEF.md` and a prototype page; `scaffold` fails until `BRIEF.md` has its goal and the owner's words, and the domain probe fails until the brief names an approved domain.

## Resolved conflicts

Draft v1 contradicted itself or the code in these places. Each resolution is in the text above; this list keeps the reason.

| Draft v1 | Conflict | v2 |
| --- | --- | --- |
| "a module with fails stops the run" | A red gate (normal mid-step) would hide the burndown and `next:` the loop needs; open steps would stop `tanks` and `verify`. | `stops` per module: setup stops, report modules continue. Open steps are report lines, never fails. |
| Acceptance 2: "edited `guardrail.toml` → FAIL naming the difference" | Contradicts goal 2: every owner edit would fail forever. | Probe checks the schema; a valid owner edit is `ok`. |
| "Agents should hold `ask` permission on these two paths" | Rule 4 lists three paths, plus the new requirements page. | Four owner-owned paths, one list in [guardrail.md](bigbang/guardrail.md). |
| "Merge hook" | Git has no hook for fast-forward merges; `pre-merge-commit` runs only for merge commits. | `pre-merge-commit` plus `pre-push` on `base`; see [guardrail.md](bigbang/guardrail.md). |
| `live` "no `[limits]` path is named against it" | Undefined. | A step line's `limit: <name>` marks it owner-blocked; see [burndown.md](bigbang/burndown.md). |
| `open` vs `red` from the `select` exit code | Most runners exit non-zero both for "no tests selected" and "tests failed". | `open` comes from a `git grep` for the tag; the exit code only splits `red`/`green`. |
| `kit egm:egm-bootstrap` writes `EGM.md` | No EGM source is in `PACK.md # Batteries included`; the command fails today. | Open decision 3. |
| Tanks `claude`, `codex`, `gemini` | Six agents in `PACK.md`; `gemini` is none of them. | Tanks named by `PACK.md` agent; hosts without a headless CLI are `unmeasured` on the card and in `verify` output. |
| Ledger lines `start <role> …` | No writer named; hand-written lines are agent-written status. | `bigbang ledger` is the one writer. |

## Open decisions

Each has a proposed default the build uses until the owner rules. Changing one is a one-place edit in the named file.

1. **Self-edit enforcement** ([guardrail.md](bigbang/guardrail.md)). Proposed: both. Host `ask` permission on the owner-owned paths is the enforcement (an agent can write any trailer); the `Owner-Approved:` trailer is the audit record the gate checks.
2. **Tank cases** ([shots-tanks.md](bigbang/shots-tanks.md)). Proposed: rail-check cases first (a seeded change: does the agent reach a passing `gate`, at what token cost), because they measure this harness. The 23 homelab cases stay in homelab.
3. **EGM contracts** ([loop.md](bigbang/loop.md)). Add an EGM source to `PACK.md`, or have goldfish briefs carry only the step line and its red test. Proposed: the latter until a source exists.
4. **Token metric** ([shots-tanks.md](bigbang/shots-tanks.md)). Decided in v4: `tokens = input + cache_write + cache_read + output`, because the context shot comes back as cache reads on every turn; `cost_usd` (vendor-reported) is the tie-breaker.
5. **Antigravity** ([shots-tanks.md](bigbang/shots-tanks.md)). Antigravity has no headless CLI and no known prompt dump. Proposed: its shot is estimated from the files it loads (rules, skills listing, MCP config) and labelled `estimated`; its tank stays `unmeasured`.
6. **Tree-sitter** ([loop.md](bigbang/loop.md)). Proposed: MCP for locating code only; `git grep -c 'TODO({id})'` stays the burn count.
8. **Context shot** ([shots-tanks.md](bigbang/shots-tanks.md)). Read as: what a vendor harness puts in the model's context before the first prompt (system prompt, tool and MCP schemas, skill listing, memory files such as `AGENTS.md`), measured by that vendor's own free dump. Confirm this reading.
9. **Breach-safe** ([domains.md](bigbang/domains.md)). Proposed: the newest version published at least 7 days ago with no OSV advisory affecting it; the cooldown is `[scaffold] cooldown_days` in `guardrail.toml`.
7. **Tracker write-back** ([burndown.md](bigbang/burndown.md)). Proposed: `bigbang` ships no tracker client; `[ids] export` is a project script run only with `--sync`. Linear links come free from ids in branch names and commit subjects.
