import io
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.core.file_refs import FileReferenceResolver
from dogent.core.history import HistoryManager
from dogent.config.paths import DogentPaths
from dogent.prompts import PromptBuilder, TemplateRenderer
from dogent.core.todo import TodoItem, TodoManager


class PromptTests(unittest.TestCase):
    def _write_template(
        self,
        root: Path,
        name: str,
        skill_text: str,
        *,
        templates: dict[str, str] | None = None,
    ) -> None:
        template_dir = root / name
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
        for rel_path, text in (templates or {}).items():
            ref_path = template_dir / "templates" / rel_path
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(text, encoding="utf-8")

    def test_prompts_include_todos_and_files(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
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
            self.assertIn("Referenced Files", user_prompt)
            self.assertIn("- sample.txt", user_prompt)
            self.assertNotIn("content from file", user_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_template_warns_on_missing_and_reads_config_values(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history, console=console)
            builder._system_template = (
                "Profile {config:llm_profile} nested {config:custom.nested} missing {unknown}"
            )
            builder._user_template = "User message: {user_message} cfg {config:custom.nested}"

            config_data = {"llm_profile": "demo", "custom": {"nested": "value"}}
            system_prompt = builder.build_system_prompt(config=config_data)
            self.assertIn("demo", system_prompt)
            self.assertIn("value", system_prompt)

            warning_output = console.file.getvalue()
            self.assertIn("Warning", warning_output)
            user_prompt = builder.build_user_prompt("msg", [], config=config_data)
            self.assertIn("msg", user_prompt)
            self.assertIn("value", user_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_template_renderer_skips_json_braces(self) -> None:
        console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
        renderer = TemplateRenderer(console=console)
        template = 'Schema: {"label": "A"} and {working_dir}'

        def resolver(key: str) -> str | None:
            if key == "working_dir":
                return "/tmp"
            return None

        rendered = renderer.render(template, resolver, template_name="test")
        self.assertIn('{"label": "A"}', rendered)
        output = console.file.getvalue()
        self.assertNotIn("Warning: template 'test' missing values", output)

    def test_doc_template_injected_into_system_prompt(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")
            templates_dir = paths.doc_templates_dir
            templates_dir.mkdir(parents=True, exist_ok=True)
            self._write_template(
                templates_dir,
                "demo",
                "---\nname: demo\ndescription: Demo template.\n---\n# Demo\n\n## Introduction\nDemo intro.\n\n## Writing Requirements\nDemo requirements.",
            )

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt(
                config={"doc_template": "demo"}
            )

            self.assertIn("Demo requirements.", system_prompt)
            self.assertNotIn("Demo intro.", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_default_doc_template_used_when_general(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt(config={"doc_template": "general"})

            self.assertIn("Start with a brief overview or context.", system_prompt)
            self.assertNotIn("General-purpose template for professional documents", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_template_override_moves_to_user_prompt(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")
            templates_dir = paths.doc_templates_dir
            templates_dir.mkdir(parents=True, exist_ok=True)
            self._write_template(
                templates_dir,
                "override",
                "---\nname: override\ndescription: Override template.\n---\n# Override\n\n## Introduction\nOverride intro.\n\n## Writing Requirements\nOverride requirements.",
            )

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            config = {"doc_template": "general", "doc_template_override": "override"}
            system_prompt = builder.build_system_prompt(config=config)
            user_prompt = builder.build_user_prompt("msg", [], config=config)

            self.assertNotIn("Override requirements.", system_prompt)
            self.assertIn("Doc Template Reference", user_prompt)
            self.assertIn("Override requirements.", user_prompt)
            self.assertNotIn("Override intro.", user_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_doc_template_templates_are_appended_to_prompt_content(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.doc_preferences.write_text("prefs", encoding="utf-8")
            self._write_template(
                paths.doc_templates_dir,
                "demo",
                "---\nname: demo\ndescription: Demo template.\n---\n# Demo\n\n## Introduction\nBase intro.\n\n## Writing Requirements\nBase template.",
                templates={"sections.md": "Section rules."},
            )

            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)
            system_prompt = builder.build_system_prompt(config={"doc_template": "demo"})

            self.assertIn("Base template.", system_prompt)
            self.assertNotIn("Base intro.", system_prompt)
            self.assertIn("## Output Template: templates/sections.md", system_prompt)
            self.assertIn("Section rules.", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_system_prompt_distinguishes_sdk_questions_and_ui_requests(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            todo_manager = TodoManager()
            history = HistoryManager(paths)
            builder = PromptBuilder(paths, todo_manager, history)

            system_prompt = builder.build_system_prompt()

            self.assertIn("Use `AskUserQuestion` for simple clarification only", system_prompt)
            self.assertIn("Use the MCP tool `mcp__dogent__ui_request`", system_prompt)
            self.assertIn("Plain-text questions are not allowed", system_prompt)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
