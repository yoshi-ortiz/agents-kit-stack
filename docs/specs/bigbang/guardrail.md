# `guardrail` and `gate`

Reached from [bigbang.md](../bigbang.md) build step 3.

## `guardrail`: files it creates

Templates live in `skills/bigbang/templates/`. `apply` copies each missing one; existing files are the owner's.

### `guardrail.toml`

The one source of project facts the other modules read. Full schema, with template defaults:

```toml
base = "dev"                       # str, an existing local branch; every change must hold it
test = "pytest"                    # str, a shell command; exit code is the verdict
spec = "docs/specs"                # str, a directory; holds requirements.md (goals.md)

[limits]                           # name = path or glob; a change touching one fails the gate
# hardware = "contracts/hardware.toml"

[ids]                              # burndown.md "Ticket ids"
pattern = "[A-Z][A-Z0-9]*-[0-9]+"  # regex a ticket id fully matches; default: Linear-style ENG-123
# url = "https://linear.app/<workspace>/issue/{id}"   # optional; report lines print links
# export = "scripts/push-states.sh"                    # optional; runs only with --sync

[burndown]                         # burndown.md
select = "pytest -q -k '_{tid}_'"  # str containing {id}, {tid} or {lid}
tests = ["tests/**", "**/*_test.*", "**/test_*.*"]   # globs searched for step tags

[evidence]                         # ticket id = command; exit code is the verdict
# "ENG-101" = "scripts/journey.sh ENG-101"

[loop]                             # loop.md
max_steps = 5                      # int >= 1
stale_hours = 3                    # number > 0

[tanks]                            # tanks.md
agents = ["claude-code", "codex"]  # names from PACK.md # Agents
reps = 3                           # int >= 2 (a spread needs two)
max_cost_usd = 5.0                 # number > 0
covers = ["skills/", "AGENTS.md"]  # paths whose content hash a card must match

[tanks.price.codex]                # optional, per tank that reports no cost: USD per million tokens
# input = 0.0
# output = 0.0
```

`apply` fills `base` with the current branch when `dev` is absent, and `test` and `[burndown] select` from the first manifest found:

| Manifest | `test` | `select` |
| --- | --- | --- |
| `package.json` | `npm test` | `npm test -- -t '^{id}: '` |
| `Cargo.toml` | `cargo test` | `cargo test _{lid}_` |
| `go.mod` | `go test ./...` | `go test ./... -run '_{tid}_'` |
| `pyproject.toml`, `pytest.ini`, `setup.py` | `pytest` | `pytest -q -k '_{tid}_'` |
| `*.sln`, `*.csproj` | `dotnet test` | `dotnet test --filter 'Name~_{tid}_'` |

The placeholders and the `_…_` delimiters are defined once in [burndown.md](burndown.md) "Ticket ids". No manifest → the file is written with `test = ""` and probe fails `set test in guardrail.toml`.

Probe: every key's type and constraint above; `base` exists (`git rev-parse --verify refs/heads/<base>`); `spec` is a directory; `[tanks] agents` names `PACK.md` agents; `[ids] pattern` compiles and matches no requirement id (`R1`, `R1.1`, `D1`); unknown top-level keys or tables fail (typos must surface). Each `Fail` names the key, the found value and the expected form.

### `HALLUCINATIONS.md`

A claim → owning-source table. Before acting on a remembered fact, the agent checks it against the owner listed here. Template: the header, one sentence of purpose, and this table seeded with the project's own owners:

| Claim about | Owner |
| --- | --- |
| project facts (base, test, limits) | `guardrail.toml` |
| the owner's requirements | `<spec>/requirements.md` |
| step state | `bigbang` output (`burndown:` lines) |
| token cost | `tanks/card.json` |

### Owner-owned paths

`guardrail.toml`, `HALLUCINATIONS.md`, `ROADMAP.md`, `<spec>/requirements.md`. One list, defined once in `modules.py` as `OWNER_OWNED`, read by gate rule 4 and by the `apply` step that writes host permissions:

- Claude Code: `permissions.ask` entries `Edit(<path>)` and `Write(<path>)` in the project's `.claude/settings.json`.
- Codex, Cursor, Pi, Zed, Antigravity: each host's project-level equivalent where one exists; where none exists, `ok: guardrail` carries `ask: unenforced on <agent>` so the gap is visible. Build step 3 records which hosts have one, from each host's docs.

### Hooks

Git runs no hook on a fast-forward merge, so the gate is held at two points:

- `pre-merge-commit`: merges with a commit into `base`.
- `pre-push`: any push whose remote ref is `refs/heads/<base>`.

Each hook runs `python3 <absolute path to packages.py> bigbang --only gate` and exits with its code. `apply` writes them to `.bigbang/hooks/` (versioned) and runs `git config core.hooksPath .bigbang/hooks`. Probe: `git config core.hooksPath` equals `.bigbang/hooks` and both files are executable. An existing `core.hooksPath` pointing elsewhere (husky, lefthook) → `Fail` naming it, with the fix: add the two lines to that tool's hooks.

The light loop merges locally (`git merge --no-ff`), so `pre-merge-commit` always runs there.

## `gate`: the evidence gate

`stops = False`. On the current branch, one `Fail` per rule broken:

1. **Red.** `test` exits non-zero. Fix: the failing output's last 20 lines.
2. **Stale.** `git merge-base --is-ancestor <base> HEAD` fails. Fix: `git merge <base>`.
3. **Limit.** `git diff --name-only <base>...HEAD` matches a `[limits]` path. Fix: the owner changes the limit, or the change moves off it.
4. **Self-edit.** A commit in `<base>..HEAD` touches an owner-owned path and its message lacks an `Owner-Approved: <name>` trailer (`git interpret-trailers --parse`). Fix: the owner amends or approves.
5. **Card.** `tanks` is selected and `tanks/card.json`'s `covers` differs from the current hash. Fix: `bigbang core tanks` (oracle) or `--paid`.

On `base` itself (no branch), rules 2–4 have no range and pass; rules 1 and 5 still run.
