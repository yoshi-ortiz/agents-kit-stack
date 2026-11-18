# Shots and sprints to build NEXT

Status: proposed plan; no implementation or user acceptance recorded.
Requirements: [NEXT.md](../../NEXT.md).
Decision map: [Build NEXT through bounded Shots](map.md).

## Delivery shape

A sprint groups a usable capability. A planned Shot below is one bounded
deliverable; execution creates a real Shot record with its own identity.
Corrections create further attempts attached to the same roadmap Item, not a
new unrelated feature. Local labels such as `S1.1` are schedule references only.

Plan one Shot per agent session. Use 100K context tokens as the maximum planning
envelope inherited from wayfinder, not a spending target or measured usage.
Before starting, bind a smaller explicit time/token cap to the actual work.
Split a Shot if its proof cannot fit. Sprint durations and total cost remain
unestimated until the first completed Shots provide evidence.

```text
Sprint 1: bounded next action
    └─ Sprint 2: trustworthy evidence
         ├─ Sprint 3: portable observation ─┐
         ├─ Sprint 4: bounded compiler ────┼─ Sprint 6: field evidence and integration
         └─ Sprint 5: package health ──────┘

After field evidence: conditional domain guard / rail graph investigations
```

Sprints 3–5 may overlap only with disjoint write scopes. Compiler contracts,
Tokens QA contracts, `repo_context.py`, and gate registration each have one
writer at a time. Package extraction can be researched earlier, but coordinate
its writes to `tools/check.py`, `tools/fog.py`, and related tests.

## Decision gates

These are unresolved design questions. Recommendations live in the ticket and
are not accepted answers. Read only the ticket blocking the selected Shot.

| Decision | Blocks |
| --- | --- |
| [Choose the bounded Item contract](issues/01-bounded-item-contract.md) | Complete-decision behavior and contract consolidation |
| [Choose feedback history and closure concurrency](issues/02-feedback-history.md) | Evidence migration, event writes, closure and retention |
| [Choose the portable proof adapter](issues/03-portable-proof-adapter.md) | Second output adapter and common caller migration |
| [Choose the first compiler invocation](issues/04-compiler-invocation.md) | One-path compiler, intent adapter and runner proof gate |
| [Choose package-check ownership](issues/05-package-check-ownership.md) | Extraction and gate discovery migration |
| [Choose the first field evaluation](issues/06-field-evaluation.md) | Real measurement and any improvement claim |

## Sprint 1: one complete next action

NEXT stage 1. Associate with R-71 when its selected scope allows it.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S1.1: characterize the current public flow | `tools/test_compass_flow.py`, `tools/test_repo_context.py`, Genesis tests; capture existing selection/feedback/proof behavior and missing-contract cases | Select Item and session scope | Existing successful flow stays green; a focused regression demonstrates the chosen contract gap |
| S1.2: return one bounded decision | `tools/repo_context.py`, `first/genesis/scripts/compass.py`, matching tests; versioned result with reviewed criteria, read/write scope, exclusions, proof, budget and reasons | S1.1; Choose the bounded Item contract | Explicit Item never changes silently; active/dependency/deferred rules, absent requirements, zero/unknown/incompatible budgets and deterministic output |
| S1.3: make entry instructions agree | `docs/SPEC/FEATURE_COMPASS.md`, root `CONTEXT.md`/`CLAUDE.md`, Genesis `SKILL.md`, existing topology callers | S1.2 | Follow short entry recipe in a scratch project; standalone Genesis selects without Tools; closure callers use the verified composition |

Exit: one query gives a complete bounded action. Documentary consolidation
follows tested behavior; legacy topology checks remain where still needed.

## Sprint 2: evidence survives correction

NEXT stage 2. Resolve storage choices before touching historical records.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S2.1: preserve feedback events | Tokens QA schema, I/O, record/feedback commands and tests; versioned history with idempotent operations | Sprint 1; Choose feedback history and closure concurrency | Rejection remains after later feedback; duplicate write has one effect; concurrent writers lose no event; legacy input remains readable without invented provenance |
| S2.2: retain unresolved corrections | Tokens QA history/verdict/correction output and Repo Context join | S2.1 | New pending attempt retains earlier constraints; explicit resolution references clear only named corrections; bounded output excludes unrelated history |
| S2.3: enforce evidence-backed closure | Tokens QA gate, Repo Context closure, public flow tests; provenance, proof coverage and expected revision | S2.2 | Reject caller-only acceptance under new policy, stale latest Shot, unresolved correction, hard veto, changed/mismatched proof; accept a complete synthetic fixture without claiming real user acceptance |
| S2.4: make retention explicit | Tokens QA storage/retention, Shot contract, `.gitignore`, existing publication rules and tests | S2.3 | Scratch tests cover redaction, containment, permissions where supported, exact deletion preview, explicit deletion and resulting unverifiable proof; private records excluded from Git/publication |

Exit: rejection → corrected attempt → actual verdict is auditable. User words
and check provenance are recorded assertions with sources, not authentication
created by hashing. Authorized deletions preserve no sensitive tombstone payload.

## Sprint 3: a second output type works

