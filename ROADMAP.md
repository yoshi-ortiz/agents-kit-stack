# Roadmap

The burndown. One row per item, each in exactly one state, so "what is left"
is answerable without reading prose.

States: `TODO` · `IN-PROGRESS` · `BLOCKED` · `DONE`

Bugs live in [BUGS.md](BUGS.md) with their root causes. Shipped changes live in
[CHANGELOG.md](CHANGELOG.md). This file is what remains.

Fog. Lives on `dev`, never published to `main`.

Contract and vocabulary: [SPEC.md](SPEC.md), [GOAL.md](GOAL.md),
[UBIQUITOUS_LANGUAGE.md](UBIQUITOUS_LANGUAGE.md). Promoted specs live under
`docs/SPEC/`.

## The rail

Six **families**, one command surface. Prefix routes; no router command.

| Family | Phase | Shipped in this repo | Planned owner |
| --- | --- | --- | --- |
| `kit` | Day 0 on-ramp | `kit/` (`starter-pack`, `silly` nested) | `kit/SKILL.md` |
| `first` | Plan | `first/genesis/`, `first/knowledge/`, `first/aesthetic/` | genesis + aesthetic |
| `build` | Code · Build · Test | — | `build/SKILL.md` |
| `land` | Release · Deploy | — | `land/SKILL.md` |
| `check` | Monitor (return arc) | `check/build-context-token-vectors/` | `check/SKILL.md` |
| `fix` | Operate (bare on-ramp) | — | `fix/SKILL.md` |

```text
kit → first → build → land
        ↑         │
        └── check ┘
        └── fix ──┘
```

Eat-your-own-food: Repo-Dev work runs through these skills. After a commit here,
`kit sync` re-arms the collection; graphics and the landing hero ship through
`aesthetic` / `text-to-graphics` on **this** checkout (`design/`,
`shots/landing.hero.flow.svg`), not hand-copy.

Out of repo scope: work that only applies to an external design fixture (e.g.
`keynote-performance` preview redraws). Harness lessons from that fixture stay;
the fixture's ledger does not.

## Agent burndown: two sprint groups

The ordering tables are indexes, not duplicate state. Every referenced `R-`
row appears once below with its canonical state. A fresh agent takes one atomic
row, starts with its deterministic red check, produces one reviewable diff,
and stops at the commit/push boundary unless the user approved crossing it.

| Program Epic | North star |
| --- | --- |
| **Genesis** | Reusable deterministic declarations and Assistant apps platform exist before domain adapters build on them. |
| **Cook** | A lean router composes diagnostics, Tokens QA, tokens ontology, Moses, and reviewed git delivery without owning their rules. |
| **Aesthetic** | Graphics inference is the main value; its Assistant app and domain-tool escalation make that value observable and project-specific. |

### Sprint Group 1: quick wins and executable seams

| Rank | Program Epic | Sub-epic | Atomic rows | Exit |
| ---: | --- | --- | --- | --- |
| 1 | Cook | MVP router | R-82, R-74 | Routes `zoom-out` → `diagnosing-bugs` → `ponytail-review` → reviewed commit/push; contains no copied diagnostic doctrine. |
| 2 | Genesis | deterMDinistic | R-69, R-61, R-70, R-87, R-88, R-89 | One lean contract turns declared module state into replayable Markdown/TSV/JSON, guards exact values procedurally, and records deterministic outcomes without making public comparisons authoritative. |
| 3 | Cook | Tokens QA | R-63, R-65, R-68, R-73 | One real invocation yields a correlated RL trajectory, Shot ID, and visible QA table through an agent-session adapter. |
| 4 | Aesthetic | Assistant app adapter | R-18, R-60, R-83 | Ranking, brief, and corpus tags round-trip through the reusable live-state contract. |
| 5 | Aesthetic | Graphics domain escalation | R-72, R-84, R-86 | Common powerful graphics tools are in the harness manifest; niche project tools are researched and recorded before custom generation. |

#### Agent Session Group SG-1

Agents work in isolated worktrees. They may run concurrently, but integration
lands in the listed order so a later session consumes reviewed contracts rather
than inventing them again.

