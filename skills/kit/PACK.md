# Kit pack

Read by `packages.py`, never loaded into an agent, so this file can grow.
Nothing here installs by itself. `kit <domain>` or `kit <skill>` installs only what it names.

# Agents

The universal store `.agents/skills` serves every agent that reads it (Codex, Cursor,
Antigravity, Cline, Amp and others). Other agents listed here get symlinks into the store.
`*` is refused: it makes real copies for some agents.

1. claude-code
2. codex
3. pi
4. cursor
5. zed
6. antigravity

# Agent-owned

Entries the agents ship or manage themselves. Kit ignores these names in agent skill folders.

1. check-work
2. code-review
3. create-skill
4. docx
5. help
6. imagine
7. pptx
8. xlsx
9. synced
10. hatch-pet
11. imagegen
12. openai-docs
13. review-agent
14. skill-creator
15. skill-installer
16. rex

# Tools

Tools no Claude Code session loads. `kit tools` and `kit-starter-pack` write them as bare-name deny
rules in `~/.claude/settings.json`, which leave a tool out of context entirely. Bare names and globs only.
Evidence: TokenEconomizer found each unused across 42 sessions and 604 prompts in this repo. The desktop
app's own tools (`ccd_*`, terminal, browser, computer use) are left alone.

1. `mcp__Blender__*`
2. `mcp__Figma__*`
3. `mcp__092ad12a-3008-41b0-a890-65b381d8104c__*`
4. `mcp__Shadcn_UI__*`
5. `mcp__cmux-cua__*`
6. `NotebookEdit`
7. `CronCreate`
8. `CronDelete`
9. `CronList`
10. `RemoteTrigger`
11. `PushNotification`

# Tags

Canonical tags for filtering skills (`kit tag <tag>...` or `kit <tag>`).
Set tags in the `# Batteries included` table or via a `Tags: a, b` line under a `## <domain>` heading.
Domain names are implicit tags. Every tag used below must be declared here; undeclared or malformed tags fail verification.

1. apple
2. architecture
3. cloud
4. code
5. core
6. debugging
7. design
8. docs
9. ios
10. mcp
11. media
12. swift
13. testing
14. web
15. workflow

# Batteries included

The catalog. One table row per source: `| Source | Skills | Tags |`.
`all` offers every skill in the repo; otherwise list the skill names.
The link text is the publisher stamped into each installed skill's `metadata:`.
A row here that does not parse fails the run.

| Source | Skills | Tags |
| --- | --- | --- |
| <img src="https://github.com/mattpocock.png" width="20"> [Matt Pocock](https://github.com/mattpocock/skills) | all | code, workflow, architecture, testing |
| <img src="https://github.com/addyosmani.png" width="20"> [Addy Osmani](https://github.com/addyosmani/agent-skills) | all | web, workflow, architecture, testing |
| <img src="https://github.com/backnotprop.png" width="20"> [pstack](https://github.com/backnotprop/pstack) | all | code, workflow, architecture, debugging |
| <img src="https://github.com/DietrichGebert.png" width="20"> [ponytail](https://github.com/DietrichGebert/ponytail) | all | code, workflow |
| <img src="https://github.com/obra.png" width="20"> [superpowers](https://github.com/obra/superpowers) | all | code, workflow, debugging, testing |
| <img src="https://github.com/google.png" width="20"> [Elephant Goldfish Model](https://github.com/google/elephant-goldfish-model) | all | workflow, architecture |
| <img src="https://github.com/microsoft.png" width="20"> [TokenEconomizer](https://github.com/microsoft/TokenEconomizer) | all | workflow |
| <img src="https://github.com/googlechrome.png" width="20"> [Modern Web Guidance](https://github.com/googlechrome/modern-web-guidance) | all | web |
| <img src="https://github.com/tuist.png" width="20"> [Tuist](https://github.com/tuist/agent-skills) | all | apple, ios, swift |
| <img src="https://github.com/anthropics.png" width="20"> [Anthropic](https://github.com/anthropics/skills) | all | web, docs, design, mcp |
| <img src="https://github.com/upstash.png" width="20"> [Context7](https://github.com/upstash/context7) | all | docs, mcp |
| <img src="https://github.com/hashicorp.png" width="20"> [HashiCorp](https://github.com/hashicorp/agent-skills) | all | cloud |
| <img src="https://github.com/cloudflare.png" width="20"> [Cloudflare](https://github.com/cloudflare/skills) | all | cloud, web |
| [benjitaylor/skills](https://github.com/benjitaylor/skills) | all | design, web |
| <img src="https://github.com/mindrally.png" width="20"> [mindrally](https://github.com/mindrally/skills) | bootstrap, swift, swiftui-development | - |
| <img src="https://github.com/digitalsamba.png" width="20"> [Digital Samba](https://github.com/digitalsamba/claude-code-video-toolkit) | ffmpeg | media |

# Domains

What to install per project domain. Write a skill as its name, as `owner/repo:name`
(or `owner/repo: a, b` to group skills from one repo), or `owner/repo` alone for all of its skills.

## core

Tags: code

1. ponytail
2. ponytail-review
3. handoff
4. diagnosing-bugs
5. codebase-design
6. mattpocock/skills:tdd
7. writing-for-agents
8. research
9. mcp:tree-sitter

## architecture

1. backnotprop/pstack:architect
2. improve-codebase-architecture

## web

Tags: design

1. frontend-design
2. modern-web-guidance
3. frontend-ui-engineering

## docs

1. context7-mcp

## cloud

Tags: mcp

1. hashicorp/agent-skills: terraform-style-guide, terraform-test, terraform-stacks, terraform-policy, aws-ami-builder, azure-image-builder, azure-verified-modules
2. cloudflare/skills: cloudflare, wrangler, workers-best-practices, durable-objects, agents-sdk
3. mcp:terraform
4. mcp:cloudflare

## ios

Tags: apple, swift

1. tuist/agent-skills: using-tuist-generated-projects, debug-generated-project, fix-flaky-tests
2. mindrally/skills: swift, swiftui-development

# Helpers

Not installed. Read by hand.

* `okf` skill helper from source scripts: [okf-wiki QUICKSTART](https://github.com/mchu1966/okf-wiki/blob/master/QUICKSTART.md)
* `engineering:*` (system-design and others): installed locally as `engineering@inline`; no source repo known.
* Cloudflare MCP guide (not a skill): [cloudflare/mcp AGENTS.md](https://github.com/cloudflare/mcp/blob/main/AGENTS.md)
* HashiCorp Terraform MCP prompt (not a skill): [developer.hashicorp.com](https://developer.hashicorp.com/terraform/mcp-server/prompt)

# MCP servers

Added per project by `kit domain <domain>` when a domain lists `mcp:<name>`: Claude Code gets them in
`.mcp.json`, Codex in `.codex/config.toml`. They load only in that project. Format: `1. name url` or `1. name command args`.

1. terraform docker run -i --rm hashicorp/terraform-mcp-server:1.4.1
2. cloudflare https://mcp.cloudflare.com/mcp
3. tree-sitter uvx --with mcp<2 mcp-server-tree-sitter==0.7.0

Not added yet, reference only: context7, [WebMCP](https://developer.chrome.com/docs/ai/webmcp?hl=es-419),
[chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp), playwright.
