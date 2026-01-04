import tempfile
import unittest
from pathlib import Path

from prompt_toolkit.document import Document

from dogent.cli import DogentCompleter


class DogentCompleterTests(unittest.TestCase):
    def test_command_completion(self) -> None:
        completer = DogentCompleter(Path("."), ["/init", "/help"])
        comps = list(completer.get_completions(Document("/i"), None))
        texts = [c.text for c in comps]
        self.assertIn("/init", texts)

    def test_command_args_completion_does_not_show_all_commands_on_space(self) -> None:
        completer = DogentCompleter(Path("."), ["/learn", "/help", "/init"])
        comps = list(completer.get_completions(Document("/learn "), None))
        texts = [c.text for c in comps]
        self.assertIn("on", texts)
        self.assertIn("off", texts)
        self.assertNotIn("/help", texts)

        comps = list(completer.get_completions(Document("/help "), None))
        self.assertEqual([], [c.text for c in comps])

        # After the user starts typing free-form text for /learn, do not keep
        # popping the fixed on/off list on every subsequent space.
        comps = list(completer.get_completions(Document("/learn do this "), None))
        self.assertEqual([], [c.text for c in comps])

        comps = list(completer.get_completions(Document("/learn on "), None))
        self.assertEqual([], [c.text for c in comps])

    def test_clear_command_shows_target_options(self) -> None:
        completer = DogentCompleter(Path("."), ["/clean"])
        comps = list(completer.get_completions(Document("/clean "), None))
        texts = [c.text for c in comps]
        self.assertIn("history", texts)
        self.assertIn("lesson", texts)
        self.assertIn("memory", texts)
        self.assertIn("all", texts)

    def test_show_command_shows_targets(self) -> None:
        completer = DogentCompleter(Path("."), ["/show"])
        comps = list(completer.get_completions(Document("/show "), None))
        texts = [c.text for c in comps]
        self.assertIn("history", texts)
        self.assertIn("lessons", texts)

    def test_archive_command_shows_targets(self) -> None:
        completer = DogentCompleter(Path("."), ["/archive"])
        comps = list(completer.get_completions(Document("/archive "), None))
        texts = [c.text for c in comps]
        self.assertIn("history", texts)
        self.assertIn("lessons", texts)
        self.assertIn("all", texts)

    def test_init_template_completion(self) -> None:
        templates = ["built-in:resume", "global:research-report"]
        completer = DogentCompleter(
            Path("."), ["/init"], template_provider=lambda: templates
        )
        comps = list(completer.get_completions(Document("/init re"), None))
        texts = [c.text for c in comps]
        self.assertIn("built-in:resume", texts)

    def test_file_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "context.txt").write_text("hi", encoding="utf-8")
            completer = DogentCompleter(root, ["/init"])
            comps = list(completer.get_completions(Document("read @"), None))
            texts = [c.text for c in comps]
            self.assertIn("context.txt", texts)

    def test_edit_completion_filters_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "note.md").write_text("hi", encoding="utf-8")
            (root / "data.csv").write_text("1,2", encoding="utf-8")
            (root / "docs").mkdir()
            completer = DogentCompleter(root, ["/edit"])
            comps = list(completer.get_completions(Document("/edit "), None))
            texts = [c.text for c in comps]
            self.assertIn("note.md", texts)
            self.assertIn("docs/", texts)
            self.assertNotIn("data.csv", texts)


if __name__ == "__main__":
    unittest.main()
