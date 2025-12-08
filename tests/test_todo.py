import io
import tempfile
import unittest
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ToolUseBlock
from rich.console import Console

from dogent.agent import AgentRunner
from dogent.config import ConfigManager
from dogent.history import HistoryManager
from dogent.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.todo import TodoItem, TodoManager


class TodoManagerTests(unittest.TestCase):
    def test_update_from_payload(self) -> None:
        manager = TodoManager()
        payload = {"items": [{"title": "write intro", "status": "pending"}]}
        updated = manager.update_from_payload(payload, source="test")
        self.assertTrue(updated)
        self.assertEqual(len(manager.items), 1)
        self.assertEqual(manager.items[0].title, "write intro")

        json_payload = '{"items": [{"title": "research", "status": "doing"}]}'
        manager.update_from_payload(json_payload, source="json")
        self.assertEqual(manager.items[0].title, "research")
        self.assertEqual(manager.items[0].status, "doing")

        mixed_payload = {"todos": [{"content": "正在研究 SDK", "status": "completed", "activeForm": "ignore"}]}
        manager.update_from_payload(mixed_payload, source="mixed")
        self.assertEqual(manager.items[0].title, "研究 SDK")
        self.assertEqual(manager.items[0].status, "completed")

    def test_agent_updates_todo_from_tool(self) -> None:
        console = Console(file=io.StringIO(), force_terminal=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = DogentPaths(root)
            todo_manager = TodoManager(console=console)
            prompt_builder = PromptBuilder(paths, todo_manager, HistoryManager(paths))
            agent = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=prompt_builder,
                todo_manager=todo_manager,
                history=HistoryManager(paths),
                console=console,
            )

            tool_use = ToolUseBlock(id="1", name="TodoWrite", input={"items": [{"title": "draft"}]})
            msg = AssistantMessage(content=[tool_use], model="unit")
            agent._handle_assistant_message(msg)

            self.assertEqual(len(todo_manager.items), 1)
            self.assertEqual(todo_manager.items[0].title, "draft")


if __name__ == "__main__":
    unittest.main()
