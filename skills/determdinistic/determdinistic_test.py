import json
import subprocess
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from determdinistic import audit, calculate, tickets  # noqa: E402


class AuditTests(unittest.TestCase):
    def test_unclosed_frontmatter_is_reported_and_preserved(self):
        source = "---\n- Status: example\n"
        report, fixed = audit(source)
        self.assertEqual(report["diagnostics"], [{"line": 1, "code": "unclosed_frontmatter"}])
        self.assertEqual(fixed, source)

    def test_normalizes_fields_and_preserves_other_bytes(self):
        source = (
            "\ufeff---\r\n- Example: metadata\r\n---\r\n"
            "# Release\r\n- **Status** :  Open\r\n* Owner: Zoë  \r\n\r\n"
            "````text\r\n \t````\r\n- Example: code\r\n````\r\n"
            "<!--\r\n\r\n- Example: comment\r\n-->\r\n"
            "## Details\r\n+ Status: `ready`"
        )
        report, fixed = audit(source)
        self.assertEqual(
            report["sections"][1:],
            [
                {"heading": ["Release"], "line": 4, "values": {"Status": "Open", "Owner": "Zoë"}},
                {"heading": ["Release", "Details"], "line": 16, "values": {"Status": "`ready`"}},
            ],
        )
        self.assertEqual(
            fixed,
            source.replace("**Status** :  Open", "**Status:** Open")
            .replace("Owner: Zoë", "**Owner:** Zoë")
            .replace("Status: `ready`", "**Status:** `ready`"),
        )
        clean_report, second_fix = audit(fixed)
        self.assertEqual(clean_report["diagnostics"], [])
        self.assertEqual(second_fix, fixed)

    def test_flags_ambiguous_values_and_preserves_their_source(self):
        source = (
            "- Status: Open\n- status: Closed\n- Owner:\n"
            "- Notes: first line\nsecond line\n\n"
            "- Detail: first line\n\n  another paragraph\n"
        )
        report, fixed = audit(source)
        self.assertEqual(report["sections"][0]["values"], {})
        self.assertEqual(
            [(item["line"], item["code"]) for item in report["diagnostics"]],
            [(1, "duplicate_key"), (2, "duplicate_key"), (3, "empty_value"),
             (4, "multiline_value"), (7, "multiline_value")],
        )
        self.assertEqual(fixed, source)


class CalculationTests(unittest.TestCase):
    def test_sums_one_named_column_exactly(self):
        source = (
            "# Ledger\n| Item | Amount |\n| --- | ---: |\n"
            "| Flour \\| Sugar | 10000000000000000000000000000.1 |\n"
            "| Credit | -10000000000000000000000000000 |\n"
            "| Tax | .2 |\n\n# Other section\n"
        )
        self.assertEqual(calculate(source, 2, "Amount"), "0.3")
        with self.assertRaisesRegex(ValueError, "line 6.*requires a plain decimal"):
            calculate(source.replace(".2 |", "$0.20 |"), 2, "Amount")
        with self.assertRaisesRegex(ValueError, "line 6.*expected 2"):
            calculate(source.replace(".2 |", ".2 | extra |"), 2, "Amount")
        with self.assertRaisesRegex(ValueError, "nonempty and unique"):
            calculate(source.replace("Item | Amount", "Amount | Amount"), 2, "Amount")

    def test_counts_items_not_marker_values_or_nested_items(self):
        source = (
            "# Checklist\n3. First\n   1. Child\n   2. Child\n"
            "\n99. Second\n    continuation\n\n# Another list\n1. Unrelated\n"
        )
        self.assertEqual(calculate(source, 2), 2)
        with self.assertRaisesRegex(ValueError, "expected the first item"):
            calculate("```md\n1. example\n```\n", 2)

    def test_cli_exit_status_for_an_expectation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gate.md"
            path.write_bytes(b"| Amount |\n| --- |\n| 0.1 |\n| 0.2 |\n")
            script = Path(__file__).with_name("determdinistic.py")
            command = [sys.executable, str(script), str(path), "--sum", "1", "Amount", "--expect"]
            for expected, status in (("0.30", 0), ("0.31", 1)):
                result = subprocess.run([*command, expected], capture_output=True, check=False)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout), {"actual": "0.3", "expected": expected, "matches": status == 0}
                )


