# Kit catalog on demand

Catalog skills cost zero startup tokens. A user or agent loads one only when it is needed: `tag` lists what exists, and `use` prints one skill's full `SKILL.md` from the local index.

## Sub-features

- `catalog-tags` lists declared tags with skill counts and domains.
- `catalog-tag-filter` filters catalog skills by one or more tags.
- `catalog-use` prints a skill wrapped in `<skill name=... dir=...>`.
- `catalog-use-miss` makes an unknown name fail.

## How to get to it (user POV)

- `python3 skills/kit/packages.py tag [<tag>...]`
- `python3 skills/kit/packages.py use <skill>` (`kit <skill>` in any agent)

## Driving it with vk

Preconditions:

- `vk doctor "$RUN"` reports `catalog cache present`.

- **Tags.** Run `vk kit "$RUN" tags -- tag`. Expect exit `0`, a first line of `tags (<n>):`, and rows such as `code (<n>)  domains: core`.
- **Use.** Run `vk kit "$RUN" use -- use ponytail`. Expect exit `0` and stdout starting with `<skill name="ponytail" publisher="ponytail" source="DietrichGebert/ponytail" dir="$RUN/home/.cache/kit/...">`, followed by the skill's frontmatter.
- **Miss.** Run `vk kit "$RUN" use-miss -- use no-such-skill-xyz`. Expect a non-zero exit and a `FAIL` line. *(Not yet driven: record the exact output here the first time it runs.)*
- **Zero writes.** For each step, `status.before` equals `status.after`.

## Gotchas

- `dir=` must point into `$RUN/home/.cache/kit`. A path under the real HOME means isolation leaked.
- Skill and tag counts follow `PACK.md`. Assert on presence, not on fixed numbers.
