import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI


class CommandHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_command_records_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HOME": tmp_home}, clear=False), mock.patch(
                "pathlib.Path.home", return_value=Path(tmp_home)
            ):
                console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
                cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

                await cli._handle_command("/help")

                entries = cli.history_manager.read_entries()
                self.assertTrue(entries)
                self.assertEqual(entries[-1].get("status"), "command")
                self.assertEqual(entries[-1].get("prompt"), "/help")


if __name__ == "__main__":
    unittest.main()
