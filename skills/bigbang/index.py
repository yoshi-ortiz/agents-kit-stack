"""index: the context indexing convention. AGENTS.md is the one index every vendor reaches; it points, never holds.

- AGENTS.md carries a managed block between the markers below: one pointer per context file, with when to read it.
  bigbang owns only the text between the markers; the rest of AGENTS.md is the project's.
- A vendor whose host reads another memory file gets that file with an import of AGENTS.md (CLAUDE.md, GEMINI.md).
- Every pointer resolves, and every nested AGENTS.md (a directory's own index) is listed.
"""
import re
from pathlib import Path

from base import Fail, Module, git_out, template, write_new

START, END = "<!-- bigbang:index -->", "<!-- /bigbang:index -->"
INDEX = "AGENTS.md"
IMPORT = "@AGENTS.md"
MEMORY = {"claude-code": "CLAUDE.md", "antigravity": "GEMINI.md"}  # hosts that read a file other than AGENTS.md
POINTERS = [  # (path, when to read it); listed only when the path exists
    ("ROADMAP.md", "start every session here (`@ROADMAP.md`): tickets, order, status"),
    ("guardrail.toml", "project facts: domains, base branch, test command, ticket ids, limits"),
    ("HALLUCINATIONS.md", "before acting on a remembered fact"),
    ("runbooks/loop.md", "when building the next ticket"),
    ("runbooks/babysitter.md", "on a `shot:` prompt"),
    ("sketch/BRIEF.md", "the approved brief and its prototype"),
    ("docs/specs/requirements.md", "the owner's words, verbatim (goals)"),
    ("docs/specs", "specs, one file per topic"),
    ("GLOSSARY.md", "the project's words; use them as written"),
    ("TANKS.md", "token spend verdicts per vendor"),
    ("receipts", "closing receipts per ticket: journey reports and screenshots"),
]


def nested_indexes(root):
    listed = git_out(root, "ls-files", "-co", "--exclude-standard", "--", "*/AGENTS.md")
    return sorted(p for p in listed.splitlines() if p != INDEX)


def entries(root):
    root = Path(root)
    found = [(p, when) for p, when in POINTERS if (root / p).exists()]
    found += [(p, "that directory's own index") for p in nested_indexes(root)]
    return found


def block(root):
    lines = [START, "## Index", "", "Read a file when its line applies; nothing here needs reading up front.", ""]
    lines += [f"- [{p}]({p}) — {when}" for p, when in entries(root)]
    return "\n".join(lines + [END])


def current_block(text):
    m = re.search(re.escape(START) + r".*?" + re.escape(END), text, re.S)
    return m.group(0) if m else None


def with_block(text, new):
    old = current_block(text)
    if old is not None:
        return text.replace(old, new)
    return text + ("" if text.endswith("\n") or not text else "\n") + ("\n" if text else "") + new + "\n"


def imports_index(path):
    path = Path(path)
    if path.is_symlink():
        return path.resolve().name == INDEX
    return path.is_file() and any(line.strip() == IMPORT for line in path.read_text().splitlines())


class Index(Module):
    name = "index"

    def probe(self, ctx):
        root, fails = ctx.root, []
        path = root / INDEX
        if not path.is_file():
            return [Fail(f"{INDEX} missing", "bigbang (writes the index)")]
        text = path.read_text()
        if current_block(text) != block(root):
            fails.append(Fail(f"{INDEX} index block missing or stale", "bigbang (rewrites only the block between its markers)"))
        for target in re.findall(r"\]\(([^)#\s]+)\)", current_block(text) or ""):
            if not (root / target).exists():
                fails.append(Fail(f"{INDEX} points at {target}, which does not exist", "bigbang (rebuilds the block)"))
        for agent, name in MEMORY.items():
            if agent not in ctx.pack.agents:
                continue
            memory = root / name
            if memory.exists() and not imports_index(memory):
                fails.append(Fail(f"{name} does not import {INDEX}; {agent} would miss the index",
                                  f"add a line `{IMPORT}` to {name} (or make it a symlink to {INDEX})"))
            elif not memory.exists():
                fails.append(Fail(f"{name} missing; {agent} reads it instead of {INDEX}", f"bigbang (writes `{IMPORT}`)"))
        return fails

    def apply(self, ctx):
        root, actions = ctx.root, []
        path = root / INDEX
        if not path.is_file():
            actions.append((f"write {INDEX} with the index", lambda: write_new(path, template("AGENTS.md") + "\n" + block(root) + "\n")))
        elif current_block(path.read_text()) != block(root):
            actions.append((f"refresh the index block in {INDEX}", lambda: path.write_text(with_block(path.read_text(), block(root)))))
        for agent, name in MEMORY.items():
            if agent in ctx.pack.agents and not (root / name).exists():
                actions.append((f"write {name} importing {INDEX}", lambda name=name: write_new(root / name, IMPORT + "\n")))
        return actions

    def report(self, ctx):
        found = entries(ctx.root)
        return [f"index: {INDEX} points at {len(found)} file(s); "
                + ", ".join(f"{name} → {INDEX}" for a, name in MEMORY.items() if a in ctx.pack.agents)]
