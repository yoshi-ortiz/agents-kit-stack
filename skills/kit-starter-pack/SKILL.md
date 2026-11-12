---
name: kit-starter-pack
disable-model-invocation: true
description: Set up or refresh Kit's local catalog and explicit-only Claude Code and Codex plugins.
---

# Kit starter pack

Run `python3 ~/.agents/skills/kit/packages.py kit-starter-pack`. Report which hosts received the plugins and any failures.

Setup indexes the catalog, installs publisher plugins, registers shared commands, and applies Kit's Claude Code tool rules. Start a fresh session to pick up changes. Use `/publisher:skill` in Claude Code, `$publisher:skill` in Codex CLI and desktop, `/publisher-skill` in Cursor and Zed, `/skill:publisher-skill` in Pi, or `/kit publisher:skill` in Antigravity. Use `kit <domain>` from a project to configure its declared MCP servers.
