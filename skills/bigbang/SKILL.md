---
name: bigbang
description: Bootstrap a project from a prompt or sketch, untangle a chaotic codebase, burn down its @ROADMAP.md (status, priority, spec change), or audit each vendor's context and token spend.
---

# Bigbang

`B` means `python3 /abs/path/to/skills/kit/packages.py bigbang`, resolving
`../kit/packages.py` from this skill's directory. Run it from the project.

## A new project

- The prompt names a stack (Astro, Godot, a book…): run `B <domain>` with the
  matching `PACK.md # Domains` entry. No entry fits: draft a manifest in
  `skills/kit/domains/` and show it to the owner first.
- Anything else: run `B sketch`, fill `sketch/BRIEF.md` and the prototype from
  the owner's words, and show both. The stack waits for the owner's approval.
- A `FAIL` naming `scaffold-plan.md`: hand that file alone to a goldfish (a
  fresh small-model session); on a host with no session tool, run it yourself.

## A codebase in chaos

The target: every file has one **home**, the place its domain keeps that kind
of code, asset or config, and each module is **deep** (`kit use codebase-design`
gives the vocabulary: module, interface, seam, depth).

1. Run `B <domain>` on the checkout. Existing files stay where they are.
2. Map it: one line per top-level path with its domain, its role and its home.
   Done when every path has a home or is marked homeless, duplicate or shallow.
3. Turn the map into a layout epic in `ROADMAP.md`: one ticket per move or
   deepening, each with `entry:` and `visible:`. Show the map and the epic to
   the owner; the approval is the commit's `Owner-Approved` trailer, and each
   structure decision goes in that commit's body.
4. Burn the epic with `runbooks/loop.md`, one move per ticket, the gate green
   after each. `B` rebuilds the `AGENTS.md` index as homes change.

## Every session

1. Run `B` for real (`--dry-run` only previews). A checkout with no
   `guardrail.toml` names its stack once: `B <domain>`, or `B core` for code
   with no closer domain. Each module prints `ok`, `done:` or `FAIL: … · fix: …`;
   apply each fix and run `B` again. This step stays open until `B` exits 0.
   A traceback with `Operation not permitted` is the host sandbox: rerun `B`
   with the host's permission to leave it (Antigravity: `BypassSandbox`). A
   `FAIL` no fix clears goes to the owner as its exact line.
2. Follow the header of the project's `ROADMAP.md` for status, priority, spec
   and build requests. Building follows `runbooks/loop.md`.

**Evidence** is what `B` prints: ticket states, `shot:` lines (what each vendor
loads before the first prompt) and `tank:` lines (what it spends). A ticket is
`live` only with a committed receipt (`receipts/<id>/`: journey report and
screenshots). End every shot, and answer every status request, with `B brief`
plus a fresh screenshot in `.bigbang/status/`, attached.

**Owner-owned:** `guardrail.toml`, `HALLUCINATIONS.md`, `ROADMAP.md`,
`docs/specs/requirements.md`. Edit them on the owner's chat words, in a commit
with the trailer `Owner-Approved: <owner>` and those words in the body.

## Flags

```
B [domain...] [--compass goals,babysitter,tanks] [--dry-run] [--paid] [--sync] [--only <module>]
```

`core` is always on. `goals` keeps the owner's words (`B goals <file>`);
`babysitter` runs `shot:` prompts (`B ledger …`); `tanks` measures spend, and
`--paid` spends money, so run it when the owner asks. `--dry-run` writes and
spends nothing. When a fix is unclear, read [the spec](../../docs/specs/bigbang.md).
