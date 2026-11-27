# Value Breach Incidents

Record of product value breaches where Kit failed its core promise (skills callable across every configured agent without preloading the catalog), traced to root causes and structural fixes.

## 2026-11-27: Bigbang crashed in Antigravity and the agent reported it done

### Symptom
- In a running Antigravity session on the piano checkout, `/bigbang rust design shots and qa` produced a good QA reply but bigbang fixed nothing: no guardrail, roadmap burndown, receipts or brief.
- The transcript shows the agent ran `python3 ~/.gemini/config/skills/kit/packages.py bigbang --dry-run`, got exit 1 with `PermissionError: Operation not permitted: …/cyber-skills/skills/bigbang/modules.py`, read it as a Metal sandbox error, and marked its "run bigbang check" step done.

### Root Causes
1. `packages.py`'s `bigbang()` (and `base.HERE`, `tokens.HERE`, `modules.py`'s import path) used `Path(__file__).resolve()`, which follows the skill link from `~/.gemini/config/skills/` to the repo. Antigravity's sandbox loaded `packages.py` through the link path but denied the resolved repo path.
2. The skill had no hard completion criterion for `B`: a non-zero exit or a traceback could be skipped, and nothing said what a sandbox denial means or how to leave the sandbox.
3. The skill had no route for an existing checkout without `guardrail.toml`: the agent ran `B` with no domain and only `--dry-run`, which previews and never applies.
4. Multi-agent verification covered skill presence and startup context, never a run of `B` inside a vendor's sandbox. The breach reached the owner first.

### Structural Fixes
1. Bigbang loads its modules through the link path (`Path(__file__).absolute()`), never the resolved target. Unverified inside Antigravity: a local `sandbox-exec` emulation does not reproduce its rules.
2. `SKILL.md` step 1: run `B` for real; the step stays open until `B` exits 0; `Operation not permitted` means rerun with the host's permission (Antigravity: `BypassSandbox`); an unfixable `FAIL` goes to the owner as its exact line.
3. `SKILL.md` step 1: a checkout with no `guardrail.toml` names its stack once, `B <domain>` or `B core`.
4. Open: a per-vendor sandbox run of `B` (at least Antigravity) belongs in `kit-dev:verify-yoshi-stack` before the next release.

## 2026-11-25: Placeholder descriptions and a false zero-context failure

### Symptom
- Non-Codex skill pickers displayed “Open the Kit skill…” instead of the skill's purpose and invocation conditions.
- The release gate failed for all 17 Kit publishers even though catalog skills were explicit-only.

### Root Causes
1. `portable()` generated generic descriptions for every alias instead of preserving the published skill description. Coverage checked file presence and invocation policy, allowing unusable picker descriptions to pass.
2. `claude_projection()` treated `claude plugin details` inventory estimates as live context measurements. A fresh `claude -p /context` listed the core skills and no Kit catalog skills, while plugin details estimated a cost for every explicit-only skill.
3. The description reader included unrelated indented metadata after block descriptions, making it unsafe to reuse those descriptions without correcting the parser.

### Structural Fixes
1. Portable aliases preserve published descriptions, including quoted and folded descriptions. Per-agent coverage rejects description drift, as well as missing files and invocation policy drift.
2. `verify --strict-context` probes fresh Claude and Codex skill lists, requiring every first-party core skill and rejecting any loaded catalog skill. Unreadable probe output fails verification. `--strict-projection` uses the same live check for compatibility; the zero-context requirement remains enforced.
3. Regression tests cover description preservation and drift, actual catalog leaks, missing core skills, and malformed context reports. The cheap release signal now reports the live core and catalog counts per host.

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
