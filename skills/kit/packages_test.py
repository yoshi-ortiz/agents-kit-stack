"""kit 2026-11-12: keep-off on refresh, prune, source drift. Every catalog skill stays explicit-only."""
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import chdir
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

    def test_write_skill_sets_host_policies(self):
        src = self.h / "src/s/SKILL.md"
        src.parent.mkdir(parents=True)
        src.write_text("---\nname: s\ndescription: d\n---\nbody\n")
        with mock.patch.object(K, "stamp"):
            K.write_skill(self.h / "out/b", src, "P", "o/r")
        self.assertIn("disable-model-invocation: true", (self.h / "out/b/SKILL.md").read_text())
        self.assertIn("allow_implicit_invocation: true", (self.h / "out/b/agents/openai.yaml").read_text())

    def test_model_visible_catalog_install_fails_verify(self):
        store = self.h / ".agents/skills"
        for name, head in (("vis", ""), ("ondemand", "disable-model-invocation: true\n")):
            (store / name).mkdir(parents=True)
            (store / name / "SKILL.md").write_text(f"---\n{head}name: {name}\ndescription: d\n---\n")
        (self.h / ".agents/.skill-lock.json").write_text(json.dumps({"skills": {
            "vis": {"source": "o/r"}, "ondemand": {"source": "o/r"}}}))
        pack = mock.Mock(repo=lambda src: src == "o/r", owned=set())
        with mock.patch.object(K.Scope, "folders", lambda self: []), mock.patch.object(K.Scope, "locked",
                lambda self: json.loads(self.lock.read_text())["skills"]):
            problems = K.Scope(True).drift(pack)
        self.assertEqual([p for p in problems if "loads into every session" in p],
                         ["global: vis loads into every session; it is already on demand from kit. "
                          "Run: python3 packages.py remove vis -g"])

    def test_bigbang_mcp_start_check(self):
        ok = 'import sys,json; sys.stdin.readline(); print(json.dumps({"jsonrpc":"2.0","id":1,"result":{}}))'
        self.assertEqual(K.mcp_starts({"command": sys.executable, "args": ["-c", ok]}), "")
        bad = K.mcp_starts({"command": sys.executable, "args": ["-c", "raise SystemExit('No module named mcp.server.fastmcp')"]})
        self.assertIn("fastmcp", bad)

    def test_bigbang_bootstraps_a_project_without_git(self):
        target = self.h / "greenfield"
        target.mkdir()
        index = self.h / "index.json"
        pack = mock.Mock(domains={"core": ["mcp:example"]}, mcp={"example": "example-server"})
        real_run = K.run

        def run(cmd, **kwargs):
            if cmd[:3] == ["claude", "mcp", "add"]:
                root = kwargs["cwd"]
                self.assertEqual(root, target.resolve())
                self.assertTrue((root / ".git").is_dir())
                (root / ".mcp.json").write_text(json.dumps({"mcpServers": {
                    "example": {"command": "example-server"}}}))
                return subprocess.CompletedProcess(cmd, 0)
            if cmd[:3] == ["claude", "mcp", "remove"]:
                return subprocess.CompletedProcess(cmd, 0)
            return real_run(cmd, **kwargs)

        with (chdir(target), mock.patch.object(K, "INDEX", index),
              mock.patch.object(K, "main") as starter, mock.patch.object(K, "resolve", return_value={}),
              mock.patch.object(K, "run", side_effect=run), mock.patch.object(K.shutil, "which", return_value=True),
              mock.patch.object(K, "verify", return_value=0), mock.patch.object(K, "mcp_starts", return_value="") as start):
            self.assertEqual(K.bigbang(pack, [], True), 0)
            self.assertEqual(list(target.iterdir()), [])
            start.assert_not_called()
            starter.assert_called_once_with(["kit-starter-pack", "--dry-run"])
            index.touch()
            existing = target / "notes.md"
            existing.write_text("Existing requirements")
            self.assertEqual(K.bigbang(pack, [], False), 0)
            self.assertEqual(existing.read_text(), "Existing requirements")
            self.assertIn('[mcp_servers.example]', (target / ".codex/config.toml").read_text())
            start.assert_called_once_with({"command": "example-server"}, cwd=target.resolve())

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

    def test_codex_deduplication_preserves_manual_settings_and_is_reversible(self):
        home = self.h / "codex"
        home.mkdir()
        config = home / "config.toml"
        base = (f'[marketplaces.kit]\nsource_type = "local"\nsource = "{K.MARKET}"\n'
                '[plugins."pub@kit"]\nenabled = true\n')
        manual = self.h / ".agents/skills/pub-manual/SKILL.md"
        config.write_text(base + f'[[skills.config]]\npath = "{manual}"\nenabled = true\n')
        for name in ("owned", "manual", "foreign"):
            source = K.MARKET / "plugins/pub/skills" / name / "SKILL.md"
            source.parent.mkdir(parents=True)
            source.touch()
            shortcut = self.h / ".agents/skills" / f"pub-{name}" / "SKILL.md"
            shortcut.parent.mkdir(parents=True)
            shortcut.write_text(f"Open `~/{source.relative_to(self.h)}`.")
            if name != "foreign":
                (shortcut.parent / ".kit-stub").write_text("kit-portable-v1\n")
        with mock.patch.dict(K.os.environ, {"CODEX_HOME": str(home)}), mock.patch.object(K.shutil, "which", return_value="codex"):
            K.dedupe_codex()
            first = config.read_text()
            entries = tomllib.loads(first)["skills"]["config"]
            self.assertEqual([(Path(e["path"]).parent.name, e["enabled"]) for e in entries],
                             [("pub-manual", True), ("pub-owned", False)])
            K.dedupe_codex()
            self.assertEqual(config.read_text(), first)
            config.write_text(first.replace('[plugins."pub@kit"]\nenabled = true',
                                            '[plugins."pub@kit"]\nenabled = false'))
            K.dedupe_codex()
            self.assertEqual(tomllib.loads(config.read_text())["skills"]["config"],
                             [{"path": str(manual), "enabled": True}])

    def test_dev_sync_pushes_only_an_allowed_branch_and_links_after_push(self):
        repo, remote = self.h / "repo", self.h / "remote.git"
        subprocess.run(["git", "init", "-q", "-b", "dev", str(repo)], check=True)
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        git = ["git", "-C", str(repo)]
        for name in ("kit", "bigbang", "dev-sync", "new-skill"):
            skill = repo / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(f"---\nname: {name}\ndescription: Test skill.\n---\n")
        script = repo / "skills/kit/packages.py"
        script.touch()
        subprocess.run([*git, "add", "skills"], check=True)
        subprocess.run([*git, "-c", "user.name=Kit Test", "-c", "user.email=test@example.com",
                        "commit", "-qm", "initial"], check=True)
        subprocess.run([*git, "remote", "add", "origin", str(remote)], check=True)
        link = self.h / ".agents/skills/dev-sync"
        with mock.patch.object(K, "__file__", str(script)), mock.patch.object(K, "main", return_value=0) as refresh:
            subprocess.run([*git, "switch", "-qc", "main"], check=True)
            with self.assertRaises(SystemExit):
                K.dev_sync([], False)
            self.assertEqual(K.dev_sync(["--allow-main"], True), 0)
            refresh.assert_not_called()
            self.assertFalse(link.exists())
            subprocess.run([*git, "switch", "-q", "dev"], check=True)
            untracked = repo / "skills/new-skill/new.py"
            untracked.touch()
            with self.assertRaises(SystemExit):
                K.dev_sync([], False)
            refresh.assert_not_called()
            gemini = self.h / ".gemini/config/skills"
            (gemini / "kit").mkdir(parents=True)
            (gemini / "kit/.kit-stub").write_text("kit-portable-v1\n")
            stale = gemini / "stale-skill"
            stale.symlink_to(self.h / ".agents/skills/stale-skill")
            self.assertEqual(K.dev_sync(["--local-only"], False), 0)
            self.assertTrue((self.h / ".claude/skills/new-skill").is_symlink())
            self.assertTrue((self.h / ".cursor/skills/new-skill").is_symlink())
            self.assertTrue((gemini / "new-skill").is_symlink())
            self.assertTrue((gemini / "kit").is_symlink())
            self.assertFalse(stale.is_symlink())
            self.assertEqual(subprocess.check_output(["git", "-C", str(remote), "for-each-ref"]), b"")
            untracked.unlink()
            refresh.reset_mock()
            self.assertEqual(K.dev_sync([], False), 0)
            refresh.assert_called_once_with(["kit-starter-pack"])
            self.assertEqual(link.resolve(), (repo / "skills/dev-sync").resolve())
            pushed = subprocess.check_output(["git", "-C", str(remote), "for-each-ref",
                                              "--format=%(refname)", "refs/heads"], text=True)
            self.assertEqual(pushed.splitlines(), ["refs/heads/dev"])

    def test_repository_skills_must_remain_model_invocable(self):
        repo = self.h / "repo"
        script = repo / "skills/kit/packages.py"
        skill = repo / "skills/kit/SKILL.md"
        skill.parent.mkdir(parents=True)
        script.touch()
        skill.write_text("---\nname: kit\ndescription: Router.\ndisable-model-invocation: true\n---\n")
        with mock.patch.object(K, "__file__", str(script)):
            with self.assertRaises(SystemExit):
                K.repository_skills()
            skill.write_text("---\nname: kit\ndescription: Router.\n---\n")
            policy = repo / "skills/kit/agents/openai.yaml"
            policy.parent.mkdir()
            policy.write_text("policy:\n  allow_implicit_invocation: false\n")
            with self.assertRaises(SystemExit):
                K.repository_skills()
            policy.write_text("policy:\n  allow_implicit_invocation: true\n")
            self.assertEqual(list(K.repository_skills()), ["kit"])

    def test_portable_links_cursor_and_agent_coverage_gates_missing_agents(self):
        repo = self.h / "repo"
        script = repo / "skills/kit/packages.py"
        core = repo / "skills/kit/SKILL.md"
        core.parent.mkdir(parents=True)
        script.touch()
        core.write_text("---\nname: kit\ndescription: Router.\n---\n")
        skill = K.MARKET / "plugins/pub/skills/demo/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: demo\ndescription: Demo.\n---\n")
        (K.MARKET / ".claude-plugin").mkdir(parents=True)
        (K.MARKET / ".claude-plugin/marketplace.json").write_text(json.dumps({
            "plugins": [{"name": "pub", "source": "./plugins/pub"}]
        }))
        pack = mock.Mock(agents=["cursor", "zed", "antigravity"])
        with mock.patch.object(K, "__file__", str(script)), mock.patch.object(K.shutil, "which", return_value=None):
            problems, _ = K.agent_coverage(pack)
            self.assertTrue(any("cursor: missing core skill" in p for p in problems))
            self.assertTrue(any("cursor: missing 1/1 catalog aliases" in p for p in problems))
            for root in (self.h / ".agents/skills", self.h / ".cursor/skills", self.h / ".gemini/config/skills"):
                root.mkdir(parents=True, exist_ok=True)
                (root / "kit").symlink_to(core.parent, target_is_directory=True)
            K.portable()
            self.assertTrue((self.h / ".cursor/skills/pub-demo").is_symlink())
            self.assertTrue((self.h / ".gemini/config/skills/pub-demo").is_symlink())
            self.assertNotIn("disable-model-invocation", (self.h / ".agents/skills/pub-demo/SKILL.md").read_text())
            problems, summary = K.agent_coverage(pack)
            self.assertEqual(problems, [])
            self.assertEqual(summary, [
                "cursor=1/1 core, 1/1 aliases",
                "zed=1/1 core, 1/1 aliases",
                "antigravity=1/1 core, 1/1 aliases",
            ])


if __name__ == "__main__":
    unittest.main()
