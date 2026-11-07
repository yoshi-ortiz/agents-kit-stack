# Project goals

Cyber Skills packages agent skills across a six-family rail based on the software development lifecycle.

The primary goal is direct: advance feature burndown through verified, accepted work with fewer attempts and lower token burn.

## Failures prevented

Sessions usually fail in three predictable ways. Each failure has a distinct defense.

| Failure | Symptoms | Defense |
| --- | --- | --- |
| Max | The context window fills up, compacts mid-thought, and loses the thread. | Enforce strict byte limits on always-loaded files (`max_file_bytes`). Caps are checked mechanically before a run. |
| Waste | Agents burn tokens searching blindly or re-deriving decisions already recorded in the tree. | High signal density. Use a single term per concept, keep specs free of speculation, and route to exact files. |
| Stuck | An agent loops on a blocked task, burning budget without completing items. | Nonblocking background tasks, full logs, and a burndown tracking one state per task (`TODO`, `IN-PROGRESS`, `BLOCKED`, `DONE`). |

## Token weight

Text read by a model carries cost on two separate axes:

- **Token cost**: How many tokens the text consumes. Counted in bytes before the session runs.
- **Signal density**: Whether the text sharpens attention or dilutes it. Dense text gives concrete instructions, file references, and single-meaning terms so the model acts on the first read.

A skill file byte cap sets its worst-case session load. Keeping files small prevents silent window bloat.

## The workflow rail

The rail organizes skills by lifecycle phase instead of an arbitrary list:

- **kit**: Day 0 machine and tool setup. Runs outside the loop.
- **first**: Planning, scoping, glossary definitions, and specification promotion (`/first-*`).
- **build**: Writing code, building assets, and testing (`/build-*`).
- **land**: Irreversible operations, releases, and deployments (`/land-*`).
- **check**: Read-only verification, progress auditing, and codebase checks (`/check-*`).
- **fix**: Incident response, bug fixes, and context recovery (`/fix`).

## Operational rules

- **Nonblocking execution**: Long tasks fan out in the background, send progress updates, and avoid freezing the main interaction loop.
- **Full logs**: Logs are saved in full and inspected directly. Pipes like `head` or `tail` that mask exit codes are avoided.
- **Idempotence**: Commands can run again without corrupting repository state.
- **Firm budgets**: A blown byte limit triggers an incident report in `BUGS.md`, not an automatic increase of the limit.
