import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock
from rich.console import Console

from dogent.agent import AgentRunner, NEEDS_CLARIFICATION_SENTINEL
from dogent.clarification import CLARIFICATION_JSON_TAG
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

    def test_unfinished_todos_marks_run_awaiting_input_and_preserves_todos(self) -> None:
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
            self.assertEqual(runner.last_outcome.status, "awaiting_input")
            output = console.file.getvalue()
            self.assertIn("Awaiting input", output)

            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "awaiting_input")

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

    def test_result_clarification_overrides_error(self) -> None:
        payload = {
            "response_type": "clarification",
            "title": "Need details",
            "questions": [
                {
                    "id": "audience",
                    "question": "Target audience?",
                    "options": [{"label": "Team", "value": "team"}],
                    "allow_freeform": False,
                }
            ],
        }

        class DummyResult:
            result = f"{CLARIFICATION_JSON_TAG}\n{json.dumps(payload)}"
            is_error = True
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

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "needs_clarification")
            self.assertIsNotNone(runner._clarification_payload)
            output = console.file.getvalue()
            self.assertIn("Needs clarification", output)
            self.assertNotIn("Failed", output)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_result_sentinel_sets_clarification_status(self) -> None:
        class DummyResult:
            result = f"Need details\n{NEEDS_CLARIFICATION_SENTINEL}"
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

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "needs_clarification")
            output = console.file.getvalue()
            self.assertIn("Needs clarification", output)
            self.assertNotIn(NEEDS_CLARIFICATION_SENTINEL, output)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_result_skips_clarification_when_already_seen(self) -> None:
        payload = {
            "response_type": "clarification",
            "title": "Need details",
            "questions": [
                {
                    "id": "audience",
                    "question": "Target audience?",
                    "options": [{"label": "Team", "value": "team"}],
                    "allow_freeform": False,
                }
            ],
        }

        class DummyResult:
            result = f"{CLARIFICATION_JSON_TAG}\n{json.dumps(payload)}"
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
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )
            runner._clarification_seen = True
            runner._needs_clarification = False

            with mock.patch.object(runner, "_process_clarification_text") as process:
                runner._handle_result(DummyResult())  # type: ignore[arg-type]
                process.assert_not_called()

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_finalize_aborted_records_status(self) -> None:
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

            runner._aborted_reason = "User denied permission: Read path outside workspace."
            runner._finalize_aborted()

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "aborted")
            output = console.file.getvalue()
            self.assertIn("Aborted", output)
            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "aborted")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class AgentResetTests(unittest.IsolatedAsyncioTestCase):
    async def test_reset_stops_wait_indicator(self) -> None:
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

            runner._stop_wait_indicator = mock.AsyncMock()  # type: ignore[assignment]
            await runner.reset()
            runner._stop_wait_indicator.assert_awaited_once()

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class AgentClarificationDisplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_clarification_answers_not_shortened(self) -> None:
        class DummyClient:
            def __init__(self) -> None:
                self.options = SimpleNamespace(system_prompt="")

            async def query(self, _prompt: str) -> None:
                return None

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
            runner._client = DummyClient()
            message = "Clarification answers:\n" + ("A" * 260) + "TAILMARKER"
            with mock.patch.object(
                runner, "_stream_responses", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_safe_disconnect", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_start_wait_indicator", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_stop_wait_indicator", new=mock.AsyncMock()
            ):
                await runner.send_message(message, [], config_override=None)
            output = console.file.getvalue()
            self.assertIn("TAILMARKER", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_invalid_clarification_payload_shows_original_text(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(
                file=io.StringIO(), force_terminal=True, color_system=None, width=200
            )
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
            text = f"{CLARIFICATION_JSON_TAG}\n{{\"title\":\"Need\",\"questions\":[]}}"
            message = AssistantMessage(content=[TextBlock(text)], model="test")
            runner._handle_assistant_message(message)
            output = console.file.getvalue()
            self.assertIn("Clarification payload invalid", output)
            self.assertIn(CLARIFICATION_JSON_TAG, output)
            self.assertIn("{\"title\":\"Need\",\"questions\":[]}", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
