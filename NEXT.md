# Next: bounded feature work and evidence-driven improvement

Status: implementation specification. No implementation is claimed complete.
Context: Repo-Dev only. This document is development Fog.

For implementation scheduling, read the [Shots and sprints plan](.scratch/next/spec.md).
For an unresolved design choice, use its linked [decision map](.scratch/next/map.md).

## Upgrade file map

Numbers refer to implementation stages below. Braces group existing files;
angle brackets mark destinations chosen during implementation, not new files
to scaffold. Stages 7–8 remain conditional.

```text
cyber-skills/
├── NEXT.md                                 implementation sequence; retire to history
├── CONTEXT.md, CLAUDE.md                    [1] bounded entry and contract pointers
├── ROADMAP.md                              [1,6] Item scope, proof, separate R-50 outcomes
├── QA.md                                   [1,2] compliance and evidence authority
├── SPEC.md                                 [8] settled Family transitions
├── docs/SPEC/
│   ├── FEATURE_COMPASS.md                  [1] selection, budget, closure authority
│   ├── SHOT_OBSERVATION.md                 [2] feedback events, provenance, retention
│   └── INFERENCE_CONTEXT_COMPILER.md       [4,6] structured input, overflow, split acceptance
├── first/genesis/
│   ├── SKILL.md                            [1,4] small entry recipe and triggered references
│   ├── scripts/
│   │   ├── compass.py                      [1] shared Item selection and validation
│   │   ├── genesis_flow.py                 [1] retain topology audit; retire closure callers
│   │   └── test_{compass,genesis_flow}.py   [1] selection parity and migration proof
│   └── references/{sourcing,architecture}.md [7] declared-domain guard prototype
├── check/tokens-qa/
│   ├── SKILL.md                            [1–3,6] public observation and correction recipe
│   └── scripts/
│       ├── tokens_qa.py                    [2,3,6] record, verdict, history, portable observations
│       ├── shot_contract.py                [2] versioned events and provenance validation
│       ├── shot_io.py                      [2] preserved history, private storage, retention
│       ├── shot_view.py                    [2,6] effective verdict and honest cumulative cost
│       ├── feedback.py                     [2,3] advisory classification; bounded corrections
│       └── test_*.py                       [2,3,6] public contracts and failure cases
├── cook/
│   ├── {cook,qa,prove}.py                  [3,5,6] portable proof and real measurement path
│   └── <host/output adapters and tests>    [3] isolate Claude/Aesthetic; one second output type
├── first/aesthetic/scripts/
│   ├── {assistant_app,deliver}.py          [3] migrate callers to common Shot interface
│   ├── contracts.py                        [5] move generic package checks into Tools
│   └── bootstrap_harness.py                [5] retain skill-specific runtime checks
├── <selected invocation owner>/
│   └── <existing compiler, runner, tests>  [4] reviewed intent, bundle/trace, enforced proof gate
├── tools/
│   ├── repo_context.py                    [1,2] deepen existing Attempt Ledger composition
│   ├── test_{repo_context,compass_flow}.py  [1,2] bounded decisions and latest-proof closure
│   ├── {check,release}.py                  [5] one verification discovery path
│   ├── {publish,fog}.py                    [2,5] exclude private evidence and development Fog
│   ├── test_{check,release,fog}.py          [5] verification discovery and publication exclusions
│   ├── <generic package checks>            [5] destination of extracted package policy
│   └── skill_catalog.py                    [8] reuse for legal exits if multiple routers need them
├── {kit,first,build,land,check,fix}/SKILL.md [8] migrate only affected Family routers
├── .audit/                                 [2,6] private local evidence; never publish
│   └── <Shots, feedback, proofs, measurements> preserve failures; record actual user verdicts
└── bugs/                                   source reviews; historical evidence, not runtime policy

harness-core/<domain catalog>               [7] reference only; changes need a separate Item
<development-only learner location>         [6] optional separate experiment; no scaffold now
```

For every changed owner, update its `CONTEXT.md` only when ownership or admission
changes. Reuse its existing tests and fixtures; the map does not require a new
test file for each upgrade.

