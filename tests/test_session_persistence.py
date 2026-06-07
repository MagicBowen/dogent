import asyncio
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.core.todo import TodoManager
from dogent.prompts import PromptBuilder


def _make_runner(root: Path, console: Console) -> AgentRunner:
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


class SessionPersistenceTests(unittest.TestCase):
    def test_client_stays_alive_after_send_message(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            mock_client.receive_response.return_value = _async_iter([])
            runner._client = mock_client

            async def run():
                await runner.send_message(
                    "hello", [], config_override={"role": "assistant"}
                )

            asyncio.run(run())
            self.assertIsNotNone(runner._client)
            self.assertIs(runner._client, mock_client)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_client_reused_across_turns(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            mock_client.receive_response.return_value = _async_iter([])
            runner._client = mock_client

            async def run():
                await runner.send_message(
                    "turn 1", [], config_override={"role": "assistant"}
                )
                mock_client.receive_response.return_value = _async_iter([])
                await runner.send_message(
                    "turn 2", [], config_override={"role": "assistant"}
                )

            asyncio.run(run())
            self.assertEqual(mock_client.query.call_count, 2)
            self.assertIs(runner._client, mock_client)
            self.assertEqual(runner._turn_count, 2)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_client_stays_alive_on_error(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            mock_client.query.side_effect = RuntimeError("SDK error")
            runner._client = mock_client

            async def run():
                await runner.send_message(
                    "hello", [], config_override={"role": "assistant"}
                )

            asyncio.run(run())
            self.assertIsNotNone(runner._client)
            self.assertIs(runner._client, mock_client)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_interrupt_keeps_client_alive(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            runner._client = mock_client

            async def run():
                await runner.interrupt("user pressed Esc")

            asyncio.run(run())
            self.assertIsNotNone(runner._client)
            self.assertIs(runner._client, mock_client)
            mock_client.interrupt.assert_awaited_once()
            mock_client.disconnect.assert_not_called()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_reset_clears_client_and_state(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            runner._client = mock_client
            runner._turn_count = 5
            runner._interrupted = True
            runner.last_outcome = mock.Mock()

            async def run():
                await runner.reset()

            asyncio.run(run())
            self.assertIsNone(runner._client)
            self.assertEqual(runner._turn_count, 0)
            self.assertFalse(runner._interrupted)
            self.assertIsNone(runner.last_outcome)
            mock_client.disconnect.assert_awaited_once()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_reset_creates_fresh_client_on_next_turn(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            first_client = mock.AsyncMock()
            first_client.receive_response.return_value = _async_iter([])
            runner._client = first_client

            async def run():
                await runner.reset()
                await runner.send_message(
                    "after reset", [], config_override={"role": "assistant"}
                )

            asyncio.run(run())
            self.assertIsNotNone(runner._client)
            self.assertIsNot(runner._client, first_client)
            self.assertEqual(runner._turn_count, 1)
            first_client.disconnect.assert_awaited_once()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_turn_count_increments_per_send(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            runner = _make_runner(Path(tmp), console)

            mock_client = mock.AsyncMock()
            mock_client.receive_response.return_value = _async_iter([])
            runner._client = mock_client

            async def run():
                self.assertEqual(runner._turn_count, 0)
                await runner.send_message(
                    "turn 1", [], config_override={"role": "assistant"}
                )
                self.assertEqual(runner._turn_count, 1)
                await runner.send_message(
                    "turn 2", [], config_override={"role": "assistant"}
                )
                self.assertEqual(runner._turn_count, 2)
                await runner.interrupt("test")
                self.assertEqual(runner._turn_count, 2)

            asyncio.run(run())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


async def _async_iter(items):
    for item in items:
        yield item


if __name__ == "__main__":
    unittest.main()