@unittest.skipUnless(find_spec("duckdb"), "analytics requires DuckDB")
class QueryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "ledger.md"
        self.path.write_text(
            "```md\n# Expenses\n| Vendor | Amount |\n| --- | --- |\n```\n\n"
            "# Expenses\n\n| Vendor | Amount |\n| --- | --- |\n"
            "| B | 3.01 |\n| A | 0.10 |\n| A | 0.20 |\n",
            encoding="utf-8",
        )
        script = Path(__file__).with_name("determdinistic.py")
        self.command = [sys.executable, str(script), "query", str(self.path), "--table", "Expenses"]

    def run_query(self, *args):
        return subprocess.run([*self.command, *args], capture_output=True, check=False)

    def test_grouped_statistics_are_sorted_and_total_preserves_scale(self):
        args = (
            "--group-by", "Vendor", "--decimal", "Amount=2", "--metric", "sum:Amount",
            "--metric", "count", "--metric", "median:Amount", "--metric", "p95:Amount",
            "--metric", "stddev:Amount",
        )
        result = self.run_query(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.run_query(*args).stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["header_line"], 9)
        first, second = report["rows"]
        self.assertEqual((first["Vendor"], first["sum:Amount"], first["count"]), ("A", "0.30", 2))
        self.assertAlmostEqual(first["median:Amount"], 0.15)
        self.assertAlmostEqual(first["p95:Amount"], 0.195)
        self.assertAlmostEqual(first["stddev:Amount"], 0.0707106781)
        self.assertEqual(second["Vendor"], "B")
        self.assertIsNone(second["stddev:Amount"])

    def test_exact_and_statistical_gates(self):
        for expected, status in (("3.31", 0), ("3.30", 1)):
            result = self.run_query("--metric", "sum:Amount", "--expect", expected)
            self.assertEqual(result.returncode, status, result.stderr)
            self.assertEqual(json.loads(result.stdout)["matches"], status == 0)

        args = ("--metric", "avg:Amount", "--expect", "1.10333")
        result = self.run_query(*args)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"requires --tolerance", result.stderr)
        result = self.run_query(*args, "--tolerance", "0.00001")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_query("--metric", "sum:Amount", "--decimal", "Amount=1")
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"line 11", result.stderr)


LINEAR = r"[A-Z][A-Z0-9]*-[0-9]+"
REQ = r"R[0-9]+(?:\.[0-9]+)?"
ROADMAP = (
    "## Epic: ENG-100 · Convert · benchmark: books open\n"
    "Order: ENG-102, ENG-101\n"
    "- ENG-101 · req: R1, R2 · entry: `Files tab` · visible: opens\n"
    "- BUG-7 · req: R2 · visible: y · limit: hardware\n"
    "```\n- ENG-999 · req: R1\n```\n"
    "## R1.1 · 2026-11-27 · refines R1\n"
    "- ENG-101 · req: R3\n"
)


class TicketTests(unittest.TestCase):
    def test_links_are_many_to_many_and_skip_code(self):
        report = tickets(ROADMAP, [LINEAR, REQ], "ROADMAP.md")
        ids = [t["id"] for t in report["tickets"]]
        self.assertEqual(ids, ["ENG-100", "ENG-101", "BUG-7", "R1.1", "ENG-101"])
        edges = {(e["from"], e["field"], e["to"]) for e in report["links"]}
        self.assertTrue({("ENG-101", "req", "R1"), ("ENG-101", "req", "R2"), ("BUG-7", "req", "R2"),
                         ("ENG-100", "Order", "ENG-102"), ("R1.1", "refines", "R1")} <= edges)
        self.assertNotIn("ENG-999", ids)
        self.assertEqual(report["tickets"][0]["label"], "Epic")
        self.assertEqual(report["tickets"][2]["fields"]["limit"], "hardware")
        self.assertEqual([d["code"] for d in report["diagnostics"]], ["duplicate_ticket"])

    def test_any_convention_by_pattern(self):
        custom = "- S1 · req: R1\n- TODO-3 · req: R1 · blocks: S1\n- ENG-5 · req: R1\n"
        report = tickets(custom, [r"(S|TODO)-?[0-9]+", REQ])
        self.assertEqual([t["id"] for t in report["tickets"]], ["S1", "TODO-3"])
        self.assertIn({"from": "TODO-3", "field": "blocks", "to": "S1", "file": "", "line": 2}, report["links"])


@unittest.skipUnless(find_spec("duckdb"), "ticket SQL requires DuckDB")
class TicketSqlTests(unittest.TestCase):
    def test_requirement_to_tickets_join(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ROADMAP.md"
            path.write_text(ROADMAP)
            sql = "SELECT dst AS req, string_agg(DISTINCT src, ',' ORDER BY src) AS tickets FROM links " \
                  "WHERE field = 'req' GROUP BY dst ORDER BY dst"
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("determdinistic.py")), "tickets",
                                     str(path), "--pattern", LINEAR, "--pattern", REQ, "--sql", sql],
                                    capture_output=True, text=True)
            rows = json.loads(result.stdout)["rows"]
            self.assertIn({"req": "R2", "tickets": "BUG-7,ENG-101"}, rows)


if __name__ == "__main__":
    unittest.main()
