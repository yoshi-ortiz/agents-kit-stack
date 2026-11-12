---
name: kit
disable-model-invocation: true
description: Call any skill from the kit catalog without preloading it, add a domain's MCP servers, or add a source. Use for kit, kit <skill>, kit <domain>, kit add, kit-starter-pack.
---

# Kit

`K` means `python3 packages.py` using the script beside this skill. Run it from the user's project for project commands.

| The user says | Run | Then |
| --- | --- | --- |
| `kit` | `K` | Report the `ok` or `FAIL` lines. On `first run`, run `K kit-starter-pack`. |
| `kit-starter-pack` | `K kit-starter-pack` | Report the last line. |
| `kit <skill>` or `kit <publisher>:<skill>` | `K use <skill>` with the supplied name | Follow the printed skill. Resolve its relative paths from the printed `dir`. |
| `kit domain <domain>`, or a declared domain such as `kit cloud` | `K domain <domain>` | Report the project MCP servers and available skill commands. |
| `kit add <github url or owner/repo>` | `K add <url>` | Then run `K kit-starter-pack`. |
| `kit install <skill>` | `K <skill>` | Install in the project for native discovery. |
| `kit remove <skill>` | `K remove <skill>` | |
| `kit tools` | `K tools` | |

Rules:

1. `use` says a name is offered twice: run `K use owner/repo:<skill>` with the source the user means.
2. After setup, Claude Code has `/publisher:skill`, Codex has `$publisher:skill`, Cursor and Zed have `/publisher-skill`, and Pi has `/skill:publisher-skill`. In Antigravity, use `/kit publisher:skill`.
3. Read [PACK.md](PACK.md) when editing the catalog. Put skill repositories under `# Batteries included` and MCP endpoints under `# MCP servers`. A domain activates only the servers it lists as `mcp:name`.
4. For a release check, run `K verify --strict-projection`. Compare startup context in fresh sessions separately from the Claude Code token estimate.
