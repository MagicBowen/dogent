import os
import tempfile
import unittest
from pathlib import Path

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.features.lesson_drafter import ClaudeLessonDrafter


class LessonDrafterTests(unittest.TestCase):
    def test_build_options_uses_tools_empty_array(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            drafter = ClaudeLessonDrafter(ConfigManager(paths), paths)

            options = drafter._build_options("sys")
            self.assertEqual(options.tools, [])
            self.assertEqual(options.allowed_tools, [])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
