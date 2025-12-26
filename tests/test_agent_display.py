import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from claude_agent_sdk import TextBlock, ToolResultBlock
from rich.console import Console

from dogent.agent import AgentRunner, NEEDS_CLARIFICATION_SENTINEL
from dogent.config import ConfigManager
from dogent.history import HistoryManager
from dogent.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.todo import TodoItem, TodoManager


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

    def test_todos_clear_after_normal_completion(self) -> None:
        class DummyResult:
            result = "done"
            total_cost_usd = 0.0
            duration_ms = 1
            duration_api_ms = 1

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            todo.set_items([TodoItem(title="old", status="done")])
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )

            runner._handle_result(DummyResult())  # type: ignore[arg-type]
            self.assertEqual(todo.items, [])

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_unfinished_todos_marks_run_failed_and_preserves_todos(self) -> None:
        class DummyResult:
            result = "ok"
            is_error = False
            total_cost_usd = 0.0
            duration_ms = 1
            duration_api_ms = 1

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            todo.set_items([TodoItem(title="step 1", status="pending")])
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )

            runner._handle_result(DummyResult())  # type: ignore[arg-type]
            self.assertNotEqual(todo.items, [])
            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "error")
            output = console.file.getvalue()
            self.assertIn("Failed", output)

            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "error")

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_needs_clarification_status_when_sentinel_present(self) -> None:
        class DummyResult:
            result = "Awaiting input"
            is_error = False
            total_cost_usd = 0.0
            duration_ms = 1
            duration_api_ms = 1

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            todo.set_items([TodoItem(title="step 1", status="pending")])
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )

            question = f"Need a title?\n{NEEDS_CLARIFICATION_SENTINEL}"
            runner._handle_assistant_message(SimpleNamespace(content=[TextBlock(question)]))
            runner._handle_result(DummyResult())  # type: ignore[arg-type]

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "needs_clarification")
            self.assertNotEqual(todo.items, [])
            output = console.file.getvalue()
            self.assertIn("Needs clarification", output)
            self.assertNotIn(NEEDS_CLARIFICATION_SENTINEL, output)

            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "needs_clarification")

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
