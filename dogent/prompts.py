from __future__ import annotations

import json
import re
import textwrap
from importlib import resources
from typing import Any, Callable, Iterable, List

from rich.console import Console

from .file_refs import FileAttachment
from .paths import DogentPaths
from .todo import TodoManager
from .history import HistoryManager


class TemplateRenderer:
    """Simple placeholder renderer with warnings for missing values."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(
        self,
        template: str,
        resolver: Callable[[str], str | None],
        *,
        template_name: str,
    ) -> str:
        missing: list[str] = []

        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            value = resolver(key)
            if value is None or value == "":
                missing.append(key)
                return ""
            return str(value)

        rendered = re.sub(r"{([^{}]+)}", replace, template)
        if missing:
            unique = ", ".join(sorted(set(missing)))
            self.console.print(
                f"[yellow]Warning: template '{template_name}' missing values for: {unique}. They were replaced with empty strings.[/yellow]"
            )
        return rendered


class PromptBuilder:
    """Builds system and user prompts from templates."""

    def __init__(
        self,
        paths: DogentPaths,
        todo_manager: TodoManager,
        history: HistoryManager,
        console: Console | None = None,
    ) -> None:
        self.paths = paths
        self.todo_manager = todo_manager
        self.history = history
        self.console = console or Console()
        self.renderer = TemplateRenderer(console=self.console)
        self._system_template = self._load_template("system.md")
        self._user_template = self._load_template("user_prompt.md")

    def build_system_prompt(
        self, settings=None, config: dict[str, Any] | None = None
    ) -> str:
        config_data = config or {}
        context = self._base_context(settings, config_data)
        rendered = self.renderer.render(
            self._system_template,
            lambda key: self._resolve_value(key, context, config_data),
            template_name="system prompt",
        )
        lessons = context.get("lessons", "")
        if lessons and "{lessons}" not in self._system_template:
            rendered = rendered.rstrip() + "\n\n## Lessons\n\n" + lessons.strip() + "\n"
        return rendered

    def build_user_prompt(
        self,
        user_message: str,
        attachments: List[FileAttachment],
        settings=None,
        config: dict[str, Any] | None = None,
    ) -> str:
        config_data = config or {}
        context = self._base_context(settings, config_data)
        context.update(
            {
                "user_message": user_message.strip(),
                "attachments": self._format_attachments(attachments),
            }
        )
        return self.renderer.render(
            self._user_template,
            lambda key: self._resolve_value(key, context, config_data),
            template_name="user prompt",
        )

    def _base_context(self, settings, config: dict[str, Any]) -> dict[str, str]:
        preferences = self._read_preferences()
        history_full = self.history.read_raw()
        recent_history = self.history.to_prompt_block()
        memory_content = self._read_memory()
        lessons_content = self._read_lessons()
        todo_plain = self.todo_manager.render_plain()
        return {
            "working_dir": str(self.paths.root),
            "preferences": preferences,
            "history": history_full,
            "history:last": recent_history,
            "history_block": recent_history,
            "memory": memory_content,
            "lessons": lessons_content,
            "todo_block": todo_plain,
            "todo_list": todo_plain,
        }

    def _resolve_value(
        self, key: str, context: dict[str, str], config: dict[str, Any]
    ) -> str | None:
        if key.startswith("config:"):
            return self._resolve_config_value(config, key.split("config:", 1)[1])
        return context.get(key)

    def _resolve_config_value(self, config: dict[str, Any], path: str) -> str | None:
        if not config:
            return None
        current: Any = config
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current.get(part)
            else:
                return None
        if current is None:
            return ""
        if isinstance(current, (dict, list)):
            return json.dumps(current, ensure_ascii=False)
        return str(current)

    def _read_preferences(self) -> str:
        fallback = "Not provided; ask the user to run /init and fill .dogent/dogent.md."
        if self.paths.doc_preferences.exists():
            text = self.paths.doc_preferences.read_text(
                encoding="utf-8", errors="replace"
            ).strip()
            return text or fallback
        return fallback

    def _read_memory(self) -> str:
        if not self.paths.memory_file.exists():
            return ""
        try:
            return self.paths.memory_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _read_lessons(self) -> str:
        if not self.paths.lessons_file.exists():
            return "No lessons recorded yet."
        try:
            text = self.paths.lessons_file.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                return "No lessons recorded yet."
            max_chars = 20000
            if len(text) <= max_chars:
                return text
            tail = text[-max_chars:]
            return (
                f"(Lessons truncated to the last {max_chars} characters. Edit .dogent/lessons.md to prune.)\n\n"
                + tail
            )
        except Exception:
            return "No lessons recorded yet."

    def _format_attachments(self, attachments: Iterable[FileAttachment]) -> str:
        attachments = list(attachments)
        if not attachments:
            return "No @file context."
        blocks = []
        for attachment in attachments:
            notice = " (truncated)" if attachment.truncated else ""
            blocks.append(
                textwrap.dedent(
                    f"""\
                    @file {attachment.path}{notice}
                    ```
                    {attachment.content}
                    ```
                    """
                ).strip()
            )
        return "\n\n".join(blocks)

    def _load_template(self, name: str) -> str:
        local = self.paths.global_prompts_dir / name
        if local.exists():
            return local.read_text(encoding="utf-8")
        base = resources.files("dogent").joinpath("prompts")
        return base.joinpath(name).read_text(encoding="utf-8")
