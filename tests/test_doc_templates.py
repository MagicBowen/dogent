import os
import tempfile
import unittest
from pathlib import Path

from dogent.features.doc_templates import DocumentTemplateManager
from dogent.config.paths import DogentPaths


class DocTemplateTests(unittest.TestCase):
    def test_extract_intro_prefers_introduction_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "# Title",
                    "",
                    "## Introduction",
                    "First line.",
                    "Second line.",
                    "",
                    "## Details",
                    "Other content.",
                ]
            )
            intro = manager._extract_intro(content)
            self.assertEqual(intro, "First line. Second line.")

    def test_extract_intro_falls_back_to_first_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "Line 1",
                    "Line 2",
                    "Line 3",
                    "Line 4",
                    "Line 5",
                    "Line 6",
                ]
            )
            intro = manager._extract_intro(content)
            self.assertEqual(intro, "Line 1 Line 2 Line 3 Line 4 Line 5")

    def test_resolve_precedence_and_prefixes(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            workspace_dir = paths.doc_templates_dir
            workspace_dir.mkdir(parents=True, exist_ok=True)
            (workspace_dir / "sample.md").write_text("workspace template", encoding="utf-8")

            global_dir = paths.global_templates_dir
            global_dir.mkdir(parents=True, exist_ok=True)
            (global_dir / "sample.md").write_text("global template", encoding="utf-8")

            manager = DocumentTemplateManager(paths)

            resolved = manager.resolve("sample")
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.source, "workspace")
            self.assertIn("workspace template", resolved.content)

            resolved_global = manager.resolve("global:sample")
            self.assertIsNotNone(resolved_global)
            self.assertEqual(resolved_global.source, "global")
            self.assertIn("global template", resolved_global.content)

            built_in = manager.resolve("built-in:resume")
            self.assertIsNotNone(built_in)
            self.assertIn("Resume", built_in.content)

            self.assertIsNone(manager.resolve("resume"))

            general = manager.resolve("general")
            self.assertIsNotNone(general)
            self.assertIn("General Document Template", general.content)

            display_names = manager.list_display_names()
            self.assertIn("sample", display_names)
            self.assertIn("global:sample", display_names)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
