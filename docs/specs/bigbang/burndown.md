# `burndown`: the roadmap graph

Reached from [bigbang.md](../bigbang.md) build step 5. `stops = False`.

## Input: `ROADMAP.md`

The owner's page (owner-owned, [guardrail.md](guardrail.md)). One epic first, then goals. Every epic, goal and step is keyed by a **ticket id** in the project's own convention (below).

```markdown
## Epic: ENG-100 · <name> · benchmark: <measurable pass/fail>
Order: ENG-103, ENG-101
- ENG-101 · req: R1 · entry: `Files tab → Upload` · visible: the PDF opens as Markdown with its chapter headings
- ENG-102 · req: R1.1 · entry: `cli convert book.epub` · visible: `book.md` with front matter · parked: needs GPU outside budget
- BUG-7 · req: R2 · entry: `bigbang` · visible: `next:` names ENG-101 · limit: hardware
## Goals
- ENG-110 · req: R2 · benchmark: <pass/fail> · steps: ENG-103, ENG-104
```

## Read through determdinistic

`burndown` and `goals` parse `ROADMAP.md` and the requirements page with `tickets()` from `skills/determdinistic/determdinistic.py`, the one Markdown parser in the stack (fences, HTML blocks and front matter are skipped the same way its audit skips them). It returns every ticket line and a `links` edge `{from, field, to}` for each id a field cites. The relation is many-to-many: one ticket cites several requirements (`req: R1, R2`), one requirement is cited by many tickets, a goal lists many steps (`steps:`), and `Order:` links the epic to the steps it puts first. Bigbang reads the edges in Python, with no DuckDB needed. A person or agent asking cross-cutting questions runs the same index through DuckDB:

```bash
python3 skills/determdinistic/determdinistic.py tickets ROADMAP.md docs/specs/requirements.md \
  --pattern '[A-Z][A-Z0-9]*-[0-9]+' --pattern 'R[0-9]+(\.[0-9]+)?' \
  --sql "SELECT dst AS req, string_agg(src, ',') AS tickets FROM links WHERE field = 'req' GROUP BY dst"
```

## Ticket ids

The tracker is the project's choice: Linear (`ENG-123`, the template default), Jira (`PROJ-42`), GitHub issues (`GH-17`), or a custom convention (`EPIC-1`, `S1`, `BUG-7`, `TODO-3`). `[ids] pattern` in `guardrail.toml` is the one definition; an id is any token the regex fully matches. Examples:

| Convention | `pattern` |
| --- | --- |
| Linear, Jira, `GH-17` | `[A-Z][A-Z0-9]*-[0-9]+` |
| Custom prefixes | `(EPIC\|S\|BUG\|TODO)-?[0-9]+` |
| Bare steps from v1 | `[SG][0-9]+` |

The role of an id comes from where it sits on the page (the epic heading, a step line, a goal line), never from its prefix. So one tracker's ids fill every role, and a `BUG-7` is a step like any other.

**Derived forms**, used by `select` templates, test tags and the loop:

| Placeholder | Form | `ENG-123` | `S1` |
| --- | --- | --- | --- |
| `{id}` | as written | `ENG-123` | `S1` |
| `{tid}` | every non-alphanumeric run → `_` | `ENG_123` | `S1` |
| `{lid}` | `{tid}` lowercased | `eng_123` | `s1` |

A test is tagged by `_{tid}_` or `_{lid}_` in its name (`test_ENG_123_pdf_opens`, `fn test_eng_123_pdf_opens`), or by a `{id}: ` name prefix (`test("ENG-123: pdf opens")`). The delimiters make `ENG-12` miss `ENG-123`. In code, `TODO({id})` marks a site; commit subjects start `{id}: `; the loop's branch is `{lid}-<slug>` with `_` → `-`, so Linear, Jira and GitHub link branches and commits to the ticket on their own.

**Tracker state carries zero weight.** A ticket marked Done in the tracker is agent- or human-written status (F7). The tracker is where ids come from and where links point; `bigbang` computes state from tests on `base`.

- `[ids] url` (optional): report and push-brief lines print `{id}` as that link.
- `[ids] export` (optional): after `apply` appends a burndown row, `bigbang --sync` pipes the row as JSON to this command, which may write states back to the tracker. It runs only with `--sync` (an outward-facing write, explicit like `--paid`), and `--dry-run` prints it as `would:`.
- Importing tickets: the agent reads the tracker through its MCP or CLI and drafts step lines. They enter `ROADMAP.md` like any owner-owned edit; each still needs `req:`, `entry:` and `visible:`.

