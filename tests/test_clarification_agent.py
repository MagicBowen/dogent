import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.history import HistoryManager
from dogent.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.todo import TodoManager


class ClarificationAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_message_keeps_session_on_clarification(self) -> None:
        class DummyClient:
            def __init__(self) -> None:
                self.options = SimpleNamespace(system_prompt="")
                self.interrupted = False

            async def query(self, _prompt: str) -> None:
                return None

            async def interrupt(self) -> None:
                self.interrupted = True

            async def receive_response(self):
                if False:
                    yield None

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
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

            async def fake_stream() -> None:
                runner._needs_clarification = True

            with mock.patch.object(
                runner, "_stream_responses", new=mock.AsyncMock(side_effect=fake_stream)
            ):
                with mock.patch.object(
                    runner, "_safe_disconnect", new=mock.AsyncMock()
                ) as safe_disconnect:
                    with mock.patch.object(
                        runner, "_start_wait_indicator", new=mock.AsyncMock()
                    ):
                        with mock.patch.object(
                            runner, "_stop_wait_indicator", new=mock.AsyncMock()
                        ):
                            await runner.send_message("Need info", [], config_override=None)
                    safe_disconnect.assert_not_awaited()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_interrupts_stream_when_clarification_detected(self) -> None:
        class DummyClient:
            def __init__(self) -> None:
                self.options = SimpleNamespace(system_prompt="")
                self.interrupted = False

            async def query(self, _prompt: str) -> None:
                return None

            async def interrupt(self) -> None:
                self.interrupted = True

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
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
            client = DummyClient()
            runner._client = client
            runner._needs_clarification = True

            from claude_agent_sdk import AssistantMessage, TextBlock
            from dogent.clarification import CLARIFICATION_JSON_TAG

            async def fake_receive():
                runner._needs_clarification = True
                message = AssistantMessage(
                    content=[
                        TextBlock(
                            f"{CLARIFICATION_JSON_TAG}\n"
                            "{"
                            "\"response_type\": \"clarification\","
                            "\"title\": \"Need details\","
                            "\"questions\": ["
                            "  {"
                            "    \"id\": \"info\","
                            "    \"question\": \"Provide info\","
                            "    \"options\": ["
                            "      {\"label\": \"A\", \"value\": \"a\"}"
                            "    ]"
                            "  }"
                            "]"
                            "}"
                        )
                    ],
                    model="test",
                )
                yield message

            with mock.patch.object(runner, "_handle_assistant_message") as handler:
                handler.side_effect = lambda _msg: setattr(runner, "_needs_clarification", True)
                runner._client.receive_response = fake_receive  # type: ignore[assignment]
                await runner._stream_responses()
            self.assertTrue(client.interrupted)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_thinking_block_does_not_trigger_clarification(self) -> None:
        class DummyClient:
            def __init__(self) -> None:
                self.options = SimpleNamespace(system_prompt="")
                self.interrupted = False

            async def query(self, _prompt: str) -> None:
                return None

            async def interrupt(self) -> None:
                self.interrupted = True

        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
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
            client = DummyClient()
            runner._client = client

            from claude_agent_sdk import AssistantMessage, ThinkingBlock
            from dogent.clarification import CLARIFICATION_JSON_TAG

            payload = {
                "response_type": "clarification",
                "title": "Need details",
                "questions": [
                    {
                        "id": "info",
                        "question": "Provide info",
                        "options": [{"label": "A", "value": "a"}],
                        "allow_freeform": True,
                    }
                ],
            }
            text = f"{CLARIFICATION_JSON_TAG}\n{json.dumps(payload)}"

            async def fake_receive():
                message = AssistantMessage(
                    content=[ThinkingBlock(thinking=text, signature="sig")],
                    model="test",
                )
                yield message

            runner._client.receive_response = fake_receive  # type: ignore[assignment]
            await runner._stream_responses()
            self.assertFalse(client.interrupted)
            self.assertIsNone(runner._clarification_payload)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
