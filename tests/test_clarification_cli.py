import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import (
    DogentCLI,
    ClarificationTimeout,
    CLARIFICATION_SKIP,
    CLARIFICATION_SKIP_TEXT,
)
from dogent.clarification import (
    ClarificationOption,
    ClarificationPayload,
    ClarificationQuestion,
)


class ClarificationCliTests(unittest.IsolatedAsyncioTestCase):
    async def test_choice_text_uses_default_on_empty(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            options = [
                ClarificationOption(label="Alpha", value="alpha"),
                ClarificationOption(label="Beta", value="beta"),
            ]
            with mock.patch.object(
                cli, "_read_input", new=mock.AsyncMock(return_value="")
            ):
                result = await cli._prompt_clarification_choice_text(
                    title="Question 1/1",
                    question="Pick one",
                    options=options,
                    selected=1,
                )
            self.assertEqual(result, 1)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_choice_text_esc_skips(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            options = [
                ClarificationOption(label="Alpha", value="alpha"),
                ClarificationOption(label="Beta", value="beta"),
            ]
            with mock.patch.object(
                cli, "_read_input", new=mock.AsyncMock(return_value="esc")
            ):
                result = await cli._prompt_clarification_choice_text(
                    title="Question 1/1",
                    question="Pick one",
                    options=options,
                    selected=0,
                )
            self.assertIs(result, CLARIFICATION_SKIP)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_freeform_text_esc_skips(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            with mock.patch.object(
                cli, "_read_input", new=mock.AsyncMock(return_value="esc")
            ):
                result = await cli._prompt_freeform_answer_text("Your answer: ")
            self.assertIs(result, CLARIFICATION_SKIP)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_prompt_question_skip_records_answer(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            question = ClarificationQuestion(
                question_id="q1",
                question="Question?",
                options=[ClarificationOption(label="Yes", value="yes")],
                recommended="yes",
                allow_freeform=False,
                placeholder=None,
            )
            with mock.patch.object(
                cli,
                "_prompt_clarification_choice_text",
                new=mock.AsyncMock(return_value=CLARIFICATION_SKIP),
            ):
                answer = await cli._prompt_clarification_question(
                    question, index=1, total=1, timeout_s=None
                )
            self.assertEqual(answer["answer"], CLARIFICATION_SKIP_TEXT)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_collect_answers_reports_timeout(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            payload = ClarificationPayload(
                title="Need info",
                preface=None,
                questions=[
                    ClarificationQuestion(
                        question_id="q1",
                        question="Question?",
                        options=[ClarificationOption(label="Yes", value="yes")],
                        recommended="yes",
                        allow_freeform=False,
                        placeholder=None,
                    )
                ],
            )
            with mock.patch.object(
                cli, "_prompt_clarification_question", side_effect=ClarificationTimeout
            ):
                answers, reason = await cli._collect_clarification_answers(payload)
            self.assertIsNone(answers)
            self.assertEqual(reason, "timeout")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_record_clarification_history(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            payload = ClarificationPayload(
                title="Need info",
                preface=None,
                questions=[
                    ClarificationQuestion(
                        question_id="q1",
                        question="Question?",
                        options=[ClarificationOption(label="Yes", value="yes")],
                        recommended="yes",
                        allow_freeform=False,
                        placeholder=None,
                    )
                ],
            )
            text = "Clarification answers:\n- q1: Question?\n  Answer: Yes"
            cli._record_clarification_history(payload, text)
            entries = cli.history_manager.read_entries()
            self.assertEqual(entries[-1]["status"], "clarification")
            self.assertEqual(entries[-1]["prompt"], text)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_other_choice_uses_freeform_prompt(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            question = ClarificationQuestion(
                question_id="q1",
                question="Question?",
                options=[ClarificationOption(label="Alpha", value="alpha")],
                recommended="alpha",
                allow_freeform=True,
                placeholder=None,
            )
            cli._prompt_freeform_answer = mock.AsyncMock(return_value="details")  # type: ignore[assignment]
            with mock.patch.object(
                cli,
                "_prompt_clarification_choice_text",
                new=mock.AsyncMock(return_value=1),
            ):
                answer = await cli._prompt_clarification_question(
                    question, index=1, total=1, timeout_s=None
                )
            self.assertEqual(answer["answer"], "details")
            cli._prompt_freeform_answer.assert_awaited_once_with(  # type: ignore[union-attr]
                question,
                label="Question?",
                skip_on_editor_cancel=True,
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_other_choice_strips_trailing_period(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            question = ClarificationQuestion(
                question_id="q1",
                question="Answer this.",
                options=[ClarificationOption(label="Alpha", value="alpha")],
                recommended="alpha",
                allow_freeform=True,
                placeholder=None,
            )
            cli._prompt_freeform_answer = mock.AsyncMock(return_value="details")  # type: ignore[assignment]
            with mock.patch.object(
                cli,
                "_prompt_clarification_choice_text",
                new=mock.AsyncMock(return_value=1),
            ):
                answer = await cli._prompt_clarification_question(
                    question, index=1, total=1, timeout_s=None
                )
            self.assertEqual(answer["answer"], "details")
            cli._prompt_freeform_answer.assert_awaited_once_with(  # type: ignore[union-attr]
                question,
                label="Answer this",
                skip_on_editor_cancel=True,
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
