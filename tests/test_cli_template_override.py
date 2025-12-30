import io
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.cli import DogentCLI
from dogent.file_refs import FileAttachment


class TemplateOverrideTests(unittest.TestCase):
    def test_extract_template_override(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            message, template = cli._extract_template_override("Write @@demo")
            self.assertEqual(message, "Write")
            self.assertEqual(template, "demo")

            message, template = cli._extract_template_override("Start @@alpha then @@beta")
            self.assertEqual(message, "Start then")
            self.assertEqual(template, "beta")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_normalize_template_override(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli.paths.doc_templates_dir.mkdir(parents=True, exist_ok=True)
            cli.paths.doc_templates_dir.joinpath("demo.md").write_text(
                "# Demo\n\n## Introduction\nTest\n", encoding="utf-8"
            )

            self.assertEqual(cli._normalize_template_override("demo"), "demo")
            self.assertIsNone(cli._normalize_template_override("missing"))
            self.assertEqual(
                cli._build_prompt_override("demo"),
                {"doc_template": "demo"},
            )
            self.assertIsNone(cli._build_prompt_override(None))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_blocked_media_attachments_when_vision_disabled(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            image_path = root / "image.png"
            image_path.write_bytes(b"fake")
            attachments = [FileAttachment(path=Path("image.png"))]

            blocked = cli._blocked_media_attachments(attachments)
            self.assertEqual(blocked, [Path("image.png")])

            cli.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            cli.paths.config_file.write_text(
                '{"vision_profile": "glm-4.6v"}',
                encoding="utf-8",
            )
            blocked = cli._blocked_media_attachments(attachments)
            self.assertEqual(blocked, [])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
