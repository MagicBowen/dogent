import os
import tempfile
import unittest
from pathlib import Path

from dogent.features.doc_templates import DocumentTemplateManager
from dogent.config.paths import DogentPaths


class DocTemplateTests(unittest.TestCase):
    def test_extract_description_prefers_frontmatter_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "---",
                    "name: demo",
                    "description: Frontmatter description.",
                    "---",
                    "# Title",
                    "",
                    "Body paragraph.",
                ]
            )
            intro = manager._extract_description(content)
            self.assertEqual(intro, "Frontmatter description.")

    def test_extract_description_does_not_fall_back_to_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "---",
                    "name: demo",
                    "---",
                    "# Demo",
                    "",
                    "First paragraph.",
                    "Still first paragraph.",
                    "",
                    "Second paragraph.",
                ]
            )
            intro = manager._extract_description(content)
            self.assertEqual(intro, "")

    def test_extract_description_supports_indented_yaml_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "---",
                    "name: demo",
                    "description:",
                    "  Consultant proposal template for structured delivery plans.",
                    "---",
                    "# Demo",
                ]
            )
            intro = manager._extract_description(content)
            self.assertEqual(
                intro,
                "Consultant proposal template for structured delivery plans.",
            )

    def test_strip_intro_block_prefers_introduction_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join(
                [
                    "# Demo",
                    "",
                    "## Introduction",
                    "Intro line 1.",
                    "Intro line 2.",
                    "",
                    "## Writing Requirements",
                    "- Keep it concise.",
                ]
            )
            stripped = manager._strip_intro_block(content)
            self.assertEqual(
                stripped,
                "## Writing Requirements\n- Keep it concise.",
            )

    def test_strip_intro_block_falls_back_to_dropping_first_ten_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            manager = DocumentTemplateManager(paths)
            content = "\n".join([f"Line {index}" for index in range(1, 15)])
            stripped = manager._strip_intro_block(content)
            self.assertEqual(
                stripped,
                "\n".join([f"Line {index}" for index in range(11, 15)]),
            )

    def test_resolve_precedence_and_prefixes(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            workspace_dir = paths.doc_templates_dir
            (workspace_dir / "sample").mkdir(parents=True, exist_ok=True)
            (workspace_dir / "sample" / "SKILL.md").write_text(
                "---\nname: sample\ndescription: Workspace sample\n---\n# Sample\n\nworkspace template",
                encoding="utf-8",
            )

            global_dir = paths.global_templates_dir
            (global_dir / "sample").mkdir(parents=True, exist_ok=True)
            (global_dir / "sample" / "SKILL.md").write_text(
                "---\nname: sample\ndescription: Global sample\n---\n# Sample\n\nglobal template",
                encoding="utf-8",
            )

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
            self.assertIn("## Writing Steps (Process)", built_in.content)
            self.assertNotIn("## Introduction", built_in.content)

            self.assertIsNone(manager.resolve("resume"))

            general = manager.resolve("general")
            self.assertIsNotNone(general)
            self.assertIn("## Writing Requirements", general.content)
            self.assertNotIn("## Introduction", general.content)

            display_names = manager.list_display_names()
            self.assertIn("sample", display_names)
            self.assertIn("global:sample", display_names)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_resolve_aggregates_templates_and_ignores_examples_assets_and_legacy_flat_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            template_root = paths.doc_templates_dir / "brief"
            template_root.mkdir(parents=True, exist_ok=True)
            (template_root / "SKILL.md").write_text(
                "---\nname: brief\ndescription: Brief template\n---\n# Brief\n\n## Introduction\nIntro guidance.\n\n## Writing Requirements\nBase guidance.",
                encoding="utf-8",
            )
            (template_root / "templates").mkdir(parents=True, exist_ok=True)
            (template_root / "templates" / "audience.md").write_text(
                "Audience guidance.",
                encoding="utf-8",
            )
            (template_root / "templates" / "nested").mkdir(parents=True, exist_ok=True)
            (template_root / "templates" / "nested" / "output.md").write_text(
                "Output guidance.",
                encoding="utf-8",
            )
            (template_root / "examples").mkdir(parents=True, exist_ok=True)
            (template_root / "examples" / "sample.md").write_text(
                "Example content that should not be auto-injected.",
                encoding="utf-8",
            )
            (template_root / "assets").mkdir(parents=True, exist_ok=True)
            (template_root / "assets" / "diagram.svg").write_text(
                "<svg></svg>",
                encoding="utf-8",
            )
            paths.doc_templates_dir.mkdir(parents=True, exist_ok=True)
            (paths.doc_templates_dir / "legacy.md").write_text(
                "# Legacy\n\nShould be ignored.",
                encoding="utf-8",
            )

            manager = DocumentTemplateManager(paths)

            resolved = manager.resolve("brief")
            self.assertIsNotNone(resolved)
            assert resolved is not None
            self.assertIn("Base guidance.", resolved.content)
            self.assertNotIn("Intro guidance.", resolved.content)
            self.assertIn("## Output Template: templates/audience.md", resolved.content)
            self.assertIn("Audience guidance.", resolved.content)
            self.assertIn("## Output Template: templates/nested/output.md", resolved.content)
            self.assertIn("Output guidance.", resolved.content)
            self.assertNotIn("Example content that should not be auto-injected.", resolved.content)
            self.assertNotIn("legacy", manager.list_display_names())
            self.assertIsNone(manager.resolve("legacy"))


if __name__ == "__main__":
    unittest.main()