## Outcome

An agent can obtain one bounded Item, retain the user's correction, produce a
Shot, and determine whether closure is permitted through one small interface.
Genesis supplies selection; Tokens QA supplies observations and verdicts.
Package verification and the Context compiler consume those facts without
reconstructing their rules or loading unrelated skill doctrine.

Use **feature evidence loop** for this workflow. **Safe self-improvement (SRI)**
means an explicitly authorized, reviewed instruction or regression-test change
supported by recorded outcomes. The optional offline learner produces
recommendations. Recording feedback alone does not train a model.

## Execution entry

1. Select the implementation stage below that serves the user's current Item.
   Query that Item through `tools/repo_context.py`; R-71 covers the existing
   compass integration and R-50 tracks the compiler. Associate subsequent
   stages with explicit roadmap Items when implementation begins.
   Completion: one Item, one stage, and one deliverable are named.
2. Read the selected owner's `CONTEXT.md`, the source files listed for that
   stage, and the latest relevant correction. Open a review only when its
   recommendation or rationale is in question.
   Completion: permitted paths, acceptance criteria, proof, and session budget
   are explicit. A read-only request ends with its requested artifact.
3. Implement the smallest verifiable change in that stage. Preserve existing
   worktree changes and historical records. Migrate callers before removing an
   interface. Stop at the agreed deliverable or budget.
   Completion: the stage's applicable contract tests and public command path pass.
4. Record actual evidence and remaining work against the same Item. Keep
   synthetic test feedback separate from real user feedback.
   Completion: report technical verification and user acceptance separately;
   pending feedback leaves closure pending.

This specification authorizes no background retries, automatic prompt edits,
publication, or changes to other repositories. Selecting a later stage does
not activate every preceding review suggestion as a prerequisite.

## Sources and decisions

The requested reports are historical inputs, not executable contracts:

- [Architecture review, A](/Users/bebote-pro/Development/cyber-skills/bugs/architecture-review-20260905-030336.html).
- [Compass/SRI review, B](/Users/bebote-pro/Development/cyber-skills/bugs/cyber-skills-rl-sri-architecture-review-20260905.html).

| Recommendation | Implementation disposition |
| --- | --- |
| A1: deepen Burndown; B1: retain Item/Shot separation | Stages 1–2 compose existing owners through one interface; do not rebuild the parser already shared by Repo Context |
| A2: remove Aesthetic dependence from Shot work | Stage 3 moves host and output knowledge into concrete adapters |
| A3: deepen Genesis entry | Stages 1 and 4 return bounded facts and disclose reference branches |
| A4: Tools owns package health | Stage 5 separates package checks from skill runtime checks |
| A5: deterministic domain guards | Stage 7 is an evidence-gathering prototype before generalization |
| A6: one rail graph | Stage 8 remains conditional on settled transitions and real callers |
| B2: precise learning language | Apply the terminology above to changed contracts |
| B3–4: acceptance authority and privacy | Stage 2 adds provenance, preserved feedback history, and explicit storage policy |
| B5: deterministic compiler input | Stage 4 separates reviewed intent from compilation and defines overflow |
| B6: consolidate policy; measurement and deletion recommendations | Stages 1 and 6 establish ownership, migration, and honest evaluation |

Reconcile these claims with the current code before relying on them:

- `tools/repo_context.py` already delegates roadmap parsing to
  `first/genesis/scripts/compass.py` and exposes `next` and `check`.
- `cmd_feedback` in `check/tokens-qa/scripts/tokens_qa.py` updates and replaces
  the existing Shot. Full feedback history is a requirement below, not an
  existing guarantee of immutability.
- `feedback --status accepted` records a caller assertion. Neither that command
  nor a hash authenticates a user or proves that a check actually ran.
- The synthetic public flow verifies control behavior. It has not measured
  fewer corrective attempts or lower tokens per accepted result.

## Target ownership and interface

