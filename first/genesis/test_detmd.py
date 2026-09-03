from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "detmd.py"
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import detmd


@contextlib.contextmanager
def project():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        before = Path.cwd()
        os.chdir(root)
        try:
            yield root
        finally:
            os.chdir(before)


def marker(spec: dict) -> str:
    return "<!-- detmd " + json.dumps(spec, separators=(",", ":")) + " -->\n"


def table_spec(identifier: str, source: dict, columns: list[dict], **extra) -> dict:
    return {
        "version": 1,
        "id": identifier,
        "direction": "source-to-markdown",
        "sources": {"main": source},
        "from": "main",
        "schema": columns,
        "key": [columns[0]["name"]],
        "order_by": [columns[0]["name"]],
        "operations": [],
        "renderer": "pipe",
        **extra,
    }


class PublicSurfaceTests(unittest.TestCase):
    def test_bundled_script_exposes_the_three_v1_commands(self) -> None:
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        for command in ("check", "render", "export"):
            self.assertIn(command, done.stdout)

    def test_local_package_metadata_exposes_the_same_module_and_command(self) -> None:
        metadata = tomllib.loads((HERE / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["name"], "determdinistic")
        self.assertEqual(metadata["project"]["version"], "0.1.0")
        self.assertEqual(metadata["project"]["scripts"]["detmd"], "detmd:main")
        self.assertEqual(metadata["tool"]["setuptools"]["py-modules"], ["detmd"])

    def test_graphics_flow_action_guide_is_a_live_mirror(self) -> None:
        payload = json.loads(detmd.export("graphics-flow-actions", [ROOT], "json"))
        self.assertEqual([row["action"] for row in payload["rows"]], [
            "edit-scene-spec", "add-corpus", "observe", "seed-tags", "refine",
            "compile", "export-avge", "preflight", "run-avge", "build",
            "repair-output", "apply-correction", "verify-delivery", "done",
        ])
        self.assertFalse([issue for issue in detmd.check([ROOT])
                          if issue.declaration_id == "graphics-flow-actions"])

    def test_json_source_renders_checks_and_exports_without_touching_prose(self) -> None:
        with project() as root:
            (root / "data.json").write_text(
                json.dumps({"rows": [{"name": "beta", "bytes": 2000},
                                      {"name": "alpha", "bytes": 1000}]}),
                encoding="utf-8",
            )
            spec = table_spec(
                "sizes",
                {"kind": "json", "path": "data.json", "pointer": "/rows"},
                [{"name": "name", "type": "id"},
                 {"name": "bytes", "type": "integer"}],
            )
            doc = root / "README.md"
            doc.write_text("before\n" + marker(spec) + "| stale |\n| --- |\n\nafter\n",
                           encoding="utf-8")

            self.assertEqual([issue.code for issue in detmd.check([root])], ["drift"])
            result = detmd.render([root])
            self.assertTrue(result[0].changed)
            self.assertEqual(detmd.check([root]), ())
            rendered = doc.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith("before\n<!-- detmd "))
            self.assertTrue(rendered.endswith("\nafter\n"))
            self.assertIn("| alpha | 1000 |\n| beta | 2000 |", rendered)

            payload = json.loads(detmd.export("sizes", [root], "json"))
            self.assertEqual([row["name"] for row in payload["rows"]], ["alpha", "beta"])
            self.assertEqual(payload["detmd"], 1)
            self.assertEqual(len(payload["provenance"]["canonical_sha256"]), 64)
            self.assertEqual(detmd.export("sizes", [root], "tsv"),
                             "name\tbytes\nalpha\t1000\nbeta\t2000\n")

    def test_markdown_inputs_remain_editable_and_derived_cells_are_repaired(self) -> None:
        with project() as root:
            spec = {
                "version": 1, "id": "sizes", "direction": "markdown-with-derived",
                "schema": [
                    {"name": "name", "type": "id", "role": "input"},
                    {"name": "bytes", "type": "integer", "role": "input"},
                    {"name": "size", "type": "string", "role": "derived"},
                ],
                "key": ["name"], "order_by": ["name"],
                "operations": [{"op": "bytes_iec", "column": "bytes", "as": "size",
                                "unit": "KiB", "places": 1}], "renderer": "pipe",
            }
            doc = root / "sizes.md"
            doc.write_text(marker(spec) +
                           "| name | bytes | size |\n| --- | --- | --- |\n"
                           "| beta | 2048 | definitely two |\n| alpha | 1024 | wrong |\n",
                           encoding="utf-8")

            self.assertEqual([i.code for i in detmd.check([root])], ["drift"])
            detmd.render([root])
            body = doc.read_text(encoding="utf-8")
            self.assertIn("| alpha | 1024 | 1.0 KiB |", body)
            self.assertIn("| beta | 2048 | 2.0 KiB |", body)

            doc.write_text(body.replace("| beta | 2048 |", "| beta | 3072 |"), encoding="utf-8")
            detmd.render([root])
            self.assertIn("| beta | 3072 | 3.0 KiB |", doc.read_text(encoding="utf-8"))

    def test_tsv_source_supports_sum_and_si_bytes(self) -> None:
        with project() as root:
            (root / "sizes.tsv").write_text("kind\tbytes\na\t1000\na\t2000\nb\t500\n",
                                             encoding="utf-8")
            spec = table_spec(
                "totals", {"kind": "tsv", "path": "sizes.tsv",
                           "types": {"bytes": "integer"}},
                [{"name": "kind", "type": "id"},
                 {"name": "total", "type": "integer", "role": "derived"},
                 {"name": "size", "type": "string", "role": "derived"}],
                operations=[
                    {"op": "sum", "column": "bytes", "as": "total", "group_by": ["kind"]},
                    {"op": "bytes_si", "column": "total", "as": "size",
                     "unit": "kB", "places": 1},
                ],
            )
            doc = root / "totals.md"
            doc.write_text(marker(spec) + "| old |\n| --- |\n", encoding="utf-8")
            detmd.render([root])
            text = doc.read_text(encoding="utf-8")
            self.assertIn("| a | 3000 | 3.0 kB |", text)
            self.assertIn("| b | 500 | 0.5 kB |", text)

    def test_python_export_runs_out_of_process(self) -> None:
        with project() as root:
            (root / "source.py").write_text(
                "def rows():\n    return [{'name': 'from-python', 'ok': True}]\n",
                encoding="utf-8",
            )
            spec = table_spec(
                "python", {"kind": "python-export", "path": "source.py", "function": "rows"},
                [{"name": "name", "type": "id"}, {"name": "ok", "type": "boolean"}],
            )
            (root / "python.md").write_text(marker(spec) + "| old |\n| --- |\n",
                                             encoding="utf-8")
            detmd.render([root])
            self.assertIn("| from-python | true |",
                          (root / "python.md").read_text(encoding="utf-8"))

    def test_link_rows_join_and_validate_many_to_many_references(self) -> None:
        with project() as root:
            for name, rows in {
                "links": [{"agent_id": "a1", "skill_id": "s1"},
                          {"agent_id": "a1", "skill_id": "s2"}],
                "agents": [{"agent_id": "a1", "agent": "Ada"}],
                "skills": [{"skill_id": "s1", "skill": "Genesis"},
                           {"skill_id": "s2", "skill": "Aesthetic"}],
            }.items():
                (root / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
            spec = {
                "version": 1, "id": "links", "direction": "source-to-markdown",
                "sources": {name: {"kind": "json", "path": f"{name}.json"}
                            for name in ("links", "agents", "skills")},
                "from": "links",
                "schema": [
                    {"name": "agent_id", "type": "ref"},
                    {"name": "agent", "type": "string"},
                    {"name": "skill_id", "type": "ref"},
                    {"name": "skill", "type": "string"},
                ],
                "key": ["agent_id", "skill_id"], "order_by": ["skill_id"],
                "operations": [
                    {"op": "foreign_key", "column": "agent_id", "source": "agents",
                     "target": "agent_id"},
                    {"op": "foreign_key", "column": "skill_id", "source": "skills",
                     "target": "skill_id"},
                    {"op": "join", "source": "agents", "on": [["agent_id", "agent_id"]]},
                    {"op": "join", "source": "skills", "on": [["skill_id", "skill_id"]]},
                ], "renderer": "pipe",
            }
            (root / "links.md").write_text(marker(spec) + "| old |\n| --- |\n",
                                            encoding="utf-8")
            detmd.render([root])
            text = (root / "links.md").read_text(encoding="utf-8")
            self.assertIn("| a1 | Ada | s1 | Genesis |", text)
            self.assertIn("| a1 | Ada | s2 | Aesthetic |", text)

    def test_fenced_source_mirror_is_supported(self) -> None:
        with project() as root:
            (root / "snippet.json").write_text(json.dumps({"code": "print('ok')\n"}),
                                                encoding="utf-8")
            spec = {
                "version": 1, "id": "snippet", "direction": "source-to-markdown",
                "sources": {"main": {"kind": "json", "path": "snippet.json",
                                     "pointer": "/code"}},
                "from": "main", "schema": [], "key": [], "order_by": [],
                "operations": [], "renderer": "fence", "language": "python",
            }
            doc = root / "snippet.md"
            doc.write_text(marker(spec) + "```python\nstale\n```\n", encoding="utf-8")
            detmd.render([root])
            self.assertTrue(doc.read_text(encoding="utf-8").endswith(
                "```python\nprint('ok')\n```\n"))

    def test_executable_cell_declarations_are_validated_but_never_run(self) -> None:
        with project() as root:
            spec = {
                "version": 1, "id": "deferred", "direction": "markdown-to-runtime",
                "schema": [], "key": [], "order_by": [], "operations": [],
                "renderer": "fence", "language": "python", "execution": {},
            }
            (root / "cell.md").write_text(
                marker(spec) + "```python\nraise RuntimeError('must stay deferred')\n```\n",
                encoding="utf-8",
            )
            issues = detmd.check([root])
            self.assertEqual([issue.code for issue in issues], ["bad-execution"])
            spec["execution"] = {
                "runner": "python", "cwd": ".", "timeout_seconds": 10,
                "expected_exit": 0, "inputs": [], "outputs": [],
            }
            (root / "cell.md").write_text(
                marker(spec) + "```python\nraise RuntimeError('must stay deferred')\n```\n",
                encoding="utf-8",
            )
            self.assertEqual(detmd.check([root]), ())

    def test_invalid_input_fails_closed_and_render_is_atomic_per_file(self) -> None:
        with project() as root:
            (root / "ok.json").write_text('[{"id":"fresh"}]', encoding="utf-8")
            good = table_spec("good", {"kind": "json", "path": "ok.json"},
                              [{"name": "id", "type": "id"}])
            bad = table_spec("bad", {"kind": "json", "path": "../escape.json"},
                             [{"name": "id", "type": "id"}])
            doc = root / "atomic.md"
            original = (marker(good) + "| old |\n| --- |\n\n" + marker(bad)
                        + "| untouched |\n| --- |\n")
            doc.write_text(original, encoding="utf-8")
            with self.assertRaises(detmd.DetmdError):
                detmd.render([root])
            self.assertEqual(doc.read_text(encoding="utf-8"), original)

    def test_bad_sources_and_duplicate_ids_are_issues(self) -> None:
        cases = [
            ({"kind": "json", "path": "float.json"}, '[{"id":"x","n":1.5}]'),
            ({"kind": "python-export", "path": "boom.py", "function": "rows"},
             "def rows():\n    raise RuntimeError('boom')\n"),
        ]
        for source, body in cases:
            with self.subTest(source=source["kind"]), project() as root:
                (root / source["path"]).write_text(body, encoding="utf-8")
                spec = table_spec("bad", source,
                                  [{"name": "id", "type": "id"},
                                   {"name": "n", "type": "integer", "nullable": True}])
                (root / "bad.md").write_text(marker(spec) + "| old |\n| --- |\n",
                                              encoding="utf-8")
                self.assertTrue(detmd.check([root]))

        with project() as root:
            (root / "data.json").write_text('[{"id":"x"}]', encoding="utf-8")
            spec = table_spec("same", {"kind": "json", "path": "data.json"},
                              [{"name": "id", "type": "id"}])
            for name in ("a.md", "b.md"):
                (root / name).write_text(marker(spec) + "| old |\n| --- |\n",
                                         encoding="utf-8")
            self.assertIn("duplicate-id", [issue.code for issue in detmd.check([root])])

    def test_cli_reports_drift_then_repairs_it(self) -> None:
        with project() as root:
            (root / "data.json").write_text('[{"id":"x"}]', encoding="utf-8")
            spec = table_spec("cli", {"kind": "json", "path": "data.json"},
                              [{"name": "id", "type": "id"}])
            (root / "cli.md").write_text(marker(spec) + "| old |\n| --- |\n",
                                          encoding="utf-8")
            red = subprocess.run([sys.executable, str(SCRIPT), "check", "."],
                                 capture_output=True, text=True)
            self.assertEqual(red.returncode, 1)
            self.assertIn("drift", red.stderr)
            green = subprocess.run([sys.executable, str(SCRIPT), "render", "."],
                                   capture_output=True, text=True)
            self.assertEqual(green.returncode, 0, green.stderr)
            self.assertEqual(subprocess.run(
                [sys.executable, str(SCRIPT), "check", "."],
                capture_output=True, text=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
