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
        with tempfile.TemporaryDirectory() as tmp:
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
            self.assertIn("content from file", user_prompt)
            self.assertIn("@file sample.txt", user_prompt)

    def test_system_prompt_uses_configured_images_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("约束", encoding="utf-8")
            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)

            settings = type("Settings", (), {"images_path": "/tmp/custom/images"})
            prompt = builder.build_system_prompt(settings=settings)

            self.assertIn("/tmp/custom/images", prompt)

    def test_template_warns_on_missing_and_reads_config_values(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            prompts_dir = Path(tmp_home) / ".dogent" / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            (prompts_dir / "system.md").write_text(
                "Profile {config:profile} nested {config:custom.nested} missing {unknown}",
                encoding="utf-8",
            )
            (prompts_dir / "user_prompt.md").write_text(
                "User message: {user_message} cfg {config:custom.nested}", encoding="utf-8"
            )

            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history, console=console)

            config_data = {"profile": "demo", "custom": {"nested": "value"}}
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


if __name__ == "__main__":
    unittest.main()
