import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI
from dogent.features.lessons import LessonIncident


class FakeLessonDrafter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def draft_from_incident(self, incident: LessonIncident, user_correction: str) -> str:
        self.calls.append(("incident", (incident.status, incident.summary, user_correction)))
        return "## From Incident\n\n### Problem\nx\n\n### Cause\ny\n\n### Correct Approach\nz\n"

    async def draft_from_free_text(self, free_text: str) -> str:
        self.calls.append(("free", free_text))
        return "## From Free Text\n\n### Problem\nx\n\n### Cause\ny\n\n### Correct Approach\nz\n"


class LearnCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_command_parses_args(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=Path(tmp),
                console=console,
                lesson_drafter=FakeLessonDrafter(),
                interactive_prompts=False,
            )
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/learn off")
            self.assertFalse(cli.auto_learn_enabled)

            await cli._handle_command("/learn on")
            self.assertTrue(cli.auto_learn_enabled)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_learn_appends_lesson_file(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            drafter = FakeLessonDrafter()
            cli = DogentCLI(
                root=root,
                console=console,
                lesson_drafter=drafter,
                interactive_prompts=False,
            )
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/learn use pathlib for paths")
            self.assertTrue(cli.paths.lessons_file.exists())
            text = cli.paths.lessons_file.read_text(encoding="utf-8")
            self.assertIn("## From Free Text", text)
            self.assertTrue(any(call[0] == "free" for call in drafter.calls))

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_learn_uses_incident_when_armed(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            drafter = FakeLessonDrafter()
            cli = DogentCLI(
                root=root,
                console=console,
                lesson_drafter=drafter,
                interactive_prompts=False,
            )
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli._armed_incident = LessonIncident(
                status="error",
                summary="boom",
                todos_markdown="- [pending] fix it",
            )

            await cli._handle_command("/learn do X not Y")
            self.assertIsNone(cli._armed_incident)
            self.assertTrue(any(call[0] == "incident" for call in drafter.calls))

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_learn_on_off_is_persisted_in_project_config(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=root,
                console=console,
                lesson_drafter=FakeLessonDrafter(),
                interactive_prompts=False,
            )
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/learn off")
            self.assertFalse(cli.auto_learn_enabled)
            cfg = cli.paths.config_file.read_text(encoding="utf-8")
            self.assertIn('"learn_auto": false', cfg.lower())

            cli2 = DogentCLI(
                root=root,
                console=console,
                lesson_drafter=FakeLessonDrafter(),
                interactive_prompts=False,
            )
            self.assertFalse(cli2.auto_learn_enabled)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_init_does_not_overwrite_learn_auto_setting(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(
                root=root,
                console=console,
                lesson_drafter=FakeLessonDrafter(),
                interactive_prompts=False,
            )
            cli._prompt_yes_no = mock.AsyncMock(return_value=True)  # type: ignore[assignment]

            await cli._handle_command("/learn off")
            await cli._handle_command("/init")
            cfg = cli.paths.config_file.read_text(encoding="utf-8").lower()
            self.assertIn('"learn_auto": false', cfg)
            self.assertIn('"web_profile"', cfg)
            self.assertIn('"llm_profile"', cfg)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

if __name__ == "__main__":
    unittest.main()