**Attempt Ledger** names the interface joining an Item to its Shots. It is
initially the deepened Repo Context composition, not a new database, independent
skill, or parallel policy engine. Retain public CLI adapters during migration.

| Owner | Authoritative responsibility | Consumers |
| --- | --- | --- |
| Genesis | Roadmap parsing, managed Item structure, dependency eligibility, workstream priority | Attempt Ledger, installed Genesis selector |
| Tokens QA | Shot schema, observation storage, feedback events, verdict, vetoes, artifact integrity, retention operations | Attempt Ledger, Cook, output adapters |
| Attempt Ledger | Item/Shot join, bounded next action, budget reconciliation, closure eligibility | Repo Context commands, compiler input adapter, package gate |
| Context compiler | Admission and packing of reviewed structured inputs; Compiler trace | Selected invocation paths |
| Tools | Package policy, verification discovery, publication exclusions | Local verification and release |
| Human and host adapter | User intent and verdict provenance; actual tool results and observed usage | Tokens QA and reviewed intent input |

The logical interface below is a target contract, not a claim that these Python
functions or new commands already exist. Reuse existing commands where possible.

| Operation | Required input | Result and effects |
| --- | --- | --- |
| `next` | Project root; selected Item or workstream | Read-only bounded decision; no automatic selection of a different feature after an explicit request |
| `record_attempt` | Item ID, invocation ID, scope, observed usage, artifact manifest, check observations, provenance | New Shot ID; local record creation only |
| `record_verdict` | Shot ID, source event reference, actor/source kind, observed time, independent supplied feedback fields, operation ID | Append feedback event; return effective verdict; replaying the operation is idempotent |
| `close` | Item ID and expected latest Shot ID/revision | Read-only closure eligibility and reasons; an authorized roadmap writer revalidates that revision before marking DONE |

`next` returns a versioned object containing Item identity and outcome, scope
paths, acceptance criteria, exclusions, required proof, latest Shot reference,
effective feedback and unresolved correction references, budget status,
`next_action`, and reasons. Large source text and history stay behind pointers.
Reads and writes are separate fields. Unknown observations stay unknown.

Decision precedence is deterministic: invalid state or references; unresolved
scope or acceptance requirements; pending feedback; accepted but insufficient
proof; closure eligibility; then correction or execution subject to budget.
An execution action becomes `resolve-budget` when cumulative usage is unknown
or incompatible, and `budget-exhausted` at the cap. Zero is a valid cap. Return
blockers and veto reasons alongside the action. `no-ready-item` means no eligible
selection, never that the project is complete. An explicit deferred Item needs
an explicit eligibility change; selecting it must not silently rewrite state.

## Stage 1: consolidate the feature contract

Read `docs/SPEC/FEATURE_COMPASS.md`, `CONTEXT.md#feature-burndown`,
`first/genesis/SKILL.md`, `tools/repo_context.py`, and the compass implementation.

Keep `docs/SPEC/FEATURE_COMPASS.md` authoritative for cross-owner selection,
budget and closure policy. Keep `QA.md` authoritative for compliance and
`docs/SPEC/SHOT_OBSERVATION.md` for serialization. Replace duplicated policy in
root context and Genesis with a short invocation recipe and conditional pointers.
Installed Genesis must remain usable without the development-only Tools tree.
Its standalone selector reports structural selection, not verified closure.

Deepen existing `next`/`check` composition to satisfy the interface above. Resolve
free-text requirements into explicit reviewed fields before execution. Preserve
legacy rows as readable history; opt them into enforcement deliberately.
Isolate `genesis_flow.py` as topology auditing until all closure callers migrate.

Done when public tests cover explicit selection, active-item resumption,
dependencies, cycles, deferred and blocked Items, absent requirements, zero and
unknown budgets, and one deterministic decision for identical inputs. The
standalone Genesis path and Repo Context path share selection results.

## Stage 2: preserve feedback and establish evidence authority

Read `check/tokens-qa/scripts/{tokens_qa,shot_contract,shot_io,shot_view}.py`,
`feedback.py`, their tests, and `tools/test_compass_flow.py`.

