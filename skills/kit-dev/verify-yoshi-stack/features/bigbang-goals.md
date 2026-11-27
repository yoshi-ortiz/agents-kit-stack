# Bigbang goals

`bigbang goals <file>` appends the owner's words to `docs/specs/requirements.md` byte for byte, under the next `R<n>` id with today's date. Recording the same words again appends nothing.

## Sub-features

- `goals-new` records a new file as `R<n> · <date>`.
- `goals-dedupe` reports an identical second call as `already R<n>`.
- `goals-trace` makes `bigbang`'s `goals` module report requirement counts and uncovered ids.

## How to get to it (user POV)

- `python3 skills/kit/packages.py bigbang goals <quote-file>` from the project.
- The `bigbang` skill tells the agent to do this before choosing a stack.

## Driving it with vk

Preconditions:

- The `setup` step from [bigbang-setup](./bigbang-setup.md) ran in this `$RUN`.

- **Write words.** Run `vk sh "$RUN" words -- sh -c 'printf "I want a tiny calculator CLI.\n" > words.txt'`.
- **Goals.** Run `vk kit "$RUN" goals -- bigbang goals words.txt`. Expect exit `0` and `ok: goals: R1 → docs/specs/requirements.md`.
- **Verbatim.** Run `vk sh "$RUN" goals-read -- tail -2 docs/specs/requirements.md`. stdout is `## R1 · <today>` followed by `> I want a tiny calculator CLI.`
- **Dedupe.** Run `vk kit "$RUN" goals-again -- bigbang goals words.txt`. Expect exit `0` and `ok: goals: already R1`. `goals-again/status.before` equals `goals-again/status.after`.
- **Counted.** Run `vk kit "$RUN" goals-audit -- bigbang --only goals`. Expect an `goals: 1 requirement(s)` line.

## Gotchas

- The page quotes each line with `> `. "Verbatim" means the bytes after that prefix.
- Words that differ only in trailing whitespace may count as new words. Use one fixed file.
- `requirements.md` is owner-owned (it has `.claude/settings.json` ask rules). An agent edit made by hand is what the rail is meant to catch. Use only `bigbang goals`.
