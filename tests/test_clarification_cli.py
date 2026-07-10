import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.agent import HumanPromptRequest
from dogent.cli import (
    DogentCLI,
    ClarificationTimeout,
    CLARIFICATION_SKIP,
    CLARIFICATION_SKIP_TEXT,
)
from dogent.features.clarification import (
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

    async def test_format_clarification_answers_wraps_editor_text(self) -> None:
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
                        allow_freeform=True,
                        placeholder=None,
                    )
                ],
            )
            answers = [
                {
                    "id": "q1",
                    "question": "Question?",
                    "answer": "Line1\nLine2",
                    "editor": "true",
                }
            ]
            text = cli._format_clarification_answers(payload, answers)
            self.assertIn("```markdown", text)
            self.assertIn("Line1", text)
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

    async def test_prompt_sdk_questions_collects_single_and_multi_select_answers(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            with mock.patch.object(
                cli,
                "_read_input",
                new=mock.AsyncMock(side_effect=["2", "1, 2"]),
            ):
                result = await cli._prompt_sdk_questions(
                    HumanPromptRequest(
                        kind="question",
                        title="Clarification · Sub-agent agent-12",
                        agent_id="agent-1234",
                        input_data={
                        "questions": [
                            {
                                "question": "Choose a style",
                                "header": "Style",
                                "options": [
                                    {"label": "Formal", "description": "Business tone"},
                                    {"label": "Casual", "description": "Relaxed tone"},
                                ],
                                "multiSelect": False,
                            },
                            {
                                "question": "Choose sections",
                                "header": "Parts",
                                "options": [
                                    {"label": "Intro", "description": "Opening"},
                                    {"label": "Summary", "description": "Closing"},
                                ],
                                "multiSelect": True,
                            },
                        ]
                        },
                    )
                )
            self.assertEqual(result["answers"]["Choose a style"], "Casual")
            self.assertEqual(result["answers"]["Choose sections"], "Intro, Summary")
            self.assertIn("Sub-agent agent-12", console.file.getvalue())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_sdk_question_uses_dedicated_inline_choices(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            cli = DogentCLI(
                root=Path(tmp),
                console=Console(file=io.StringIO(), force_terminal=True, color_system=None),
                interactive_prompts=True,
            )
            with mock.patch.object(
                cli, "_can_use_inline_choice", return_value=True
            ), mock.patch.object(
                cli, "_prompt_choice", new=mock.AsyncMock(return_value=1)
            ) as prompt_choice:
                answer = await cli._prompt_sdk_question(
                    {
                        "question": "Choose one",
                        "header": "Choice",
                        "options": [
                            {"label": "A", "description": "Alpha"},
                            {"label": "B", "description": "Beta"},
                        ],
                        "multiSelect": False,
                    },
                    index=1,
                    total=1,
                    agent_label="Sub-agent agent-12",
                    queued_count=2,
                )

            self.assertEqual(answer, "B")
            self.assertIn(
                "2 queued requests", prompt_choice.await_args.kwargs["status_text"]
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_sdk_multi_question_uses_dedicated_multi_select(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            cli = DogentCLI(
                root=Path(tmp),
                console=Console(file=io.StringIO(), force_terminal=True, color_system=None),
                interactive_prompts=True,
            )
            with mock.patch.object(
                cli, "_can_use_inline_choice", return_value=True
            ), mock.patch.object(
                cli,
                "_prompt_inline_multi_choice",
                new=mock.AsyncMock(return_value=[0, 1]),
            ) as prompt_multi:
                answer = await cli._prompt_sdk_question(
                    {
                        "question": "Choose sections",
                        "options": [
                            {"label": "Intro", "description": "Opening"},
                            {"label": "Summary", "description": "Closing"},
                        ],
                        "multiSelect": True,
                    },
                    index=1,
                    total=1,
                    agent_label="Sub-agent agent-12",
                    queued_count=1,
                )

            self.assertEqual(answer, "Intro, Summary")
            self.assertIn(
                "1 queued request", prompt_multi.await_args.kwargs["status_text"]
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_inline_multi_choice_runs_inside_dedicated_frame(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            cli = DogentCLI(
                root=Path(tmp),
                console=Console(file=io.StringIO(), force_terminal=True, color_system=None),
                interactive_prompts=True,
            )
            with mock.patch.object(
                cli, "_run_dedicated_prompt", new=mock.AsyncMock(return_value=[0, 1])
            ) as run_prompt:
                result = await cli._prompt_inline_multi_choice(
                    title="Clarification · Sub-agent agent-12",
                    prompt_text="Choose sections",
                    options=["Intro", "Summary"],
                    status_text="Active: Sub-agent agent-12 | 1 queued request",
                )

            self.assertEqual(result, [0, 1])
            app = run_prompt.await_args.args[0]
            self.assertEqual(type(app.layout.container).__name__, "HSplit")
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