Introduce a versioned append-only feedback representation. Preserve earlier
rejections, corrections, and acceptance events when later feedback arrives.
Resolve corrections by explicit event reference; a new pending Shot does not
erase outstanding constraints. Preserve old records without fabricating events
or backfilling provenance. Legacy acceptance without source evidence is reported
as unverified when evaluated under the new closure policy.

Source provenance must distinguish user feedback, caller assertions, and test
fixtures. A user-verdict adapter records the actual source reference and user
words, or an explicit redacted reference. Advisory classification can propose
fields but cannot write a verdict. Local provenance remains an auditable
assertion, not cryptographic authentication of the human.

Closure requires the latest item-linked Shot, explicit user acceptance, no
unresolved correction or hard veto, observed passing L2, and unchanged artifacts
covering the Item's proof requirements. A hash establishes integrity only.
Record which check ran, its result, artifact references, and observer. Reading
or gating a record must never execute an arbitrary command stored inside it.

Store only the task evidence needed for this workflow. Raw transcripts and
hidden reasoning are excluded. Support redacted text with source references;
missing required evidence produces an explicit unresolved result. Use private
local permissions where supported and reject paths escaping the declared root.
Keep private records out of Git and both published channels; sanitized,
explicitly designated fixtures may be versioned separately.

Retention defaults to local retention until explicit deletion, with no automatic
export. Provide a preview naming exact records before deletion, and require an
explicit request for the write. Deletion records may retain only non-sensitive
identity/status metadata. Removed proof makes closure unverifiable, not accepted.
No claim of redaction or privacy may depend solely on a secret-scanning heuristic.

Done when public tests preserve rejection history, reject unsupported acceptance,
retain corrections across attempts, handle duplicate and concurrent writes,
detect stale closure, and refuse escaped paths and changed or mismatched proof.
Exercise redaction, deletion, and publication exclusions in scratch projects.

## Stage 3: prove portable Shot observation

Read `cook/{cook,qa,prove}.py`, `cook/CONTEXT.md`, Tokens QA's public commands,
and the Aesthetic callers in `first/aesthetic/scripts/{assistant_app,deliver}.py`.
Read `first/aesthetic/AGENTS.md` before changing that owner.

Keep verdict and cost rules in Tokens QA. Move Claude transcript discovery and
Aesthetic artifact knowledge into their respective adapters. Add one actual
code or document adapter using declared request, artifact, proof and host usage
inputs. The common path must work without an Aesthetic project or Claude files.
Host telemetry that is unavailable remains unknown.

Done when Aesthetic and the second output adapter cross the same Shot interface,
with contract tests for binary artifacts, absent telemetry, vetoes, and bounded
correction output. Retain synthetic fixtures as interface evidence only.

## Stage 4: compile one bounded invocation path

Read `docs/SPEC/INFERENCE_CONTEXT_COMPILER.md`,
`bugs/determdinistic-spec-review.md`, and the chosen invocation owner's context.
Inspect existing compiler code only for that path before proposing replacement.

Choose one invocation path and one tokenizer profile. Take a reviewed structured
intent record containing exact constraints, corrections, acceptance criteria,
and their source references. Natural-language extraction is a separate adapter;
its output becomes a compiler input only after explicit review. Include the
intent digest, source revision or content hashes, declarations, profile version,
and budget in reproducibility inputs.

Admit compatible files first. Order content by corrections, acceptance criteria,
required evidence, instructions, then optional doctrine. If mandatory content
exceeds the budget, return `required-context-overflow` with required and available
counts and source references. Do not truncate a mandatory constraint. Unknown
required token cost blocks exact-budget compilation or requires an explicitly
selected estimated profile. Trace every admission and omission deterministically.

The runner enforces the declared proof gate before an expensive pass; compiler
output alone cannot police a host. An explicit user exception must be recorded
with its exact scope. Isolate Repo-Dev and Design-Inference declarations. Admit
only eligible compiled sections of shared QA contracts, never whole histories.

