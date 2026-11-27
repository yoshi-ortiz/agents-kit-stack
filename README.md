# Yoshi Stack

Set up a checkout without loading an entire skill catalog into agent context.

- [Kit](skills/kit/SKILL.md) provides skills on demand and configures MCP servers for named domains.
- [Bigbang](skills/bigbang/SKILL.md) sets up a checkout, checks that its stdio MCP servers start, and verifies Kit.
- [deterMDinistic](skills/determdinistic/SKILL.md) audits and normalizes Markdown so tools can read its values.
- [OTA CI](skills/kit-dev/ota-ci/SKILL.md) (`/kit-dev:ota-ci`, internal dev-env tooling, explicit-only) refreshes every repo skill and the Kit catalog on this machine from `dev`. Pass `--push` to push committed changes first. Syncing from `main` requires `--allow-main`.

See [Goal and scope](GOAL.md) for the project spec.
