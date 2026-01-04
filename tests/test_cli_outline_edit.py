import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI, EditorOutcome
from dogent.outline_edit import OutlineEditPayload


class OutlineEditCliTests(unittest.IsolatedAsyncioTestCase):
    async def test_collect_outline_edit_submit_with_save_note(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            payload = OutlineEditPayload(title="Review", outline_text="Original")
            saved_path = root / "outline.md"
            cli._prompt_outline_action = mock.AsyncMock(return_value="edit")  # type: ignore[assignment]
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(action="submit", text="Edited", saved_path=saved_path)
            )
            message, abort_reason = await cli._collect_outline_edit(payload)
            self.assertIsNone(abort_reason)
            self.assertIn("Saved file: outline.md", message)
            self.assertIn("```markdown", message)
            self.assertIn("Edited", message)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_collect_outline_edit_discard_uses_original(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            payload = OutlineEditPayload(title="Review", outline_text="Original")
            cli._prompt_outline_action = mock.AsyncMock(return_value="edit")  # type: ignore[assignment]
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(action="discard", text="Edited")
            )
            message, abort_reason = await cli._collect_outline_edit(payload)
            self.assertIsNone(abort_reason)
            self.assertIn("Original", message)
            self.assertIn("```markdown", message)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_collect_outline_edit_adopt(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            payload = OutlineEditPayload(title="Review", outline_text="Original")
            cli._prompt_outline_action = mock.AsyncMock(return_value="adopt")  # type: ignore[assignment]
            message, abort_reason = await cli._collect_outline_edit(payload)
            self.assertIsNone(abort_reason)
            self.assertEqual(message, "Outline approved, continue.")
            output = console.file.getvalue()
            self.assertIn("Review", output)
            self.assertIn("Original", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_collect_outline_edit_save_pauses(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            payload = OutlineEditPayload(title="Review", outline_text="Original")
            cli._prompt_outline_action = mock.AsyncMock(return_value="save")  # type: ignore[assignment]
            cli._save_outline_for_edit = mock.AsyncMock(  # type: ignore[assignment]
                return_value=root / "outline_20250101_000000.md"
            )
            message, abort_reason = await cli._collect_outline_edit(payload)
            self.assertIsNone(message)
            self.assertEqual(abort_reason, "paused")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_save_outline_auto_filename(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._prompt_outline_save_mode = mock.AsyncMock(  # type: ignore[assignment]
                return_value="auto"
            )
            saved_path = await cli._save_outline_for_edit("Outline")
            self.assertIsNotNone(saved_path)
            if saved_path is None:
                return
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.read_text(encoding="utf-8"), "Outline")
            self.assertEqual(saved_path.parent, root)
            self.assertTrue(saved_path.name.startswith("outline_"))
            self.assertTrue(saved_path.name.endswith(".md"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_save_outline_manual_filename(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._prompt_outline_save_mode = mock.AsyncMock(  # type: ignore[assignment]
                return_value="manual"
            )
            cli._prompt_outline_filename = mock.AsyncMock(  # type: ignore[assignment]
                return_value="custom_outline.md"
            )
            saved_path = await cli._save_outline_for_edit("Outline")
            self.assertIsNotNone(saved_path)
            if saved_path is None:
                return
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.read_text(encoding="utf-8"), "Outline")
            self.assertEqual(saved_path, root / "custom_outline.md")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
