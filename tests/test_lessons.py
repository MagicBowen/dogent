import os
import tempfile
import unittest
from pathlib import Path

from dogent.core.history import HistoryManager
from dogent.features.lessons import LessonsManager
from dogent.config.paths import DogentPaths
from dogent.prompts import PromptBuilder
from dogent.core.todo import TodoManager


class LessonsManagerTests(unittest.TestCase):
    def test_append_entry_creates_file_and_lists_titles(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            manager = LessonsManager(paths)

            path = manager.append_entry("## My Lesson\n\n### Problem\nx\n\n### Cause\ny\n\n### Correct Approach\nz\n")
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("# Lessons", text)
            self.assertIn("## My Lesson", text)
            titles = manager.list_recent_titles(limit=5)
            self.assertIn("My Lesson", titles)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_system_prompt_includes_lessons_file(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.lessons_file.write_text("# Lessons\n\n## L1\n\nok\n", encoding="utf-8")

            builder = PromptBuilder(paths, TodoManager(), HistoryManager(paths))
            system_prompt = builder.build_system_prompt()
            self.assertIn("## L1", system_prompt)

        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()

