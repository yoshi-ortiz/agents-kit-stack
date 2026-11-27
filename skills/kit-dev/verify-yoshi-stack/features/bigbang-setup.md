# Bigbang setup

`bigbang` turns an empty directory or an existing checkout into a project guarded. It inits Git, indexes the catalog, configures the domain's MCP servers and writes the rail files, the requirements page, the roadmap and the loop runbook. Then it audits the result. A second run repairs nothing and writes nothing.

## Sub-features

- `setup-dry` prints `would:` lines and writes nothing.
- `setup-first` runs every module on an empty dir and writes the rail.
- `setup-rerun` gives only `ok:` and report lines, with no writes.
- `setup-domains` takes compass layers (`--compass goals,babysitter,tanks`) and rejects unknown ones.

## How to get to it (user POV)

- `python3 skills/kit/packages.py bigbang [domain...]` from the project dir.
- The `bigbang` skill (`/bigbang`), which runs the same command.

## Driving it with vk

Preconditions:

- `vk doctor "$RUN"` exits 0 and reports `proj is empty (not yet git)`.

- **Dry run.** Run `vk kit "$RUN" setup-dry -- bigbang web --dry-run`. Expect exit `0` and `would: git: git init`, `would: guardrail: write guardrail.toml` and `would: loop: write runbooks/loop.md`. `setup-dry/tree.after` is empty.
- **First run.** Run `vk kit "$RUN" setup -- bigbang web`. Expect `done: git: git init`, `ok:` for `git`, `catalog`, `domains`, `mcp`, `guardrail`, `gate`, `burndown`, `loop`, `index` and `shots`, and `mcp: 1 stdio server(s) start: tree-sitter`. `setup/tree.after` lists `guardrail.toml`, `HALLUCINATIONS.md`, `ROADMAP.md`, `runbooks/loop.md`, `docs/specs/requirements.md`, `.bigbang/hooks/pre-merge-commit`, `.bigbang/hooks/pre-push`, `.claude/settings.json`, `.mcp.json`, `.gitignore`, and the index's `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`.
- **Exit code.** On a clean checkout the exit is `0`. On a dirty `skills/kit` it is `1`, from `FAIL: verify: uncommitted kit change: ...` lines only. Any other `FAIL:` is a real failure.
- **Rerun.** Run `vk kit "$RUN" setup-rerun -- bigbang`. Expect zero `done:` lines, `setup-rerun/status.before` equal to `setup-rerun/status.after`, and an unchanged `tree.after`.
- **Hooks wired.** Run `vk sh "$RUN" hooks -- git config core.hooksPath`. stdout is `.bigbang/hooks`.
- **Unknown domain.** Run `vk kit "$RUN" bad-domain -- bigbang nope`. Expect exit `1` and `FAIL: bigbang: nope: not a domain. Domains: ...`.

## Gotchas

- Bigbang's final `verify` module checks this checkout's own Kit install in `$RUN/home`. A dirty `skills/kit` makes the exit `1` even when the project setup is perfect. Read the FAIL lines before calling a run red.
- The first run has no commits, so `burndown` reports `base `main` has no commits yet`. That is a report line, not a failure.
- `guardrail` reports `test unset (no manifest found)` on an empty dir, which is expected.
- With a cached catalog the first run takes a few seconds. Without one, the `catalog` module clones every source (minutes, and it needs network).
