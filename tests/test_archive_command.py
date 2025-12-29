import json
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI


class ArchiveCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_archive_history_creates_archive_and_clears(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console)

            entries = [{"summary": "old entry", "status": "completed"}]
            cli.history_manager._write_entries(entries)  # type: ignore[attr-defined]

            await cli._cmd_archive("/archive history")

            self.assertEqual(cli.history_manager.read_entries(), [])
            archives_dir = cli.paths.archives_dir
            files = list(archives_dir.glob("history_*.json"))
            self.assertEqual(1, len(files))
            archived_entries = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(entries, archived_entries)
            output = console.export_text()
            self.assertIn("Archived", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_archive_lessons_creates_archive_and_resets(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console)

            lessons_content = "# Lessons\n\n## L1\n\nNote\n"
            cli.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            cli.paths.lessons_file.write_text(lessons_content, encoding="utf-8")

            await cli._cmd_archive("/archive lessons")

            archives_dir = cli.paths.archives_dir
            files = list(archives_dir.glob("lessons_*.md"))
            self.assertEqual(1, len(files))
            archived_text = files[0].read_text(encoding="utf-8")
            self.assertEqual(lessons_content, archived_text)
            self.assertEqual(
                "# Lessons\n\n",
                cli.paths.lessons_file.read_text(encoding="utf-8"),
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_archive_skips_empty_targets(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console)

            cli.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            cli.paths.lessons_file.write_text("# Lessons\n\n", encoding="utf-8")

            await cli._cmd_archive("/archive")

            self.assertFalse(cli.paths.archives_dir.exists())
            output = console.export_text()
            self.assertIn("Nothing to archive", output)
            self.assertIn("history (empty)", output)
            self.assertIn("lessons (empty)", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
