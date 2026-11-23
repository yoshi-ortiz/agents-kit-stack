# Yoshi Stack (`cyber-skills`)

Agent harness core that makes a checkout ready to work across every configured agent while keeping startup context small.

## Product Contract (Non-Negotiables)

1. **Multi-agent parity**: Every agent in `skills/kit/PACK.md` (`# Agents`: `claude-code`, `codex`, `pi`, `cursor`, `zed`, `antigravity`) must receive all first-party core skills (`skills/*`) and catalog access. Never ship a Claude-only fix.
2. **Zero-context catalog**: Catalog skills (`PACK.md # Batteries included`) load on demand. Never preload the full catalog into startup context on hosts that support explicit-only invocation (`disable-model-invocation: true` / `allow_implicit_invocation: false`).
3. **Model-visible harness core**: First-party skills under `skills/` (`kit`, `bigbang`, `determdinistic`, `dev-sync`) MUST remain model-invocable (no `disable-model-invocation: true`, `allow_implicit_invocation: true`) so every agent sees the harness core and can route prose requests through `kit`.
4. **No false-positive verification**: Never claim skills are installed based only on lockfiles or a router stub. Verify each agent's real global skill directory and live prompt behavior.

## Host Discovery & Invocation Matrix

| Agent | Global Skills Dir | Catalog Mechanism | Explicit Invocation |
| --- | --- | --- | --- |
| `claude-code` | `~/.claude/skills/` | `@kit` plugins (`~/.claude/plugins/`) | `/publisher:skill` (`disable-model-invocation: true` → 0 tok) |
| `codex` | `~/.agents/skills/` | `@kit` plugins (`~/.codex/plugins/`); `dedupe_codex()` hides `~/.agents/skills/` stubs | `$publisher:skill` picker (**`$`**, not `/`; `allow_implicit_invocation: false` → 0 tok) |
| `cursor` | `~/.cursor/skills/` | Symlinks to `~/.agents/skills/<publisher>-<skill>` stubs | `/publisher-skill` |
| `pi` | `~/.agents/skills/` | `~/.agents/skills/<publisher>-<skill>` stubs | `/skill:publisher-skill` |
| `zed` | `~/.agents/skills/` | `~/.agents/skills/<publisher>-<skill>` stubs | `/publisher-skill` |
| `antigravity` | `~/.gemini/config/skills/` | Symlinks to `~/.agents/skills/<publisher>-<skill>` stubs | `/publisher-skill` |

## Commands

- **Unit tests**: `python3 -m unittest skills/kit/packages_test.py skills/determdinistic/determdinistic_test.py`
- **Verify (gates + per-agent coverage)**: `python3 skills/kit/packages.py`
- **Local sync (all agents)**: `python3 skills/kit/packages.py dev-sync --local-only`
- **Push + sync (`dev` branch)**: `python3 skills/kit/packages.py dev-sync`
- **Codex startup context probe**: `codex debug prompt-input "hello"`

## Boundaries

- Keep skill `SKILL.md` files short; put repeatable logic in code (`skills/kit/packages.py`, `skills/determdinistic/determdinistic.py`).
- Never force-push.
- When specs and code conflict, surface the conflict explicitly instead of silently picking a side.
- Record product value breaches and their root causes in `INCIDENTS.md`.
- See `GOAL.md` for full scope and `slop` branch history for prior rationale.
