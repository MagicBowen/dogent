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
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                permission_prompt=mock.AsyncMock(
                    return_value=PermissionDecision(True, remember=True)
                ),
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

            self.assertIsNotNone(result.updated_permissions)
            assert result.updated_permissions is not None
            self.assertEqual(len(result.updated_permissions), 1)
            self.assertEqual(result.updated_permissions[0].destination, "session")

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
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
                sdk_question_prompt=mock.AsyncMock(
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
                ),
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
                    ToolPermissionContext(suggestions=[]),
                )

            self.assertEqual(result.updated_input["answers"]["Pick one"], "B")
            mocked_permission.assert_not_called()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
