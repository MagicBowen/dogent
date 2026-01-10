import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI
from dogent.cli.claude_commands import load_claude_commands


class ClaudeCommandsTests(unittest.TestCase):
    def test_loads_project_and_user_commands(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            user_cmds = Path(tmp_home) / ".claude" / "commands"
            user_cmds.mkdir(parents=True, exist_ok=True)
            (user_cmds / "review.md").write_text(
                "---\ndescription: Review code\n---\nBody",
                encoding="utf-8",
            )

            project_cmds = Path(tmp) / ".claude" / "commands"
            project_cmds.mkdir(parents=True, exist_ok=True)
            (project_cmds / "refactor.md").write_text("Refactor code", encoding="utf-8")

            specs = load_claude_commands(Path(tmp))
            names = {spec.name: spec.description for spec in specs}
            canonicals = {spec.name: spec.canonical for spec in specs}
            self.assertEqual(names.get("/claude:review"), "Review code")
            self.assertEqual(names.get("/claude:refactor"), "Refactor code")
            self.assertEqual(canonicals.get("/claude:review"), "/review")
            self.assertEqual(canonicals.get("/claude:refactor"), "/refactor")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_command_registers_with_prefix(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            project_cmds = Path(tmp) / ".claude" / "commands"
            project_cmds.mkdir(parents=True, exist_ok=True)
            (project_cmds / "help.md").write_text("Help from Claude", encoding="utf-8")

            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            self.assertIsNotNone(cli.registry.get("/help"))
            self.assertIsNotNone(cli.registry.get("/claude:help"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_plugin_command_is_registered(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            plugin_root = root / "plugins" / "demo"
            (plugin_root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            (plugin_root / ".claude-plugin" / "plugin.json").write_text(
                '{"name": "demo-plugin"}',
                encoding="utf-8",
            )
            (plugin_root / "commands").mkdir(parents=True, exist_ok=True)
            (plugin_root / "commands" / "greet.md").write_text(
                "Say hello",
                encoding="utf-8",
            )

            dogent_dir = root / ".dogent"
            dogent_dir.mkdir(parents=True, exist_ok=True)
            (dogent_dir / "dogent.json").write_text(
                '{"claude_plugins": ["plugins/demo"]}',
                encoding="utf-8",
            )

            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)

            self.assertIsNotNone(cli.registry.get("/claude:demo-plugin:greet"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
