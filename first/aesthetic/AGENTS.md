# Working on this skill

This is Repo-Dev Context. Do not follow the design run in `SKILL.md`, open the
companion, or treat repository design fixtures as user evidence.

## Enter the development environment

From the repository root, read the work style and inspect the checkout without
changing it.

```bash
git branch --show-current
python3 tools/repo_context.py --json module aesthetic
```

Source work normally happens on `dev`. Do not switch branches on the user's
behalf. Keep the current feature Item separate from a user-selected legacy Item
such as R-50.

## Select one product

Load one development prompt before source files.

| Product | Development prompt |
| --- | --- |
| Design Shot inference | [`docs/development/design-shot-inference.md`](docs/development/design-shot-inference.md) |
| Aesthetic ranking artifact | [`docs/development/ranking-artifact.md`](docs/development/ranking-artifact.md) |

If the request spans both, state the shared contract before loading the second
prompt. A nearby file is not enough reason to widen the change.

## The loop

Work one directory at a time.

```bash
python3 tools/check.py
python3 first/aesthetic/scripts/golden_rules.py --design <spec.json> --min-coverage 0.8
```

`golden_rules` stays separate: it grades one design spec, so it needs a file
argument and has no repository-wide form for the runner to call.

| Step | Answers |
| --- | --- |
| `tools/contracts` | does every directory honour its contract and budget? |
| `unittest` | does the behaviour claimed actually hold? |
| `self-test` | are ledger invariants intact? |
| `golden_rules` | what fraction of decisions are rule-pinned vs improvised? |

## Keep metrics separate

| Metric | Meaning |
| --- | --- |
| Entry cost | Bytes of `SKILL.md`, paid every invocation. |
| Golden-rule coverage | Determinism, not quality. A fully declared wrong design repeats. |
| Ledger coverage | User-set ranks over standing elements. See `references/stats.md`. This does not prove a round improved. |

## Editing the article front end

Load `modern-web-guidance` before changing article CSS or script.

- **Measure the rendered page, never the source.**
- **Controls stylesheet ships after the article's.** Double `.dh-fb` to outrank.
- **Round zone inverts ground.** Build from the row's own ground, never `transparent`.

## Rules

- Red before green. Assert parsed structure, not generated substrings. See `references/verification.md`.
- Before adding SKILL.md prose, ask whether a tool could enforce it.
- This repository copy is canonical. Propagate it with the verified install command after editing.
- Restart the companion after editing `helper.js` or `frame-template.html`.