| Session | Agent-owned slice | Atomic rows | Starts with | Handoff / merge gate |
| --- | --- | --- | --- | --- |
| SG1-A | Genesis RL + deterMDinistic contracts | R-69, R-61, R-70, R-87, R-88, R-89 | Stale `graphics_flow.FLOW` documentation mirror | Contract first; two-file mirror engine second; executable-cell runner remains its own deferred diff |
| SG1-B | Cook MVP routing | R-82, R-74 | Route-resolution failure for each named skill | Router contains no copied doctrine; stop before unapproved git delivery |
| SG1-C | Tokens QA correlation | R-63, R-65, R-68, R-73 | Two-invocation false-correlation repro | One real Shot trajectory, table, and feedback arc correlate by stable identity |
| SG1-D | Aesthetic Assistant app adapter | R-18, R-60, R-83 | Ranking/brief/tag reconnect replay | Independent feedback fields round-trip through the live UI |
| SG1-E | Graphics tool escalation | R-72, R-84, R-86 | Clean-host missing-tool inventory | Common toolbelt installs; niche research remains per-project evidence |

#### SG1-A lean contract

| Concern | Settled decision |
| --- | --- |
| Authority | Each opt-in block declares direction; codebase state is authoritative by default and bidirectional sync is forbidden. |
| Declaration | One JSON-bearing `detmd` HTML comment owns exactly the next table or fence; ids are repository-global and immutable after publication. |
| State | Explicit columns and `string`, `integer`, `boolean`, `null`, `id`, or `ref` values normalize to one JSONB-compatible envelope; many-to-many uses link rows. |
| Source | V1 supports root-confined `python-export`, JSON with an optional RFC 6901 pointer, and TSV; Python runs in a bounded subprocess and none of the adapters can invoke arbitrary commands or the network. |
| Operations | Closed registry: project, sort, join, count, integer sum, SI/IEC byte conversion, key uniqueness, and foreign-key validation. No `eval`, floats, implicit coercion, or natural-language query. |
| Surface | One bundled/installable module at `first/genesis/detmd.py`, one fogged development test, and minimal `pyproject.toml`; `check`, `render`, and `export --format json|pipe|tsv`. No manifest, dependency DAG, persisted sidecar, database I/O, or general Markdown parser. |
| First proof | Render the documented graphics action table from `graphics_flow.FLOW`; deletion or reordering produces drift, and rendering changes only the declared region. |
| Execution | V1 validates executable-cell declarations but does not run them. R-89 adds the explicit runner, timeout, inputs/outputs, and proof gate separately. |

### Sprint Group 2: longest systems

| Rank | Program Epic | Sub-epic | Atomic rows | Exit |
| ---: | --- | --- | --- | --- |
| 6 | Genesis | Assistant apps platform | R-56, R-71, R-75, R-76, R-77, R-78, R-81 | Lean live Web UI persists replayable state through a relational envelope plus PostgreSQL JSONB and reaches consumers through the install path. |
| 7 | Cook | Moses | R-64, R-67 | Every run carries an enforced admitted/excluded context trace and separates Repo-Dev from domain/MCP Shot context. |
| 8 | Cook | Tokens ontology | R-40, R-50, R-52, R-53, R-54, R-55, R-57, R-66, R-79, R-80 | Token/context declarations, pgvector indexing, and PostgreSQL analytics produce reproducible advisory reads. |
| 9 | Aesthetic | Graphics inference | R-24, R-62, R-85, E-02–E-09 | The real project goes from sourced domain evidence to generated graphics, visual proof, ranking, and publication through Aesthetic. |

#### Agent Session Group SG-2

SG2 begins only after SG1's contracts and adapters are reviewed. Long-running
data and inference sessions stay separate; one integration agent owns the final
cross-module proof instead of letting every session edit the same seam.

| Session | Agent-owned slice | Atomic rows | Depends on | Handoff / merge gate |
| --- | --- | --- | --- | --- |
| SG2-A | Genesis Assistant apps platform | R-56, R-71, R-75, R-76, R-77, R-78 | SG1-A | Live state and PostgreSQL JSONB replay pass independently of Aesthetic |
| SG2-B | Cook Moses | R-64, R-67 | SG1-A, SG1-C | Admitted/excluded context trace enforces semantic boundaries |
| SG2-C | Cook tokens ontology + analytics | R-40, R-50, R-52, R-53, R-54, R-55, R-57, R-66, R-79, R-80 | SG2-A, SG2-B | Reproducible trajectory features and advisory pgvector reads |
| SG2-D | Aesthetic graphics inference | R-24, R-62, R-85, E-02–E-09 | SG1-D, SG1-E, SG2-B, SG2-C | Real graphics rollout reaches visual review with domain evidence intact |
| SG2-I | Program integration | R-81 | SG2-A–SG2-D | Assistant apps → JSONB → Shot review → analytics passes as one correlated trajectory |

## Atomic rows by repository surface