Done when a public path produces identical bundle bytes and stable trace content
for identical inputs, fails mandatory overflow, preserves corrections, excludes
incompatible context, and blocks an expensive pass with missing proof. Demonstrate
the path using only the bounded entry recipe and its triggered pointers.

## Stage 5: make package health independent of Aesthetic

Read `tools/{check,release,publish,fog}.py`, `tools/CONTEXT.md`, and
`first/aesthetic/scripts/{contracts,bootstrap_harness}.py` to separate actual
package checks from skill runtime logic.

Move generic directory-contract and package verification ownership into Tools.
Keep skill-specific harness and JavaScript checks with their skill, invoked
through declared adapters. Local verification and release consume one discovery
mechanism. Optional skill absence must not break unrelated package checks;
present skills retain all applicable checks. Keep NEXT.md and learning artifacts
out of both generated publication trees.

Done when the common board checks a minimal package without Aesthetic, a present
Aesthetic adapter runs its checks, new test discovery still works, failures
propagate to release, and both publication channels exclude development records.
Remove old package-check entrypoints only after callers and documentation migrate.

## Stage 6: measure SRI through real use

Use the Stage 3 public path on one real Item. Record every attempt through final
acceptance, including rejected, discarded and restarted work. A real correction
may motivate one authorized instruction or regression-test change. Record its
rationale and rerun the same acceptance path. Do not manufacture a rejection to
complete this experiment; first-pass acceptance is a valid observed outcome.

For each accepted Item report cumulative observed input/output tokens across all
its attempts, corrective-attempt count, model/harness/profile versions, proof,
and explicit user verdict. Unknown usage makes the total incomplete. Estimates
remain separate. Report pending, abandoned and never-accepted Items alongside
accepted ones so failures do not disappear from evaluation.

A single corrected-and-accepted Item demonstrates measurement and correction
retention. To claim lower median tokens or corrective attempts, predeclare a
cohort of comparable Items, baseline/candidate assignment, unchanged requirements,
model and budget controls, sample size, and uncertainty reporting. Count all
attempts in each arm. A cheaper accepted candidate than its rejected predecessor
alone does not establish improved tokens per accepted result.

Done when the measurement path has real evidence and the report distinguishes
observation from demonstrated improvement. Split R-50 completion into one-path
compiler correctness, broader invocation migration, and optional learner
evaluation. A development-only recommender is a separately selected experiment;
it cannot mutate prompts, project state, budgets or publication automatically.

## Conditional follow-up

**Stage 7, domain guards.** After the evidence loop works, choose one explicitly
declared project domain and one documented failure with an existing deterministic
check. Inspect Genesis sourcing/architecture references and the external domain
catalog as needed. Produce a fixture showing the guard catches that failure and
permits a valid case. Compare feature locality through declared input, rules,
persistence, output and proof; folder naming alone cannot establish architecture
quality. Generalize only after a second real consumer appears. Work in
`harness-core` requires a separately scoped Item.

**Stage 8, rail graph.** After transitions settle, inspect `SPEC.md`,
`tools/skill_catalog.py`, and only affected Family routers. Encode legal exits
once if at least two routers currently reconstruct them. Done when those routers
consume the declaration and tests reject illegal exits without loading another
Family's doctrine. If no duplicated executable decision exists, retain the
settled contract and record that no graph implementation is warranted.

## Completion and deletion

Each stage closes independently with its proof and required user acceptance.
Run owner-specific checks while implementing and the full `tools/check.py` board
before package release verification. Report existing failures separately; passing
new tests never excuses a weakened gate. No release is part of writing this spec.

Delete migrated duplicate parsers, verdict logic, closure paths, prose and tests
that only assert retired implementation details. Preserve public behavior tests,
negative fixtures, historical reports and user records. Before deletion, search
callers and show that the replacement interface covers their behavior. If a new
facade merely forwards operations while callers still reconstruct policy,
deepen the existing owner instead of adding another interface.

After implementation, permanent rules live in their owning contracts. NEXT.md
then becomes historical development context, with pointers to shipped Items and
unresolved follow-up rather than a competing runtime procedure.
