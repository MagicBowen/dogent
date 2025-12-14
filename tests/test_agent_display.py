import io
import os
import tempfile
import unittest
from pathlib import Path

from claude_agent_sdk import ToolResultBlock
from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.history import HistoryManager
from dogent.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.todo import TodoManager


class AgentDisplayTests(unittest.TestCase):
    def test_tool_result_error_shows_reason(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )
            block = ToolResultBlock(tool_use_id="1", content="timeout", is_error=True)
            runner._log_tool_result("WebFetch", block)
            output = console.file.getvalue()
            self.assertIn("Failed WebFetch", output)
            self.assertIn("Failed: timeout", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
