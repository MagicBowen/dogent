import io
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.file_refs import FileReferenceResolver
from dogent.history import HistoryManager
from dogent.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.todo import TodoItem, TodoManager


class PromptTests(unittest.TestCase):
    def test_prompts_include_todos_and_files(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("自定义约束", encoding="utf-8")

            sample = root / "sample.txt"
            sample.write_text("content from file", encoding="utf-8")

            todo_manager = TodoManager()
            todo_manager.set_items(
                [TodoItem(title="draft section", status="pending")],
                source="test",
            )
            history = HistoryManager(paths)
            resolver = FileReferenceResolver(root)
            message, attachments = resolver.extract("Please read @sample.txt")

            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt()
            user_prompt = builder.build_user_prompt(message, attachments)

            self.assertIn("自定义约束", system_prompt)
            self.assertIn("draft section", user_prompt)
            self.assertIn('"path": "sample.txt"', user_prompt)
            self.assertNotIn("content from file", user_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_template_warns_on_missing_and_reads_config_values(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history, console=console)
            builder._system_template = (
                "Profile {config:llm_profile} nested {config:custom.nested} missing {unknown}"
            )
            builder._user_template = "User message: {user_message} cfg {config:custom.nested}"

            config_data = {"llm_profile": "demo", "custom": {"nested": "value"}}
            system_prompt = builder.build_system_prompt(config=config_data)
            self.assertIn("demo", system_prompt)
            self.assertIn("value", system_prompt)

            warning_output = console.file.getvalue()
            self.assertIn("Warning", warning_output)
            user_prompt = builder.build_user_prompt("msg", [], config=config_data)
            self.assertIn("msg", user_prompt)
            self.assertIn("value", user_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_doc_template_injected_into_system_prompt(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")
            templates_dir = paths.doc_templates_dir
            templates_dir.mkdir(parents=True, exist_ok=True)
            templates_dir.joinpath("demo.md").write_text(
                "# Demo\n\n## Introduction\nDemo template.", encoding="utf-8"
            )

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt(
                config={"doc_template": "demo"}
            )

            self.assertIn("Demo template.", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_default_doc_template_used_when_general(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt(config={"doc_template": "general"})

            self.assertIn("General Document Template", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
