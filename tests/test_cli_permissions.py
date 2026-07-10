import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from rich.console import Console

from dogent.agent import HumanPromptRequest
from dogent.cli import DogentCLI


class PermissionPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_dedicated_prompt_preserves_area_during_stdout_writes(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            cli = DogentCLI(
                root=Path(tmp),
                console=Console(record=True, force_terminal=False, color_system=None),
                interactive_prompts=False,
            )
            app = SimpleNamespace(run_async=mock.AsyncMock(return_value=2))
            stdout_context = mock.MagicMock()

            with mock.patch(
                "dogent.cli.app.patch_stdout", return_value=stdout_context
            ) as patched_stdout:
                result = await cli._run_dedicated_prompt(app)

            self.assertEqual(result, 2)
            patched_stdout.assert_called_once_with(raw=True)
            stdout_context.__enter__.assert_called_once()
            stdout_context.__exit__.assert_called_once()
            app.run_async.assert_awaited_once()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_inline_choice_runs_inside_dedicated_frame(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            cli = DogentCLI(
                root=Path(tmp),
                console=Console(record=True, force_terminal=False, color_system=None),
                interactive_prompts=True,
            )
            with mock.patch.object(
                cli, "_run_dedicated_prompt", new=mock.AsyncMock(return_value=1)
            ) as run_prompt:
                result = await cli._prompt_inline_choice(
                    title="Permission required · Sub-agent agent-12",
                    prompt_text="Choose",
                    options=["Allow", "Deny"],
                    status_text="Active: Sub-agent agent-12 | 2 queued requests",
                )

            self.assertEqual(result, 1)
            app = run_prompt.await_args.args[0]
            self.assertEqual(type(app.layout.container).__name__, "HSplit")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_prompt_handles_none_response(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            async def fake_read_input(*_args, **_kwargs):
                return None

            cli._read_input = fake_read_input  # type: ignore[assignment]
            decision = await cli._prompt_tool_permission(
                HumanPromptRequest(
                    kind="permission",
                    title="Permission required · Main agent",
                    message="Read path outside workspace.",
                )
            )
            self.assertTrue(decision.allow)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_prompt_remember_option(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            async def fake_read_input(*_args, **_kwargs):
                return "2"

            cli._read_input = fake_read_input  # type: ignore[assignment]
            decision = await cli._prompt_tool_permission(
                HumanPromptRequest(
                    kind="permission",
                    title="Permission required · Main agent",
                    message="Modify protected file.",
                )
            )
            self.assertTrue(decision.allow)
            self.assertTrue(decision.remember)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
