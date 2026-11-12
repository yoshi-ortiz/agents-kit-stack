---
name: kit-shot
description: Build one feature as a shot: spec and ADR gate, dev.<feature>.model and dev.<feature>.ui branches, TODO skeleton first, one story per loop, QA against the stories. Use when asked to build, implement or ship a feature.
---

# Shot

A shot is one feature, built in this order. Do not skip a step or reorder it.

1. **Spec gate.** Find the feature's spec (`**/work/<feature>/spec.md` or the repo's spec folder). It must list numbered stories `S1`, `S2`… with acceptance checks. If it is missing or has no stories, write it and stop for the owner's approval. A change to architecture needs an ADR first, accepted by the owner.
2. **Base check.** Before branching, list branches with commits the base branch lacks: `git for-each-ref --format='%(refname:short)' refs/heads refs/remotes | while read b; do n=$(git rev-list --count dev..$b); [ "$n" -gt 0 ] && echo "$n $b"; done`. If one carries this feature's earlier work, merge it first or ask. Never rebuild what a branch already has.
3. **Branches.** Backend and interfaces go on `dev.<feature>.model`, UI on `dev.<feature>.ui`, both cut from `dev`. Never commit a feature to `dev`, `main` or another feature's branch. One branch per side, one commit per story.
4. **Skeleton first.** Before any implementation, commit a skeleton: one `TODO(<feature>:S<n>)` per story at the place it will live, and one failing or skipped test named after each story. The skeleton commit is the plan.
5. **Loop.** Take the lowest open story. Make its test pass with the smallest change, remove its TODO, commit as `<feature> S<n>: <story title>`. Repeat. A story that needs a design change goes back to step 1.
6. **QA.** The shot is done only when every story has a passing test and no `TODO(<feature>:` remains: `git grep -n "TODO(<feature>:"` prints nothing. Report each story with its test and evidence. Say plainly which stories are not done.
7. **Merge.** Merge `dev.<feature>.model`, then `dev.<feature>.ui`, into `dev` through the repo's gate. Never force-push, never merge unfinished stories.
