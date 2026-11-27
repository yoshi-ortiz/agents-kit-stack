# Goal and scope

Kit and Bigbang make a checkout ready to work across every configured agent
while keeping startup context small.

- **Kit** provides a catalog of skills that load on demand across every agent
  declared in [PACK.md](skills/kit/PACK.md) (`claude-code`, `codex`, `pi`,
  `cursor`, `zed`, `antigravity`). First-party harness core skills (`skills/*`)
  stay model-visible; catalog skills stay out of startup context wherever the
  host supports explicit invocation. A project opts into named domains, and each
  domain declares its MCP servers.
- **Bigbang** sets up an empty project directory or an existing checkout. It
  initializes Git if needed, prepares the Kit catalog, configures the
  selected domains (default: core), runs the project's mise setup when present,
  checks that configured stdio MCP servers answer initialization, and runs Kit
  verification. Setup failures stop the run and surface the failed step.

Keep the skill instructions short and put repeatable operations in code. Use
[AGENTS.md](AGENTS.md) for active harness rules, [INCIDENTS.md](INCIDENTS.md)
for value-breach postmortems, and the `slop` branch to recover the rationale
behind previous work.

## Planned skill goals

- **Bigbang** establishes a convention for starting and evolving a project.
  Verbatim user requirements first, then refine the user instincts understanding of an
  umbrella domain as work proceeds. Use that understanding to design a repository
  where each domain's code, assets, and configuration have a clear home.
  Link requirements to roadmap items and use Shot outcomes to track
  burndown against those requirements. Keep requirements, roadmap state, and
  decisions that change the repository structure in version control so the
  layout stays understandable as the project grows.
- **deterMDinistic** audits Markdown documents and fixes inconsistent
  structure so tools can read values directly. It preserves the document's
  meaning and flags ambiguous values for review.
  Its value for tickets: it indexes ticket ids in any tracker convention and the
  many-to-many links between them (tickets, requirements, goals), queryable in
  DuckDB, and Bigbang's burndown reads the roadmap through it.
