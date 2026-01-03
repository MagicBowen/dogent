import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI, MultilineEditRequest, CLARIFICATION_SKIP


class FakeSession:
    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.defaults = []
        self.calls = 0

    async def prompt_async(self, _prompt: str, **kwargs):
        self.defaults.append(kwargs.get("default"))
        if self.calls >= len(self._responses):
            raise AssertionError("No more fake responses configured.")
        response = self._responses[self.calls]
        self.calls += 1
        return response


class MultilineEditorTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_input_uses_editor_result(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli.session = FakeSession([MultilineEditRequest("draft")])
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            cli._open_multiline_editor = mock.AsyncMock(return_value="edited")  # type: ignore[assignment]

            result = await cli._read_input(prompt="dogent> ", allow_multiline_editor=True)

            self.assertEqual(result, "edited")
            cli._open_multiline_editor.assert_awaited_once_with(  # type: ignore[union-attr]
                "draft", title="dogent>"
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_read_input_returns_to_prompt_after_cancel(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli.session = FakeSession([MultilineEditRequest("draft"), "final"])
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            cli._open_multiline_editor = mock.AsyncMock(return_value=None)  # type: ignore[assignment]

            result = await cli._read_input(prompt="dogent> ", allow_multiline_editor=True)

            self.assertEqual(result, "final")
            self.assertEqual(cli.session.defaults[1], "draft")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_freeform_inline_uses_editor_result(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            cli._run_freeform_inline_app = mock.AsyncMock(  # type: ignore[assignment]
                return_value=MultilineEditRequest("draft")
            )
            cli._open_multiline_editor = mock.AsyncMock(return_value="edited")  # type: ignore[assignment]

            result = await cli._prompt_freeform_answer_inline("Your answer: ")

            self.assertEqual(result, "edited")
            cli._open_multiline_editor.assert_awaited_once_with(  # type: ignore[union-attr]
                "draft", title="Your answer:"
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_freeform_inline_skip_on_editor_cancel(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._can_use_multiline_editor = mock.Mock(return_value=True)  # type: ignore[assignment]
            cli._run_freeform_inline_app = mock.AsyncMock(  # type: ignore[assignment]
                return_value=MultilineEditRequest("draft")
            )
            cli._open_multiline_editor = mock.AsyncMock(return_value=None)  # type: ignore[assignment]

            result = await cli._prompt_freeform_answer_inline(
                "Your answer: ", skip_on_editor_cancel=True
            )

            self.assertIs(result, CLARIFICATION_SKIP)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
