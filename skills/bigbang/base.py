"""Shared pieces of bigbang modules: Fail, Ctx, Module, and small git and file helpers."""
import functools
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
DETERMDINISTIC = HERE.parent / "determdinistic" / "determdinistic.py"
RAIL = "guardrail.toml"
STATE = ".bigbang"
WORKTREE = f"{STATE}/wt"
TIMEOUT = 1800  # seconds for one project command (tests, evidence, mise)
REQ_PATTERN = r"R[0-9]+(?:\.[0-9]+)?"
DECISION_PATTERN = r"D[0-9]+"
ZERO_SHA = "0" * 40


@dataclass(frozen=True)
class Fail:
    problem: str
    fix: str

    def line(self, module):
        one_line = lambda text: " ⏎ ".join(part.strip() for part in str(text).splitlines() if part.strip())  # noqa: E731
        return f"FAIL: {module}: {one_line(self.problem)} · fix: {one_line(self.fix)}"


Action = tuple[str, Callable[[], None]]  # (what it does, do it); the runner skips the call on --dry-run


@dataclass
class Ctx:
    root: Path
    pack: object
    kit: ModuleType
    domains: list
    items: list
    compass: list = field(default_factory=lambda: ["core"])
    asked_domains: list = field(default_factory=list)   # domains named on this command line
    asked_compass: list | None = None                    # --compass on this command line
    dry: bool = False
    paid: bool = False
    sync: bool = False
    only: str | None = None
    cases: list | None = None
    rail: dict = field(default_factory=dict)
    out: Callable[[str], None] = print

    @property
    def modules(self):
        return {i.name for i in self.items if i.kind == "module"}


class Module:
    name = ""
    stops = False     # a FAIL here ends the run: later modules read what this one makes
    always = False    # selected without a `module:` item
    runs = False      # probe runs project commands: --dry-run prints `would:` instead of probing

    def selected(self, ctx):
        return self.always or self.name in ctx.modules

    def probe(self, ctx) -> list[Fail]:
        return []

    def apply(self, ctx) -> list[Action]:
        return []

    def report(self, ctx) -> list[str]:
        return []


def sh(cmd, cwd, *, shell=False, env=None, input=None, timeout=TIMEOUT):
    """Run a command, capture text output, never raise on exit code or timeout."""
    try:
        return subprocess.run(cmd, cwd=cwd, shell=shell, env=env, input=input, capture_output=True, text=True,
                              timeout=timeout, stdin=None if input is not None else subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"timed out after {timeout}s")
    except FileNotFoundError as error:
        return subprocess.CompletedProcess(cmd, 127, "", str(error))


def git(root, *args, **kw):
    return sh(["git", *args], root, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"), **kw)


def git_ok(root, *args):
    return git(root, *args).returncode == 0


def git_out(root, *args):
    result = git(root, *args)
    return result.stdout.strip() if result.returncode == 0 else ""


def branch_sha(root, branch):
    """The commit a local branch points at, or '' (missing branch, or an unborn one)."""
    return git_out(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}")


def current_branch(root):
    return git_out(root, "symbolic-ref", "--quiet", "--short", "HEAD")


def tail(text, lines=20):
    return "\n".join(text.strip().splitlines()[-lines:])


def read_rail(root):
    """Parsed guardrail.toml, {} when missing, or {'__error__': message} when it is not TOML."""
    path = Path(root) / RAIL
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text())
    except (tomllib.TOMLDecodeError, UnicodeError) as error:
        return {"__error__": str(error)}


def spec_dir(ctx):
    return ctx.rail.get("spec", "docs/specs") if isinstance(ctx.rail.get("spec"), str) else "docs/specs"


def owner_owned(ctx):
    """The paths only the owner moves: gate rule 4 and host `ask` permissions read this one list."""
    return [RAIL, "HALLUCINATIONS.md", "ROADMAP.md", f"{spec_dir(ctx)}/requirements.md"]


def write_new(path, text, mode=None):
    """Create a file that is missing; an existing file is the owner's and stays as it is."""
    path = Path(path)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mode:
        path.chmod(mode)


def template(name):
    return (TEMPLATES / name).read_text()


def ignore_lines(root, lines):
    """Lines missing from .gitignore (state that stays per checkout)."""
    path = Path(root) / ".gitignore"
    have = set(path.read_text().splitlines()) if path.is_file() else set()
    return [line for line in lines if line not in have]


def append_ignore(root, lines):
    path = Path(root) / ".gitignore"
    missing = ignore_lines(root, lines)
    if missing:
        old = path.read_text() if path.is_file() else ""
        path.write_text(old + ("\n" if old and not old.endswith("\n") else "") + "\n".join(missing) + "\n")


def ignore_action(root, lines):
    missing = ignore_lines(root, lines)
    return [(f"add {', '.join(missing)} to .gitignore", lambda: append_ignore(root, missing))] if missing else []


DEPENDENCY_DIRS = ("node_modules", ".venv", "venv")  # installed, ignored, and needed to run the tests


def share_dependencies(root, path):
    """Link the checkout's installed dependency folders into the worktree, so base tests run without a reinstall."""
    for name in DEPENDENCY_DIRS:
        source, target = Path(root) / name, Path(path) / name
        if source.is_dir() and not target.exists() and not target.is_symlink():
            target.symlink_to(source, target_is_directory=True)


def worktree_at(root, sha):
    """A detached worktree of the repository at sha (reused across runs), or an error message."""
    path = Path(root) / WORKTREE
    if (path / ".git").exists():
        result = git(path, "checkout", "--quiet", "--detach", "--force", sha)
        if result.returncode == 0:
            git(path, "clean", "-fdxq")
            share_dependencies(root, path)
            return path, ""
        git(root, "worktree", "remove", "--force", str(path))
    git(root, "worktree", "prune")
    result = git(root, "worktree", "add", "--quiet", "--detach", "--force", str(path), sha)
    if result.returncode:
        return path, tail(result.stderr, 3)
    share_dependencies(root, path)
    return path, ""


@functools.cache
def load_determdinistic():
    """The sibling determdinistic skill's script: the one Markdown and ticket-link parser bigbang uses."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("determdinistic", DETERMDINISTIC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def jsonl(path):
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def id_forms(ticket):
    """{id} as written, {tid} with every non-alphanumeric run as `_`, {lid} that lowercased."""
    tid = re.sub(r"[^A-Za-z0-9]+", "_", ticket).strip("_")
    return {"id": ticket, "tid": tid, "lid": tid.lower()}


def fill(command, ticket):
    forms = id_forms(ticket)
    return command.replace("{id}", forms["id"]).replace("{tid}", forms["tid"]).replace("{lid}", forms["lid"])
