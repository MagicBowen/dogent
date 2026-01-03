import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI, SelectionCancelled


class ConfirmationPromptTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_home = os.environ.get("HOME")
        self._tmp_home = tempfile.TemporaryDirectory()
        self._tmp_root = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self._tmp_home.name
        console = Console(record=True, force_terminal=False, color_system=None)
        self.cli = DogentCLI(
            root=Path(self._tmp_root.name),
            console=console,
            interactive_prompts=False,
        )

    async def asyncTearDown(self) -> None:
        if self._original_home is not None:
            os.environ["HOME"] = self._original_home
        else:
            os.environ.pop("HOME", None)
        self._tmp_home.cleanup()
        self._tmp_root.cleanup()

    async def test_yes_no_text_returns_true_for_yes(self) -> None:
        async def fake_read_input(*_args, **_kwargs):
            return "y"

        self.cli._read_input = fake_read_input  # type: ignore[assignment]
        result = await self.cli._prompt_yes_no(
            title="Test",
            message="",
            prompt="Proceed? [y/N] ",
            default=False,
            show_panel=False,
        )
        self.assertTrue(result)

    async def test_yes_no_text_esc_cancels(self) -> None:
        async def fake_read_input(*_args, **_kwargs):
            return "esc"

        self.cli._read_input = fake_read_input  # type: ignore[assignment]
        with self.assertRaises(SelectionCancelled):
            await self.cli._prompt_yes_no(
                title="Test",
                message="",
                prompt="Proceed? [y/N] ",
                default=False,
                show_panel=False,
            )

    async def test_confirm_overwrite_esc_cancels(self) -> None:
        async def fake_read_input(*_args, **_kwargs):
            return "esc"

        self.cli._read_input = fake_read_input  # type: ignore[assignment]
        target = Path(self._tmp_root.name) / "dogent.md"
        with self.assertRaises(SelectionCancelled):
            await self.cli._confirm_overwrite(target)

    async def test_confirm_save_lesson_esc_cancels(self) -> None:
        async def fake_read_input(*_args, **_kwargs):
            return "esc"

        self.cli._read_input = fake_read_input  # type: ignore[assignment]
        with self.assertRaises(SelectionCancelled):
            await self.cli._confirm_save_lesson()

    async def test_prompt_tool_permission_esc_denies(self) -> None:
        async def fake_read_input(*_args, **_kwargs):
            return "esc"

        self.cli._read_input = fake_read_input  # type: ignore[assignment]
        allowed = await self.cli._prompt_tool_permission(
            "Permission required: Read", "Read path outside workspace."
        )
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
