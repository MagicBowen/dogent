import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "prepare_claude_plugin_skills.py"
)
SPEC = importlib.util.spec_from_file_location("prepare_claude_plugin_skills", SCRIPT_PATH)
prepare_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = prepare_module
SPEC.loader.exec_module(prepare_module)


class PrepareClaudePluginSkillsTests(unittest.TestCase):
    def test_copies_selected_skills_and_removes_stale_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ["pptx"])
            self._write_skill(root, "pptx")
            self._write_skill(root, "skill-creator")
            stale = root / "dogent/plugins/claude/skills/stale/SKILL.md"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("old", encoding="utf-8")

            messages: list[str] = []
            copied = prepare_module.prepare_skills(
                root / "dogent/plugins/claude/skills_manifest.json",
                root,
                runner=self._runner(),
                out=messages.append,
            )

            self.assertEqual(["pptx"], copied)
            self.assertTrue((root / "dogent/plugins/claude/skills/pptx/SKILL.md").exists())
            self.assertFalse((root / "dogent/plugins/claude/skills/stale").exists())
            self.assertFalse(
                (root / "dogent/plugins/claude/skills/skill-creator").exists()
            )
            self.assertIn("Claude skills source commit: abc123", messages)
            self.assertIn("Copied Claude plugin skills: pptx", messages)

    def test_update_failure_warns_and_uses_current_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ["pptx"])
            self._write_skill(root, "pptx")

            messages: list[str] = []
            prepare_module.prepare_skills(
                root / "dogent/plugins/claude/skills_manifest.json",
                root,
                runner=self._runner(update_returncode=1, update_stderr="network down"),
                out=messages.append,
            )

            self.assertIn(
                "Warning: failed to update claude/skills submodule; continuing with current checkout.",
                messages,
            )
            self.assertIn("network down", messages)
            self.assertTrue((root / "dogent/plugins/claude/skills/pptx/SKILL.md").exists())

    def test_missing_requested_skill_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ["pptx"])
            (root / "claude/skills/skills").mkdir(parents=True)

            with self.assertRaisesRegex(
                prepare_module.PrepareError, "Requested skill not found"
            ):
                prepare_module.prepare_skills(
                    root / "dogent/plugins/claude/skills_manifest.json",
                    root,
                    runner=self._runner(),
                    out=lambda _message: None,
                )

    def test_missing_source_fails_after_update_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ["pptx"])

            with self.assertRaisesRegex(
                prepare_module.PrepareError, "Skill source directory not found"
            ):
                prepare_module.prepare_skills(
                    root / "dogent/plugins/claude/skills_manifest.json",
                    root,
                    runner=self._runner(),
                    out=lambda _message: None,
                )

    def test_invalid_skill_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_manifest(root, ["../bad"])

            with self.assertRaisesRegex(prepare_module.PrepareError, "Invalid skill name"):
                prepare_module.load_manifest(
                    root / "dogent/plugins/claude/skills_manifest.json", root
                )

    def _write_manifest(self, root: Path, skills: list[str]) -> None:
        path = root / "dogent/plugins/claude/skills_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "source": "claude/skills/skills",
                    "target": "dogent/plugins/claude/skills",
                    "skills": skills,
                }
            ),
            encoding="utf-8",
        )

    def _write_skill(self, root: Path, name: str) -> None:
        skill = root / "claude/skills/skills" / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        (skill / "LICENSE.txt").write_text("license\n", encoding="utf-8")

    def _runner(
        self, *, update_returncode: int = 0, update_stderr: str = ""
    ) -> prepare_module.CommandRunner:
        def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            if args[:3] == ["git", "submodule", "update"]:
                return subprocess.CompletedProcess(
                    args, update_returncode, "", update_stderr
                )
            if args[:3] == ["git", "-C", "claude/skills"]:
                return subprocess.CompletedProcess(args, 0, "abc123\n", "")
            return subprocess.CompletedProcess(args, 1, "", "unexpected command")

        return run


if __name__ == "__main__":
    unittest.main()
