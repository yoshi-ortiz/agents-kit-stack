"""bigbang modules against throwaway repositories. Acceptance numbers refer to docs/specs/bigbang.md."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import chdir
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "kit"))
import packages as K  # noqa: E402
import modules as M  # noqa: E402
import loop as L  # noqa: E402
import tokens as T  # noqa: E402
import shots as S  # noqa: E402
import scaffold as F  # noqa: E402
import index as I  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
PY_TEST = "python3 -m unittest -q"
PY_SELECT = "python3 -m unittest -q -k _{tid}_"


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def fake_kit(root):
    index = Path(root) / "index.json"
    index.write_text("{}")
    return SimpleNamespace(INDEX=index, Item=K.Item, BIGBANG_MODULES=K.BIGBANG_MODULES, CACHE=Path(root) / "cache",
                           main=lambda argv: 0, domain=lambda *a, **k: 0, mcp_starts=lambda *a, **k: "",
                           verify=lambda pack: print("ok: agents: all six"))


CORE = ("guardrail", "gate", "burndown", "loop", "index", "shots")


def pack(core=CORE, domains=("web", "notes", "sketch", "astro", "book")):
    compass = {"core": [K.Item("module", m) for m in core], "goals": [K.Item("module", "goals")],
               "babysitter": [K.Item("module", "babysitter")], "tanks": [K.Item("module", "tanks")]}
    return SimpleNamespace(domains={d: [] for d in domains}, items={d: [] for d in domains}, compass=compass, mcp={},
                           agents=["claude-code", "codex", "pi", "cursor", "zed", "antigravity"])


def fake_shot(total=1000, memory=200, skills=("bigbang",)):
    return {"method": "measured", "total": total, "categories": {"System prompt": total - memory, "Memory files": memory},
            "model": "m", "window": 200000, "skills": list(skills), "mcp": []}


class Repo(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, GIT_ENV)
        self.env.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.root = self.home / "project"
        self.root.mkdir()
        self.kit = fake_kit(self.home)
        self.pack = pack()
        self.shot = fake_shot()
        self.patches = [mock.patch.object(S, "PROBES", {a: (lambda root, a=a: self.shot) for a in self.pack.agents}),
                        mock.patch.object(S, "vendors", lambda: {"max_age_days": 7})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def bigbang(self, *argv, pack=None):
        lines = []
        with chdir(self.root):
            code = M.main(self.kit, pack or self.pack, list(argv), out=lines.append)
        return code, lines

    def git(self, *args):
        result = sh(["git", *args], self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message, *trailers):
        self.git("add", "-A")
        args = ["commit", "-qm", message]
        for t in trailers:
            args += ["--trailer", t]
        self.git(*args)

    def python_project(self, *flags):
        """A ready project on base `main`: guardrail filled in, a passing test, one owner-approved commit."""
        self.git("init", "-q", "-b", "main")
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.write("calc.py", "def add(a, b):\n    return a + b\n")
        self.write("test_calc.py", "import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
                                   "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n")
        code, lines = self.bigbang("web", *flags)
        rail = (self.root / "guardrail.toml").read_text()
        rail = rail.replace('test = "pytest"', f'test = "{PY_TEST}"').replace(
            "select = \"pytest -q -k '_{tid}_'\"", f'select = "{PY_SELECT}"')
        self.write("guardrail.toml", rail)
        self.commit("bootstrap", "Owner-Approved: owner")
        return code, lines


class SetupTests(Repo):
    def test_fresh_empty_dir_passes_and_second_run_writes_nothing(self):  # acceptance 1
        code, lines = self.bigbang("web")
        self.assertEqual(code, 0, lines)
        before = self.git("status", "--porcelain", "-uall")
        code, lines = self.bigbang()
        self.assertEqual(code, 0, lines)
        self.assertFalse([l for l in lines if l.startswith(("done:", "FAIL:"))], lines)
        self.assertEqual(self.git("status", "--porcelain", "-uall"), before)

    def test_dry_run_writes_nothing(self):  # acceptance 6
        for flags in ([], ["--paid"], ["--paid", "--sync"]):
            code, lines = self.bigbang("web", "--dry-run", "--compass", "tanks", *flags)
            self.assertEqual(list(self.root.iterdir()), [], lines)
            self.assertTrue(any(l.startswith("would: git") for l in lines))

    def test_every_fail_names_a_fix(self):
        code, lines = self.bigbang("--only", "nope")
        self.assertEqual(code, 1)
        self.assertTrue(all(" · fix: " in l for l in lines if l.startswith("FAIL:")), lines)

    def test_module_lists_agree(self):
        self.assertEqual(M.check_names(K), [])

    def test_schema_violation_names_key_and_leaves_file(self):  # acceptance 2
        self.python_project()
        path = self.root / "guardrail.toml"
        bad = path.read_text().replace("reps = 3", 'reps = "three"')
        path.write_text(bad)
        code, lines = self.bigbang()
        self.assertEqual(code, 1)
        self.assertTrue(any("`tanks.reps` is 'three', expected an integer" in l for l in lines), lines)
        self.assertEqual(path.read_text(), bad)
        path.write_text(bad.replace('reps = "three"', "reps = 5"))
        code, lines = self.bigbang()
        self.assertIn("ok: guardrail", lines)

    def test_ids_pattern_must_not_swallow_requirement_ids(self):
        self.python_project()
        path = self.root / "guardrail.toml"
        path.write_text(path.read_text().replace('pattern = "[A-Z][A-Z0-9]*-[0-9]+"', 'pattern = "[A-Z][0-9.]+"'))
        code, lines = self.bigbang()
        self.assertTrue(any("matches requirement ids R1" in l for l in lines), lines)


class GateTests(Repo):
    def setUp(self):
        super().setUp()
        self.python_project()

    def gate_fails(self):
        code, lines = self.bigbang("--only", "gate")
        return [l for l in lines if l.startswith("FAIL: gate")]

    def test_green_branch_passes(self):
        self.git("checkout", "-qb", "eng-1")
        self.write("notes.md", "x\n")
        self.commit("ENG-1: notes")
        self.assertEqual(self.gate_fails(), [])

    def test_each_rule_fails_alone(self):  # acceptance 3
        self.git("checkout", "-qb", "red")
        self.write("calc.py", "def add(a, b):\n    return a - b\n")
        self.commit("red")
        self.assertTrue(any("red:" in f for f in self.gate_fails()))

        self.git("checkout", "-q", "main")
        self.git("checkout", "-qb", "stale")
        self.git("checkout", "-q", "main")
        self.write("other.md", "y\n")
        self.commit("main moves")
        self.git("checkout", "-q", "stale")
        self.assertTrue(any("stale:" in f for f in self.gate_fails()))

        self.git("checkout", "-q", "main")
        rail = self.root / "guardrail.toml"
        rail.write_text(rail.read_text().replace("# hardware = ", 'hardware = "contracts/"\n# x = '))
        self.commit("limits", "Owner-Approved: owner")
        self.git("checkout", "-qb", "limit")
        self.write("contracts/hardware.toml", "gpu = 1\n")
        self.commit("touch hardware")
        self.assertTrue(any("limit `hardware` touched" in f for f in self.gate_fails()))

        self.git("checkout", "-q", "main")
        self.git("checkout", "-qb", "self-edit")
        self.write("ROADMAP.md", (self.root / "ROADMAP.md").read_text() + "\n<!-- moved the goalposts -->\n")
        self.commit("edit roadmap")
        fails = self.gate_fails()
        self.assertTrue(any("self-edit" in f for f in fails), fails)
        self.git("commit", "-q", "--amend", "--no-edit", "--trailer", "Owner-Approved: owner")
        self.assertEqual(self.gate_fails(), [])

    def test_hook_refuses_a_red_merge(self):  # acceptance 12
        hook = self.root / ".bigbang/hooks/pre-merge-commit"
        self.assertTrue(os.access(hook, os.X_OK))
        self.git("checkout", "-qb", "red")
        self.write("calc.py", "def add(a, b):\n    return a - b\n")
        self.commit("red")
        self.git("checkout", "-q", "main")
        env = dict(os.environ, BIGBANG_KIT=str(HERE.parent / "kit" / "packages.py"))
        refused = sh(["git", "merge", "--no-ff", "-q", "-m", "merge red", "red"], self.root, env=env)
        self.assertNotEqual(refused.returncode, 0, refused.stdout)
        self.assertIn("red:", refused.stdout + refused.stderr)
        sh(["git", "merge", "--abort"], self.root)
        self.git("checkout", "-q", "red")
        self.write("calc.py", "def add(a, b):\n    return a + b\n")
        self.commit("green again")
        self.git("checkout", "-q", "main")
        merged = sh(["git", "merge", "--no-ff", "-q", "-m", "merge red", "red"], self.root, env=env)
        self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)


ROADMAP = """# Roadmap