## Step grammar

One line per step, fields split on ` · `:

| Field | Required | Rule |
| --- | --- | --- |
| id | yes | first; fully matches `[ids] pattern`; unique on the page |
| `req:` | with `goals` | an `R`/`R.m` id from the requirements page ([goals.md](goals.md)) |
| `entry:` | yes | where an end user starts: a UI path or a command |
| `visible:` | yes | what the user sees when it works (shot-lessons: two-word step titles produced proofs of the wrong path) |
| `parked:` | no | a reason; the step leaves `next:` |
| `limit:` | no | a `[limits]` name the step must change; the step is owner-blocked |

Any other text on the line, including `Status:`, is ignored. `Order:` under the epic heading lists steps to work first; unlisted steps follow in file order.

Probe fails: page missing (apply writes the template), no epic heading or an epic heading without an id, a step line missing a required field, an id that does not fully match `[ids] pattern`, a duplicate id, a `limit:` naming no `[limits]` key, a goal naming an unknown step.

## State per step

Computed on `base`, at its current sha:

| State | Rule |
| --- | --- |
| `open` | `git grep -l -e '_{tid}_' -e '_{lid}_' -e '{id}: '` over `[burndown] tests` globs finds nothing |
| `red` | a tagged test exists; `select` with the id's placeholders filled exits non-zero |
| `green` | `select` exits 0, but the step's `[evidence]` command fails, or no receipt is committed under `receipts/<id>/` at that sha (with `[receipts] required = true`, the default); the row's `why` names which |
| `live` | `select` exits 0, `[evidence]` (when present) exits 0, a receipt is committed, no `limit:` |
| `blocked` | `select` exits 0 and the step has `limit:` |
| `parked` | the line has `parked:`; no command runs |

A step with no `[evidence]` entry can reach `live` on its tagged test alone: `[evidence]` is the project's choice to raise the bar.

**Running on `base`.** `git worktree add --detach .bigbang/wt <base-sha>` (reused, moved with `git -C .bigbang/wt checkout --detach <sha>`), then each `select` runs there. `.bigbang/wt` is in the template `.gitignore` lines `apply` appends to `.gitignore` when missing.

**Cache.** `.bigbang/burndown.jsonl`, one row per `base` sha:

```json
{"sha": "a1b2c3d…", "ts": "2026-11-27T10:00:00Z", "roadmap": "<sha256 of ROADMAP.md>", "states": {"ENG-101": "live", "ENG-102": "parked"}}
```

When the latest row has the current `base` sha and the same `roadmap` hash, its states are reused and nothing runs. Otherwise `apply` computes the states and appends a row. A run on an unchanged sha appends nothing (F8). The file is per checkout (ignored by git): versioned, committing a row would move `base` and call for another row.

## Receipts and the shot brief

A **receipt** closes a ticket: `receipts/<id>/journey.md` (the walk from `entry:` to `visible:`, each step with the screenshot it produced) plus screenshots or a GIF of the visible result, committed with the ticket's code. `burndown` reads it with `git ls-tree` at the base sha, so an uncommitted or branch-only receipt does not count. `[receipts] dir` and `required` live in `guardrail.toml`.

`bigbang brief` prints the **shot brief** (and saves `.bigbang/brief.md`): the `burndown:` and `graph:` lines, the newest project status screenshots from `.bigbang/status/` (ignored by git; the agent captures one per shot), a backlog table with each ticket's state, its `why` when green, and links to its journey report and screenshots, then `next:` and `held:`. The agent posts it at the end of every shot and for every status request, with the screenshots attached.

## Report

Printed every run, at most 8 lines:

```
burndown: Epic <name> · live 3/7, green 1, red 2, open 0, blocked 0, parked 1 (was live 2/7 at a1b2c3d)
| Step | State | Changed |
| ENG-104 | live | was green at a1b2c3d |
| BUG-7 | red | first seen |
graph: live ▁▂▂▃▅ (last 5 base commits)
next: BUG-7 · entry: `…` · visible: `…`
```

- The first line's "was" compares the latest row with the previous one.
- The table lists only steps whose state changed between those two rows, at most 4; more → `… and <n> more`.
- `graph:` uses the live counts of the last 5 rows, scaled to `▁▂▃▄▅▆▇█` against the step count.
- `next:` is the first step in `Order:`, then file order, whose state is `open`, `red` or `green`. None left → `next: none · push brief due`.
- `blocked` and `parked` steps go to the push brief ([loop.md](loop.md)), never to `next:`.
