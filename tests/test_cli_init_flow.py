import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI, SelectionCancelled
from dogent.cli.wizard import WizardResult


class InitFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_home = os.environ.get("HOME")
        self._tmp_home = tempfile.TemporaryDirectory()
        self._tmp_root = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self._tmp_home.name
        console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
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

    async def test_init_prompt_can_start_writing(self) -> None:
        wizard_result = WizardResult(
            doc_template=None,
            primary_language=None,
            dogent_md="# Test\n",
        )
        self.cli.init_wizard.generate = mock.AsyncMock(return_value=wizard_result)
        self.cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
        self.cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

        await self.cli._run_init("/init write resume", force_wizard=True)

        expected = self.cli._build_start_writing_prompt("write resume")
        self.cli._run_with_interrupt.assert_awaited_once_with(expected, [])

    async def test_build_start_writing_prompt_format(self) -> None:
        prompt = self.cli._build_start_writing_prompt("draft a resume")
        self.assertIn("initialized the current dogent project", prompt)
        self.assertIn("draft a resume", prompt)

    async def test_auto_init_decline_continues(self) -> None:
        self.cli._prompt_yes_no = mock.AsyncMock(return_value=False)  # type: ignore[assignment]
        self.cli._run_init = mock.AsyncMock()  # type: ignore[assignment]
        should_continue = await self.cli._maybe_auto_init_for_request("hello")
        self.assertTrue(should_continue)
        self.cli._run_init.assert_not_called()

    async def test_auto_init_accept_runs_wizard(self) -> None:
        self.cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
        self.cli._run_init = mock.AsyncMock()  # type: ignore[assignment]
        should_continue = await self.cli._maybe_auto_init_for_request("hello")
        self.assertFalse(should_continue)
        self.cli._run_init.assert_awaited_once()

    async def test_auto_init_esc_cancels(self) -> None:
        self.cli._prompt_yes_no = mock.AsyncMock(  # type: ignore[assignment]
            side_effect=SelectionCancelled
        )
        self.cli._run_init = mock.AsyncMock()  # type: ignore[assignment]
        should_continue = await self.cli._maybe_auto_init_for_request("hello")
        self.assertFalse(should_continue)
        self.cli._run_init.assert_not_called()

    async def test_auto_init_prompt_defaults_yes(self) -> None:
        prompt_mock = mock.AsyncMock(return_value=False)
        self.cli._prompt_yes_no = prompt_mock  # type: ignore[assignment]
        self.cli._run_init = mock.AsyncMock()  # type: ignore[assignment]

        await self.cli._maybe_auto_init_for_request("hello")

        _, kwargs = prompt_mock.call_args
        self.assertTrue(kwargs["default"])
        self.assertIn("[Y/n]", kwargs["prompt"])


if __name__ == "__main__":
    unittest.main()
