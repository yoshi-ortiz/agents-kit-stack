---
name: dev-sync
description: Push committed Yoshi Stack changes and refresh Kit skills across supported agents on this machine.
disable-model-invocation: true
---

# Dev Sync

Run the Kit script at `../kit/packages.py` relative to this skill. Use its
absolute path in the command:

```bash
python3 /path/to/skills/kit/packages.py dev-sync
```

Use `--dry-run` to preview or `--local-only` to refresh without pushing.
Each sync picks up every skill with a `skills/<name>/SKILL.md` entrypoint.
On `main`, pass `--allow-main` only if the user
explicitly requested a main sync. Report the push and refresh results. If a
step fails, report it and stop. Never force-push.
