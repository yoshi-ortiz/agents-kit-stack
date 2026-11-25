---
name: dev-sync
description: Refresh Kit skills across supported agents on this machine, with optional --push for committed Yoshi Stack changes.
---

# Dev Sync

Run the Kit script at `../kit/packages.py` relative to this skill. Use its
absolute path in the command:

```bash
python3 /path/to/skills/kit/packages.py dev-sync
```

Syncs locally by default. Pass `--push` to push committed changes first, or
`--dry-run` to preview. Each sync picks up every skill with a
`skills/<name>/SKILL.md` entrypoint. On `main`, pass `--allow-main` only if
the user explicitly requested a main sync. Report the refresh (and push, if
requested) results. If a step fails, report it and stop. Never force-push.
