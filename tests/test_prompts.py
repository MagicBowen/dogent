import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
