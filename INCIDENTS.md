# Value Breach Incidents

Record of product value breaches where Kit failed its core promise (skills callable across every configured agent without preloading the catalog), traced to root causes and structural fixes.

## 2026-11-23: Skills invisible or missing across non-Claude agents

### Symptom
- Agents could not discover or invoke the four first-party harness core skills (`kit`, `bigbang`, `determdinistic`, `dev-sync`) or route to catalog skills on demand.
- Even after fixing model visibility on the four core skills, Cursor (`~/.cursor/skills/`) had **0 core skills and 0 catalog skills**, and `verify()` still exited `0` (`ok`).
- The owner had to search GitHub and paste `principle-fix-root-causes` manually into an agent session even though `backnotprop/pstack` was already in `PACK.md`.

### Root Causes
1. **First-party core skills were marked explicit-only**: `skills/{kit,bigbang,determdinistic,dev-sync}/SKILL.md` carried `disable-model-invocation: true` and `agents/openai.yaml` carried `allow_implicit_invocation: false`. This hid the harness core—including the `kit` on-demand router—from every agent's system prompt, making skills completely unreachable in Antigravity and invisible to prose requests in Claude Code, Codex, Cursor, Zed, and Pi.
2. **False assumption that `~/.agents/skills` is universal globally**: `packages.py` treated `~/.agents/skills` as the global directory for every agent except Claude Code. In reality, three configured agents use separate global skill directories:
   - Claude Code: `~/.claude/skills` (plus `@kit` plugins)
   - Cursor: `~/.cursor/skills`
   - Antigravity: `~/.gemini/config/skills`
   Because `dev_sync()` and `portable()` did not target `~/.cursor/skills` or `~/.gemini/config/skills`, Cursor received nothing and Antigravity accumulated 338 dangling symlinks.
3. **No always-on per-agent verification signal**: `packages.py verify` only inspected `skills-lock.json` and `~/.agents/.skill-lock.json`. It never verified that every agent declared in `PACK.md # Agents` actually had the core skills and catalog aliases/plugins present and valid, allowing silent drift to pass as `ok`.

### Structural Fixes
1. **Model-invocable gate on first-party skills**: Removed `disable-model-invocation: true` and set `allow_implicit_invocation: true` on all repository skills; `repository_skills()` now fails hard if any first-party skill hides itself from models.
2. **Unified multi-agent sync**: `dev_sync()` links every repository skill into `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills`, and `~/.gemini/config/skills` and prunes broken symlinks in all of them. `portable()` symlinks every catalog alias into `~/.cursor/skills` alongside `~/.agents/skills`.
3. **Always-on per-agent coverage gate in `verify()`**: `agent_coverage()` verifies every agent in `PACK.md # Agents` for both core skills and catalog coverage, failing `verify()` if any agent is missing skills and printing a per-agent status summary on every run.
