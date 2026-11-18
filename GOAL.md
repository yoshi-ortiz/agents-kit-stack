# Goal and scope

Kit and Bigbang make a checkout ready to work while keeping agent context small.

- **Kit** provides a catalog of skills that load on demand. A project opts into
  named domains, and each domain declares its MCP servers. The catalog and
  domain definitions live in [PACK.md](skills/kit/PACK.md).
- **Bigbang** sets up one checkout. It prepares the Kit catalog, configures the
  selected domains (default: core), runs the project's mise setup when present,
  checks that configured stdio MCP servers answer initialization, and runs Kit
  verification. Setup failures stop the run and surface the failed step.

Keep the skill instructions short and put repeatable operations in code. Use
the `slop` branch to recover the rationale behind previous work.

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
