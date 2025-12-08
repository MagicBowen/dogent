import asyncio
import io
import os
import tempfile
import threading
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI


class DummyAgent:
    def __init__(self) -> None:
        self.interrupted = False
        self.reason: str | None = None

    async def send_message(self, message: str, attachments) -> None:  # noqa: ARG002
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
            cli = DogentCLI(root=Path(tmp), console=console)
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


if __name__ == "__main__":
    unittest.main()
