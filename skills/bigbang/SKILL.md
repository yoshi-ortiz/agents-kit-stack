---
name: bigbang
description: Bootstrap a project from an empty directory or existing checkout, then configure its Kit domains and verify setup.
---

# Bigbang

For a new project, capture the user's requirements verbatim before choosing
domain stacks or a layout. From the target directory, run the Kit script using
its absolute path:

```bash
python3 /path/to/skills/kit/packages.py bigbang [<domain>...]
```

Resolve `../kit/packages.py` from this skill's directory. Domains default to `core`. Report the `ok` and `FAIL` lines. A `FAIL` names its fix; do not work around it.

Add `--dry-run` to preview without writing files. Setup runs these steps:

1. Initialize Git if needed. Use the existing repository root when already
   inside a checkout. Leave existing project files and Git history in place.
2. Index the Kit catalog if needed and configure the selected domains' MCP servers.
3. If a mise config exists, run its `stage0` task or `mise install`.
4. Check the project's stdio MCP servers and run Kit verification.
