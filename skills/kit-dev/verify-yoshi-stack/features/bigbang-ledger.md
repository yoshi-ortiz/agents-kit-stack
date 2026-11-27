# Bigbang ledger

`bigbang ledger` is the one writer of `.bigbang/sessions.jsonl`. It keeps at most one live session per role, so two SWE agents cannot work the same loop at once.

## Sub-features

- `ledger-start` records a live session for a role.
- `ledger-conflict` refuses a second live session in the same role.
- `ledger-end` closes a session with the commit sha it delivered.
- `ledger-park` closes a session without a sha.

## How to get to it (user POV)

- `python3 skills/kit/packages.py bigbang ledger start <role> <name> <session-id>`
- `... bigbang ledger end <name> <sha>` and `... bigbang ledger park <name>`
- The project's `runbooks/loop.md` and `runbooks/babysitter.md` tell agents when to run each one.

## Driving it with vk

Preconditions:

- The `setup` step from [bigbang-setup](./bigbang-setup.md) ran in this `$RUN`.

- **Start.** Run `vk kit "$RUN" ledger-start -- bigbang ledger start swe a sess1`. Expect exit `0` and `ok: ledger: start a`. `.bigbang/sessions.jsonl` gains `{"id": "sess1", "name": "a", "op": "start", "role": "swe", ...}`.
- **Conflict.** Run `vk kit "$RUN" ledger-conflict -- bigbang ledger start swe b sess2`. Expect exit `1` and `FAIL: ledger: a is the live swe · fix: bigbang ledger end a <sha> (or park a) first`.
- **Bad sha.** Run `vk kit "$RUN" ledger-badsha -- bigbang ledger end a deadbeef`. Expect exit `1` and `FAIL: ledger: deadbeef is not a commit here`.
- **End.** Make a commit with `vk sh "$RUN" commit -- git commit --allow-empty -m work`, take its sha from `vk sh "$RUN" sha -- git rev-parse HEAD`, then run `vk kit "$RUN" ledger-end -- bigbang ledger end a <sha>`. Expect exit `0`. Then `ledger-start` with `swe b sess2` succeeds. *(Not yet driven: record the exact output here the first time it runs.)*

## Gotchas

- `.bigbang/sessions.jsonl` is gitignored by `bigbang`, so it never shows up in `status.*`. Read the file itself.
- An entry older than `stale_hours` in `guardrail.toml` no longer blocks. A slow test machine will not hit this, but a run left open overnight will.
