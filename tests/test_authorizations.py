import json
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths


class AuthorizationConfigTests(unittest.TestCase):
    def test_add_authorizations_records_paths(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(record=True, force_terminal=False, color_system=None)
            manager = ConfigManager(DogentPaths(root), console=console)
            inside_path = root / "notes.txt"
            outside_path = Path("/tmp/dogent-test.txt")

            manager.add_authorizations("Read", [inside_path, outside_path])

            data = json.loads(manager.paths.config_file.read_text(encoding="utf-8"))
            authorizations = data.get("authorizations", {})
            self.assertIn("Read", authorizations)
            patterns = authorizations["Read"]
            self.assertIn("notes.txt", patterns)
            self.assertIn(str(outside_path.resolve()), patterns)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
