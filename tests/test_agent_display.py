import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from claude_agent_sdk import AssistantMessage, ToolResultBlock, ToolUseBlock
from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.core.history import HistoryManager
from dogent.config.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.core.todo import TodoItem, TodoManager


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

    def test_needs_clarification_status_when_ui_request_present(self) -> None:
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

            tool_use = ToolUseBlock(
                id="1",
                name="mcp__dogent__ui_request",
                input={
                    "response_type": "clarification",
                    "title": "Need a title?",
                    "questions": [
                        {
                            "id": "title",
                            "question": "Title?",
                            "options": [{"label": "A", "value": "a"}],
                        }
                    ],
                },
            )
            runner._handle_assistant_message(
                AssistantMessage(content=[tool_use], model="unit")
            )
            runner._handle_result(DummyResult())  # type: ignore[arg-type]

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "needs_clarification")
            self.assertNotEqual(todo.items, [])
            output = console.file.getvalue()
            self.assertIn("Needs clarification", output)

            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "needs_clarification")

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_ui_request_accepts_type_and_oneof_payload(self) -> None:
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

            payload = {
                "title": "Resume - Missing Info",
                "preface": "Need details.",
                "questions": [
                    {
                        "id": "role",
                        "question": "Target role?",
                        "options": [{"label": "A", "value": "A"}],
                    }
                ],
            }
            tool_use = ToolUseBlock(
                id="1",
                name="mcp__dogent__ui_request",
                input={"type": "clarification", "oneOf": json.dumps(payload)},
            )
            runner._handle_assistant_message(
                AssistantMessage(content=[tool_use], model="unit")
            )
            self.assertTrue(runner._needs_clarification)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_result_clarification_overrides_error(self) -> None:
        class DummyResult:
            result = "error"
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

            tool_use = ToolUseBlock(
                id="1",
                name="mcp__dogent__ui_request",
                input={
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
                },
            )
            runner._handle_assistant_message(
                AssistantMessage(content=[tool_use], model="unit")
            )
            runner._handle_result(DummyResult())  # type: ignore[arg-type]

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "needs_clarification")
            output = console.file.getvalue()
            self.assertIn("Needs clarification", output)
            self.assertNotIn("Failed", output)

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
            todo.set_items(
                [TodoItem(title="pending task", status="pending")],
                source="TodoWrite",
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
            self.assertEqual(todo.items, [])
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

    async def test_wait_indicator_skips_when_permission_prompt_active(self) -> None:
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
            runner._permission_prompt_active = True
            await runner._start_wait_indicator()
            self.assertIsNone(runner._wait_indicator)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class AgentPermissionAbortTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_permission_denied_aborts_and_clears_todos(self) -> None:
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
            todo.set_items(
                [TodoItem(title="pending task", status="pending")],
                source="TodoWrite",
            )
            await runner._handle_permission_denied("Read path outside workspace.")
            self.assertTrue(runner._abort_requested)
            self.assertEqual(todo.items, [])
            entries = history.read_entries()
            self.assertEqual(entries[-1]["status"], "aborted")

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

    async def test_send_message_skips_recording_user_input_when_disabled(self) -> None:
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
            with mock.patch.object(
                runner, "_stream_responses", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_safe_disconnect", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_start_wait_indicator", new=mock.AsyncMock()
            ), mock.patch.object(
                runner, "_stop_wait_indicator", new=mock.AsyncMock()
            ):
                await runner.send_message(
                    "Outline approved, continue.",
                    [],
                    config_override=None,
                    record_user_input=False,
                )
            entries = history.read_entries()
            self.assertIsNone(entries[-1].get("user_input"))
            self.assertEqual(history.prompt_history_strings(limit=30), [])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_invalid_ui_request_logs_error(self) -> None:
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
            tool_use = ToolUseBlock(
                id="1",
                name="mcp__dogent__ui_request",
                input={"response_type": "clarification", "title": "Need"},
            )
            message = AssistantMessage(content=[tool_use], model="test")
            runner._handle_assistant_message(message)
            output = console.file.getvalue()
            self.assertIn("Invalid clarification payload", output)
            self.assertFalse(runner._needs_clarification)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
