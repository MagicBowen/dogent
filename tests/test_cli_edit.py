import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI, EditorOutcome


class EditCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_creates_missing_file_when_confirmed(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(action="discard", text="")
            )

            await cli._cmd_edit("/edit notes.md")

            target = root / "notes.md"
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "")
            cli._open_multiline_editor.assert_awaited()
            args, kwargs = cli._open_multiline_editor.call_args
            self.assertEqual(args[0], "")
            self.assertEqual(kwargs["context"], "file_edit")
            self.assertEqual(kwargs["file_path"], target.resolve())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_edit_rejects_unsupported_extension(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            (root / "data.csv").write_text("1,2", encoding="utf-8")
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(action="discard", text="")
            )

            await cli._cmd_edit("/edit data.csv")

            cli._open_multiline_editor.assert_not_called()
            self.assertIn("Unsupported file type", console.file.getvalue())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_edit_submit_sends_prompt_with_file_reference(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            target = root / "note.md"
            target.write_text("Old", encoding="utf-8")
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(
                    action="submit", text="Updated", saved_path=target
                )
            )
            cli._prompt_file_usage = mock.AsyncMock(  # type: ignore[assignment]
                return_value="Please review"
            )
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._cmd_edit("/edit note.md")

            self.assertEqual(target.read_text(encoding="utf-8"), "Updated")
            cli._run_with_interrupt.assert_awaited()
            message, attachments = cli._run_with_interrupt.call_args.args[:2]
            self.assertEqual(message, "Please review [local file]: note.md")
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0].path, Path("note.md"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_edit_without_path_saves_new_file(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            target = root / "new.md"
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(action="save", text="Draft", saved_path=target)
            )

            await cli._cmd_edit("/edit")

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "Draft")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_edit_submit_sends_when_prompt_empty(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            target = root / "note.md"
            target.write_text("Old", encoding="utf-8")
            cli._open_multiline_editor = mock.AsyncMock(  # type: ignore[assignment]
                return_value=EditorOutcome(
                    action="submit", text="Updated", saved_path=target
                )
            )
            cli._prompt_file_usage = mock.AsyncMock(return_value="")  # type: ignore[assignment]
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._cmd_edit("/edit note.md")

            cli._run_with_interrupt.assert_awaited()
            message, attachments = cli._run_with_interrupt.call_args.args[:2]
            self.assertEqual(message, "[local file]: note.md")
            self.assertEqual(len(attachments), 1)
            self.assertEqual(attachments[0].path, Path("note.md"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
