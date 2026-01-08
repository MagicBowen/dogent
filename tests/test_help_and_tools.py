import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.agent import AgentRunner
from dogent.cli import DogentCLI
from dogent.core.todo import TodoManager


class DummyBlock:
    def __init__(self, content, is_error=False) -> None:
        self.content = content
        self.is_error = is_error
        self.tool_use_id = "id"


class HelpAndToolDisplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_command_shows_usage(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(record=True, force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            await cli._cmd_help("/help")

            output = console.export_text()
            self.assertIn("Model", output)
            self.assertIn("/help", output)
            self.assertIn("Commands", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_web_tool_result_states_success_and_failure(self) -> None:
        console = Console(record=True, force_terminal=False, color_system=None)
        runner = AgentRunner(
            config=None,  # type: ignore[arg-type]
            prompt_builder=None,  # type: ignore[arg-type]
            todo_manager=TodoManager(console=console),
            history=None,  # type: ignore[arg-type]
            console=console,
        )

        runner._log_tool_result("WebFetch", DummyBlock("Fetched page"), summary=None)
        runner._log_tool_result("WebSearch", DummyBlock("timeout", is_error=True), summary=None)

        output = console.export_text()
        self.assertIn("Success: Fetched page", output)
        self.assertIn("Failed: timeout", output)

    def test_non_web_tool_result_states_success_and_failure(self) -> None:
        console = Console(record=True, force_terminal=False, color_system=None)
        runner = AgentRunner(
            config=None,  # type: ignore[arg-type]
            prompt_builder=None,  # type: ignore[arg-type]
            todo_manager=TodoManager(console=console),
            history=None,  # type: ignore[arg-type]
            console=console,
        )

        runner._log_tool_result("Bash", DummyBlock("Command completed"), summary=None)
        runner._log_tool_result(
            "Bash",
            DummyBlock([{"type": "text", "text": "permission denied"}], is_error=True),
            summary=None,
        )

        output = console.export_text()
        self.assertIn("Success: Command completed", output)
        self.assertIn("Failed: permission denied", output)

    def test_web_search_error_displays_message_blocks(self) -> None:
        console = Console(record=True, force_terminal=False, color_system=None)
        runner = AgentRunner(
            config=None,  # type: ignore[arg-type]
            prompt_builder=None,  # type: ignore[arg-type]
            todo_manager=TodoManager(console=console),
            history=None,  # type: ignore[arg-type]
            console=console,
        )

        runner._log_tool_result(
            "WebSearch",
            DummyBlock([{"type": "text", "text": "search quota exceeded"}], is_error=True),
            summary=None,
        )

        output = console.export_text()
        self.assertIn("Failed: search quota exceeded", output)

    def test_custom_web_tools_display_friendly_names(self) -> None:
        console = Console(record=True, force_terminal=False, color_system=None)
        runner = AgentRunner(
            config=None,  # type: ignore[arg-type]
            prompt_builder=None,  # type: ignore[arg-type]
            todo_manager=TodoManager(console=console),
            history=None,  # type: ignore[arg-type]
            console=console,
        )

        runner._log_tool_result("mcp__dogent__web_search", DummyBlock("ok"), summary=None)
        output = console.export_text()
        self.assertIn("dogent_web_search", output)
        self.assertNotIn("mcp__dogent__web_search", output)


if __name__ == "__main__":
    unittest.main()
