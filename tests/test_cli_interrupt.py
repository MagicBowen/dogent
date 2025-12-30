import asyncio
import io
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI


class DummyAgent:
    def __init__(self) -> None:
        self.interrupted = False
        self.reason: str | None = None

    async def send_message(  # noqa: ARG002
        self, message: str, attachments, *, config_override=None
    ) -> None:
        await asyncio.sleep(1)

    async def interrupt(self, reason: str) -> None:
        self.interrupted = True
        self.reason = reason


class InterruptHelperTests(unittest.TestCase):
    def test_interrupt_helper_cancels_tasks_and_calls_agent(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            dummy_agent = DummyAgent()
            cli.agent = dummy_agent  # type: ignore[assignment]
            stop_event = threading.Event()

            async def run_interrupt():
                agent_task = asyncio.create_task(asyncio.sleep(1))
                esc_task = asyncio.create_task(asyncio.sleep(1))
                await cli._interrupt_running_task(
                    reason="test interrupt",
                    agent_task=agent_task,
                    esc_task=esc_task,
                    stop_event=stop_event,
                )
                return agent_task, esc_task

            agent_task, esc_task = asyncio.run(run_interrupt())
            self.assertTrue(dummy_agent.interrupted)
            self.assertEqual(dummy_agent.reason, "test interrupt")
            self.assertTrue(stop_event.is_set())
            self.assertTrue(agent_task.cancelled() or agent_task.done())
            self.assertTrue(esc_task.cancelled() or esc_task.done())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_interrupt_helper_waits_for_escape_listener(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            dummy_agent = DummyAgent()
            cli.agent = dummy_agent  # type: ignore[assignment]
            stop_event = threading.Event()
            marker = {"finished": False}

            async def esc_listener() -> None:
                while not stop_event.is_set():
                    await asyncio.sleep(0.01)
                marker["finished"] = True

            async def run_interrupt():
                agent_task = asyncio.create_task(asyncio.sleep(1))
                esc_task = asyncio.create_task(esc_listener())
                await cli._interrupt_running_task(
                    reason="test interrupt",
                    agent_task=agent_task,
                    esc_task=esc_task,
                    stop_event=stop_event,
                )
                return agent_task, esc_task

            agent_task, esc_task = asyncio.run(run_interrupt())
            self.assertTrue(marker["finished"])
            self.assertTrue(esc_task.done())
            self.assertFalse(esc_task.cancelled())
            self.assertTrue(agent_task.cancelled() or agent_task.done())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_read_escape_key_drains_sequence(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            stop_event = threading.Event()
            captured: list[str] = []
            read_values = ["\x1b", "[", "D"]
            select_calls: list[float] = []

            def read_side_effect(_: int) -> str:
                if read_values:
                    value = read_values.pop(0)
                else:
                    value = ""
                captured.append(value)
                return value

            def select_side_effect(rlist, wlist, xlist, timeout):  # noqa: ARG001
                select_calls.append(timeout)
                if len(select_calls) == 1:
                    return ([0], [], [])
                if len(select_calls) in {2, 3}:
                    return ([0], [], [])
                return ([], [], [])

            with (
                mock.patch("dogent.cli.termios.tcgetattr", return_value=object()),
                mock.patch("dogent.cli.termios.tcsetattr"),
                mock.patch("dogent.cli.tty.setcbreak"),
                mock.patch("dogent.cli.select.select", side_effect=select_side_effect),
                mock.patch("dogent.cli.sys.stdin.fileno", return_value=0),
                mock.patch("dogent.cli.sys.stdin.read", side_effect=read_side_effect),
            ):
                result = cli._read_escape_key(stop_event)

            self.assertTrue(result)
            self.assertGreaterEqual(len(captured), 3)
            self.assertEqual(captured[:3], ["\x1b", "[", "D"])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
