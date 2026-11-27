# Kit verify

`packages.py` with no verb is the hard gate. It checks that every agent in `PACK.md # Agents` has all core skills and catalog access in its real global skill dir. It installs nothing.

## Sub-features

- `verify-coverage` prints one coverage line per agent (`claude-code`, `codex`, `pi`, `cursor`, `zed`, `antigravity`).
- `verify-missing` makes an empty agent dir FAIL with the fix command.
- `verify-dirty` makes uncommitted kit sources FAIL.
- `verify-context` (`verify --strict-context`) probes live Claude and Codex startup context.

## How to get to it (user POV)

- `python3 skills/kit/packages.py` from any git project.
- `python3 skills/kit/packages.py verify --strict-context` before a release.

## Driving it with vk

Preconditions:

- `vk doctor "$RUN"` exits 0. The `.claude/skills/kit` line and the other three agent-dir lines resolve to this checkout.

- **Coverage.** Run `vk kit "$RUN" verify -- `. stdout includes `ok: agents: claude-code=4/4 core, 17/17 plugins; codex=4/4 core, ...; antigravity=4/4 core, 249/249 aliases` (the counts follow `PACK.md`). The exit is `0` on a clean checkout and `1` on a dirty one, with only `uncommitted kit change` problems.
- **Missing agent.** Remove one agent's link with `vk sh "$RUN" break -- rm "$RUN/home/.cursor/skills/kit"`, then run `vk kit "$RUN" verify-broken -- `. Expect exit `1` and `cursor: missing core skill(s) in .../.cursor/skills: kit`.
- **Repair.** Run `vk kit "$RUN" resync --cwd repo -- dev-sync` and then `vk kit "$RUN" verify-again -- `. The cursor line is back to `4/4 core`.

*(Not yet driven standalone: record the exact output here the first time it runs.)*

## Gotchas

- An empty arg list after `--` is valid, and runs bare verify.
- `verify --strict-context` starts real `claude` and `codex` sessions under the throwaway HOME. They are unauthenticated there, so expect it to fail or skip. Run it on the real machine only when the user asks.
- Lockfiles and router stubs carry zero weight (AGENTS.md rule 4). Prove coverage from the agent dirs under `$RUN/home`, never from `skills-lock.json`.
