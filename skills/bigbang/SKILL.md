---
name: bigbang
disable-model-invocation: true
description: Set up this checkout in one command: kit catalog, domain MCP servers (default core), the project's mise stage 0, and proof that every stdio MCP server starts. Use for bigbang, setup, stage 0.
---

# Bigbang

From the project root, run the Kit script using its absolute path:

```bash
python3 /path/to/skills/kit/packages.py bigbang [<domain>...]
```

Resolve `../kit/packages.py` from this skill's directory. Domains default to `core`. Report the `ok` and `FAIL` lines. A `FAIL` names its fix; do not work around it.

Steps it runs, each a hard gate:

1. `kit-starter-pack` if the catalog is not indexed yet (skills stay on demand: callable, never loaded until invoked).
2. `domain <domain>...`: the domain's MCP servers into `.mcp.json` and `.codex/config.toml`.
3. `mise run stage0` when the project defines it, else `mise install`.
4. Start each stdio server in `.mcp.json` once with an MCP `initialize`.
5. `verify`.
