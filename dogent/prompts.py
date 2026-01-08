from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable, List

from rich.console import Console

from .features.doc_templates import DocumentTemplateManager
from .core.file_refs import FileAttachment
from .config.paths import DogentPaths
from .config.resources import read_prompt_text, read_template_text
from .core.todo import TodoManager
from .core.history import HistoryManager


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
        suppress_empty_keys: set[str] | None = None,
    ) -> str:
        missing: list[str] = []
        suppress = suppress_empty_keys or set()

        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            if "\"" in key:
                return "{" + key + "}"
            value = resolver(key)
            if value is None or value == "":
                if key in suppress:
                    return ""
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
        self.doc_templates = DocumentTemplateManager(self.paths)
        self.renderer = TemplateRenderer(console=self.console)
        self._system_template = self._load_template("system.md")
        self._user_template = self._load_template("user_prompt.md")
        self._default_doc_template = self._load_default_doc_template()

    def build_system_prompt(
        self, settings=None, config: dict[str, Any] | None = None
    ) -> str:
        config_data = config or {}
        template_override = self._template_override_key(config_data)
        context = self._base_context(settings, config_data)
        suppress_empty_keys: set[str] | None = None
        if template_override:
            context["doc_template"] = ""
            suppress_empty_keys = {"doc_template"}
        rendered = self.renderer.render(
            self._system_template,
            lambda key: self._resolve_value(key, context, config_data),
            template_name="system prompt",
            suppress_empty_keys=suppress_empty_keys,
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
        template_override = self._template_override_key(config_data)
        context = self._base_context(settings, config_data)
        doc_template_block = ""
        if template_override:
            override_content = self._resolve_template_override_content(template_override)
            doc_template_block = (
                "\nDoc Template Reference:\n"
                f"- {template_override}\n\n"
                "Note:\n"
                "- Workspace templates use plain names (e.g., `resume`).\n"
                "- Global templates require `global:` prefix.\n"
                "- Built-in templates require `built-in:` prefix.\n"
                "- Templates are used to guide how to write and the format of output documents, not user content.\n\n"
                "Doc Template Content (User-specified Override):\n"
                "```markdown\n"
                f"{override_content.strip() if override_content else ''}\n"
                "```\n"
            )
        context.update(
            {
                "user_message": user_message.strip(),
                "attachments": self._format_attachments(attachments),
                "file_refs_block": self._format_file_refs_block(attachments),
                "doc_template_block": doc_template_block,
            }
        )
        rendered = self.renderer.render(
            self._user_template,
            lambda key: self._resolve_value(key, context, config_data),
            template_name="user prompt",
            suppress_empty_keys={"doc_template_block"},
        )
        return rendered

    def _base_context(self, settings, config: dict[str, Any]) -> dict[str, str]:
        preferences = self._read_preferences()
        history_full = self.history.read_raw()
        recent_history = self.history.to_prompt_block()
        memory_content = self._read_memory()
        lessons_content = self._read_lessons()
        todo_plain = self.todo_manager.render_plain()
        doc_template = self._read_doc_template(config)
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
            "doc_template": doc_template,
        }

    def _template_override_key(self, config: dict[str, Any]) -> str | None:
        raw = (config or {}).get("doc_template_override")
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip()
        return cleaned if cleaned else None

    def _resolve_template_override_content(self, template_key: str) -> str:
        resolved = self.doc_templates.resolve(template_key)
        if not resolved:
            self.console.print(
                f"[yellow]Warning: doc_template override '{template_key}' not found. Skipping override content.[/yellow]"
            )
            return ""
        return resolved.content.strip()

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

    def _read_doc_template(self, config: dict[str, Any]) -> str:
        key = (config or {}).get("doc_template")
        if not key or (isinstance(key, str) and key.strip().lower() == "general"):
            return self._default_doc_template
        resolved = self.doc_templates.resolve(str(key) if key is not None else None)
        if not resolved:
            self.console.print(
                f"[yellow]Warning: doc_template '{key}' not found. Using default template.[/yellow]"
            )
            return self._default_doc_template
        return resolved.content.strip()

    def _format_attachments(self, attachments: Iterable[FileAttachment]) -> str:
        attachments = list(attachments)
        if not attachments:
            return "[]"
        payloads: list[dict[str, object]] = []
        for attachment in attachments:
            item: dict[str, object] = {
                "path": str(attachment.path),
                "name": attachment.path.name,
            }
            if attachment.sheet:
                item["sheet"] = attachment.sheet
            suffix = attachment.path.suffix.lstrip(".").lower()
            item["type"] = suffix or "file"
            payloads.append(item)
        return json.dumps(payloads, ensure_ascii=False)

    def _format_file_refs_block(self, attachments: Iterable[FileAttachment]) -> str:
        attachments = list(attachments)
        if not attachments:
            return "None"
        lines: list[str] = []
        for attachment in attachments:
            suffix = f"#{attachment.sheet}" if attachment.sheet else ""
            lines.append(f"- {attachment.path}{suffix}")
        return "\n".join(lines)

    def _load_template(self, name: str) -> str:
        return read_prompt_text(name)

    def _load_default_doc_template(self) -> str:
        text = read_template_text("doc_general.md").strip()
        return text or "General document template not available."
