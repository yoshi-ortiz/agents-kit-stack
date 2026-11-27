# Shots and tanks: context against spend, per vendor

Reached from [bigbang.md](../bigbang.md) build steps 7, 8, 11 and 12. This is the skill's first job (goal 1).

- A **context shot** is what one vendor harness puts in the model's context before the first prompt: system prompt, tool and MCP schemas, the skill listing, memory files (`AGENTS.md`, `CLAUDE.md`, rules). It is paid again, mostly as cache reads, on every turn of every session.
- A **tank** is what that vendor spends to finish real work: tokens and dollars per passing case on the suite below.

`shots` ($0, compass `core`) measures and fixes the shot on every run. `tanks` (compass `tanks`, paid with `--paid`) measures the tank, and the hillclimb keeps a shot fix only when the tank shows it.

## Shots

### Probes

Each vendor's own free dump, never a model call:

| Agent | Probe | Reads | Status |
| --- | --- | --- | --- |
| `claude-code` | `claude -p /context --output-format json --no-session-persistence` | tokens per category: system prompt, system tools, MCP tools, custom agents, memory files, skills | measured (Kit's `verify --strict-context` already parses its skill table) |
| `codex` | `codex debug prompt-input "hello"` | the rendered prompt items: instructions, `AGENTS.md`, skill listing, tools | measured text; tokens `estimated` (bytes ÷ 4) until a tokenizer is pinned |
| `cursor`, `pi`, `zed`, `antigravity` | the files the host loads: its global skill dir (Kit's `agent_global_dir`) and memory files | memory and skills, from file bytes; skills with `disable-model-invocation: true` are assumed unlisted and counted in the label | `estimated`, labelled so on every line; system prompt and tools are unknown, so these shots are lower bounds |

A probe that fails or returns nothing is a `Fail` naming the vendor (no silent zero: AGENTS.md rule 4).

### Shot card and budget

`.bigbang/shots.jsonl` (per checkout, ignored: the shot depends on this machine's global skills and settings) gets one row per run whose shot changed: `{ts, agent, method, total, categories: {name: tokens}, sources: {category: [files or servers]}}`.

```toml
[shots]                    # guardrail.toml
budget = { "claude-code" = 20000, "codex" = 15000 }   # tokens at start; written from the first measurement + 10%
```

Report, one line per agent:

```
shot: claude-code · 18.2k tokens at start (budget 20.0k) · tools 9.1k · mcp 4.0k · memory 2.3k · skills 1.1k
shot: antigravity · ~11.4k estimated · skills 6.8k · memory 2.3k
```

### Leaks and fixes

Probe fails, per agent, on each leak below. `apply` fixes what this project or Kit owns; for global settings the fail prints the command, because those are the owner's.

| Leak | Seen as | Fix |
| --- | --- | --- |
| A catalog skill in the startup listing | a `PACK.md # Batteries included` skill in the skills category | print `kit kit-starter-pack` (explicit-only again; it rewrites global state, so the agent runs it) |
| An MCP server outside the project's domains | a server in `.mcp.json` no selected domain lists | print `claude mcp remove -s project <name>` (the owner may have added it on purpose) |
| A plugin enabled and never used | Kit's `unused_plugins()` | print `kit prune <plugin>` (owner confirms) |
| A tool `PACK.md # Tools` denies, still loaded | a tool name in the tools category | `apply`: `kit tools` |
| Memory files over budget | `memory` above `[shots] memory_budget` (default 3000 tokens) | print the largest file and section; the fix is disclosure (move reference behind a pointer), edited by the owner or on their chat words |
| Total over budget with no leak above | total > `budget` | print the three largest categories; raising `budget` is an owner edit of `guardrail.toml` |

## Shots against tanks

Every paid tank row also records the vendor's shot at run time (`shot` tokens) and its `turns`. The card adds per tank:

- `shot_tokens`: the shot when the run started.
- `shot_share`: `shot_tokens × turns ÷ tokens`, the share of the tank spent re-reading the shot.

```
tank: claude-code · pass 1.0 · 41k tokens/pass ± 3k · $0.82 · shot 18.2k × 4 turns = 64% of spend
```

A shot fix is one hillclimb attempt like any other: change, run `bigbang --compass tanks --paid`, and `TANKS.md` records the verdict. `keep` needs the pass rate to hold and tokens/pass to fall beyond the spread (see "Ledger and hillclimb"); the shot dropping alone is not enough.

# Tanks

A **tank** is one agent's token budget on the case suite, named by its `PACK.md # Agents` name, plus `oracle` ($0, deterministic, the floor that proves the cases and graders work).

## Cases: `tanks/cases.json`

```json
[{"id": "gate-red-test",
  "fixture": "tanks/fixtures/gate-red-test.sh",
  "prompt": "tanks/prompts/gate-red-test.md",
  "grade": "python3 -m pytest -q -k _S1_ && git log -1 --format=%s | grep -q '^S1:'",
  "oracle": "tanks/oracle/gate-red-test.sh"}]
```

| Field | Rule |
| --- | --- |
| `fixture` | a script run in an empty temp dir; builds the throwaway repo |
| `prompt` | the file the tank receives as its prompt |
| `grade` | a command run in the repo after the tank stops; exit 0 = pass. It reads the repo's end state (files, git log, test exit), never the transcript |
| `oracle` | a script run in the repo in place of an agent (the known answer); must pass `grade` |

`apply` writes this sample case (`gate-red-test`: a red tagged test for `ENG-1`) when `tanks/cases.json` is missing. Probe fails when a case lacks a field, a path is missing, or an id repeats. Proposed first suite (open decision 2): rail-check cases, each a seeded state a correct agent turns into a passing `gate` (a red test, a stale branch, an `uncovered:` requirement, a `next:` step to burn).

## Run

Each case × `reps` per tank, each in a fresh temp repo:

- Environment: `PATH`, `HOME`, `LANG`, `TMPDIR` and the tank's own auth only; other variables stay out.
- Permission: the host's restricted headless mode (below), working directory the temp repo.
- Stop on the first of: cumulative `cost_usd` ≥ `max_cost_usd`, or output matching the quota pattern (homelab `run.py:47`). A stop marks the card `partial` and skips the remaining runs.
- Without `--paid`: only `oracle` runs.

## Adapters

Every tank emits one JSON row per run:

```json
{"case": "id", "rep": 0, "tank": "claude-code", "pass": true,
 "input": 0, "output": 0, "cache_read": 0, "cache_write": 0,
 "cost_usd": 0.0, "latency_ms": 0, "turns": 0, "model": "..."}
```

| Tank | Headless call | Usage source | Status |
| --- | --- | --- | --- |
| `oracle` | `sh <oracle>` | zeros | works (homelab `--agent oracle`) |
| `claude-code` | `claude -p --output-format json --permission-mode acceptEdits` | `usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`; `total_cost_usd`; `num_turns`; `modelUsage` | works (homelab `run.py:329`) |
| `codex` | `codex exec --json` (JSONL events) | the event carrying token usage | flags checked 2026-11-27; usage event unverified |
| `cursor` | `cursor-agent -p --output-format json` | to read from the saved fixture | flags checked 2026-11-27; usage unverified |
| `pi` | `pi -p --mode json` | to read from the saved fixture | flags checked 2026-11-27; usage unverified |
| `zed` | none | — | `unmeasured`: no headless agent CLI |
| `antigravity` | none | — | `unmeasured`: no headless CLI (open decision 5) |

Build step 8 saves one real run per unverified tank as `skills/bigbang/fixtures/<tank>.jsonl`; the adapter test parses that fixture. A tank whose output carries no token counts stays `unmeasured` with that reason. Cost: when the host reports no `cost_usd`, the row carries `null` and the cap counts tokens × the price in `guardrail.toml [tanks.price.<tank>]`, or the tank refuses `--paid` until one is set.

## Card: `tanks/card.json`

Rewritten by each run:

```json
{"complete": true, "partial": false,
 "covers": "<sha256>", "harness": "<sha256>", "cases": 4, "reps": 3,
 "unmeasured": {"zed": "no headless agent CLI", "antigravity": "no headless CLI"},
 "tanks": {"claude-code": {"pass_rate": 1.0, "tokens_per_pass": 0, "tokens_per_pass_spread": 0,
                           "cache_read_per_pass": 0, "cost_usd": 0.0,
                           "by_case": {"gate-red-test": {"pass": 3, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0}}}}}
```

- `covers`: sha256 over `git ls-files -s -- <covers…>` output (blob hashes, so only content changes count). `harness`: the same over `tanks/` and `skills/bigbang/tanks.py`.
- `complete` only when every case × rep ran for every tank in `agents`; any subset (`--cases`, a cap, a quota stop) sets `partial: true` (F1).
- `cases` is `len(cases.json)` at run time (F5); tokens stay per case and per tank (F2).
- `tokens` = `input + cache_write + cache_read + output` (open decision 4; v3 code still leaves out `cache_read`); `tokens_per_pass` = total tokens / passes. With zero passes it is `null`.
- `tokens_per_pass_spread` = max − min of the per-rep `tokens_per_pass` (F3).
- Any tank can produce a valid card (F6).

Probe fails: card missing; `partial`; `covers` or `harness` differs from now; a tank in `agents` missing from `tanks` and absent from `unmeasured`. Without `--paid`, `apply` runs the oracle, and the remaining fail names `bigbang core tanks --paid`. `report` prints one line per tank: `tank: claude-code · pass 12/12 · 41k tokens/pass ± 3k · $0.82`.

## Ledger and hillclimb: `TANKS.md`

`tanks` appends one row per paid run, kept and reverted alike (F4):

| Date | Change | Tank | Pass before → after | Tokens/pass before → after (± spread) | Verdict |
| --- | --- | --- | --- | --- | --- |

**Change** is `git log -1 --format='%h %s'` of HEAD; **before** is the previous card on `base`. **Verdict** is computed:

- `keep`: pass rate after ≥ before, and tokens/pass after < before − max(spread before, spread after).
- `revert`: anything else, including a red `test`.

One change per attempt. On `revert` the agent runs `git revert --no-edit HEAD`; the row stays.
