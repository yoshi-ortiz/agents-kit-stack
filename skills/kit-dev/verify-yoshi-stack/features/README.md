# Yoshi Stack verification map

This directory is the maintained source for verifying what a user of this checkout runs: the Kit CLI and its `bigbang` verb. Read the index, then use the matching feature file as the recipe.

## Baseline preconditions

- A fresh run from `vk launch`, with its dir passed as `$RUN`.
- `vk doctor "$RUN"` exits 0.
- `$RUN/proj` is empty unless a recipe says otherwise.
- Never drive the real HOME, or a run this verification did not launch.

## Driving conventions

- Run Kit verbs as `vk kit "$RUN" <label> -- <args>` and other commands as `vk sh "$RUN" <label> -- <cmd>`.
- Give every step its own label. A label is the evidence folder name.
- Assert on line prefixes (`ok:`, `done:`, `would:`, `FAIL:`, `<module>:`) and on exit codes. Paths differ between runs.
- Treat the quoted commands as literal.

## Proof and skip reporting

- CLI proof is `cmd`, `stdout`, `stderr` and `exit` from the evidence folder.
- Write proof is `tree.after` plus the `status.before` and `status.after` diff.
- Install proof is the file or link under `$RUN/home`.
- A `FAIL: verify: uncommitted kit change` line on a dirty checkout counts as an expected FAIL. Report it. Never commit just to clear it.
- Report an unreachable step with its command and the unmet precondition.

## Feature entry contract

Each file has an H1, a one-paragraph description, then `Sub-features`, `How to get to it (user POV)`, `Driving it with vk` (starting with `Preconditions:`), and `Gotchas`.

## Features

- [Bigbang setup](./bigbang-setup.md): first run, dry run and rerun of `bigbang` on an empty dir. **Proved 2026-11-27.**
- [Bigbang goals](./bigbang-goals.md): owner's words recorded verbatim as `R<n>`, with dedupe. Observed by hand, not yet driven through `vk`.
- [Bigbang ledger](./bigbang-ledger.md): one live CTO/SWE per role. `start` and the conflict were observed; `end` with a real sha has not been driven.
- [Kit verify](./kit-verify.md): per-agent coverage gate. Seen inside bigbang's `verify` module, not yet driven standalone.
- [Kit catalog on demand](./kit-catalog.md): `tag` and `use`. Observed by hand, not yet driven through `vk`.
