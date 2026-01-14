import io
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.agent import RunOutcome
from dogent.cli import DogentCLI
from dogent.features.clarification import (
    ClarificationOption,
    ClarificationPayload,
    ClarificationQuestion,
)


class PromptModeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_home = os.environ.get("HOME")
        self._tmp_home = tempfile.TemporaryDirectory()
        self._tmp_root = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self._tmp_home.name
        self.console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
        self.cli = DogentCLI(
            root=Path(self._tmp_root.name),
            console=self.console,
            interactive_prompts=False,
        )

    async def asyncTearDown(self) -> None:
        if self._original_home is not None:
            os.environ["HOME"] = self._original_home
        else:
            os.environ.pop("HOME", None)
        self._tmp_home.cleanup()
        self._tmp_root.cleanup()

    async def test_run_prompt_completed_returns_zero(self) -> None:
        async def fake_send_message(*_args, **_kwargs):
            self.cli.agent.last_outcome = RunOutcome(
                status="completed",
                summary="done",
                todos_snapshot=[],
                remaining_todos_markdown="",
            )

        self.cli.agent.send_message = fake_send_message  # type: ignore[assignment]
        self.cli.agent.pop_clarification_payload = lambda: None  # type: ignore[assignment]
        self.cli.agent.pop_outline_edit_payload = lambda: None  # type: ignore[assignment]

        code = await self.cli.run_prompt("hello")
        self.assertEqual(code, 0)
        output = self.console.file.getvalue()
        self.assertIn("Completed.", output)
        self.assertTrue(self.cli.paths.config_file.exists())

    async def test_run_prompt_needs_clarification_returns_code(self) -> None:
        async def fake_send_message(*_args, **_kwargs):
            self.cli.agent.last_outcome = RunOutcome(
                status="needs_clarification",
                summary="clarify",
                todos_snapshot=[],
                remaining_todos_markdown="",
            )

        self.cli.agent.send_message = fake_send_message  # type: ignore[assignment]
        self.cli.agent.pop_clarification_payload = lambda: None  # type: ignore[assignment]
        self.cli.agent.pop_outline_edit_payload = lambda: None  # type: ignore[assignment]

        code = await self.cli.run_prompt("hello")
        self.assertEqual(code, 11)

    async def test_run_prompt_auto_skips_clarification(self) -> None:
        calls = 0

        async def fake_send_message(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            status = "needs_clarification" if calls == 1 else "completed"
            self.cli.agent.last_outcome = RunOutcome(
                status=status,
                summary=status,
                todos_snapshot=[],
                remaining_todos_markdown="",
            )

        payload = ClarificationPayload(
            title="Clarify",
            preface=None,
            questions=[
                ClarificationQuestion(
                    question_id="q1",
                    question="Pick one",
                    options=[ClarificationOption(label="A", value="a")],
                    recommended=None,
                    allow_freeform=False,
                    placeholder=None,
                )
            ],
        )
        payloads = [payload, None]

        def pop_payload():
            if payloads:
                return payloads.pop(0)
            return None

        self.cli.agent.send_message = fake_send_message  # type: ignore[assignment]
        self.cli.agent.pop_clarification_payload = pop_payload  # type: ignore[assignment]
        self.cli.agent.pop_outline_edit_payload = lambda: None  # type: ignore[assignment]

        code = await self.cli.run_prompt("hello", auto=True)
        self.assertEqual(code, 0)
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
