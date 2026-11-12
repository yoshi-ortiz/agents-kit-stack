"""kit 2026-11-12: keep-off on refresh, prune, source drift. Every catalog skill stays explicit-only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packages as K  # noqa: E402



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

    def test_write_skill_is_always_explicit_only(self):
        src = self.h / "src/s/SKILL.md"
        src.parent.mkdir(parents=True)
        src.write_text("---\nname: s\ndescription: d\n---\nbody\n")
        with mock.patch.object(K, "stamp"):
            K.write_skill(self.h / "out/b", src, "P", "o/r")
        self.assertIn("disable-model-invocation: true", (self.h / "out/b/SKILL.md").read_text())
        self.assertIn("allow_implicit_invocation: false", (self.h / "out/b/agents/openai.yaml").read_text())

    def test_unused_and_prune_keep_used_plugins(self):
        (self.h / "settings.json").write_text(json.dumps({"enabledPlugins": {
            "ponytail@kit": True, "tuist@kit": True, "pstack@kit": True, "other@x": True}}))
        (self.h / "claude.json").write_text(json.dumps({
            "pluginUsage": {"ponytail@kit": {"usageCount": 3}, "tuist@kit": {"usageCount": 0}},
            "skillUsage": {"pstack:how": {"usageCount": 1}}}))
        self.assertEqual(K.unused_plugins(), ["tuist@kit"])
        K.prune(False)  # bare prune only lists
        self.assertIs(json.loads((self.h / "settings.json").read_text())["enabledPlugins"]["tuist@kit"], True)
        with self.assertRaises(SystemExit):
            K.prune(False, ["ponytail"])  # used: refused
        K.prune(False, ["tuist"])
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
