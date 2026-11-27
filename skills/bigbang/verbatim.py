"""goals: the owner's words as verbatim, dated requirements, and the trace from every ticket back to them."""
import re
import time
from pathlib import Path

from base import (DECISION_PATTERN, REQ_PATTERN, Fail, Module, git_out, load_determdinistic, read_rail, spec_dir,
                  template, write_new)

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOP = re.compile(r"^R(\d+)$")


def page_path(ctx_or_root, rail=None):
    if rail is None:
        return Path(ctx_or_root.root) / spec_dir(ctx_or_root) / "requirements.md"
    spec = rail.get("spec") if isinstance(rail.get("spec"), str) else "docs/specs"
    return Path(ctx_or_root) / spec / "requirements.md"


def quotes(text):
    """{R id: the quoted words} for each `## R<n> · date` block: `> ` lines with the prefix removed."""
    found, current, lines = {}, None, []
    for line in text.splitlines() + ["## end"]:
        if line.startswith("#"):
            if current:
                found[current] = "\n".join(lines).strip("\n")
            m = re.match(r"^##\s+(R\d+)\s+·", line)
            current, lines = (m.group(1) if m else None), []
        elif current is not None and (line == ">" or line.startswith("> ")):
            lines.append(line[2:])
    return found


class Page:
    def __init__(self, text):
        dm = load_determdinistic()
        self.text = text
        self.index = dm.tickets(text, [re.compile(REQ_PATTERN), re.compile(DECISION_PATTERN)], "requirements.md")
        self.blocks = [t for t in self.index["tickets"] if t["kind"] == "heading"]
        self.ids = {t["id"] for t in self.blocks}
        self.quotes = quotes(text)

    def requirements(self):
        return [t["id"] for t in self.blocks if TOP.match(t["id"])]

    def next_id(self):
        numbers = [int(TOP.match(r).group(1)) for r in self.requirements()]
        return f"R{max(numbers, default=0) + 1}"

    def fails(self):
        fails = [Fail(f"requirements.md:{d['line']}: {d['code'].replace('_', ' ')} {d.get('key', '')}".rstrip(),
                      "give each requirement, refinement and decision one block") for d in self.index["diagnostics"]]
        for t in self.blocks:
            where = f"requirements.md:{t['line']}"
            if not t["text"] or not DATE.match(t["text"][0]):
                fails.append(Fail(f"{where}: {t['id']} has no `· YYYY-MM-DD` date", f"write `## {t['id']} · <date>`"))
            if TOP.match(t["id"]) and not self.quotes.get(t["id"]):
                fails.append(Fail(f"{where}: {t['id']} quotes no words", "bigbang goals <file with the owner's words>"))
            if "." in t["id"]:
                parent = t["id"].split(".")[0]
                if t["fields"].get("refines") != parent:
                    fails.append(Fail(f"{where}: {t['id']} must say `refines {parent}`", f"add `· refines {parent}`"))
                if parent not in self.ids:
                    fails.append(Fail(f"{where}: {t['id']} refines unknown {parent}", "refine an existing requirement"))
            if t["id"].startswith("D"):
                req = t["fields"].get("req", "")
                if not req or req not in self.ids:
                    fails.append(Fail(f"{where}: decision {t['id']} needs `req:` naming a known requirement",
                                      f"add `· req: R<n>` to {t['id']}"))
        return fails


def read_page(ctx):
    path = page_path(ctx)
    return Page(path.read_text()) if path.is_file() else None


class Goals(Module):
    name = "goals"

    def probe(self, ctx):
        path = page_path(ctx)
        if not path.is_file():
            return [Fail(f"{path.relative_to(ctx.root)} missing", "bigbang (writes the page header)")]
        page = read_page(ctx)
        fails = page.fails()
        import burndown
        roadmap = burndown.read_roadmap(ctx)
        if roadmap and roadmap.epic:
            for t in roadmap.steps + roadmap.goals:
                cited = [e["to"] for e in roadmap.links if e["from"] == t["id"] and e["field"] == "req"]
                if not cited:
                    fails.append(Fail(f"ROADMAP.md:{t['line']}: {t['id']} has no `req:`",
                                      f"add req: R<n> to {t['id']} in ROADMAP.md"))
                for r in cited:
                    if r not in page.ids:
                        fails.append(Fail(f"ROADMAP.md:{t['line']}: {t['id']} cites unknown {r}",
                                          f"bigbang goals the words behind {r}, or fix the id"))
        return fails

    def apply(self, ctx):
        path = page_path(ctx)
        if path.is_file():
            return []
        return [(f"write {path.relative_to(ctx.root)}", lambda: write_new(path, template("requirements.md")))]

    def report(self, ctx):
        page = read_page(ctx)
        if page is None:
            return []
        reqs = page.requirements()
        refinements = [t["id"] for t in page.blocks if "." in t["id"]]
        decisions = [t["id"] for t in page.blocks if t["id"].startswith("D")]
        lines = [f"goals: {len(reqs)} requirement(s), {len(refinements)} refinement(s), {len(decisions)} decision(s)"]
        if not reqs:
            lines.append("goals: no requirements yet · bigbang goals <file with the owner's words>")
            return lines
        import burndown
        roadmap = burndown.read_roadmap(ctx)
        cited = {e["to"].split(".")[0] for e in (roadmap.links if roadmap else []) if e["field"] == "req"}
        uncovered = [r for r in reqs if r not in cited]
        if uncovered:
            lines.append(f"uncovered: {', '.join(uncovered)}")
        return lines


def goals_main(cwd, args, out=print):
    """`bigbang goals <quote-file>`: append the file's words verbatim as the next requirement."""
    if len(args) != 1:
        out("FAIL: goals: name one file holding the owner's words · fix: bigbang goals <file>")
        return 1
    source = Path(args[0])
    try:
        words = source.read_bytes().decode("utf-8").replace("\r\n", "\n").strip("\n")
    except (OSError, UnicodeError) as error:
        out(f"FAIL: goals: {error} · fix: name a readable UTF-8 file")
        return 1
    if not words.strip():
        out(f"FAIL: goals: {source} is empty · fix: write the owner's words into it")
        return 1
    root = Path(git_out(cwd, "rev-parse", "--show-toplevel") or cwd)
    path = page_path(root, read_rail(root))
    if not path.is_file():
        write_new(path, template("requirements.md"))
    text = path.read_text()
    page = Page(text)
    for rid, quote in page.quotes.items():
        if quote == words:
            out(f"ok: goals: already {rid}")
            return 0
    rid = page.next_id()
    block = f"## {rid} · {time.strftime('%Y-%m-%d')}\n" + "\n".join(f"> {l}" if l else ">" for l in words.split("\n"))
    path.write_text(text + ("" if text.endswith("\n") else "\n") + "\n" + block + "\n")
    out(f"ok: goals: {rid} → {path.relative_to(root)}")
    return 0