## Epic: ENG-100 · Calculator · benchmark: every ticket live
Order: ENG-102, ENG-101
- ENG-101 · req: R1 · entry: `add(2, 3)` · visible: 5
- ENG-102 · req: R1, R2 · entry: `sub(5, 3)` · visible: 2 · Status: live
- ENG-103 · req: R2 · entry: `mul(2, 3)` · visible: 6 · parked: needs the owner's call

## Goals
- ENG-110 · req: R1 · benchmark: add and sub live · steps: ENG-101, ENG-102
"""


class TicketTests(Repo):
    def setUp(self):
        super().setUp()
        self.python_project()
        words = self.home / "words.txt"
        words.write_text("add numbers\nand subtract them\n")
        with chdir(self.root):
            self.assertEqual(M.main(self.kit, self.pack, ["goals", str(words)], out=lambda _: None), 0)
            words.write_text("multiply too\n")
            M.main(self.kit, self.pack, ["goals", str(words)], out=lambda _: None)
        self.write("ROADMAP.md", ROADMAP)
        self.write("test_tickets.py", "import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
                                      "    def test_ENG_101_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n"
                                      "    def test_ENG_102_sub(self):\n        from calc import sub\n"
                                      "        self.assertEqual(sub(5, 3), 2)\n")
        self.write("calc.py", "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a + b\n")
        self.write("receipts/ENG-101/journey.md", "1. `add(2, 3)` → 5 ![result](result.png)\n")
        self.write("receipts/ENG-101/result.png", "png")
        self.commit("roadmap", "Owner-Approved: owner")

    def burndown(self):
        code, lines = self.bigbang("--only", "burndown")
        return [l for l in lines if l.startswith(("burndown:", "next:", "| ENG", "held:", "FAIL"))]

    def test_states_come_from_tests_on_base_not_status_lines(self):  # acceptance 8, 17
        lines = self.burndown()
        self.assertIn("burndown: Epic ENG-100 · live 1/3, green 0, red 1, open 0, blocked 0, parked 1", lines)
        self.assertIn("| ENG-102 | red | first seen |", lines)
        self.assertTrue(any(l.startswith("next: ENG-102 · red") for l in lines), lines)

    def test_live_needs_a_committed_receipt(self):
        self.git("rm", "-rq", "receipts")
        self.commit("drop the receipt")
        lines = self.burndown()
        self.assertIn("| ENG-101 | green | first seen |", lines)
        row = json.loads((self.root / ".bigbang/burndown.jsonl").read_text().splitlines()[-1])
        self.assertEqual(row["why"], {"ENG-101": "no receipt in receipts/ENG-101/"})
        self.write("receipts/ENG-101/journey.md", "uncommitted\n")
        lines = self.burndown()
        self.assertTrue(any("live 0/3" in l for l in lines), lines)

    def test_brief_links_receipts_and_status_shots(self):
        self.burndown()
        self.write(".bigbang/status/now.png", "png")
        lines = []
        with chdir(self.root):
            code = M.main(self.kit, self.pack, ["brief"], out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(code, 0, text)
        self.assertIn("# Shot brief · Epic ENG-100", text)
        self.assertIn("| ENG-101 | live | [journey](receipts/ENG-101/journey.md) · ![result](receipts/ENG-101/result.png) |", text)
        self.assertIn("| ENG-102 | red | — |", text)
        self.assertIn("![status](", text)
        self.assertIn("next: ENG-102", text)
        self.assertEqual((self.root / ".bigbang/brief.md").read_text().rstrip("\n"), text)

    def test_same_base_sha_appends_one_row(self):  # acceptance 9
        first = self.burndown()
        second = self.burndown()
        rows = (self.root / ".bigbang/burndown.jsonl").read_text().splitlines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(first, second)

    def test_red_gate_still_prints_burndown(self):  # acceptance 15
        self.git("checkout", "-qb", "eng-102-sub")
        self.write("calc.py", "def add(a, b):\n    return a - b\n")
        self.commit("ENG-102: wip")
        code, lines = self.bigbang()
        self.assertEqual(code, 1)
        self.assertTrue(any(l.startswith("FAIL: gate: red") for l in lines))
        self.assertTrue(any(l.startswith("next: ENG-102") for l in lines), lines)

    def test_any_id_convention_gives_the_same_states(self):  # acceptance 16
        linear = self.burndown()[0]
        rail = self.root / "guardrail.toml"
        rail.write_text(rail.read_text().replace('pattern = "[A-Z][A-Z0-9]*-[0-9]+"',
                                                 'pattern = "(EPIC|S|BUG)-?[0-9]+"'))
        mapping = {"ENG-100": "EPIC-1", "ENG-101": "S1", "ENG-102": "BUG-7", "ENG-103": "S3", "ENG-110": "S10"}
        roadmap, tests = ROADMAP, (self.root / "test_tickets.py").read_text()
        for old, new in mapping.items():
            roadmap = roadmap.replace(old, new)
            tests = tests.replace("_" + old.replace("-", "_") + "_", "_" + new.replace("-", "_") + "_")
        self.write("ROADMAP.md", roadmap)
        self.write("test_tickets.py", tests)
        self.git("mv", "receipts/ENG-101", "receipts/S1")
        self.commit("custom ids", "Owner-Approved: owner")
        custom = self.burndown()[0]
        self.assertEqual(linear.replace("ENG-100", "EPIC-1").split(" (was")[0], custom.split(" (was")[0])

    def test_tag_delimiters_keep_ids_apart(self):  # acceptance 16
        self.write("test_tickets.py", "import unittest\n\n\nclass T(unittest.TestCase):\n"
                                      "    def test_ENG_1011_other(self):\n        pass\n")
        self.commit("only a longer id is tagged")
        lines = self.burndown()
        self.assertIn("burndown: Epic ENG-100 · live 0/3, green 0, red 0, open 2, blocked 0, parked 1", lines[0])

    def test_rejected_id_fails_with_its_line(self):  # acceptance 16
        self.write("ROADMAP.md", ROADMAP.replace("- ENG-103", "- eng103"))
        self.commit("bad id", "Owner-Approved: owner")
        lines = self.burndown()
        self.assertTrue(any("ROADMAP.md:7: `eng103` does not match [ids] pattern" in l for l in lines), lines)

    def test_sync_runs_export_only_when_asked(self):  # acceptance 17
        marker = self.home / "exported.json"
        rail = self.root / "guardrail.toml"
        rail.write_text(rail.read_text().replace('# export = "scripts/push-states.sh"',
                                                 f'export = "cat > {marker}"'))
        self.commit("export", "Owner-Approved: owner")
        self.burndown()
        self.assertFalse(marker.exists())
        self.write("note.md", "move base\n")
        self.commit("move base")
        self.bigbang("--only", "burndown", "--sync")
        self.assertEqual(json.loads(marker.read_text())["states"]["ENG-101"], "live")

    def test_req_is_optional_without_the_intake_domain(self):
        self.write("ROADMAP.md", ROADMAP.replace("req: R9", "").replace(" · req: R1 · ", " · ")
                   .replace("req: R1, R2 · ", "").replace("req: R2 · ", ""))
        self.commit("chat: drop req", "Owner-Approved: owner")
        code, lines = self.bigbang("--only", "burndown")
        self.assertIn("ok: burndown", lines)
        code, lines = self.bigbang("--only", "goals")
        self.assertTrue(any("has no `req:`" in l for l in lines), lines)

    def test_roadmap_template_is_a_session_brief(self):
        text = (HERE / "templates/ROADMAP.md").read_text()
        self.assertIn("Start a session with `@ROADMAP.md`", text)
        self.assertLessEqual(len(text.splitlines()), 20)

    def test_intake_is_verbatim_and_traced(self):  # acceptance 13, 14
        page = (self.root / "docs/specs/requirements.md").read_text()
        self.assertIn("> add numbers\n> and subtract them\n", page)
        words = self.home / "again.txt"
        words.write_text("add numbers\nand subtract them\n")
        lines = []
        with chdir(self.root):
            M.main(self.kit, self.pack, ["goals", str(words)], out=lines.append)
        self.assertEqual(lines, ["ok: goals: already R1"])
        code, lines = self.bigbang("--only", "goals")
        self.assertIn("ok: goals", lines)
        self.write("ROADMAP.md", ROADMAP.replace("req: R2 · entry: `mul", "req: R9 · entry: `mul")
                   .replace("- ENG-101 · req: R1 · ", "- ENG-101 · "))
        code, lines = self.bigbang("--only", "goals")
        fails = [l for l in lines if l.startswith("FAIL: goals")]
        self.assertTrue(any("ENG-101 has no `req:`" in f for f in fails), fails)
        self.assertTrue(any("ENG-103 cites unknown R9" in f for f in fails), fails)
        words.write_text("divide as well\n")
        with chdir(self.root):
            M.main(self.kit, self.pack, ["goals", str(words)], out=lambda _: None)
        code, lines = self.bigbang("--only", "goals")
        self.assertIn("uncovered: R3", lines)


class LedgerTests(Repo):
    def test_one_live_swe_and_stale_entries_stop_blocking(self):  # acceptance 10
        self.git("init", "-q", "-b", "main")
        t0 = datetime(2026, 11, 27, 10, tzinfo=timezone.utc)
        out = []
        self.assertEqual(L.ledger_main(self.root, ["start", "swe", "a", "s1"], out.append, t0), 0)
        self.assertEqual(L.ledger_main(self.root, ["start", "swe", "b", "s2"], out.append, t0), 1)
        self.assertIn("a is the live swe", out[-1])
        later = t0 + timedelta(hours=4)
        self.assertEqual(L.ledger_main(self.root, ["start", "swe", "b", "s2"], out.append, later), 0)
        rows = (self.root / L.LEDGER).read_text().splitlines()
        rows.append(json.dumps({"ts": "2026-11-27T14:00:00Z", "op": "start", "role": "swe", "name": "c", "id": "x"}))
        (self.root / L.LEDGER).write_text("\n".join(rows) + "\n")
        self.assertEqual(L.doubles(self.root, 3, later), {"swe": ["b", "c"]})


class TankTests(Repo):
    def setUp(self):
        super().setUp()
        self.python_project("--compass", "tanks")

    def test_without_paid_only_the_oracle_runs_and_paid_tanks_fail(self):  # acceptance 4
        self.assertTrue((self.root / T.CASES).is_file())
        code, lines = self.bigbang()
        card = json.loads((self.root / T.CARD).read_text())
        self.assertEqual(list(card["tanks"]), ["oracle"])
        self.assertEqual(card["tanks"]["oracle"]["pass_rate"], 1.0)
        self.assertEqual(card["tanks"]["oracle"]["cost_usd"], 0.0)
        self.assertIn("codex", card["unmeasured"])
        self.assertTrue(any("has no run for claude-code · fix: bigbang --paid" in l for l in lines), lines)

    def test_subset_or_cap_makes_the_card_partial(self):  # acceptance 5
        self.bigbang()
        cases = json.loads((self.root / T.CASES).read_text())
        cases.append(dict(cases[0], id="second"))
        self.write(T.CASES, json.dumps(cases))
        code, lines = self.bigbang("--cases", "second")
        card = json.loads((self.root / T.CARD).read_text())
        self.assertTrue(card["partial"])
        self.assertTrue(any("is partial" in l for l in lines), lines)

    def test_paid_adapter_reads_usage_and_cap_stops(self):
        self.bigbang()
        result = {"usage": {"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 900,
                            "cache_creation_input_tokens": 10}, "total_cost_usd": 3.0, "num_turns": 4,
                  "modelUsage": {"claude-sonnet-5-5": {}}}

        def runner(cmd, cwd, **kw):
            sh("sh " + str(self.root / "tanks/oracle/gate-red-test.sh"), cwd, env=kw.get("env"))
            return subprocess.CompletedProcess(cmd, 0, json.dumps(result), "")

        ctx = SimpleNamespace(root=self.root, rail=__import__("base").read_rail(self.root), cases=None)
        card = T.run_suite(ctx, ["claude-code"], runner)
        tank = card["tanks"]["claude-code"]
        self.assertEqual(tank["tokens_per_pass"], 1060)  # cache reads count: the shot is re-read each turn
        self.assertTrue(card["partial"])
        self.assertIn("cost cap", card["stopped"])
        self.assertEqual(T.verdict({"pass_rate": 1.0, "tokens_per_pass": 200, "tokens_per_pass_spread": 10},
                                   {"pass_rate": 1.0, "tokens_per_pass": 160, "tokens_per_pass_spread": 5}), "keep")
        self.assertEqual(T.verdict({"pass_rate": 1.0, "tokens_per_pass": 200, "tokens_per_pass_spread": 50},
                                   {"pass_rate": 1.0, "tokens_per_pass": 160, "tokens_per_pass_spread": 5}), "revert")

    def test_gate_fails_on_a_stale_card(self):
        self.bigbang()
        self.bigbang()
        self.write("AGENTS.md", "changed\n")
        code, lines = self.bigbang("--only", "gate")
        self.assertTrue(any("tanks/card.json is stale" in l for l in lines), lines)


class TaxonomyTests(Repo):
    def test_modules_never_sit_under_domains(self):  # acceptance 18
        text = K.PACK.read_text()
        real = K.Pack(text)
        self.assertEqual(set(real.compass), {"core", "goals", "babysitter", "tanks"})
        self.assertFalse([i for items in real.items.values() for i in items if i.kind == "module"])
        with self.assertRaises(SystemExit):
            K.Pack(text.replace("## astro\n", "## astro\n\n1. module:goals\n", 1))

    def test_no_domain_points_at_sketch(self):  # acceptance 19
        code, lines = self.bigbang()
        self.assertEqual(code, 1)
        self.assertTrue(any("no domain named" in l and "bigbang sketch" in l for l in lines), lines)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_selection_persists_and_changes_are_the_owners(self):  # acceptance 18
        self.git("init", "-q", "-b", "main")
        self.assertEqual(self.bigbang("web", "--compass", "goals")[0], 0)
        rail = (self.root / "guardrail.toml").read_text()
        self.assertIn('domains = ["web"]', rail)
        self.assertIn('compass = ["goals"]', rail)
        code, lines = self.bigbang()
        self.assertIn("ok: goals", lines)
        code, lines = self.bigbang("notes")
        self.assertTrue(any("names domains ['web']; this command names ['notes']" in l for l in lines), lines)


class IndexTests(Repo):
    def test_index_points_and_memory_files_import_it(self):
        self.git("init", "-q", "-b", "main")
        self.write("AGENTS.md", "# House rules\n\nKeep it short.\n")
        self.bigbang("web")
        text = (self.root / "AGENTS.md").read_text()
        self.assertTrue(text.startswith("# House rules\n\nKeep it short.\n"))
        block = I.current_block(text)
        self.assertIn("- [ROADMAP.md](ROADMAP.md) — start every session here", block)
        self.assertIn("[guardrail.toml](guardrail.toml)", block)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        self.assertEqual((self.root / "GEMINI.md").read_text(), "@AGENTS.md\n")
        self.write("pkg/AGENTS.md", "# pkg\n")
        code, lines = self.bigbang()
        self.assertIn("done: index: refresh the index block in AGENTS.md", lines)
        self.assertIn("[pkg/AGENTS.md](pkg/AGENTS.md)", (self.root / "AGENTS.md").read_text())
        self.write("CLAUDE.md", "# Claude notes\n")
        code, lines = self.bigbang()
        self.assertTrue(any("CLAUDE.md does not import AGENTS.md" in l for l in lines), lines)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "# Claude notes\n")


CONTEXT = {"total_cost_usd": 0, "result": """## Context Usage

