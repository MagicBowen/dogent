import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI
from dogent.todo import TodoItem


class ClearCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_command_resets_history_and_memory(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console)

            cli.history_manager._write_entries(  # type: ignore[attr-defined]
                [{"summary": "old entry", "status": "completed"}]
            )
            cli.paths.memory_file.parent.mkdir(parents=True, exist_ok=True)
            cli.paths.memory_file.write_text("temp notes", encoding="utf-8")
            cli.todo_manager.set_items([TodoItem(title="old todo")])

            await cli._cmd_clear("/clear")

            self.assertEqual(cli.history_manager.read_entries(), [])
            self.assertFalse(cli.paths.memory_file.exists())
            self.assertEqual(cli.todo_manager.items, [])

            output = console.export_text()
            self.assertIn("Cleared", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