NEXT stage 3. Use the existing observation interface to validate portability.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S3.1: deliver portable code/document proof | `cook/` and concrete adapter files selected by the ticket; request/artifact/proof/usage input | Sprint 2; Choose the portable proof adapter | One scratch deliverable records and gates through Tokens QA without Aesthetic project state or Claude transcript files; missing telemetry stays unknown |
| S3.2: migrate existing output callers | `cook/{cook,qa,prove}.py`, Aesthetic `assistant_app.py`/`deliver.py`, corresponding tests | S3.1 | Both output types use the same verdict/cost rules; binary artifacts and bounded corrections survive; host-specific discovery remains in adapters |

Exit: two real output adapters exercise one public observation contract.
Read Aesthetic's `AGENTS.md` before entering that owner.

## Sprint 4: compile one invocation safely

NEXT stage 4. Compiler correctness does not wait for a learner or every skill.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S4.1: bind reviewed intent | Compiler specification, selected invocation owner and existing intent adapter; structured constraints with source/digest/profile/budget | Sprint 2; Choose the first compiler invocation | Required intent absent or unreviewed produces explicit unresolved input; identical reviewed inputs have stable identities |
| S4.2: pack and explain one bundle | Selected compiler implementation and focused tests | S4.1 | Identical inputs produce identical bundle/trace; incompatible contexts excluded; mandatory overflow fails with counts; estimates labeled; corrections cannot be displaced |
| S4.3: enforce the runtime proof stop | Selected runner, compiler integration and public path test | S4.2 | Missing proof prevents expensive invocation; valid proof permits it; explicit scoped exception is recorded; no hidden execution from stored command text |

Exit: one invocation succeeds from the bounded entry recipe and its triggered
pointers. Version/tokenizer compatibility is checked against actual deployment.

## Sprint 5: package checks belong to Tools

NEXT stage 5. Coordinate shared gate files with evidence work.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S5.1: extract generic package checks | Generic checks currently in Aesthetic, destination in `tools/`, existing callers and tests | Sprint 2; Choose package-check ownership | Minimal package without Aesthetic receives generic checks; equivalent malformed contracts still fail; skill runtime checks remain skill-owned |
| S5.2: unify verification and publication proof | `tools/{check,release,publish,fog}.py`, corresponding tests and Tools context | S5.1; S3.2 for final Cook integration | Local/release discovery agrees, newly discovered tests run, failures reach release, present Aesthetic checks execute, both generated trees exclude NEXT, local plan and private evidence |

Exit: extraction changes ownership without weakening verification. Run all
publication checks against temporary outputs; publishing is a separate action.

## Sprint 6: field evidence and final integration

NEXT stage 6 plus completion requirements. Field observation may start once
Sprint 3 is usable; final integration waits for Sprints 4–5.

| Planned Shot | Scope and deliverable | Prerequisite | Proof |
| --- | --- | --- | --- |
| S6.1: record the first real Item | Selected real project/Item and private evidence; frozen criteria, versions and usage source | Sprint 3; Choose the first field evaluation | Complete record through actual verdict, including pending/failed attempts; no invented rejection or acceptance; unknown usage reported incomplete |
| S6.2: test one evidence-driven improvement, if warranted | One authorized instruction or regression test and the same acceptance path | S6.1 exposes a real correction and user authorizes its change | Preserve original failure, record candidate revision and all costs, rerun unchanged criteria, obtain actual verdict; otherwise record that no corrective change was warranted |
| S6.3: verify the integrated path | Selected public flow, existing verification board, owning contracts and roadmap evidence | Sprints 4–5; S6.1; S6.2 only when applicable | Full board reported, cold entry reaches accepted proof, migrated interfaces have no remaining callers, R-50 compiler/migration/learner outcomes tracked separately |

Exit: real field evidence and honest technical verification. One Item can
validate the measurement path. A lower-cost claim requires the separately
predeclared comparable cohort; absent that cohort, report observations only.

## Conditional horizon

| NEXT stage | Trigger | Next planned artifact | Completion rule |
| --- | --- | --- | --- |
| 7: domain guards | Evidence loop works and one declared-domain failure has a deterministic check | A decision ticket selecting the failure, then one prototype Shot in that owner's scope | Failing fixture caught, valid case allowed; generalization waits for a second actual consumer |
| 8: rail graph | Settled exits are reconstructed by at least two real routers | A decision ticket selecting shared transition ownership, then one migration Shot if justified | Both routers consume the declaration and illegal exits fail; otherwise record no implementation needed |
| Optional learner | Reviewed corpus and evaluation make a learning experiment useful | Separate research/design effort | Held-out evaluation and reviewed recommendation only; no automatic project mutation |

These are triggers, not committed sprints or fixed estimates. Read the
[engineering knowledge index](../../domain/engineering/index.md) only for the
relevant concept. Google ADK is reference knowledge, not a mandated dependency.

## Starting and closing a Shot

1. Claim the selected work; bind the planned deliverable to an actual roadmap
   Item, expected revision, allowed paths, proof and explicit session budget.
2. Confirm predecessor evidence and required decision answers. Open the selected
   stage in NEXT, its owner context, and the latest correction only.
3. Implement and run the cheapest proof that exercises the public behavior.
   Keep tests with their existing owner. If work exceeds the budget, retain
   evidence and split the remaining deliverable rather than broadening scope.
4. Record request/source references, artifact revision, actual check results,
   usage profile and counts, and user feedback. A failed attempt stays attached
   to its Item; blocked work names the external clearing condition.
5. Report verified/pending/blocked separately. DONE requires NEXT's closure
   contract and actual acceptance. A completed coding session is not acceptance.

No calendar dates, token savings or completed Shots are asserted by this plan.
