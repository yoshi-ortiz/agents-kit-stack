---
name: ota-ci
description: Use when testing Yoshi Stack changes on this machine, refreshing Kit skills across every agent after an edit, or pushing committed changes to the dev branch.
---

# OTA CI

Internal dev-env tooling for this checkout. Run the Kit script by its absolute
path, `~/.agents/skills/kit/packages.py` (every agent has Kit there):

```bash
python3 ~/.agents/skills/kit/packages.py dev-sync
```

Syncs locally by default. Pass `--push` to push committed changes first, or
`--dry-run` to preview. On `main`, pass `--allow-main` only if the user
explicitly requested a main sync. Report the refresh (and push, if requested)
results. If a step fails, report it and stop. Never force-push.
