# Babysitter (`shot:` prompts)

A host without a session tool (one that starts another agent session) runs `runbooks/loop.md` instead.

The steps are `runbooks/loop.md`'s, split across three roles. Every session start, end and park goes through
`bigbang ledger`, which refuses a second live CTO or SWE.

| Role | Model / effort (relative) | Runs | Ends its turn with |
| --- | --- | --- | --- |
| CEO: the owner's session | the opened model, low | `bigbang ledger start cto <name> <id>`, then one CTO with `cto:`; reviews each delivery against the burndown; owner-safe approvals | the burndown, and a question only for the owner's one step |
| CTO | same model, medium | steps 1–3 and 7–9; writes the red test of step 4; checks each receipt | the `bigbang brief`, screenshots attached |
| SWE goldfish, fresh per ticket | the vendor's small model, low | step 4's `TODO(<id>)` skeleton against the CTO's red test, and steps 5–6 | a report: sha, test result, receipt path, blockers |

- Relative models: a host starts sessions at the same model and effort or lower. The CEO raises the CTO's effort
  once, with the owner's allow.
- Goldfish brief: the ticket line, its red test path, and the files the test touches. History stays with the CTO.
- Ledger: `bigbang ledger start swe <name> <id>` before a goldfish starts; `bigbang ledger end <name> <sha>` when
  it reports; `bigbang ledger park <name>` when it is blocked. An entry silent past `[loop] stale_hours` stops
  blocking.
