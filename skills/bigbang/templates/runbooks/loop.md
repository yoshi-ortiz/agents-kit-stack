# Light loop

One agent, one ticket at a time. `bigbang` is the only judge of state; act on what it prints.

1. **Read.** Run `bigbang`. Done when every setup module prints `ok`. A setup `FAIL` is the work: fix it, then run
   again.
2. **Steer.** Act on what the owner said in chat first: a new `Order:`, a changed or new ticket line in
   `ROADMAP.md`, committed with `Owner-Approved: <owner>`. With the goals layer, an `uncovered: R<n>` line also
   asks for tickets.
3. **Take** the `next:` ticket. Branch from `base` as `<lid>-<slug>`: the id lowercased, non-alphanumerics as `-`
   (`ENG-123` → `eng-123-pdf-opens`). `next: none` → write the push brief and stop.
4. **Skeleton.** Locate every site the ticket touches (tree-sitter MCP when the host has it, else `rg` and the
   source). Write `TODO(<id>)` at each site, and a test named with `_<tid>_` (`test_ENG_123_pdf_opens`) or
   `<id>: ` (`test("ENG-123: pdf opens")`) that walks the ticket's `entry:` and asserts its `visible:` result.
   Done when that test runs red for the reason the ticket names. The skeleton stays uncommitted until step 5.
5. **Burn.** Implement until the `[burndown] select` command for the id exits 0 and `git grep -c 'TODO(<id>)'`
   prints nothing.
6. **Receipt.** Walk the ticket from its `entry:` to its `visible:` result as an end user would, and save
   `receipts/<id>/journey.md` (each step, with the screenshot it produced) and screenshots or a GIF of the
   visible result beside it. Use the host's capture tool (browser, simulator, desktop, terminal render).
   Commit code, test and receipt together with the id first in the subject (`ENG-123: …`); one ticket per
   commit. Without a committed receipt the ticket reads `green`, never `live`.
7. **Prove.** `git checkout <base> && git merge --no-ff <branch>` (the hook runs the gate), then `bigbang`. Done when
   the ticket reads `live`, or `green` with its failing `[evidence]` command named.
8. **Blocked** at any point (a `limit:`, an owner-level operation, a missing permission) → add the ticket and its
   one command to the push brief, return to 3 in the same turn.
9. **Brief.** Screenshot the project as it stands now into `.bigbang/status/`, run `bigbang brief`, and post
   its Markdown with the status screenshot and each new receipt attached. Then return to 1.

Stop on the first of: `next: none`; `[loop] max_steps` tickets taken this run; a plan-limit or rate-limit
message; a cost cap. The last message is the burndown and the push brief.

**Push brief.** Once, at the stop: the `bigbang brief` output with its screenshots, the epic benchmark and its
result, each blocked or parked ticket with its one command, and the push to main as the owner's one command.