**Model:** claude-x  
**Tokens:** 24.7k / 1m (2%)

### Estimated usage by category

| Category | Tokens | Percentage |
|----------|--------|------------|
| System prompt | 2.8k | 0.3% |
| System tools | 13.8k | 1.4% |
| MCP tools | 657 | 0.1% |
| System tools (deferred) | 17.4k | 1.7% |
| Memory files | 325 | 0.0% |
| Skills | 6.1k | 0.6% |
| Free space | 972.3k | 97.2% |

### MCP Tools

| Tool | Server | Tokens |
|------|--------|--------|
| mcp__context7__query-docs | context7 | 962 |

### Skills

| Skill | Source | Tokens |
|-------|--------|--------|
| bigbang | User | ~70 |
| pub:leaked | Plugin | ~50 |
"""}
CODEX_INPUT = [{"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "x" * 400}]},
               {"type": "message", "role": "developer",
                "content": [{"type": "input_text", "text": "<skills_instructions>\n- kit: load skills\n" + "y" * 80}]},
               {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md\n" + "z" * 40}]},
               {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hello"}]}]


class ShotTests(Repo):
    def setUp(self):
        super().setUp()
        self.python_project()

    def test_vendor_dumps_parse_at_zero_cost(self):  # acceptance 20
        with mock.patch.object(S, "sh", return_value=subprocess.CompletedProcess([], 0, json.dumps(CONTEXT), "")):
            shot = S.probe_claude(self.root)
        self.assertEqual(shot["total"], 2800 + 13800 + 657 + 325 + 6100)
        self.assertNotIn("System tools (deferred)", shot["categories"])
        self.assertEqual((shot["model"], shot["window"]), ("claude-x", 1000000))
        self.assertEqual(shot["skills"], ["bigbang", "pub:leaked"])
        with mock.patch.object(S, "sh", return_value=subprocess.CompletedProcess([], 0, json.dumps(CODEX_INPUT), "")):
            codex = S.probe_codex(self.root)
        self.assertEqual(codex["skills"], ["kit"])
        self.assertEqual(set(codex["categories"]), {"System prompt", "Skills", "Memory files", "Messages"})
        billed = dict(CONTEXT, total_cost_usd=0.01)
        with mock.patch.object(S, "sh", return_value=subprocess.CompletedProcess([], 0, json.dumps(billed), "")):
            with self.assertRaises(ValueError):
                S.probe_claude(self.root)

    def test_shot_recorded_once(self):
        code, lines = self.bigbang()
        self.assertFalse([l for l in lines if l.startswith("done: shots")], lines)
        self.shot = fake_shot(total=1500)
        code, lines = self.bigbang()
        self.assertTrue(any(l.startswith("done: shots: record the context shot") for l in lines), lines)

    def test_leaks_fail_with_their_fix(self):  # acceptance 21
        self.shot = fake_shot(memory=5000, total=9000, skills=("bigbang", "pub:leaked"))
        self.write(".mcp.json", json.dumps({"mcpServers": {"stray": {"command": "x"}}}))
        rail = self.root / "guardrail.toml"
        rail.write_text(rail.read_text() + '\n[shots]\nbudget = { "claude-code" = 8000 }\n')
        with mock.patch.object(S, "catalog_names", return_value={"pub:leaked"}), \
                mock.patch.object(M.McpModule, "probe", return_value=[]):
            code, lines = self.bigbang("--only", "shots")
        fails = [l for l in lines if l.startswith("FAIL: shots")]
        self.assertTrue(any("catalog skills in the startup listing: pub:leaked" in f and "kit-starter-pack" in f
                            for f in fails), fails)
        self.assertTrue(any("MCP server stray" in f and "claude mcp remove -s project stray" in f for f in fails))
        self.assertTrue(any("memory files load 5000 tokens" in f for f in fails))
        self.assertTrue(any("claude-code: context shot 9000 tokens over budget 8000" in f for f in fails))
        self.shot = fake_shot()
        (self.root / ".mcp.json").unlink()
        code, lines = self.bigbang("--only", "shots")
        self.assertFalse([l for l in lines if l.startswith("FAIL: shots")], lines)

    def test_vendor_cache_holds_model_spec_and_docs(self):
        models = json.dumps({"models": [{"slug": "gpt-x", "context_window": 272000, "visibility": "list",
                                         "model_messages": {"instructions_template": "Be brief."}}]})
        with mock.patch.object(S, "sh", return_value=subprocess.CompletedProcess([], 0, models, "")), \
                mock.patch.object(S, "fetch_text", return_value="# llms.txt"):
            problems = S.refresh_vendor(self.kit, "openai", {"agents": ["codex"], "models": "codex debug models",
                                                             "docs": "https://example.invalid/llms.txt"}, self.root)
        self.assertEqual(problems, [])
        with mock.patch.object(S, "vendors", lambda: {"openai": {"agents": ["codex"]}}):
            spec = S.model_spec(self.kit, "codex")
        self.assertEqual(spec["models"], [{"id": "gpt-x", "context_window": 272000}])
        folder = S.cache_dir(self.kit, "openai")
        self.assertEqual((folder / "prompting-gpt-x.md").read_text(), "Be brief.")
        self.assertEqual((folder / "docs.txt").read_text(), "# llms.txt")
        self.assertFalse(S.cache_stale(self.kit, "openai", 7))

    def test_tank_rows_carry_the_shot_share(self):  # acceptance 22
        self.bigbang()
        rows = [{"case": "c", "rep": 0, "tank": "claude-code", "pass": True, "input": 100, "output": 50,
                 "cache_read": 3000, "cache_write": 0, "cost_usd": 0.1, "turns": 3}]
        summaries = {"claude-code": T.summarize(rows, 1)}
        T.against_shots(SimpleNamespace(root=self.root, kit=None), rows, summaries)
        self.assertEqual(summaries["claude-code"]["shot_tokens"], 1000)
        self.assertEqual(summaries["claude-code"]["shot_share"], round(1000 * 3 / 3150, 3))


def registry(versions):
    """A fake npm registry and OSV: {version: (days old, advisories)}."""
    now = datetime.now(timezone.utc)

    def fetch(url, data=None):
        if data is not None:
            return {"vulns": [{"id": a} for a in versions[data["version"]][1]]}
        return {"versions": {v: {} for v in versions},
                "time": {v: (now - timedelta(days=d)).isoformat() for v, (d, _) in versions.items()}}
    return fetch


class ScaffoldTests(Repo):
    def setUp(self):
        super().setUp()
        self.domains = self.home / "domains"
        (self.domains / "files/demo").mkdir(parents=True)
        (self.domains / "files/demo/README.md").write_text("demo\n")
        (self.domains / "web.toml").write_text(
            'name = "web"\nkind = "code"\nsummary = "demo site"\nrequires = ["python3>=3"]\n'
            '[packages]\n"npm:demo" = "latest-safe"\n'
            '[scaffold]\nsteps = ["npm install demo@{npm:demo} --save-exact"]\nfiles = { "README.md" = "demo/README.md" }\n'
            'check = "test -f built.txt"\nignore = ["node_modules/"]\n')
        self.patches += [mock.patch.object(F, "DOMAINS", self.domains), mock.patch.object(F, "FILES", self.domains / "files")]
        for p in self.patches[-2:]:
            p.start()

    def test_breach_safe_pin_and_goldfish_plan(self):  # acceptance 23
        versions = {"5.6.0": (2, []), "5.5.0": (20, ["GHSA-bad"]), "5.4.1": (40, []), "6.0.0-beta.1": (30, [])}
        with mock.patch.object(F, "fetch_json", registry(versions)):
            code, lines = self.bigbang("web")
        self.assertEqual(code, 1)
        lock = F.read_lock(self.root)
        self.assertEqual(lock["npm:demo"]["version"], "5.4.1")
        self.assertEqual(lock["npm:demo"]["skipped"], ["5.5.0: GHSA-bad"])
        plan = (self.root / F.PLAN).read_text()
        self.assertIn("1. `npm install demo@5.4.1 --save-exact`", plan)
        self.assertIn("Done when `test -f built.txt` exits 0.", plan)
        self.assertEqual((self.root / "README.md").read_text(), "demo\n")
        self.assertTrue(any("hand .bigbang/scaffold-plan.md to a goldfish" in l for l in lines), lines)
        self.assertFalse((self.root / "guardrail.toml").exists())
        self.write("built.txt", "the goldfish ran the plan\n")
        with mock.patch.object(F, "fetch_json", side_effect=AssertionError("no network once locked")):
            code, lines = self.bigbang("web")
            self.assertIn("ok: scaffold", lines)
            code, lines = self.bigbang()
        self.assertFalse([l for l in lines if l.startswith(("done:", "FAIL:"))], lines)

    def test_no_safe_version_fails_loudly(self):
        with mock.patch.object(F, "fetch_json", registry({"1.0.0": (40, ["GHSA-1"]), "1.1.0": (1, [])})):
            with self.assertRaises(ValueError) as caught:
                F.resolve("npm:demo", "latest-safe", 7)
        self.assertIn("1.0.0: GHSA-1", str(caught.exception))


class SketchTests(Repo):
    def test_sketch_stops_until_the_owner_approves_a_stack(self):  # acceptance 25
        code, lines = self.bigbang("sketch")
        self.assertEqual(code, 1)
        self.assertTrue((self.root / "sketch/prototype/index.html").is_file())
        self.assertTrue(any("sketch/BRIEF.md is not filled in" in l for l in lines), lines)
        self.assertFalse((self.root / "guardrail.toml").exists())
        brief = self.root / "sketch/BRIEF.md"
        filled = (brief.read_text().replace("- **Goal:**", "- **Goal:** a site for the bakery")
                  .replace("- **For:**", "- **For:** customers").replace("- **Owner words:**", "- **Owner words:** make a site")
                  .replace("- **Constraints:**", "- **Constraints:** static hosting"))
        brief.write_text(filled)
        code, lines = self.bigbang("sketch")
        self.assertTrue(any("not filled in (Domain)" in l for l in lines), lines)
        brief.write_text(filled.replace("- **Domain:**", "- **Domain:** astro"))
        code, lines = self.bigbang("sketch")
        self.assertTrue(any("sketch approved for `astro`" in l and "fix: bigbang astro" in l for l in lines), lines)


class ReleaseTests(Repo):
    """Regressions from the release review."""

    def test_a_crashing_module_becomes_a_fail_line(self):
        self.git("init", "-q", "-b", "main")
        self.bigbang("web")
        self.write(".mcp.json", "{not json")
        code, lines = self.bigbang("--only", "mcp")
        self.assertEqual(code, 1)
        self.assertTrue(any(l.startswith("FAIL: mcp: mcp probe crashed: JSONDecodeError") and "BIGBANG_DEBUG=1" in l
                            for l in lines), lines)

    def test_missing_vendor_cli_is_estimated_not_failed(self):
        self.python_project()
        with mock.patch.object(S, "PROBES", {"codex": S.probe_codex}), \
                mock.patch.object(S.shutil, "which", side_effect=lambda cli: None if cli == "codex" else "/bin/x"):
            code, lines = self.bigbang("--only", "shots")
        self.assertFalse([l for l in lines if l.startswith("FAIL: shots") and "codex" in l], lines)
        self.assertTrue(any(l.startswith("shot: codex") and "codex CLI not installed" in l for l in lines), lines)

    def test_base_tests_see_installed_dependencies(self):
        self.python_project()
        (self.root / "node_modules/dep").mkdir(parents=True)
        self.write(".gitignore", (self.root / ".gitignore").read_text() + "node_modules/\n")
        self.commit("ignore deps")
        sha = self.git("rev-parse", "HEAD")
        import base
        path, error = base.worktree_at(self.root, sha)
        self.assertEqual(error, "")
        self.assertTrue((path / "node_modules/dep").is_dir())
        path, error = base.worktree_at(self.root, sha)
        self.assertTrue((path / "node_modules").is_symlink())

    def test_foreign_hooks_path_is_reported_and_the_run_goes_on(self):
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.hooksPath", ".husky")
        code, lines = self.bigbang("web")
        self.assertTrue(any("gate hooks not enforced: core.hooksPath is .husky" in l for l in lines), lines)
        self.assertIn("ok: guardrail", lines)
        self.assertIn("ok: burndown", lines)

    def test_shot_jitter_is_not_a_change(self):
        self.python_project()
        self.shot = fake_shot(total=10000)
        self.bigbang()
        self.shot = fake_shot(total=10150)
        code, lines = self.bigbang()
        self.assertFalse([l for l in lines if "shots" in l and l.startswith(("done:", "FAIL:"))], lines)

    def test_default_base_prefers_main_over_a_feature_branch(self):
        self.git("init", "-q", "-b", "main")
        self.write("x.md", "x\n")
        self.commit("first")
        self.git("checkout", "-qb", "feature")
        self.bigbang("web")
        self.assertIn('base = "main"', (self.root / "guardrail.toml").read_text())


if __name__ == "__main__":
    unittest.main()
