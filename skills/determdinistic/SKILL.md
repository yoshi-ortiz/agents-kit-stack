---
name: determdinistic
description: Audit Markdown fields, normalize their structure, extract values and calculate totals, or track ticket ids and their many-to-many links across Markdown documents.
---

# deterMDinistic

Run `determdinistic.py` beside this skill using its absolute path.

- Audit: `python3 SCRIPT FILE.md` prints JSON values and line diagnostics.
- Fix: `python3 SCRIPT FILE.md --fix` prints normalized Markdown to stdout.
  Review that output before replacing the source. Preserve ambiguous values and
  report any remaining diagnostics.
- For totals, ordered list counts, or table analytics, read `--help` or
  `query --help`.
- Tickets: `python3 SCRIPT tickets FILE.md... --pattern REGEX` indexes every
  ticket line (`- ENG-101 · req: R1, R2 · steps: …`) and emits each id it cites
  as a `links` edge. Any tracker convention works: repeat `--pattern` per
  convention (Linear `ENG-123`, `BUG-7`, `R1`). Add `--sql QUERY` to join tables
  `tickets`, `fields` and `links(src, field, dst)` in DuckDB: one ticket to many
  requirements, one requirement to many tickets. Bigbang's burndown reads
  `ROADMAP.md` through this mode.

Only `query` and `tickets --sql` require DuckDB. Replace `SCRIPT` with the
script path and `FILE.md` with the target path.
