import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI
from dogent.core.file_refs import FileAttachment


def _write_skill(path: Path, name: str, description: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            "---\n"
            f"# {name}\n\n"
            f"{body}\n"
        ),
        encoding="utf-8",
    )


class TemplateCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_template_command_registered(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

            self.assertIsNotNone(cli.registry.get("/template"))
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_and_template_list_show_same_inventory(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            _write_skill(
                root / ".dogent" / "templates" / "product_brief" / "SKILL.md",
                "product_brief",
                "Product brief template",
                "Write a product brief.",
            )
            DogentCLI(
                root=root,
                console=Console(file=io.StringIO(), force_terminal=False, color_system=None),
                interactive_prompts=False,
            )

            console1 = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli1 = DogentCLI(root=root, console=console1, interactive_prompts=False)
            await cli1._handle_command("/template")
            output1 = console1.file.getvalue()

            console2 = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli2 = DogentCLI(root=root, console=console2, interactive_prompts=False)
            await cli2._handle_command("/template list")
            output2 = console2.file.getvalue()

            self.assertEqual(output1, output2)
            self.assertIn("product_brief", output1)
            self.assertIn("built-in:resume", output1)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_create_with_brief_runs_workflow(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._maybe_auto_init_for_request = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command(
                "/template create write a bilingual software usage manual template"
            )

            cli._run_with_interrupt.assert_awaited_once()
            message, attachments = cli._run_with_interrupt.call_args.args[:2]
            self.assertEqual([], attachments)
            self.assertIn("doc-template-creator", message)
            self.assertIn("Mode: create", message)
            self.assertIn("write a bilingual software usage manual template", message)
            self.assertIn("description:", message)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_create_without_brief_shows_usage(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command("/template create")

            cli._run_with_interrupt.assert_not_awaited()
            output = console.file.getvalue()
            self.assertIn("Usage: /template create <free text requirements>", output)
            self.assertIn("Examples:", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_optimize_without_target_shows_inventory(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command("/template optimize")

            cli._run_with_interrupt.assert_not_awaited()
            output = console.file.getvalue()
            self.assertIn(
                "Usage: /template optimize <template> [free text requirements]",
                output,
            )
            self.assertIn("built-in:resume", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_optimize_with_target_runs_workflow(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)
            cli._maybe_auto_init_for_request = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command(
                "/template optimize built-in:resume make it more concise for senior backend engineers"
            )

            cli._run_with_interrupt.assert_awaited_once()
            message, attachments = cli._run_with_interrupt.call_args.args[:2]
            self.assertEqual([], attachments)
            self.assertIn("doc-template-creator", message)
            self.assertIn("Mode: optimize", message)
            self.assertIn("Target template: built-in:resume", message)
            self.assertIn("make it more concise for senior backend engineers", message)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_template_create_supports_file_and_template_references_in_brief(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            note = root / "brief.md"
            note.write_text("Use this source.", encoding="utf-8")
            _write_skill(
                root / ".dogent" / "templates" / "reference_template" / "SKILL.md",
                "reference_template",
                "Reference template",
                "## Writing Requirements\nUse a formal structure.",
            )

            console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
            cli = DogentCLI(root=root, console=console, interactive_prompts=False)
            cli._maybe_auto_init_for_request = mock.AsyncMock(return_value=True)  # type: ignore[assignment]
            cli._run_with_interrupt = mock.AsyncMock()  # type: ignore[assignment]

            await cli._handle_command(
                "/template create use @brief.md and @@reference_template as guidance"
            )

            cli._run_with_interrupt.assert_awaited_once()
            message, attachments = cli._run_with_interrupt.call_args.args[:2]
            self.assertEqual([FileAttachment(path=Path("brief.md"))], attachments)
            self.assertIn("[local file]: brief.md", message)
            self.assertIn("[doc template reference]: reference_template", message)
            self.assertIn("Referenced Template: reference_template", message)
            self.assertIn("Use a formal structure.", message)
