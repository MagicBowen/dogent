import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from claude_agent_sdk import ToolPermissionContext
from claude_agent_sdk.types import PermissionRuleValue, PermissionUpdate
from rich.console import Console

from dogent.agent import AgentRunner, PermissionDecision
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.core.todo import TodoManager
from dogent.prompts import PromptBuilder


class AgentPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_can_use_tool_remember_uses_session_permission_updates(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            permission_prompt = mock.AsyncMock(
                return_value=PermissionDecision(True, remember=True)
            )
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                permission_prompt=permission_prompt,
            )
            suggestion = PermissionUpdate(
                type="addRules",
                rules=[PermissionRuleValue(tool_name="Write", rule_content="/tmp/demo.txt")],
                behavior="allow",
                destination="projectSettings",
            )
            permission_check = SimpleNamespace(
                needs_confirm=True,
                reason="Need permission",
                targets=[Path("/tmp/demo.txt")],
            )

            with mock.patch.object(
                runner, "_ensure_tool_dependencies", new=mock.AsyncMock(return_value=True)
            ), mock.patch(
                "dogent.agent.runner.evaluate_tool_permission",
                return_value=permission_check,
            ):
                result = await runner._can_use_tool(
                    "Write",
                    {"file_path": "/tmp/demo.txt"},
                    ToolPermissionContext(
                        suggestions=[suggestion],
                        agent_id="agent-123456789",
                        tool_use_id="tool-1",
                        blocked_path="/tmp/demo.txt",
                        decision_reason="SDK requested confirmation",
                        title="Claude wants to write a file",
                        display_name="Write file",
                        description="Creates a file outside the workspace",
                    ),
                )

            self.assertIsNotNone(result.updated_permissions)
            assert result.updated_permissions is not None
            self.assertEqual(len(result.updated_permissions), 1)
            self.assertEqual(result.updated_permissions[0].destination, "session")
            request = permission_prompt.await_args.args[0]
            self.assertEqual(request.agent_label, "Sub-agent agent-12")
            self.assertEqual(request.tool_use_id, "tool-1")
            self.assertIn("Write file", request.message)
            self.assertIn("/tmp/demo.txt", request.message)
            self.assertIn("Reason: Need permission", request.message)

            data = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertIn("Write", data.get("authorizations", {}))
            self.assertIn(str(Path("/tmp/demo.txt").resolve()), data["authorizations"]["Write"])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_can_use_tool_allow_without_remember_skips_permission_updates(self) -> None:
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
                permission_prompt=mock.AsyncMock(return_value=PermissionDecision(True)),
            )
            suggestion = PermissionUpdate(
                type="addRules",
                rules=[PermissionRuleValue(tool_name="Write", rule_content="/tmp/demo.txt")],
                behavior="allow",
                destination="projectSettings",
            )
            permission_check = SimpleNamespace(
                needs_confirm=True,
                reason="Need permission",
                targets=[Path("/tmp/demo.txt")],
            )

            with mock.patch.object(
                runner, "_ensure_tool_dependencies", new=mock.AsyncMock(return_value=True)
            ), mock.patch(
                "dogent.agent.runner.evaluate_tool_permission",
                return_value=permission_check,
            ):
                result = await runner._can_use_tool(
                    "Write",
                    {"file_path": "/tmp/demo.txt"},
                    ToolPermissionContext(suggestions=[suggestion]),
                )

            self.assertIsNone(result.updated_permissions)
            self.assertFalse(paths.config_file.exists())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_subagent_denial_interrupts_only_that_subagent(self) -> None:
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
                permission_prompt=mock.AsyncMock(return_value=PermissionDecision(False)),
            )
            runner._client = SimpleNamespace(interrupt=mock.AsyncMock())
            permission_check = SimpleNamespace(
                needs_confirm=True,
                reason="Outside workspace",
                targets=[Path("/etc/hosts")],
            )

            with mock.patch.object(
                runner, "_ensure_tool_dependencies", new=mock.AsyncMock(return_value=True)
            ), mock.patch.object(
                runner, "_start_wait_indicator", new=mock.AsyncMock()
            ) as start_wait, mock.patch(
                "dogent.agent.runner.evaluate_tool_permission",
                return_value=permission_check,
            ):
                result = await runner._can_use_tool(
                    "Read",
                    {"file_path": "/etc/hosts"},
                    ToolPermissionContext(suggestions=[], agent_id="agent-123456789"),
                )

            self.assertTrue(result.interrupt)
            self.assertIn("sub-agent agent-123456789", result.message)
            self.assertFalse(runner._abort_requested)
            self.assertIsNone(runner._aborted_reason)
            runner._client.interrupt.assert_not_awaited()
            start_wait.assert_awaited_once()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_main_agent_denial_aborts_whole_turn(self) -> None:
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
                permission_prompt=mock.AsyncMock(return_value=PermissionDecision(False)),
            )
            runner._client = SimpleNamespace(interrupt=mock.AsyncMock())
            permission_check = SimpleNamespace(
                needs_confirm=True,
                reason="Outside workspace",
                targets=[Path("/etc/hosts")],
            )

            with mock.patch.object(
                runner, "_ensure_tool_dependencies", new=mock.AsyncMock(return_value=True)
            ), mock.patch(
                "dogent.agent.runner.evaluate_tool_permission",
                return_value=permission_check,
            ):
                result = await runner._can_use_tool(
                    "Read",
                    {"file_path": "/etc/hosts"},
                    ToolPermissionContext(suggestions=[]),
                )

            self.assertTrue(result.interrupt)
            self.assertTrue(runner._abort_requested)
            self.assertEqual(runner.last_outcome.status, "aborted")
            runner._client.interrupt.assert_awaited_once()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_can_use_tool_ask_user_question_returns_updated_input(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            sdk_question_prompt = mock.AsyncMock(
                return_value={
                    "questions": [
                        {
                            "question": "Pick one",
                            "header": "Choice",
                            "options": [
                                {"label": "A", "description": "Alpha"},
                                {"label": "B", "description": "Beta"},
                            ],
                            "multiSelect": False,
                        }
                    ],
                    "answers": {"Pick one": "B"},
                }
            )
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                sdk_question_prompt=sdk_question_prompt,
            )

            with mock.patch.object(
                runner, "_ensure_tool_dependencies", new=mock.AsyncMock(return_value=True)
            ), mock.patch(
                "dogent.agent.runner.evaluate_tool_permission"
            ) as mocked_permission:
                result = await runner._can_use_tool(
                    "AskUserQuestion",
                    {
                        "questions": [
                            {
                                "question": "Pick one",
                                "header": "Choice",
                                "options": [
                                    {"label": "A", "description": "Alpha"},
                                    {"label": "B", "description": "Beta"},
                                ],
                                "multiSelect": False,
                            }
                        ]
                    },
                    ToolPermissionContext(
                        suggestions=[],
                        agent_id="question-agent",
                        tool_use_id="question-tool",
                    ),
                )

            self.assertEqual(result.updated_input["answers"]["Pick one"], "B")
            request = sdk_question_prompt.await_args.args[0]
            self.assertEqual(request.agent_label, "Sub-agent question")
            self.assertEqual(request.tool_use_id, "question-tool")
            mocked_permission.assert_not_called()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_human_prompts_are_serialized_across_kinds(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            permission_started = asyncio.Event()
            release_permission = asyncio.Event()
            active = 0
            max_active = 0
            order: list[str] = []
            queued_counts: list[int] = []

            async def permission_prompt(request):
                nonlocal active, max_active
                active += 1
                max_active = max(max_active, active)
                order.append(request.agent_label)
                queued_counts.append(request.queued_count)
                permission_started.set()
                await release_permission.wait()
                active -= 1
                return PermissionDecision(True)

            async def question_prompt(request):
                nonlocal active, max_active
                active += 1
                max_active = max(max_active, active)
                order.append(request.agent_label)
                queued_counts.append(request.queued_count)
                active -= 1
                return {"questions": [], "answers": {}}

            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                permission_prompt=permission_prompt,
                sdk_question_prompt=question_prompt,
            )
            permission_task = asyncio.create_task(
                runner._request_permission(
                    "Read",
                    {"file_path": "/etc/hosts"},
                    ToolPermissionContext(suggestions=[], agent_id="first-agent"),
                    "Outside workspace",
                )
            )
            question_task = asyncio.create_task(
                runner._request_sdk_questions(
                    {"questions": []},
                    ToolPermissionContext(suggestions=[], agent_id="second-agent"),
                )
            )
            await permission_started.wait()
            await asyncio.sleep(0)
            self.assertEqual(order, ["Sub-agent first-ag"])
            release_permission.set()
            permission_result, question_result = await asyncio.gather(
                permission_task, question_task
            )

            self.assertTrue(permission_result.allow)
            self.assertIsNotNone(question_result)
            self.assertEqual(
                order, ["Sub-agent first-ag", "Sub-agent second-a"]
            )
            self.assertEqual(queued_counts, [1, 0])
            self.assertEqual(max_active, 1)
            self.assertEqual(runner._human_prompt_pending, 0)
            self.assertFalse(runner._permission_prompt_active)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_queued_prompt_is_skipped_after_abort(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console()
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            started = asyncio.Event()
            release = asyncio.Event()
            question_prompt = mock.AsyncMock(return_value={})

            async def permission_prompt(_request):
                started.set()
                await release.wait()
                return PermissionDecision(True)

            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                permission_prompt=permission_prompt,
                sdk_question_prompt=question_prompt,
            )
            permission_task = asyncio.create_task(
                runner._request_permission(
                    "Read",
                    {},
                    ToolPermissionContext(suggestions=[]),
                    "Confirm",
                )
            )
            await started.wait()
            question_task = asyncio.create_task(
                runner._request_sdk_questions(
                    {"questions": []}, ToolPermissionContext(suggestions=[])
                )
            )
            await asyncio.sleep(0)
            runner._abort_requested = True
            release.set()
            await permission_task
            self.assertIsNone(await question_task)
            question_prompt.assert_not_awaited()
            self.assertEqual(runner._human_prompt_pending, 0)
            self.assertFalse(runner._permission_prompt_active)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