### E1 — Platform plumbing

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-54 | `TODO` | One module owns the skill corpus | B-021. Six frontmatter parsers, no interface. R-55 and R-57 depend on this. |
| R-56 | `TODO` | Decide the companion seam: shared, or gated identical | `trace_preview.py` and `vectors.py` duplicate the loopback server wholesale. |
| R-51 | `IN-PROGRESS` | Port harness-core to one tested Python file | `harness.py` landed; remaining Windows parity for sync/onboard, then drop bash. Lives in harness-core. |
| R-43 | `TODO` | Index `collection.yaml`, add missing sources | `poteto`, `poteto-mode`, `zoom-out` not in any manifest today. |
| R-84 | `TODO` | Ship the critical graphics toolbelt through harness-core | Research and select the smallest broadly powerful graphics set, record license/runtime/security evidence, add it to the manifest, and prove a clean install exposes every tool. |

### E2 — Token intelligence

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-50 | `IN-PROGRESS` | Build the inference context compiler | [Contract](docs/SPEC/INFERENCE_CONTEXT_COMPILER.md). Slice in `direction_context.py`; remaining: per-skill declarations, exact tokenizer, advisory ranker. |
| R-52 | `TODO` | Agreed tokenization, visualized and gated | [Contract](docs/SPEC/AGREED_TOKENIZATION.md). Durable sha256-pinned verdicts; gate refuses stale agreements. |
| R-53 | `TODO` | Advisory clustering over the corpus | [Contract](docs/SPEC/ADVISORY_CLUSTERING.md). EVoC proposals for semantic group and contamination risk; advisory only. |
| R-55 | `TODO` | Flows become repo data; benchmark gains release mode | `token_bench.py` flows are CLI strings today, not reproducible repo data. |
| R-57 | `TODO` | Narrow the vectors interface | B-023. Split corpus load → R-54, serve → R-56; expose `embed()` and `cluster()` as callables. |
| R-40 | `TODO` | Measure the host's actual enabled collection | Model-invoked descriptions only; installed count is not context load. |
| R-63 | `TODO` | Correlate one Cook invocation across the full session arc | Replace latest-marker selection with an explicit invocation interval and stable run identity; join session, artifacts, companion, Shot, table, and feedback. |
| R-64 | `TODO` | Trace admitted and excluded context | Compile and enforce `CONTEXT.md` boundaries; record what entered inference and why incompatible Repo-Dev or Shot context was excluded. |
| R-65 | `TODO` | Adapt supported agent sessions and expose the `shot-audit` seam | Read supported session objects through adapters; keep negative sentiment and correction extraction under the universal QA boundary, not in Cook. |
| R-66 | `TODO` | Rename `build-context-token-vectors` into the tokens ontology | Migrate command, directory, references, discovery, and callers with compatibility evidence; preserve the vector tool's advisory-only boundary. |
| R-67 | `TODO` | Define the `moses` module contract and ownership | Publish a small decontamination interface for session scope, package-artifact context, and domain/MCP Shot context; Cook consumes it without reimplementing it. |
| R-68 | `TODO` | Make Cook exercise the real skill path | Run the actual skill, companion artifact, delivery path, Tokens QA table, Shot record, and feedback loop on a scratch consumer; no canned external fixture or exit-status-only pass. |
| R-69 | `DONE` | Package deterministic Markdown/context declarations | Shipped as the dependency-free `determdinistic` 0.1.0 distribution and bundled `detmd.py`: opt-in declarations, typed rows, stable keys/refs, deterministic JSONB-compatible provenance envelope, and separate canonical/render SHA-256 digests. Runtime and publication evidence is in the SG1-A gate. |
| R-87 | `TODO` | Align every skill adapter to the LLM RL observation domain | Map each bounded Shot to observable state, actions, terminal artifact, independent reward signals, costs, constraints, and deterministic-guard outcomes; preserve domain vocabulary and forbid hidden-reasoning capture, scalar reward synthesis, or online doctrine mutation. |

