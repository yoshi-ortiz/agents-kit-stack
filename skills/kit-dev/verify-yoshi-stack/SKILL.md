---
name: verify-yoshi-stack
description: Drive this checkout's Kit/bigbang CLI (skills/kit/packages.py) end to end against a throwaway HOME and an empty project, and capture stdout, exit codes and file side effects as proof. Use to prove a change to kit, bigbang, kit-dev:ota-ci or PACK.md works the way a user runs it, without touching the real ~/.claude, ~/.codex or ~/.agents.
---

# Verify Yoshi Stack

The surface is a CLI: `python3 skills/kit/packages.py <verb>` (Kit) and its
`bigbang` verb (skills/bigbang). It writes into `$HOME` (every agent's skill
dir, `~/.claude/settings.json`, `~/.codex/config.toml`, `~/.cache/kit`) and
into the project it runs in. Never drive it against the real HOME to prove
something: `bin/vk` gives each run its own `HOME`, `CODEX_HOME`,
`GIT_CONFIG_GLOBAL` and empty project dir, so runs can go side by side.

`vk` below means `skills/kit-dev/verify-yoshi-stack/bin/vk` from the repo root.
Shell state does not persist between tool calls, so pass the run dir every time.

## Launch

```bash
vk launch          # last stdout line is the run dir; keep it as RUN
```

Ready when it prints `ok: agents: claude-code=4/4 core, ... antigravity=4/4 core, ...`
and the run dir. It runs `dev-sync` and `tools` into the throwaway home, which
links this checkout's core skills and indexes the catalog. The first launch on
a machine clones every catalog repo: about 3.5 min and 430 MB, saved to
`~/.cache/verify-yoshi-stack/kit-cache`. Later launches copy that cache and
take about 15 s. If `PACK.md # Batteries included` changed, delete the
`kit-cache` dir so the next launch clones again.

Needs network on the first launch, plus `python3`, `git` and `npx` (`claude`
and `codex` too, for their agent checks).

## Doctor

```bash
vk doctor "$RUN"   # read-only; exit 0 = worth driving
```

It checks the tools on PATH, the repo branch and sha, that every agent dir's
`kit` resolves to this checkout, that the catalog cache is present, and that
the run home's config never names the real HOME. A `warn: N uncommitted
path(s) under skills/kit` line means every `verify` step (including
bigbang's last module) will FAIL on those paths. That FAIL is the product
working, not a broken harness.

## Drive

```bash
vk kit "$RUN" <label> [--cwd repo|proj] -- <packages.py args...>
vk sh  "$RUN" <label> [--cwd repo|proj] -- <any command>
```

The default cwd is the run's empty project (`$RUN/proj`). Use `--cwd repo` for
verbs that act on this checkout (`dev-sync`). `vk` passes stdout and stderr
through and returns the command's exit code. Recipes are in
[features/README.md](features/README.md). Assert on the `ok:`, `done:`,
`would:` and `FAIL:` line prefixes, not on whole lines (paths differ per run).

## Evidence

Every `kit`/`sh` call writes `~/.cache/verify-yoshi-stack/evidence/<run-id>/<label>/`:
`cmd`, `cwd`, `stdout`, `stderr`, `exit`, `status.before`, `status.after`
(`git status --porcelain` of the project) and `tree.after` (the project's
files). `launch.log` sits beside them. Override the location with `VK_EVIDENCE`.

Proof standards:

- Drive the verbs a user types. Do not import `packages.py` or call module functions.
- Prove side effects alongside output: `tree.after` and `status.*` for project
  writes, and files under `$RUN/home` for agent installs.
- Prove `--dry-run` by observation: an empty `tree.after` and no change between
  `status.before` and `status.after`. Reading the flag name proves nothing.
- Prove idempotence the way the spec defines it: rerun the same label+1 and
  check that no `done:` lines appear and `status.after` matches.

## Cleanup

```bash
vk cleanup "$RUN"  # kills only processes whose command line names $RUN, deletes $RUN
```

The evidence dir is kept. Run cleanup after a failed attempt too. Never
`pkill python3` or `pkill codex`: the user's own agents run under those names.

## Helpers

- `bin/vk`: launch, doctor, kit, sh and cleanup, as shown above. Run `vk` with
  no arguments for usage.
- `features/`: one recipe per user-facing feature. Update it when a verb, flag
  or output prefix changes.
