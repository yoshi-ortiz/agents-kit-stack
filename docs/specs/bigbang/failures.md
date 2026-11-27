# Failures this spec closes

Rationale only; no build step reads this file. Source: homelab-infra `cpu/platform/eval/agent-shot` and `drive/docs/agents/shot-lessons.md`.

| # | Failure | Evidence | Closed by |
| --- | --- | --- | --- |
| F1 | Subset scorecard reads as a full pass | `scorecard.json` v5 9/9 `pass_rate: 1.0`; `cases.json` has 23; `run.py:415` checks only picked cases | card `partial` ([shots-tanks.md](shots-tanks.md)) |
| F2 | Card drops tokens | `goal.hold` names `output_tokens` (`run.py:85`); summary keeps only cost, latency, turns (`run.py:405-410`) | per-case, per-tank tokens |
| F3 | No noise measure | `--reps` default 1 | `reps >= 2`, spread in card |
| F4 | Only winners recorded | scorecard history v3 → v4 → v5 keeps only wins | `TANKS.md` |
| F5 | Docs drift from code | brief said 24 cases incl. `supervise-epic`; file has 23, none named so | `cases` from `cases.json` |
| F6 | Gate is Claude-only | `run.py:416` returns 3 for any other agent | adapter contract |
| F7 | Burndown read Status lines | `burndown()` calls `ev.statuses(text)` on the spec (`fix/shot-supervisor` shot.py:624) | states from tagged tests + `[evidence]` ([burndown.md](burndown.md)) |
| F8 | Burndown read mutates its own baseline | `burndown()` rewrites `.burndown` on every call (shot.py:651) | sha-keyed append in `apply` |
| — | Self-written status, stale branch, waived limits | 9/9, 10/10, `done` while broken | gate rules 2–4 ([guardrail.md](guardrail.md)); states on `base` |
| — | Swarm, stale ledger entry, drifting builder, idle builder, supervisor asking | shot-lessons derails | ledger, `stale_hours`, goldfish per step, park-and-continue ([loop.md](loop.md)) |
| — | Advertised features unmet; words lost between chat and roadmap | shot-lessons "whats the spec/context issue?" | `req:` on every step, `uncovered:` ([goals.md](goals.md)) |