### E3 — Companion surface

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-18 | `TODO` | Companion live-check, every run | Hard precondition before any other Loop step; not an unchecked `open`. |
| R-60 | `TODO` | Generalize companion form-state sync | Loopback app under `.superpowers/`: inputs sync to durable file data (pattern from `trace_preview.py`). Blocked on R-56. |
| R-75 | `TODO` | Specify the Assistant apps companion artifact | Define a small, live web UI contract: one app/session identity, current state snapshot, bounded user actions, visible connection state, and replayable event correlation. No design-system or multi-product shell. |
| R-76 | `TODO` | Build the lean live-state transport | Prefer a small HTTP read/write API with server-pushed updates where needed; prove reconnect, ordering, idempotency, and stale-client behavior without coupling the UI to a skill's private ledger. |
| R-77 | `TODO` | Persist companion state in PostgreSQL JSONB | Store a relational envelope for app/session/event identity, revision, timestamps, and ownership; store flexible state and event payloads as JSONB with validation, migrations, and the minimum useful indexes. |
| R-78 | `TODO` | Decide the ORM boundary | Compare SQL-first access with one supported ORM against the actual query set; choose an ORM only if it reduces the live path without obscuring JSONB operators, migrations, transactions, or pgvector access. |
| R-79 | `TODO` | Connect tokens ontology to PostgreSQL vector reads | Add an analytical read model for declared context-token chunks and embeddings; use pgvector similarity plus metadata filters for peer/context discovery, advisory only and never a live-inference authority. |
| R-80 | `TODO` | Add PostgreSQL data-science analytics | Define reproducible SQL views or materialized views for session cost, accepted-result rate, correction retention, contamination, context utility, and vector-cluster comparisons; pin dataset/revision and tokenizer profile for every reported number. |
| R-81 | `TODO` | Prove Assistant apps end to end | Exercise live UI → state transition → JSONB write → replay/read → Tokens QA/Cook correlation → analytics query, with failure evidence for disconnects, duplicate events, invalid payloads, and context derail. |
| R-83 | `TODO` | Adapt Aesthetic to Assistant apps | Give ranking, project brief, and corpus tagging one live-state adapter; preserve independent feedback signals and keep Aesthetic domain state out of the reusable platform. |

### E4 — Aesthetic core health

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-15 | `DONE` | Split `bootstrap_harness.py` | Repaid 2026-09-01. 216,757 B to 25,326 B across thirteen `harness_*` seams; `editorial_workflow.py` 34,911 B to 3,858 B across four. `test_article.py` and `test_adopt.py` split by subject. No file in the repository is over its budget, `contracts-budget` is green, and `tools/check.py` is 27/27. Public surface, CLI help for all eighteen subcommands, and all 515 test ids verified unchanged. |
| R-62 | `TODO` | Run this repo's graphics and website as an Eat your own food project | `landing.hero.flow` through `text_to_graphics.py` → `design/landing-flow-hero.html`. Proof = `kit sync` then a green graphics run on this checkout. |
| R-24 | `TODO` | Cap golden-rule retry cost | B-013. Retries must narrow scope, not re-attempt the same rejected spec. |
| R-25 | `TODO` | Explicit `subject` in `editorial.json` | Durable model behind R-21; not urgent while dotted-id convention holds. |
| R-85 | `TODO` | Make graphics inference Aesthetic's primary value path | Compile domain evidence and approved tools into one bounded graphics Shot, produce the real artifact, verify it visually, present it in Assistant apps, and correlate user feedback. |
| R-86 | `TODO` | Research niche graphics tools per project domain | Before custom generation, query the project's domain and stack for specialized production tools; record why the common toolbelt is insufficient and admit only the selected tool's evidence. |

### E5 — Rail command surface

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-35 | `TODO` | Ship five `first-*` stubs | Over `genesis` and `aesthetic`; do not write a second planning skill. |
| R-36 | `TODO` | Write `build`, `land`, and `fix` | `build` routes ponytail/tdd; `land` owns burndown state machine; `fix` owns the rail. |
| R-34 | `TODO` | Write `check` | Read-only; `check-` prefix routes. |
| R-45 | `TODO` | Teach `alias.py` anchor and ghost-argument stubs | Whole aliases exist; § and ⇢ kinds do not. |
| R-49 | `TODO` | Record routerless rail in SPEC | Prefix scheme is intentional; document so it is not "fixed" later. |
| R-37 | `TODO` | Add `design` and `español` modes to `kit` | Two rows in the mode table; no new skill. |
| R-46 | `TODO` | Approve-features gate | Between sketch and build; decision moment is unrecorded today. |
| R-47 | `TODO` | Legibility gate on build output | Green tests are not evidence a non-coder can read the deliverable. |
| R-44 | `TODO` | Two pasteable monitor prompts | `check-user-metrics`, `check-production-health`; zero description tax. |
| R-38 | `TODO` | Declare `phase` in frontmatter | G-2. Declare without gate; load-bearing for `genesis` and `aesthetic` only. |
| R-82 | `TODO` | Reduce Cook MVP to routes | Route `zoom-out`, `diagnosing-bugs`, and `ponytail-review`, then expose reviewed git commit/push as the terminal boundary; Cook owns ordering and evidence correlation only. |

### E6 — Repo-Dev ergonomics

