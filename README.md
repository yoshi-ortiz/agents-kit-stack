# Yoshi Stack

Set up a checkout without loading an entire skill catalog into agent context.

- [Kit](skills/kit/SKILL.md) provides skills on demand and configures MCP servers for named domains.
- [Bigbang](skills/bigbang/SKILL.md) sets up a checkout, checks that its stdio MCP servers start, and verifies Kit.
- [deterMDinistic](skills/determdinistic/SKILL.md) audits and normalizes Markdown so tools can read its values.
- [Dev Sync](skills/dev-sync/SKILL.md) pushes committed changes from `dev` and refreshes every repo skill and the Kit catalog on this machine. Use `--local-only` to skip the push. Syncing from `main` requires `--allow-main`.

See [Goal and scope](GOAL.md) for the project spec.
