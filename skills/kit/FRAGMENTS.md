# Kit is the big bang

I think it should be activated with setup or bigbang, just add them and long term implement.

---

The project's MCP servers should switch on when the project is set up, not when someone remembers to type `kit domain core`. Setup is the moment, and kit already knows what goes in.

---

Leading word candidate: **big bang**. One command, run once per checkout, and everything the agent needs is there: tools pinned, MCP servers declared, hooks installed, skills indexed at zero context. Nothing after it gets bolted on by hand.

---

The owner's layering, verbatim from the handoff:
- big-bang = manifest and agent contract (stage 0)
- kit = skill installs at zero context
- build = order
- `check/tokens-qa` = token evidence per shot

---

The first and most critical tool for story coding is tree-sitter. The skeleton goes where the syntax tree says the story lands, not where grep guessed.

---

Today it takes three steps that don't know about each other: `mise run stage0`, `kit kit-starter-pack`, `kit domain core`. Stage 0 only *checks* that tree-sitter is in `.mcp.json`; kit is what *puts* it there. The check and the writer live in different repos.

---

Foreign is a verdict, not a fact. `rex` wasn't foreign; it was app-owned and nobody had said so. `bootstrap` and `ffmpeg` weren't foreign; they were uncatalogued. "Just add them" is the fix: the catalog is the allow-list, so the answer to a foreign entry is almost always a catalog row, not a delete.

---

Zero tolerance cuts both ways. Kit refuses an unknown skill, and it must refuse to bulk-disable a known one. `prune` turned off every unused plugin at once; now it lists them and only touches the ones the owner names.

---

Half-thought: should stage 0 *call* kit (`kit domain core` as a stage-0 step) so the big bang is one command? Or should kit own stage 0 entirely and `.mise.toml` just say `run = "kit bigbang"`? The second keeps the convention standard (mise task) while kit does the work.

---

Pins drift into fiction. Three versions in `.mise.toml` (packer 1.14.4, tflint 0.59.4, kubeconform 0.7.2) were never released. A big bang that has never run is a list of wishes. Setup has to execute, every time, or the pins rot.

---

After indexing, `verify` hinted that the plugins it had just added were "never used": digital-samba, mindrally. Of course they're unused; they're a minute old. "Unused" needs an age.

---

Kit is supposed to be a directory to run skills on demand! Having them callable on agents but not loading them on window if never invoked.

---

**On demand** is the contract: callable everywhere, zero bytes in the window until invoked. A catalog skill installed model-visible in a project (`bootstrap`, `ffmpeg` in `.agents/skills`) breaks it twice: its description loads every session, and it duplicates the explicit-only copy kit already publishes. Verify now fails on that, and the fix is `remove`, not a stamp.
