import asyncio
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.agent import AgentRunner, DependencyDecision
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.core.todo import TodoManager
from dogent.prompts import PromptBuilder


class DependencyFlowTests(unittest.TestCase):
    def test_manual_dependency_choice_aborts(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )

            async def dependency_prompt(_title: str, _message: str) -> DependencyDecision:
                return DependencyDecision("manual")

            runner.set_dependency_prompt(dependency_prompt)

            with (
                mock.patch(
                    "dogent.agent.runner.missing_dependencies_for_tool",
                    return_value=["pandoc"],
                ),
                mock.patch(
                    "dogent.agent.runner.manual_instructions",
                    return_value="Install pandoc.",
                ),
            ):
                ok = asyncio.run(
                    runner._ensure_tool_dependencies(
                        "mcp__dogent__export_document", {"format": "docx"}
                    )
                )

            self.assertFalse(ok)
            self.assertEqual(runner.last_outcome.status, "aborted")
            self.assertIn("Install pandoc", runner.last_outcome.summary)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_interrupt_during_dependency_install_aborts(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo = TodoManager(console=console)
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo, history)
            runner = AgentRunner(
                config=ConfigManager(paths, console=console),
                prompt_builder=builder,
                todo_manager=todo,
                history=history,
                console=console,
            )
            runner._dependency_installing = True
            runner._dependency_manual_instructions = "Install pandoc."

            asyncio.run(runner.interrupt("Esc detected"))

            self.assertIsNotNone(runner.last_outcome)
            assert runner.last_outcome
            self.assertEqual(runner.last_outcome.status, "aborted")
            self.assertIn("Install pandoc", runner.last_outcome.summary)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
