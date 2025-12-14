import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI


class HistoryCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_command_shows_recent_entries_and_todos(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console)

            entries = [
                {
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "status": "completed",
                    "summary": "Initial pass",
                    "todos": [{"title": "old", "status": "done"}],
                },
                {
                    "timestamp": "2024-02-02T12:00:00+00:00",
                    "status": "completed",
                    "summary": "Latest summary",
                    "todos": [{"title": "latest todo", "status": "doing"}],
                },
            ]
            cli.history_manager._write_entries(entries)  # type: ignore[attr-defined]

            await cli._cmd_history("/history")

            output = console.export_text()
            self.assertIn("Latest summary", output)
            self.assertIn("latest todo", output)
            self.assertIn("History", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
