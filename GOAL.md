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
