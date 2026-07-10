import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
from claude_agent_sdk.types import (
    StreamEvent,
    TaskNotificationMessage,
    TaskProgressMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
)
from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.core.todo import TodoManager
from dogent.prompts import PromptBuilder


class AgentRuntimeTests(unittest.TestCase):
    def _make_runner(self, root: Path, console: Console) -> AgentRunner:
        paths = DogentPaths(root)
        todo = TodoManager(console=console)
        history = HistoryManager(paths)
        builder = PromptBuilder(paths, todo, history)
        return AgentRunner(
            config=ConfigManager(paths, console=console),
            prompt_builder=builder,
            todo_manager=todo,
            history=history,
            console=console,
        )

    def test_handle_result_renders_usage_lines(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)

            runner._handle_result(
                ResultMessage(
                    subtype="success",
                    duration_ms=12,
                    duration_api_ms=8,
                    is_error=False,
                    num_turns=1,
                    session_id="sess",
                    total_cost_usd=0.01,
                    usage={
                        "input_tokens": 11,
                        "output_tokens": 7,
                        "cache_read_input_tokens": 3,
                        "cache_creation_input_tokens": 2,
                    },
                    result="Done",
                )
            )

            output = console.file.getvalue()
            self.assertIn("Input tokens: 11", output)
            self.assertIn("Output tokens: 7", output)
            self.assertIn("Cache read tokens: 3", output)
            self.assertIn("Cache creation tokens: 2", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_handle_error_result_renders_api_status(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)

            runner._handle_result(
                ResultMessage(
                    subtype="success",
                    duration_ms=12,
                    duration_api_ms=8,
                    is_error=True,
                    num_turns=1,
                    session_id="sess",
                    total_cost_usd=0.01,
                    result="Rate limited",
                    api_error_status=429,
                )
            )

            output = console.file.getvalue()
            self.assertIn("Rate limited", output)
            self.assertIn("HTTP 429", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_partial_streaming_suppresses_duplicate_reply_panel(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)

            runner._handle_stream_event(
                StreamEvent(
                    uuid="1",
                    session_id="sess",
                    event={
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "Hello"},
                    },
                )
            )
            runner._handle_assistant_message(
                AssistantMessage(content=[TextBlock(text="Hello")], model="unit")
            )

            output = console.file.getvalue()
            self.assertIn("Streaming reply: Hello", output)
            self.assertNotIn("💬 Reply", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_task_events_render_runtime_feedback(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)

            runner._handle_task_started(
                TaskStartedMessage(
                    subtype="task_started",
                    data={},
                    task_id="task-1",
                    description="Reviewing files",
                    uuid="1",
                    session_id="sess",
                    task_type="agent",
                )
            )
            runner._handle_task_progress(
                TaskProgressMessage(
                    subtype="task_progress",
                    data={},
                    task_id="task-1",
                    description="Reading more context",
                    usage={"input_tokens": 4, "output_tokens": 1},
                    uuid="2",
                    session_id="sess",
                )
            )
            runner._handle_task_notification(
                TaskNotificationMessage(
                    subtype="task_notification",
                    data={},
                    task_id="task-1",
                    status="completed",
                    output_file="notes.md",
                    summary="Background review finished",
                    uuid="3",
                    session_id="sess",
                )
            )

            output = console.file.getvalue()
            self.assertIn("Background Task", output)
            self.assertIn("Task Progress", output)
            self.assertIn("Task Complete", output)
            self.assertIn("notes.md", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_task_updated_finalizes_once_and_clears_progress(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)
            runner._last_task_progress["task-1"] = "Reviewing files"
            console.file.seek(0)
            console.file.truncate(0)

            runner._handle_task_updated(
                TaskUpdatedMessage(
                    subtype="task_updated",
                    data={},
                    task_id="task-1",
                    patch={"status": "completed", "summary": "Review finished"},
                    status="completed",
                    uuid="1",
                    session_id="sess",
                )
            )
            runner._handle_task_notification(
                TaskNotificationMessage(
                    subtype="task_notification",
                    data={},
                    task_id="task-1",
                    status="completed",
                    output_file=None,
                    summary="Duplicate completion",
                    uuid="2",
                    session_id="sess",
                )
            )

            output = console.file.getvalue()
            self.assertIn("Review finished", output)
            self.assertNotIn("Duplicate completion", output)
            self.assertEqual(output.count("Task Complete"), 1)
            self.assertNotIn("task-1", runner._last_task_progress)
            self.assertIn("task-1", runner._finalized_task_ids)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_task_updated_ignores_non_terminal_patch(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)
            runner._last_task_progress["task-1"] = "Reviewing files"
            console.file.seek(0)
            console.file.truncate(0)

            runner._handle_task_updated(
                TaskUpdatedMessage(
                    subtype="task_updated",
                    data={},
                    task_id="task-1",
                    patch={"status": "running"},
                    status="running",
                )
            )

            self.assertEqual(console.file.getvalue(), "")
            self.assertIn("task-1", runner._last_task_progress)
            self.assertNotIn("task-1", runner._finalized_task_ids)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_rate_limit_warning_renders_panel(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = self._make_runner(Path(tmp), console)

            runner._handle_rate_limit_event(
                SimpleNamespace(
                    subtype="rate_limit",
                    rate_limit_info={
                        "status": "allowed_warning",
                        "rate_limit_type": "requests",
                        "utilization": 0.9,
                    },
                )
            )

            output = console.file.getvalue()
            self.assertIn("Rate Limit Warning", output)
            self.assertIn("requests", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class BackgroundReconciliationTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_result_triggers_one_consolidation_turn(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = AgentRuntimeTests()._make_runner(Path(tmp), console)
            runner._background_task_ids = {"task-1", "task-2"}
            runner._finalized_task_ids = {"task-1", "task-2"}
            client = mock.Mock()
            client.query = mock.AsyncMock()
            client.receive_response = mock.Mock(
                side_effect=[
                    _async_iter(
                        [
                            ResultMessage(
                                subtype="success",
                                duration_ms=10,
                                duration_api_ms=8,
                                is_error=False,
                                num_turns=1,
                                session_id="sess",
                                total_cost_usd=0.01,
                                result="The subagents are still working in the background.",
                            )
                        ]
                    ),
                    _async_iter(
                        [
                            ResultMessage(
                                subtype="success",
                                duration_ms=20,
                                duration_api_ms=15,
                                is_error=False,
                                num_turns=2,
                                session_id="sess",
                                total_cost_usd=0.02,
                                result="Consolidated findings from both subagents.",
                            )
                        ]
                    ),
                ]
            )
            runner._client = client
            runner._start_wait_indicator = mock.AsyncMock()  # type: ignore[assignment]
            runner._stop_wait_indicator = mock.AsyncMock()  # type: ignore[assignment]

            await runner._stream_responses()

            client.query.assert_awaited_once()
            reconciliation_prompt = client.query.await_args.args[0]
            self.assertIn("complete final response", reconciliation_prompt)
            self.assertIn("All background tasks", reconciliation_prompt)
            self.assertTrue(runner._background_reconciliation_attempted)
            self.assertEqual(runner.last_outcome.status, "completed")
            self.assertEqual(
                runner.last_outcome.summary,
                "Consolidated findings from both subagents.",
            )
            output = console.file.getvalue()
            self.assertIn("Consolidating", output)
            self.assertNotIn("still working", runner.last_outcome.summary)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_complete_result_does_not_trigger_reconciliation(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = AgentRuntimeTests()._make_runner(Path(tmp), console)
            runner._background_task_ids = {"task-1"}
            runner._finalized_task_ids = {"task-1"}
            client = mock.Mock()
            client.query = mock.AsyncMock()
            client.receive_response = mock.Mock(
                return_value=_async_iter(
                    [
                        ResultMessage(
                            subtype="success",
                            duration_ms=10,
                            duration_api_ms=8,
                            is_error=False,
                            num_turns=1,
                            session_id="sess",
                            total_cost_usd=0.01,
                            result="Complete consolidated findings.",
                        )
                    ]
                )
            )
            runner._client = client
            runner._start_wait_indicator = mock.AsyncMock()  # type: ignore[assignment]
            runner._stop_wait_indicator = mock.AsyncMock()  # type: ignore[assignment]

            await runner._stream_responses()

            client.query.assert_not_awaited()
            self.assertFalse(runner._background_reconciliation_attempted)
            self.assertEqual(runner.last_outcome.summary, "Complete consolidated findings.")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


async def _async_iter(items):
    for item in items:
        yield item


if __name__ == "__main__":
    unittest.main()