| id | State | Item | Notes |
| --- | --- | --- | --- |
| R-58 | `TODO` | Give the burndown a query interface | Mode A entry is ~73 KB across five files; query `IN-PROGRESS`, `R-43`, last bug. |
| R-41 | `TODO` | Write the rail as a `CLAUDE.md` import | Fixed bytes at session start, not a command to remember. |
| R-42 | `TODO` | Move measurements to hooks / statusLine | Token rail and burndown off the command surface. |
| R-61 | `DONE` | Build the lean deterministic-mirror engine | `first/genesis/detmd.py` and its fogged test implement bounded Python/JSON/TSV sources, normalized rows/link tables, closed operations, atomic managed-region rendering, and `check`/`render`/`export`. The graphics action guide eats its own food and exposes every runtime action plus `done`. |
| R-16 | `TODO` | Enforce ubiquitous language | Checker over `UBIQUITOUS_LANGUAGE.md` banned synonyms. |
| R-17 | `TODO` | Automate verification in CI | `check.py` today is manual. |
| R-70 | `DONE` | Record Genesis escalation and exact-state doctrine | Genesis now requires research before invention and architecture before atomic construction. It explicitly delegates arithmetic, serialization, long-file joins, digests, and unsourced values to deterministic code that fails closed. |
| R-71 | `TODO` | Preserve Kit and harness-core installation boundaries | Keep install UX concise and permissions proportionate; document `cd`/pull behavior and how Genesis doctrine reaches installed consumers. |
| R-72 | `TODO` | Decontaminate Aesthetic artifact and Shot inference context | Add a Moses boundary to artifact interpretation, source the available stack before custom generation, and decompose custom work from architecture to atomic assets. |
| R-73 | `TODO` | Synchronize contracts, tests, and existing Shot records | Add writers for missing observations and corpus claims, align schema/CLI/docs, and migrate only through the versioned read path without rewriting history. |
| R-74 | `TODO` | Hold the release boundary explicitly | Review doctrine, architecture, diff, and checks before commit/push; obtain channel approval before publication, then install and verify the published commit. |
| R-88 | `TODO` | Benchmark deterministic doctrine without creating a client | Compare selected `ponytail` and `mattpocock/skills` flows on checked examples, canonical table sources, procedural derived values, local drift gates, and token cost. Pin refs and methods, keep dimensions separate, and make the result advisory. |
| R-89 | `TODO` | Run declared Markdown-authoritative cells | After R-61 is green, add an explicit allowlisted runner with repository-relative cwd, timeout, expected exit/output proof, and declared files. `check` never executes cells; fetched or untrusted blocks never run. |

### Design — three phases

Domain-neutral workflow in
[`platform-support.md`](aesthetic/references/platform-support.md). E-01 is
`DONE`. Defer external adapter epics until E4 Eat your own food is green on this repo.

| id | State | Family | Phase | Epic | Exit |
| --- | --- | --- | --- | --- | --- |
| E-02 | `TODO` | `first` | **E-A** Discover & frame | Brief + design contract | `DES-09` |
| E-03 | `TODO` | `first` | **E-A** | Inspiration adapters | `DES-01`–`DES-04` |
| E-04 | `TODO` | `first` | **E-A** | Editable workspaces | `DES-05`–`DES-07` |
| E-05 | `TODO` | `build` | **E-B** Build & prove | Blind operator control | `DES-08` |
| E-06 | `TODO` | `build` | **E-B** | Sketch-to-production | `DES-10`–`DES-12` |
| E-07 | `TODO` | `build` | **E-B** | Screenshot TDD | `DES-13` |
| E-08 | `TODO` | `land` | **E-C** Ship & publish | Observable deployment | `DES-14` |
| E-09 | `TODO` | `land` | **E-C** | Deliverables + publication | `DES-15`–`DES-17` |

`check` reads this table; `fix` returns the first failing epic to `TODO` or
`BLOCKED`.

## Done

R-01–R-10 repo bootstrap. R-11–R-12 corpus tagging. R-14 design quality
judged (external fixture used as measurement only). R-19–R-23, R-27–R-30
companion and brief. R-31–R-33, R-39, R-48 rail topology and invocation audit. R-59 graphics loop
(`graphics_flow.py` + `text_to_graphics.py status`).
E-01 support contract.

Closed out of repo scope: **R-13** (external fixture SVG previews, B-007),
**R-26** (external fixture ring type, B-017).

Detail for each shipped row: [CHANGELOG.md](CHANGELOG.md).

## Working notes

**Published article is static.** After a render change, run `article` + `publish`
or `article` with no `--cohort` before screenshotting:

```bash
python3 first/aesthetic/scripts/bootstrap_harness.py article \
  --project-root . --out /tmp/check.html
```

**Installed copy does not sync itself.** Run `kit sync` after editing skills here.
