# `loop`: the agentic loop

Reached from [bigbang.md](../bigbang.md) build step 6. `stops = False`.

The loop's logic is `bigbang`'s output; the runbooks tell the agent how to act on it. Both are templates `apply` writes into the project's `runbooks/` when missing. Probe fails when a runbook is missing or, with `module:babysitter`, when the ledger shows a second live CTO or SWE.

## Chat: the session entry point

A session starts with `@ROADMAP.md`. The template's header (`skills/bigbang/templates/ROADMAP.md`) is the agent's whole brief, so the page works on every host that loads a file mention:

| The owner says | The agent |
| --- | --- |
| status ("how are we doing?") | runs `bigbang`, answers with its `burndown:`, `next:` and `held:` lines |
| priority ("do X first") | rewrites `Order:` |
| spec ("X should show Y") | edits that ticket's `entry:`/`visible:`, or adds a ticket, in the owner's words |
| build ("go") | runs the light loop from `next:` |

Priority and spec edits change an owner-owned file, so they land in a commit with `Owner-Approved: <owner>` and the owner's chat words in the body. On Claude Code the `ask` rule makes the host confirm the edit with the owner first.

## `runbooks/loop.md`: the light loop (default)

One agent, one step at a time. The template text:

1. **Read.** Run `bigbang`. *Done when* every setup module prints `ok`. A setup `FAIL` is the work: fix it, then run again.
2. **Steer.** Act on the owner's chat first: a new `Order:` or a changed ticket line, committed with `Owner-Approved:`. With the `goals` layer, an `uncovered: R<n>` line also asks for tickets.
3. **Take** the `next:` step and branch from `base` as `{lid}-<slug>` (forms in [burndown.md](burndown.md) "Ticket ids"). `next: none` → write the push brief and stop.
4. **Skeleton.** Locate every site the step touches (tree-sitter MCP when the host has it, else `rg` and reading the source). Write `TODO({id})` at each site, and a test tagged `_{tid}_` (or `{id}: `) that walks the step's `entry:` and asserts its `visible:` result. *Done when* the tagged test runs `red` for the reason the step names. The skeleton stays uncommitted until step 5.
5. **Burn.** Implement until `select` for the id exits 0 and `git grep -c 'TODO({id})'` prints nothing.
6. **Receipt.** Walk `entry:` to `visible:` as an end user; save `receipts/<id>/journey.md` and screenshots of the visible result; commit code, test and receipt together with the id first in the subject; one ticket per commit.
7. **Prove.** `git checkout <base> && git merge --no-ff <branch>` (the hook runs the gate), then `bigbang`. *Done when* the step reads `live`, or `green` with its failing `[evidence]` command named in the report.
8. **Blocked** at any point (a `limit:`, an owner-level operation, a missing permission) → add the step and its exact command to the push brief, return to 3 in the same turn.
9. **Brief.** Screenshot the project into `.bigbang/status/`, run `bigbang brief`, post it with the screenshots attached, then return to 1.

**Stop** on the first of: `next: none`; `[loop] max_steps` steps taken this run; a plan-limit or rate-limit message; a cost cap. The last message is the burndown and the push brief.

**Push brief.** Written once, at the stop: the epic benchmark and its result, the burndown lines, each blocked or parked step with its one command, and the push to main as the owner's one command. Each command is short and readable, one per line.

## `runbooks/babysitter.md`: the babysitter loop (`shot:` only)

Installed with `module:babysitter`. A prompt starting with `shot:` points the agent to it. Its first line: "This host has no session tool → use runbooks/loop.md" for hosts without one. Same steps, split across roles:

| Role | Model / effort (relative) | Runs | Ends its turn with |
| --- | --- | --- | --- |
| CEO: the owner's session | the opened model, low | `bigbang ledger start cto …`, then starts one CTO with `cto:`; reviews each delivery against the burndown; owner-safe approvals | the burndown, and a question only for the owner's one step |
| CTO | same model, medium | steps 1–3, 6–8; writes the red test of step 4 | the burndown |
| SWE goldfish, fresh per step | the vendor's small model, low | step 4's TODO skeleton against the CTO's red test, and step 5 | a report: sha, test result, blockers |

- **Relative models**: hosts start subagents only at the same model and effort or lower. The CEO raises the CTO's effort once, with the owner's allow.
- **Goldfish brief**: the step line, its red test path, and the files the test touches. History stays with the CTO (a long-lived builder drifted for days). With an EGM source in `PACK.md` (open decision 3), add the `EGM.md` contracts of the touched directories.
- **Host tools**: Claude Code sessions, Codex `spawn_agent`, Cursor and Antigravity subagents. Pi and Zed run the light loop until their session tool is confirmed.

## Ledger: `.bigbang/sessions.jsonl`

Written only by `bigbang ledger`, one JSON row per call:

```json
{"ts": "2026-11-27T10:00:00Z", "op": "start", "role": "swe", "name": "swe-s5", "id": "<host session id>"}
{"ts": "2026-11-27T10:40:00Z", "op": "end", "name": "swe-s5", "sha": "e4f5a6b"}
{"ts": "2026-11-27T10:41:00Z", "op": "park", "name": "cto-1"}
```

- A name is **live** from its `start` until its `end` or `park`, unless its last row is older than `stale_hours`: then it is **stale** and no longer counts.
- `ledger start <role>` fails (exit 1, nothing written) while another live entry has that role and the role is `cto` or `swe`. Fix: `bigbang ledger end <name> <sha>` or `park <name>`.
- `end` requires a sha that `git cat-file -e` finds.
- The `loop` probe reports `live: cto-1, swe-s5` and fails on two live entries of one role (rows written by hand).

Ignored by git (`.gitignore` line added by `apply`): the ledger is per checkout.
