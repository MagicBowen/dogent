import tempfile
import unittest
from pathlib import Path

from prompt_toolkit.document import Document

from dogent.cli import DogentCompleter


class DogentCompleterTests(unittest.TestCase):
    def test_command_completion(self) -> None:
        completer = DogentCompleter(Path("."), ["/init", "/config"])
        comps = list(completer.get_completions(Document("/i"), None))
        texts = [c.text for c in comps]
        self.assertIn("/init", texts)

    def test_file_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "context.txt").write_text("hi", encoding="utf-8")
            completer = DogentCompleter(root, ["/init"])
            comps = list(completer.get_completions(Document("read @"), None))
            texts = [c.text for c in comps]
            self.assertIn("context.txt", texts)


if __name__ == "__main__":
    unittest.main()
