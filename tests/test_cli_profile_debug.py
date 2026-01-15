import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI


class ProfileDebugCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_llm_updates_config_and_resets(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps(
                    {"llm_profiles": {"alpha": {"ANTHROPIC_AUTH_TOKEN": "token"}}}
                ),
                encoding="utf-8",
            )

            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=Path(tmp),
                console=console,
                interactive_prompts=False,
            )
            cli._confirm_dogent_file_update = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli.agent.reset = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command("/profile llm alpha")
            data = json.loads(cli.paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("llm_profile"), "alpha")
            cli.agent.reset.assert_awaited()

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_profile_image_updates_config_and_resets(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps({"image_profiles": {"glm-image": {"api_key": "token"}}}),
                encoding="utf-8",
            )

            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=Path(tmp),
                console=console,
                interactive_prompts=False,
            )
            cli._confirm_dogent_file_update = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli.agent.reset = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command("/profile image glm-image")
            data = json.loads(cli.paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("image_profile"), "glm-image")
            cli.agent.reset.assert_awaited()

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_debug_arg_session_errors(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=Path(tmp),
                console=console,
                interactive_prompts=False,
            )
            cli._confirm_dogent_file_update = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/debug session-errors")
            data = json.loads(cli.paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("debug"), ["session", "error"])

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_debug_off_sets_null(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=Path(tmp),
                console=console,
                interactive_prompts=False,
            )
            cli._confirm_dogent_file_update = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/debug off")
            data = json.loads(cli.paths.config_file.read_text(encoding="utf-8"))
            self.assertIsNone(data.get("debug"))

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
