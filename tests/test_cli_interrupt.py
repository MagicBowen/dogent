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
            kbhit_calls = [0]

            def read_side_effect() -> str:
                if read_values:
                    value = read_values.pop(0)
                else:
                    value = ""
                captured.append(value)
                return value

            def kbhit_side_effect() -> bool:
                kbhit_calls[0] += 1
                # First call: check if escape key is available (True)
                if kbhit_calls[0] == 1:
                    return True
                # After reading escape, drain the sequence (True for remaining chars)
                if read_values:
                    return True
                # After draining, signal stop to exit loop
                stop_event.set()
                return False

            with (
                mock.patch("dogent.cli.tcgetattr", return_value=object()),
                mock.patch("dogent.cli.tcsetattr"),
                mock.patch("dogent.cli.setcbreak"),
                mock.patch("dogent.cli.kbhit", side_effect=kbhit_side_effect),
                mock.patch("dogent.cli.getch", side_effect=read_side_effect),
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
