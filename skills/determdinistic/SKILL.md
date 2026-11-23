---
name: determdinistic
description: Audit Markdown fields, normalize their structure, or extract values and calculate totals from Markdown documents.
---

# deterMDinistic

Run `determdinistic.py` beside this skill using its absolute path.

- Audit: `python3 SCRIPT FILE.md` prints JSON values and line diagnostics.
- Fix: `python3 SCRIPT FILE.md --fix` prints normalized Markdown to stdout.
  Review that output before replacing the source. Preserve ambiguous values and
  report any remaining diagnostics.
- For totals, ordered list counts, or table analytics, read `--help` or
  `query --help`. Only the `query` mode requires DuckDB.

Replace `SCRIPT` with the script path and `FILE.md` with the target path.
