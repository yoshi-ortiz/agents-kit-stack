# `goals`: the owner's words, traced to steps

Reached from [bigbang.md](../bigbang.md) build step 4. Optional: selected by the `goals` layer (`bigbang --compass goals`); without it, `req:` is optional and nothing checks the trace. Closes GOAL.md "verbatim user requirements first … link requirements to roadmap items".

## The page

`<spec>/requirements.md`, where `<spec>` is `guardrail.toml`'s `spec` (default `docs/specs`). Owner-owned ([guardrail.md](guardrail.md) rule 4). Three entry kinds, append-only, each one block:

```markdown
## R1 · 2026-11-26
> to complete the bigbang agentic framework spec? so it harness input chat instinct
> to optimal token evals, and efficient agile backlog burndown looping.

## R1.1 · 2026-11-27 · refines R1
Reading: "instinct" = the owner's intent, kept verbatim and refined in dated lines beside it.
Source: R1 does not settle it; this is the reading with fewer features (shot-lessons rule).

## D1 · 2026-11-27 · layout · req: R1
`skills/bigbang/` holds modules.py, burndown.py, tanks.py and templates/.
Reason: packages.py is 1469 lines; bigbang logic is a separate domain.
```

| Kind | Id | Body | Who writes |
| --- | --- | --- | --- |
| Requirement | `R<n>` | the owner's words as a `>` quote, byte-identical to the source | `bigbang goals` only |
| Refinement | `R<n>.<m> · refines R<n>` | one reading of a requirement the words leave open, plus its source | the agent, in an `Owner-Approved:` commit |
| Decision | `D<n> · <area> · req: R<n>` | a choice that changes the repository's layout or a domain's home, plus its reason | the agent, in an `Owner-Approved:` commit |

Requirements are immutable: a later change of mind is a new `R`, and its first line names the one it replaces (`supersedes R1`). Ids never get reused.

## `bigbang goals <quote-file>`

1. Read the file's bytes. The agent writes the owner's chat message to that file unchanged (a scratch file, outside the repo).
2. If a requirement block with the identical quote exists → print `ok: goals: already R<n>`, write nothing.
3. Otherwise append `## R<next> · <today>` and the quote (each line prefixed `> `), create the page from the template if missing, and print `ok: goals: R<n>`.

It never commits. The owner's commit (or the agent's, with the trailer) records it.

On a fresh project with the `goals` layer, the owner's first prompt becomes R1 and the sketch brief ([domains.md](domains.md) "Sketch first") cites it.

## Probe

Fails, each with its fix:

- Page missing → `fix: bigbang goals <file with the owner's words>`.
- A block header that does not parse (`## <id> · <date> …`), a duplicate id, a refinement naming an unknown `R`.
- A `ROADMAP.md` step without `req:`, or whose `req:` names an unknown id → `fix: add req: R<n> to step <ticket id> in ROADMAP.md`.

Report lines (never fails):

```
goals: 3 requirements, 2 refinements, 1 decision
uncovered: R3
```

`uncovered` lists requirements that no step or goal cites, directly or through a refinement. The loop treats an uncovered requirement as roadmap work: the CTO (or the light-loop agent) drafts the steps.

## Step line

[burndown.md](burndown.md)'s step grammar gains one required field:

```markdown
- ENG-101 · req: R1 · entry: `bigbang core` · visible: `burndown:` line with live count
```
