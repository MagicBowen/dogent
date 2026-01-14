import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI


class PermissionPromptTests(unittest.IsolatedAsyncioTestCase):
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
                "Permission required: Read", "Read path outside workspace."
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
                "Permission required: Write", "Modify protected file."
            )
            self.assertTrue(decision.allow)
            self.assertTrue(decision.remember)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
