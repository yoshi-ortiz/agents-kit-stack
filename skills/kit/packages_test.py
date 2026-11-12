"""kit upgrade 2026-11-12: workflow tier, startup listing gate, keep-off, prune, source drift."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packages as K  # noqa: E402

PACK_TEXT = Path(__file__).with_name("PACK.md").read_text()


class KitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        h = Path(self.tmp.name)
        self.patches = [mock.patch.object(K, n, v) for n, v in {
            "HOME": h, "MARKET": h / "market", "SETTINGS": h / "settings.json",
            "CLAUDE_STATE": h / "claude.json", "CACHE": h / "cache"}.items()]
        for p in self.patches:
            p.start()
        self.h = h

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def skill(self, plugin, name, desc, explicit):
        d = self.h / "market/plugins" / plugin / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\n" + ("disable-model-invocation: true\n" if explicit else "")
                                    + f"name: {name}\ndescription: {desc}\n---\nbody\n")

    def test_pack_reads_workflow(self):
        pack = K.Pack(PACK_TEXT)
        self.assertIn("ponytail:ponytail", pack.workflow)
        self.assertIn("superpowers:finishing-a-development-branch", pack.workflow)

    def test_bad_workflow_line_fails(self):
        with self.assertRaises(SystemExit):
            K.Pack(PACK_TEXT.replace("1. ponytail:ponytail", "1. ponytail"))

    def test_write_skill_keeps_workflow_skills_visible(self):
        src = self.h / "src/s/SKILL.md"
        src.parent.mkdir(parents=True)
        src.write_text("---\nname: s\ndescription: d\n---\nbody\n")
        with mock.patch.object(K, "stamp"):
            K.write_skill(self.h / "out/a", src, "P", "o/r", implicit=True)
            K.write_skill(self.h / "out/b", src, "P", "o/r")
        self.assertNotIn("disable-model-invocation", (self.h / "out/a/SKILL.md").read_text())
        self.assertIn("allow_implicit_invocation: true", (self.h / "out/a/agents/openai.yaml").read_text())
        self.assertIn("disable-model-invocation: true", (self.h / "out/b/SKILL.md").read_text())
        self.assertIn("allow_implicit_invocation: false", (self.h / "out/b/agents/openai.yaml").read_text())

    def test_listing_counts_only_visible_skills_of_enabled_plugins(self):
        self.skill("ponytail", "ponytail", "lazy", explicit=False)
        self.skill("pstack", "how", "how", explicit=True)
        self.skill("tuist", "gen", "gen", explicit=False)
        (self.h / "settings.json").write_text(json.dumps({"enabledPlugins": {"tuist@kit": False}}))
        names, size = K.visible_listing()
        self.assertEqual(names, ["ponytail:ponytail"])
        self.assertEqual(size, len("ponytail:ponytail") + len("lazy"))

    def test_unused_and_prune_keep_used_plugins(self):
        (self.h / "settings.json").write_text(json.dumps({"enabledPlugins": {
            "ponytail@kit": True, "tuist@kit": True, "pstack@kit": True, "other@x": True}}))
        (self.h / "claude.json").write_text(json.dumps({
            "pluginUsage": {"ponytail@kit": {"usageCount": 3}, "tuist@kit": {"usageCount": 0}},
            "skillUsage": {"pstack:how": {"usageCount": 1}}}))
        self.assertEqual(K.unused_plugins(), ["tuist@kit"])
        K.prune(False)
        plugins = json.loads((self.h / "settings.json").read_text())["enabledPlugins"]
        self.assertIs(plugins["tuist@kit"], False)
        self.assertIs(plugins["ponytail@kit"], True)
        self.assertEqual(K.disabled_plugins(), {"tuist@kit"})

    def test_source_drift_flags_a_copy(self):
        copy = self.h / "copy/packages.py"
        copy.parent.mkdir()
        copy.write_text("")
        with mock.patch.object(K, "__file__", str(copy)):
            problems = K.source_drift()
        self.assertEqual(len(problems), 1)
        self.assertIn("not a git checkout", problems[0])

    def test_source_drift_flags_uncommitted_changes(self):
        repo = self.h / "repo"
        (repo / "skills/kit").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        f = repo / "skills/kit/packages.py"
        f.write_text("x")
        with mock.patch.object(K, "__file__", str(f)):
            self.assertIn("uncommitted kit change", K.source_drift()[0])


if __name__ == "__main__":
    unittest.main()
