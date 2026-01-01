from __future__ import annotations

import argparse
import errno
import asyncio
import re
import select
import sys
import termios
import threading
import time
import tty
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Tuple

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .agent import AgentRunner
from .clarification import (
    ClarificationPayload,
    ClarificationQuestion,
    ClarificationOption,
    recommended_index,
)
from .commands import CommandRegistry
from .config import ConfigManager
from .doc_templates import DocumentTemplateManager
from .file_refs import FileAttachment, FileReferenceResolver
from .history import HistoryManager
from .init_wizard import InitWizard
from .lesson_drafter import ClaudeLessonDrafter, LessonDrafter
from .lessons import LessonIncident, LessonsManager
from .paths import DogentPaths
from .prompts import PromptBuilder
from .todo import TodoManager
from .vision import classify_media

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import Application
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style
    from prompt_toolkit.utils import get_cwidth
except ImportError:  # pragma: no cover - optional dependency
    PromptSession = None  # type: ignore
    Application = None  # type: ignore
    Completer = object  # type: ignore
    Completion = object  # type: ignore
    Document = object  # type: ignore
    KeyBindings = None  # type: ignore
    Layout = None  # type: ignore
    Window = None  # type: ignore
    FormattedTextControl = None  # type: ignore
    Style = None  # type: ignore
    get_cwidth = None  # type: ignore


DOC_TEMPLATE_TOKEN = "@@"


class ClarificationTimeout(Exception):
    pass


class ClarificationCancelled(Exception):
    pass


class DogentCompleter(Completer):
    """Suggests slash commands and @file paths while typing."""

    def __init__(
        self,
        root: Path,
        commands: list[str],
        *,
        template_provider: Callable[[], Iterable[str]] | None = None,
    ) -> None:
        self.root = root
        self.commands = commands
        self.template_provider = template_provider

    def get_completions(self, document: Document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        if text.startswith("/"):
            for comp in self._command_completions(text):
                yield comp
            return

        if self.template_provider and DOC_TEMPLATE_TOKEN in text:
            template_completions = list(self._match_templates(text))
            if template_completions:
                for comp in template_completions:
                    yield comp
                return

        if "@" in text:
            for comp in self._match_files(text):
                yield comp

    def _command_completions(self, text: str) -> Iterable[Completion]:
        tokens = text.split()
        if not tokens:
            return []

        command = tokens[0]
        if len(tokens) == 1 and not text.endswith(" "):
            matches = [c for c in self.commands if c.startswith(command)]
            if not matches:
                return []
            return [Completion(cmd, start_position=-len(command)) for cmd in matches]

        # If the user has already started typing arguments and then types spaces,
        # do not keep re-suggesting "fixed" args on every subsequent space.
        if len(tokens) >= 2 and text.endswith(" "):
            return []

        if len(tokens) == 1 and text.endswith(" "):
            return self._arg_completions(command, "")

        arg_prefix = "" if text.endswith(" ") else tokens[-1]
        return self._arg_completions(command, arg_prefix)

    def _arg_completions(self, command: str, arg_prefix: str) -> Iterable[Completion]:
        options: list[str] = []
        if command == "/learn":
            options = ["on", "off"]
        elif command == "/clean":
            options = ["history", "lesson", "memory", "all"]
        elif command == "/show":
            options = ["history", "lessons"]
        elif command == "/archive":
            options = ["history", "lessons", "all"]
        elif command == "/init" and self.template_provider:
            options = list(self.template_provider())
        if not options:
            return []
        if command == "/init":
            matches = []
            for opt in options:
                name = opt.split(":", 1)[1] if ":" in opt else opt
                if opt.startswith(arg_prefix) or name.startswith(arg_prefix):
                    matches.append(opt)
        else:
            matches = [opt for opt in options if opt.startswith(arg_prefix)]
        return [Completion(opt, start_position=-len(arg_prefix)) for opt in matches]

    def _match_files(self, text: str) -> Iterable[Completion]:
        at_index = text.rfind("@")
        if at_index == -1:
            return []
        partial = text[at_index + 1 :]
        base = self.root
        prefix = partial
        if "/" in partial:
            parts = partial.split("/")
            prefix = parts[-1]
            base = self.root.joinpath(*parts[:-1])
        if not base.exists() or not base.is_dir():
            return []

        results = []
        for path in sorted(base.iterdir()):
            if path.name.startswith("."):
                continue
            if path.is_dir():
                candidate = path.name + "/"
            else:
                candidate = path.name
            if candidate.startswith(prefix):
                rel = path.relative_to(self.root)
                insert = str(rel)
                results.append(
                    Completion(
                        insert,
                        start_position=-(len(partial)),
                        display=str(rel),
                    )
                )
            if len(results) >= 30:
                break
        return results

    def _match_templates(self, text: str) -> Iterable[Completion]:
        token_index = text.rfind(DOC_TEMPLATE_TOKEN)
        if token_index == -1:
            return []
        if token_index > 0 and not text[token_index - 1].isspace():
            return []
        partial = text[token_index + len(DOC_TEMPLATE_TOKEN) :]
        if " " in partial or "\n" in partial:
            return []
        options = list(self.template_provider()) if self.template_provider else []
        if not options:
            return []
        matches = [opt for opt in options if opt.startswith(partial)]
        return [
            Completion(opt, start_position=-len(partial), display=opt)
            for opt in matches
        ]


def _should_move_within_multiline(document: Document, direction: str) -> bool:
    if not document or document.line_count <= 1:
        return False
    if direction == "up":
        return document.cursor_position_row > 0
    if direction == "down":
        return document.cursor_position_row < document.line_count - 1
    return False


def _cursor_target_from_render_info(
    document: Document, render_info: object, direction: str
) -> int | None:
    mapping = getattr(render_info, "visible_line_to_row_col", None)
    cursor = getattr(render_info, "cursor_position", None)
    rowcol_to_yx = getattr(render_info, "_rowcol_to_yx", None)
    x_offset = getattr(render_info, "_x_offset", 0)
    if not mapping or cursor is None or not rowcol_to_yx:
        return None
    if direction == "up":
        target_y = cursor.y - 1
    elif direction == "down":
        target_y = cursor.y + 1
    else:
        return None
    rowcol = mapping.get(target_y)
    if not rowcol:
        return None
    row, start_col = rowcol
    lines = document.lines
    if row < 0 or row >= len(lines):
        return None
    start_col = _display_offset_to_col(lines[row], 0, start_col)
    start_yx = rowcol_to_yx.get((row, start_col))
    if not start_yx:
        return None
    _, start_x = start_yx
    start_x -= x_offset
    offset_x = cursor.x - start_x
    if offset_x < 0:
        offset_x = 0
    target_col = _display_offset_to_col(lines[row], start_col, offset_x)
    return document.translate_row_col_to_index(row, target_col)


def _cell_width(char: str) -> int:
    if get_cwidth is None:
        return 1
    width = get_cwidth(char)
    return width if width > 0 else 0


def _display_offset_to_col(line: str, start_col: int, offset_x: int) -> int:
    if offset_x <= 0:
        return start_col
    width = 0
    col = start_col
    while col < len(line):
        char_width = _cell_width(line[col])
        if width + char_width > offset_x:
            return col
        width += char_width
        col += 1
        if width == offset_x:
            return col
    return len(line)


def _clear_count_for_alt_backspace(document: Document) -> int:
    if document.line_count > 1:
        return len(document.current_line_before_cursor)
    return document.cursor_position


class DogentCLI:
    """Interactive CLI interface for Dogent."""

    def __init__(
        self,
        root: Path | None = None,
        console: Console | None = None,
        *,
        lesson_drafter: LessonDrafter | None = None,
        interactive_prompts: bool = True,
    ) -> None:
        self.console = console or Console()
        self.root = root or Path.cwd()
        self.registry = CommandRegistry()
        self.paths = DogentPaths(self.root)
        self.todo_manager = TodoManager(console=self.console)
        self.config_manager = ConfigManager(self.paths, console=self.console)
        self.doc_templates = DocumentTemplateManager(self.paths)
        self.init_wizard = InitWizard(
            config=self.config_manager,
            paths=self.paths,
            templates=self.doc_templates,
            console=self.console,
        )
        self.file_resolver = FileReferenceResolver(self.root)
        self.history_manager = HistoryManager(self.paths)
        project_cfg = self.config_manager.load_project_config()
        self.lessons_manager = LessonsManager(self.paths, console=self.console)
        self.prompt_builder = PromptBuilder(
            self.paths, self.todo_manager, self.history_manager, console=self.console
        )
        self._permission_prompt_active = threading.Event()
        self._interactive_prompts = interactive_prompts
        self.agent = AgentRunner(
            config=self.config_manager,
            prompt_builder=self.prompt_builder,
            todo_manager=self.todo_manager,
            history=self.history_manager,
            console=self.console,
            permission_prompt=self._prompt_tool_permission,
        )
        self.lesson_drafter: LessonDrafter = lesson_drafter or ClaudeLessonDrafter(
            config=self.config_manager,
            paths=self.paths,
            console=self.console,
        )
        self.auto_learn_enabled: bool = bool(project_cfg.get("learn_auto", True))
        self._armed_incident: LessonIncident | None = None
        self._register_commands()
        self.session: PromptSession | None = None
        self._shutting_down = False
        if PromptSession is not None:
            bindings = KeyBindings()

            @bindings.add("enter", eager=True)
            def _(event):  # type: ignore
                """Accept completion if menu is open, else submit."""
                buf = event.current_buffer
                if buf.complete_state and buf.complete_state.current_completion:
                    buf.apply_completion(buf.complete_state.current_completion)
                    return
                buf.validate_and_handle()

            @bindings.add("escape", "enter", eager=True)
            def _(event):  # type: ignore
                """Insert newline with Alt/Option+Enter."""
                event.current_buffer.insert_text("\n")

            @bindings.add("escape", "backspace", eager=True)
            def _(event):  # type: ignore
                buf = event.current_buffer
                count = _clear_count_for_alt_backspace(buf.document)
                if count > 0:
                    buf.delete_before_cursor(count)
                buf.selection_state = None

            @bindings.add("up", eager=True)
            def _(event):  # type: ignore
                buf = event.current_buffer
                if buf.complete_state and buf.complete_state.completions:
                    buf.complete_previous()
                    return
                window = getattr(event.app.layout, "current_window", None)
                info = getattr(window, "render_info", None)
                target = (
                    _cursor_target_from_render_info(buf.document, info, "up")
                    if info
                    else None
                )
                if target is not None:
                    buf.cursor_position = target
                    return
                if _should_move_within_multiline(buf.document, "up"):
                    buf.cursor_up(count=1)
                    return
                buf.history_backward()

            @bindings.add("down", eager=True)
            def _(event):  # type: ignore
                buf = event.current_buffer
                if buf.complete_state and buf.complete_state.completions:
                    buf.complete_next()
                    return
                window = getattr(event.app.layout, "current_window", None)
                info = getattr(window, "render_info", None)
                target = (
                    _cursor_target_from_render_info(buf.document, info, "down")
                    if info
                    else None
                )
                if target is not None:
                    buf.cursor_position = target
                    return
                if _should_move_within_multiline(buf.document, "down"):
                    buf.cursor_down(count=1)
                    return
                buf.history_forward()

            self.session = PromptSession(
                completer=DogentCompleter(
                    self.root,
                    self.registry.names(),
                    template_provider=self.doc_templates.list_display_names,
                ),
                complete_while_typing=True,
                key_bindings=bindings,
            )

    def _register_commands(self) -> None:
        """Register built-in CLI commands; keeps CLI extensible."""
        self.registry.register(
            "/init",
            self._cmd_init,
            "Initialize .dogent (dogent.md + dogent.json) with optional doc template.",
        )
        self.registry.register(
            "/learn",
            self._cmd_learn,
            "Save a lesson: /learn <text> or toggle auto prompt with /learn on|off.",
        )
        self.registry.register(
            "/show",
            self._cmd_show,
            "Show info panels: /show history or /show lessons.",
        )
        self.registry.register(
            "/clean",
            self._cmd_clean,
            "Clean workspace state: /clean [history|lesson|memory|all].",
        )
        self.registry.register(
            "/archive",
            self._cmd_archive,
            "Archive workspace records: /archive [history|lessons|all].",
        )
        self.registry.register(
            "/help",
            self._cmd_help,
            "Show Dogent usage, models, API, and available commands.",
        )
        self.registry.register(
            "/exit",
            self._cmd_exit,
            "Exit Dogent CLI gracefully.",
        )

    def _print_banner(self, settings) -> None:
        art = r"""
 ██████╗  ██████╗  ██████╗ ███████╗███╗   ██╗████████╗
 ██╔══██╗██╔═══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
 ██║  ██║██║   ██║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
 ██║  ██║██║   ██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
 ██████╔╝╚██████╔╝╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
"""
        model = settings.model or "<not set>"
        fast_model = settings.small_model or "<not set>"
        base_url = settings.base_url or "<not set>"
        web_label = settings.web_profile or "default (native)"
        project_cfg = self.config_manager.load_project_config()
        vision_profile = project_cfg.get("vision_profile") or "<not set>"
        commands = ", ".join(self.registry.names()) or "No commands registered"
        helper_lines = [
            f"Model: {model}",
            f"Fast Model: {fast_model}",
            f"API: {base_url}",
            f"LLM Profile: {settings.profile or '<not set>'}",
            f"Web Profile: {web_label}",
            f"Vision Profile: {vision_profile}",
            f"Commands: {commands}",
            "Shortcuts: Esc interrupt • Alt/Option+Enter newline • Alt/Option+Backspace delete word",
            "Ctrl+C exit • !<command> run shell command in workspace",
        ]
        body = Align.center(art.strip("\n"))
        helper = Align.center("\n".join(helper_lines))
        content = Group(body, helper)
        self.console.print(
            Panel(
                Align.center(content),
                title="🐶 Dogent",
                subtitle=None,
                expand=True,
                padding=(1, 2),
            )
        )

    async def _cmd_init(self, command: str) -> bool:
        return await self._run_init(command_text=command)

    async def _run_init(self, command_text: str) -> bool:
        parts = command_text.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else ""
        doc_template_key = "general"
        content = ""
        mode_label = "default"

        if not arg or arg.lower() == "general":
            content = self.config_manager.render_template(
                "dogent_default.md", {"doc_template": doc_template_key}
            )
        else:
            if arg.lower().startswith("workspace:"):
                self.console.print(
                    Panel(
                        "Workspace templates do not use the 'workspace:' prefix. Use the template name directly.",
                        title="Init",
                        border_style="yellow",
                    )
                )
                return True
            resolved = self.doc_templates.resolve(arg)
            if resolved:
                if resolved.source == "workspace":
                    doc_template_key = resolved.name
                else:
                    doc_template_key = f"{resolved.source}:{resolved.name}"
                content = self.config_manager.render_template(
                    "dogent_default.md", {"doc_template": doc_template_key}
                )
                mode_label = "template"
            else:
                known_global = self.doc_templates.names_for_source("global")
                known_builtin = self.doc_templates.names_for_source("built-in")
                if arg in known_global or arg in known_builtin:
                    hint = []
                    if arg in known_global:
                        hint.append(f"global:{arg}")
                    if arg in known_builtin:
                        hint.append(f"built-in:{arg}")
                    hint_text = " or ".join(hint)
                    self.console.print(
                        Panel(
                            f"Template '{arg}' is not a workspace template. Use {hint_text}.",
                            title="Init",
                            border_style="yellow",
                        )
                    )
                    return True
                doc_template_key = "general"
                mode_label = "wizard"
                self.console.print(
                    Panel(
                        "Running init wizard to draft dogent.md...",
                        title="Init Wizard",
                        border_style="cyan",
                    )
                )
                wizard_result = await self.init_wizard.generate(arg)
                content = wizard_result.dogent_md
                if wizard_result.doc_template:
                    doc_template_key = wizard_result.doc_template
                if wizard_result.primary_language:
                    self.config_manager.set_primary_language(
                        wizard_result.primary_language
                    )
                self._warn_if_missing_doc_template(doc_template_key)

        if not content.strip():
            self.console.print(
                Panel(
                    "Failed to generate dogent.md content. Please try again.",
                    title="Init",
                    border_style="red",
                )
            )
            return True

        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        config_existed = self.paths.config_file.exists()
        self.config_manager.create_config_template()
        self.config_manager.set_doc_template(doc_template_key)
        await self.agent.refresh_system_prompt()

        doc_path = self.paths.doc_preferences
        wrote_doc = False
        overwritten = False
        if doc_path.exists():
            if await self._confirm_overwrite(doc_path):
                doc_path.write_text(content.rstrip() + "\n", encoding="utf-8")
                wrote_doc = True
                overwritten = True
        else:
            doc_path.write_text(content.rstrip() + "\n", encoding="utf-8")
            wrote_doc = True

        summary_lines = []
        if wrote_doc:
            action = "Overwrote" if overwritten else "Created"
            summary_lines.append(f"{action}: {doc_path.relative_to(self.root)}")
        else:
            summary_lines.append(f"Skipped: {doc_path.relative_to(self.root)} (kept existing)")

        if config_existed:
            summary_lines.append(
                f"Updated: {self.paths.config_file.relative_to(self.root)} (doc_template={doc_template_key})"
            )
        else:
            summary_lines.append(
                f"Created: {self.paths.config_file.relative_to(self.root)} (doc_template={doc_template_key})"
            )
        summary_lines.append(f"Mode: {mode_label}")

        self.console.print(
            Panel("\n".join(summary_lines), title="Init", border_style="green")
        )
        return True

    def _warn_if_missing_doc_template(self, doc_template_key: str) -> None:
        if not doc_template_key or doc_template_key.strip().lower() == "general":
            return
        if not self.doc_templates.resolve(doc_template_key):
            self.console.print(
                Panel(
                    f"doc_template '{doc_template_key}' was not found. Using default template in prompts.",
                    title="Init",
                    border_style="yellow",
                )
            )

    async def _confirm_overwrite(self, path: Path) -> bool:
        rel = path.relative_to(self.root)
        prompt = f"{rel} exists. Overwrite? [y/N] "
        response = (await self._read_input(prompt=prompt)).strip().lower()
        if not response:
            return False
        return response in {"y", "yes"}

    async def _prompt_tool_permission(self, title: str, message: str) -> bool:
        return await self._prompt_yes_no(
            title=title,
            message=message,
            prompt="Allow? [y/N] ",
            default=False,
            show_panel=True,
        )

    async def _prompt_yes_no(
        self,
        *,
        title: str,
        message: str,
        prompt: str,
        default: bool,
        show_panel: bool,
    ) -> bool:
        self._permission_prompt_active.set()
        try:
            if show_panel and message:
                self.console.print(Panel(message, title=title, border_style="yellow"))
            if self._can_use_inline_choice():
                prompt_text = self._clean_yes_no_prompt(prompt)
                return await self._prompt_yes_no_inline(prompt_text, default)
            return await self._prompt_yes_no_text(prompt, default)
        finally:
            self._permission_prompt_active.clear()

    def _can_use_inline_choice(self) -> bool:
        if not self._interactive_prompts:
            return False
        if (
            Application is None
            or FormattedTextControl is None
            or Layout is None
            or Window is None
            or KeyBindings is None
            or Style is None
        ):
            return False
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _clean_yes_no_prompt(self, prompt: str) -> str:
        cleaned = prompt.replace("[y/N]", "").replace("[Y/n]", "")
        cleaned = cleaned.replace("[Y/N]", "").replace("[y/n]", "")
        return cleaned.strip()

    async def _prompt_yes_no_inline(self, prompt_text: str, default: bool) -> bool:
        selection = "yes" if default else "no"
        prefix = "dogent> "
        spacing = "   "

        def _fragments():
            yes_style = "class:selected" if selection == "yes" else "class:choice"
            no_style = "class:selected" if selection == "no" else "class:choice"
            text_parts = [
                ("class:prompt", prefix),
            ]
            if prompt_text:
                text_parts.append(("class:prompt", f"{prompt_text} "))
            text_parts.extend(
                [
                    (yes_style, "yes"),
                    ("", spacing),
                    (no_style, "no"),
                ]
            )
            return text_parts

        control = FormattedTextControl(_fragments, focusable=True, show_cursor=False)
        window = Window(control, height=1, dont_extend_height=True)
        layout = Layout(window, focused_element=window)
        bindings = KeyBindings()

        @bindings.add("left")
        @bindings.add("up")
        def _select_yes(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = "yes"
            event.app.invalidate()

        @bindings.add("right")
        @bindings.add("down")
        def _select_no(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = "no"
            event.app.invalidate()

        @bindings.add("enter")
        def _accept(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=selection)

        @bindings.add("escape")
        def _cancel(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="yes" if default else "no")

        @bindings.add("y")
        @bindings.add("Y")
        def _yes(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="yes")

        @bindings.add("n")
        def _no(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="no")

        @bindings.add("c-c")
        def _cancel_sigint(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="yes" if default else "no")

        style = Style.from_dict(
            {
                "prompt": "",
                "choice": "",
                "selected": "underline",
            }
        )
        app = Application(
            layout=layout,
            key_bindings=bindings,
            mouse_support=True,
            full_screen=False,
            style=style,
        )
        result = await app.run_async()
        return result == "yes"

    async def _prompt_yes_no_text(self, prompt: str, default: bool) -> bool:
        try:
            response_raw = await self._read_input(prompt=prompt)
        except (EOFError, KeyboardInterrupt):
            return default
        response = (response_raw or "").strip().lower()
        if not response:
            return default
        if response.startswith("y"):
            return True
        if response.startswith("n"):
            return False
        return default

    def _clarification_timeout_s(self) -> float | None:
        settings = self.config_manager.load_settings()
        timeout_ms = settings.api_timeout_ms
        if timeout_ms is None or timeout_ms <= 0:
            return None
        return timeout_ms / 1000.0

    async def _collect_clarification_answers(
        self, payload: ClarificationPayload
    ) -> tuple[list[dict[str, str]] | None, str | None]:
        total = len(payload.questions)
        if total == 0:
            return [], None
        intro_lines = [payload.title]
        if payload.preface:
            intro_lines.extend(["", payload.preface])
        self.console.print(
            Panel("\n".join(intro_lines), title="Clarification", border_style="cyan")
        )
        answers: list[dict[str, str]] = []
        timeout_s = self._clarification_timeout_s()
        try:
            for idx, question in enumerate(payload.questions, start=1):
                result = await self._prompt_clarification_question(
                    question,
                    index=idx,
                    total=total,
                    timeout_s=timeout_s,
                )
                answers.append(result)
        except ClarificationTimeout:
            return None, "timeout"
        except ClarificationCancelled:
            return None, "cancelled"
        return answers, None

    async def _prompt_clarification_question(
        self,
        question: ClarificationQuestion,
        *,
        index: int,
        total: int,
        timeout_s: float | None,
    ) -> dict[str, str]:
        title = f"Question {index}/{total}"
        options = list(question.options)
        freeform_value = "__freeform__"
        if question.allow_freeform:
            options.append(
                ClarificationOption(
                    label="Other (free-form answer)",
                    value=freeform_value,
                )
            )

        async def _ask() -> dict[str, str]:
            if not options and question.allow_freeform:
                answer = await self._prompt_freeform_answer(question)
                if answer is None:
                    raise ClarificationCancelled
                return {
                    "id": question.question_id,
                    "question": question.question,
                    "answer": answer,
                }
            if not options:
                raise ClarificationCancelled
            selected = recommended_index(question)
            if selected >= len(options):
                selected = 0
            if self._can_use_inline_choice():
                selected = await self._prompt_clarification_choice_inline(
                    title=title,
                    question=question.question,
                    options=options,
                    selected=selected,
                )
            else:
                selected = await self._prompt_clarification_choice_text(
                    title=title,
                    question=question.question,
                    options=options,
                    selected=selected,
                )
            if selected is None:
                raise ClarificationCancelled
            choice = options[selected]
            if question.allow_freeform and choice.value == freeform_value:
                answer = await self._prompt_freeform_answer(question)
                if answer is None:
                    raise ClarificationCancelled
                return {
                    "id": question.question_id,
                    "question": question.question,
                    "answer": answer,
                }
            answer_text = choice.label
            if choice.value and choice.value != choice.label:
                answer_text = f"{choice.label} ({choice.value})"
            return {
                "id": question.question_id,
                "question": question.question,
                "answer": answer_text,
            }

        if timeout_s is None:
            return await _ask()
        try:
            return await asyncio.wait_for(_ask(), timeout=timeout_s)
        except asyncio.TimeoutError:
            self.console.print(
                Panel(
                    "Clarification timed out. Aborting the task.",
                    title="⏱️ Timeout",
                    border_style="yellow",
                )
            )
            raise ClarificationTimeout from None

    async def _prompt_clarification_choice_inline(
        self,
        *,
        title: str,
        question: str,
        options: list[ClarificationOption],
        selected: int,
    ) -> int | None:
        selection = selected

        def _fragments():
            lines = [
                ("class:prompt", f"{title}\n"),
                ("class:prompt", f"{question}\n\n"),
            ]
            for idx, option in enumerate(options):
                marker = ">" if idx == selection else " "
                style = "class:selected" if idx == selection else "class:choice"
                lines.append((style, f"{marker} {option.label}\n"))
            lines.append(
                (
                    "class:prompt",
                    "\nUse ↑/↓ to select, Enter to confirm, Esc to cancel.",
                )
            )
            return lines

        control = FormattedTextControl(_fragments, focusable=True, show_cursor=False)
        window = Window(control, dont_extend_height=True)
        layout = Layout(window, focused_element=window)
        bindings = KeyBindings()

        @bindings.add("up")
        def _up(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = (selection - 1) % len(options)
            event.app.invalidate()

        @bindings.add("down")
        def _down(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = (selection + 1) % len(options)
            event.app.invalidate()

        @bindings.add("enter")
        def _accept(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=selection)

        @bindings.add("escape")
        def _cancel(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        @bindings.add("c-c")
        def _cancel_sigint(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        style = Style.from_dict(
            {
                "prompt": "",
                "choice": "",
                "selected": "reverse",
            }
        )
        app = Application(
            layout=layout,
            key_bindings=bindings,
            mouse_support=True,
            full_screen=False,
            style=style,
        )
        return await app.run_async()

    async def _prompt_clarification_choice_text(
        self,
        *,
        title: str,
        question: str,
        options: list[ClarificationOption],
        selected: int,
    ) -> int | None:
        lines = [title, question, ""]
        for idx, option in enumerate(options, start=1):
            marker = "*" if idx - 1 == selected else " "
            lines.append(f"{marker} {idx}) {option.label}")
        lines.append("")
        lines.append("Enter a number to select, or press Enter for default.")
        self.console.print(Panel("\n".join(lines), title="Clarification"))
        try:
            response_raw = await self._read_input(prompt="Choice: ")
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip()
        if not response:
            return selected
        if response.lower() == "esc":
            return None
        if response.isdigit():
            choice = int(response)
            if 1 <= choice <= len(options):
                return choice - 1
        return selected

    async def _prompt_freeform_answer(
        self, question: ClarificationQuestion
    ) -> str | None:
        prompt = "Your answer: "
        if question.placeholder:
            prompt = f"Your answer ({question.placeholder}): "
        try:
            response_raw = await self._read_input(prompt=prompt)
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip()
        return response or None

    def _format_clarification_answers(
        self, payload: ClarificationPayload, answers: list[dict[str, str]]
    ) -> str:
        lines = ["Clarification answers:"]
        for answer in answers:
            qid = answer.get("id", "")
            question = answer.get("question", "")
            response = answer.get("answer", "")
            label = f"{qid}: {question}".strip(": ")
            lines.append(f"- {label}")
            lines.append(f"  Answer: {response}")
        lines.append("")
        lines.append("Please continue the original request.")
        return "\n".join(lines).strip()

    def _record_clarification_history(
        self, payload: ClarificationPayload, answers_text: str
    ) -> None:
        summary = f"Clarification answers ({len(payload.questions)} questions)"
        self.history_manager.append(
            summary=summary,
            status="clarification",
            prompt=answers_text,
            todos=self.todo_manager.export_items(),
        )

    async def _cmd_learn(self, command: str) -> bool:
        parts = command.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else ""
        lowered = arg.lower()
        if lowered in {"on", "off"}:
            self.auto_learn_enabled = lowered == "on"
            with suppress(Exception):
                self.config_manager.set_learn_auto(self.auto_learn_enabled)
            state = "on" if self.auto_learn_enabled else "off"
            self.console.print(
                Panel(
                    f"Automatic 'Save a lesson?' prompt is now {state}. (Saved to .dogent/dogent.json)",
                    title="📝 Learn",
                    border_style="green",
                )
            )
            return True

        if not arg:
            state = "on" if self.auto_learn_enabled else "off"
            rel = self.paths.lessons_file.relative_to(self.root)
            self.console.print(
                Panel(
                    "\n".join(
                        [
                            f"Auto learn prompt: {state}",
                            f"Lessons file: {rel}",
                            "",
                            "Usage:",
                            "- /learn on|off",
                            "- /learn <free text>",
                            "- /show lessons",
                        ]
                    ),
                    title="📝 Learn",
                    border_style="cyan",
                )
            )
            return True

        incident = self._armed_incident
        self._armed_incident = None
        self.console.print(
            Panel(
                "Drafting lesson entry (this may take a moment)...",
                title="📝 Learn",
                border_style="cyan",
            )
        )
        drafted = await self._draft_lesson(incident, arg)
        drafted = self._ensure_user_note_in_lesson(drafted, arg)
        path = self.lessons_manager.append_entry(drafted)
        self.console.print(
            Panel(
                f"Saved lesson to {path.relative_to(self.root)}",
                title="📝 Learn",
                border_style="green",
            )
        )
        return True

    async def _cmd_show(self, command: str) -> bool:
        parts = command.split(maxsplit=1)
        arg = parts[1].strip().lower() if len(parts) > 1 else ""
        if not arg:
            self.console.print(
                Panel(
                    "Usage:\n- /show history\n- /show lessons",
                    title="🔎 Show",
                    border_style="yellow",
                )
            )
            return True
        if arg == "history":
            self._show_history()
            return True
        if arg == "lessons":
            self._show_lessons()
            return True
        self.console.print(
            Panel(
                "\n".join(
                    [
                        f"Unknown show target: {arg}",
                        "Valid targets: history, lessons",
                        "Example: /show history",
                    ]
                ),
                title="🔎 Show",
                border_style="red",
            )
        )
        return True

    def _show_lessons(self) -> None:
        titles = self.lessons_manager.list_recent_titles(limit=5)
        rel = self.paths.lessons_file.relative_to(self.root)
        if not titles:
            self.console.print(
                Panel(
                    "\n".join(
                        [
                            "No lessons recorded yet.",
                            f"File: {rel}",
                            "Add one with: /learn <text>",
                        ]
                    ),
                    title="📚 Lessons",
                    border_style="yellow",
                )
            )
            return
        body = "\n".join([f"- {t}" for t in titles])
        self.console.print(
            Panel(
                "\n".join([f"File: {rel}", "", "Recent:", body]),
                title="📚 Lessons",
                border_style="cyan",
            )
        )

    def _show_history(self) -> None:
        entries = self.history_manager.read_entries()
        if not entries:
            self.console.print(
                Panel(
                    "No history yet. Run a task to populate history.",
                    title="📜 History",
                    border_style="yellow",
                )
            )
            return

        table = Table(
            show_header=True,
            expand=True,
            box=box.MINIMAL_DOUBLE_HEAD,
            header_style="bold",
        )
        table.add_column("When", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta", no_wrap=True)
        table.add_column("Summary", style="white")
        table.add_column("Metrics", style="dim")

        for entry in reversed(entries[-5:]):
            timestamp = self._format_timestamp(entry.get("timestamp"))
            status = entry.get("status") or "-"
            summary = self._shorten(entry.get("summary") or "-")
            metrics = self._format_metrics(entry)
            table.add_row(
                timestamp,
                f"{self._status_icon(status)} {status}",
                summary,
                metrics,
            )

        todo_panel = self.todo_manager.render_snapshot_panel(
            self.history_manager.latest_todos(), title="✅ Todo Snapshot"
        )
        self.console.print(Panel(table, title="📜 History", border_style="cyan"))
        self.console.print(todo_panel)

    async def _cmd_clean(self, command: str) -> bool:
        return await self._cmd_clean_target(command)

    async def _cmd_clean_target(self, command: str) -> bool:
        parts = command.split(maxsplit=1)
        target = parts[1].strip().lower() if len(parts) > 1 else ""
        if not target:
            target = "all"
        if target == "lessons":
            target = "lesson"

        valid = {"history", "lesson", "memory", "all"}
        if target not in valid:
            self.console.print(
                Panel(
                    "\n".join(
                        [
                            f"Unknown clean target: {target}",
                            "Valid targets: history, lesson, memory, all",
                            "Example: /clean history",
                        ]
                    ),
                    title="🧹 Clean",
                    border_style="red",
                )
            )
            return True

        cleared: list[str] = []
        if target in {"history", "all"}:
            self.history_manager.clear()
            cleared.append(str(self.paths.history_file.relative_to(self.root)))

        if target in {"memory", "all"} and self.paths.memory_file.exists():
            with suppress(Exception):
                self.paths.memory_file.unlink()
            if not self.paths.memory_file.exists():
                cleared.append(str(self.paths.memory_file.relative_to(self.root)))

        if target in {"lesson", "all"} and self.paths.lessons_file.exists():
            with suppress(Exception):
                self.paths.lessons_file.unlink()
            if not self.paths.lessons_file.exists():
                cleared.append(str(self.paths.lessons_file.relative_to(self.root)))

        # Always reset in-session todos for a clean interaction state.
        self.todo_manager.set_items([])

        if cleared:
            body = "Cleared:\n" + "\n".join(cleared)
            style = "green"
        else:
            body = "Nothing to clear for the selected target."
            style = "yellow"
        self.console.print(Panel(body, title="🧹 Clean", border_style=style))
        return True

    async def _cmd_archive(self, command: str) -> bool:
        parts = command.split(maxsplit=1)
        target = parts[1].strip().lower() if len(parts) > 1 else ""
        if not target:
            target = "all"
        if target == "lesson":
            target = "lessons"

        valid = {"history", "lessons", "all"}
        if target not in valid:
            self.console.print(
                Panel(
                    "\n".join(
                        [
                            f"Unknown archive target: {target}",
                            "Valid targets: history, lessons, all",
                            "Example: /archive history",
                        ]
                    ),
                    title="📦 Archive",
                    border_style="red",
                )
            )
            return True

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived: list[str] = []
        skipped: list[str] = []
        if target in {"history", "all"}:
            archived_path, reason = self._archive_history(timestamp)
            if archived_path:
                archived.append(str(archived_path.relative_to(self.root)))
            elif reason:
                skipped.append(f"history ({reason})")
        if target in {"lessons", "all"}:
            archived_path, reason = self._archive_lessons(timestamp)
            if archived_path:
                archived.append(str(archived_path.relative_to(self.root)))
            elif reason:
                skipped.append(f"lessons ({reason})")

        if archived:
            lines = ["Archived:", *archived]
            if skipped:
                lines.extend(["", "Skipped:", *skipped])
            body = "\n".join(lines)
            style = "green"
        else:
            lines = ["Nothing to archive for the selected target."]
            if skipped:
                lines.extend(["", "Skipped:", *skipped])
            body = "\n".join(lines)
            style = "yellow"
        self.console.print(Panel(body, title="📦 Archive", border_style=style))
        return True

    def _archive_history(self, timestamp: str) -> tuple[Path | None, str | None]:
        entries = self.history_manager.read_entries()
        if not entries:
            return None, "empty"
        if not self.paths.history_file.exists():
            return None, "missing"
        content = self.paths.history_file.read_text(encoding="utf-8", errors="replace")
        archive_dir = self.paths.archives_dir
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"history_{timestamp}.json"
        archive_path.write_text(content, encoding="utf-8")
        self.history_manager.clear()
        return archive_path, None

    def _archive_lessons(self, timestamp: str) -> tuple[Path | None, str | None]:
        if not self.paths.lessons_file.exists():
            return None, "missing"
        content = self.paths.lessons_file.read_text(encoding="utf-8", errors="replace")
        if not self._lessons_has_entries(content):
            return None, "empty"
        archive_dir = self.paths.archives_dir
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"lessons_{timestamp}.md"
        archive_path.write_text(content, encoding="utf-8")
        self.paths.lessons_file.write_text("# Lessons\n\n", encoding="utf-8")
        return archive_path, None

    def _lessons_has_entries(self, content: str) -> bool:
        if not content.strip():
            return False
        for line in content.splitlines():
            if line.startswith("## "):
                return True
        return False

    async def _cmd_exit(self, _: str) -> bool:
        await self._graceful_exit()
        return False

    async def _cmd_help(self, _: str) -> bool:
        settings = self.config_manager.load_settings()
        project_cfg = self.config_manager.load_project_config()
        vision_profile = project_cfg.get("vision_profile") or "<not set>"
        commands = "\n".join(self.registry.descriptions()) or "No commands registered"
        body = "\n".join(
            [
                f"Model: {settings.model or '<not set>'}",
                f"Fast Model: {settings.small_model or '<not set>'}",
                f"API: {settings.base_url or '<not set>'}",
                f"LLM Profile: {settings.profile or '<not set>'}",
                f"Web Profile: {settings.web_profile or 'default (native)'}",
                f"Vision Profile: {vision_profile}",
                "",
                "Commands:",
                commands,
                "",
                "Shortcuts:",
                "- Esc: interrupt current task",
                "- Alt/Option+Enter: insert newline",
                "- Alt/Option+Backspace: delete word",
                "- Ctrl+C: exit gracefully",
                "- !<command>: run a shell command in the workspace",
            ]
        )
        self.console.print(Panel(body, title="💡 Help", border_style="cyan"))
        return True

    async def run(self) -> None:
        settings = self.config_manager.load_settings()
        self._print_banner(settings)
        while True:
            try:
                raw = await self._read_input()
            except (EOFError, KeyboardInterrupt):
                await self._graceful_exit()
                break
            if not raw:
                continue
            if raw.startswith("!"):
                await self._run_shell_command(raw)
                continue
            text = raw.strip()
            if text.startswith("/"):
                should_continue = await self._handle_command(text)
                if not should_continue:
                    break
                continue
            message, template_override = self._extract_template_override(text)
            template_override = self._normalize_template_override(template_override)
            _, attachments = self._resolve_attachments(text)
            message = self._replace_file_references(message, attachments)
            if template_override:
                self._show_template_reference(template_override)
            if attachments:
                self._show_attachments(attachments)
            if not message and not attachments:
                continue
            blocked = self._blocked_media_attachments(attachments)
            if blocked:
                self._show_vision_disabled_error(blocked)
                continue
            if self._armed_incident and self.auto_learn_enabled:
                if await self._confirm_save_lesson():
                    await self._save_lesson_from_incident(self._armed_incident, message)
                self._armed_incident = None
            try:
                await self._run_with_interrupt(
                    message,
                    attachments,
                    config_override=self._build_prompt_override(template_override),
                )
            except KeyboardInterrupt:
                await self._graceful_exit()
                break

    async def _run_with_interrupt(
        self,
        message: str,
        attachments: list[FileAttachment],
        *,
        config_override: dict[str, Any] | None = None,
    ) -> None:
        """Run a task while listening for Esc, then handle clarification if needed."""
        next_message = message
        next_attachments = attachments
        while True:
            await self._run_single_with_interrupt(
                next_message,
                next_attachments,
                config_override=config_override,
            )
            outcome = getattr(self.agent, "last_outcome", None)
            if outcome and str(getattr(outcome, "status", "")) in {
                "interrupted",
                "aborted",
                "error",
            }:
                break
            payload = self.agent.pop_clarification_payload()
            if not payload:
                break
            answers, abort_reason = await self._collect_clarification_answers(payload)
            if abort_reason == "timeout":
                await self.agent.abort("Clarification timed out.")
                return
            if abort_reason == "cancelled":
                await self.agent.interrupt("Clarification cancelled by user.")
                return
            answers = answers or []
            answers_text = self._format_clarification_answers(payload, answers)
            self._record_clarification_history(payload, answers_text)
            next_message = answers_text
            next_attachments = []
        self._arm_lesson_capture_if_needed()

    async def _run_single_with_interrupt(
        self,
        message: str,
        attachments: list[FileAttachment],
        *,
        config_override: dict[str, Any] | None = None,
    ) -> None:
        """Run a single agent turn while listening for Esc."""
        stop_event = threading.Event()
        agent_task = asyncio.create_task(
            self.agent.send_message(message, attachments, config_override=config_override)
        )
        esc_task = asyncio.create_task(self._wait_for_escape(stop_event))
        try:
            done, _ = await asyncio.wait(
                {agent_task, esc_task}, return_when=asyncio.FIRST_COMPLETED
            )
        except KeyboardInterrupt:
            await self._interrupt_running_task(
                reason="Ctrl+C detected, interrupting the current task...",
                agent_task=agent_task,
                esc_task=esc_task,
                stop_event=stop_event,
            )
            return

        if esc_task in done and esc_task.result():
            await self._interrupt_running_task(
                reason="Esc detected, interrupting the current task...",
                agent_task=agent_task,
                esc_task=esc_task,
                stop_event=stop_event,
            )
        else:
            stop_event.set()
            try:
                await asyncio.wait_for(esc_task, timeout=0.5)
            except asyncio.TimeoutError:
                esc_task.cancel()
                with suppress(asyncio.CancelledError):
                    await esc_task
            except asyncio.CancelledError:
                pass
        if agent_task.done() and not agent_task.cancelled():
            with suppress(Exception):
                await agent_task

    async def _wait_for_escape(self, stop_event: threading.Event) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._read_escape_key(stop_event))

    def _read_escape_key(self, stop_event: threading.Event) -> bool:
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            return False
        try:
            while not stop_event.is_set():
                if self._permission_prompt_active.is_set():
                    time.sleep(0.05)
                    continue
                rlist, _, _ = select.select([fd], [], [], 0.2)
                if not rlist:
                    continue
                if self._permission_prompt_active.is_set():
                    continue
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    for _ in range(8):
                        rlist, _, _ = select.select([fd], [], [], 0)
                        if not rlist:
                            break
                        sys.stdin.read(1)
                    return True
        except Exception:
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return False

    async def _interrupt_running_task(
        self,
        reason: str,
        agent_task: asyncio.Task,
        esc_task: asyncio.Task,
        stop_event: threading.Event,
    ) -> None:
        stop_event.set()
        self.console.print(f"[yellow]{reason}[/yellow]")
        await self.agent.interrupt(reason)
        if not agent_task.done():
            agent_task.cancel()
            with suppress(asyncio.CancelledError):
                await agent_task
        if not esc_task.done():
            try:
                await asyncio.wait_for(esc_task, timeout=0.5)
            except asyncio.TimeoutError:
                esc_task.cancel()
                with suppress(asyncio.CancelledError):
                    await esc_task
            except asyncio.CancelledError:
                pass
        # Arm lesson capture after a user interrupt.
        self._arm_lesson_capture_if_needed()

    async def _handle_command(self, command: str) -> bool:
        cmd_name = command.split(maxsplit=1)[0]
        cmd = self.registry.get(cmd_name)
        if not cmd:
            available = "\n".join(self.registry.descriptions())
            self.console.print(
                Panel(
                    f"Unknown command: {command}\nAvailable commands:\n{available}",
                    title="Unknown Command",
                    border_style="red",
                )
            )
            return True
        return await cmd.handler(command)

    async def _run_shell_command(self, raw: str) -> None:
        command = raw[1:].strip()
        if not command:
            self.console.print(
                Panel("No shell command provided.", title="ᯓ➤ Shell", border_style="yellow")
            )
            return
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
        except Exception as exc:  # noqa: BLE001
            self.console.print(Panel(str(exc), title="ᯓ➤ Shell", border_style="red"))
            return

        body_lines = [f"$ {command}"]
        stdout_text = (stdout or b"").decode(errors="replace").rstrip()
        stderr_text = (stderr or b"").decode(errors="replace").rstrip()
        if stdout_text:
            body_lines.extend(["", "STDOUT:", stdout_text])
        if stderr_text:
            body_lines.extend(["", "STDERR:", stderr_text])
        body_lines.extend(["", f"Exit code: {proc.returncode}"])
        style = "green" if proc.returncode == 0 else "red"
        self.console.print(
            Panel("\n".join(body_lines), title="ᯓ➤ Shell Result", border_style=style)
        )

    async def _read_input(self, prompt: str = "dogent> ") -> str:
        loop = asyncio.get_event_loop()
        if self.session:
            prompt_callable = getattr(self.session, "prompt_async", None)
            if callable(prompt_callable):
                return await prompt_callable(prompt)
            return await loop.run_in_executor(None, lambda: self.session.prompt(prompt))
        return await loop.run_in_executor(
            None,
            lambda: Prompt.ask(
                "[bold cyan]dogent>[/bold cyan]" if prompt == "dogent> " else prompt
            ),
        )

    def _extract_template_override(self, message: str) -> Tuple[str, str | None]:
        pattern = re.compile(r"(^|\s)" + re.escape(DOC_TEMPLATE_TOKEN) + r"([^\s]+)")
        matches = list(pattern.finditer(message))
        if not matches:
            return message, None
        template_key = None

        def replace(match: re.Match[str]) -> str:
            nonlocal template_key
            prefix = match.group(1)
            raw = match.group(2)
            cleaned = raw.rstrip(".,;:!?)]}")
            suffix = raw[len(cleaned) :] if cleaned else ""
            if cleaned:
                template_key = cleaned
                return f"{prefix}[doc template]: {cleaned}{suffix}"
            return match.group(0)

        replaced_message = pattern.sub(replace, message)
        replaced_message = re.sub(r"[ \t]{2,}", " ", replaced_message).strip()
        return replaced_message, template_key

    def _normalize_template_override(self, template_key: str | None) -> str | None:
        if not template_key:
            return None
        cleaned = template_key.strip()
        if not cleaned:
            return None
        if cleaned.lower().startswith("workspace:"):
            self.console.print(
                Panel(
                    "Workspace templates do not use the 'workspace:' prefix. Use the template name directly.",
                    title="Template Override",
                    border_style="yellow",
                )
            )
            return None
        if not self.doc_templates.resolve(cleaned):
            self.console.print(
                Panel(
                    f"Template '{cleaned}' not found. Using configured doc_template.",
                    title="Template Override",
                    border_style="yellow",
                )
            )
            return None
        return cleaned

    def _build_prompt_override(self, template_key: str | None) -> dict[str, Any] | None:
        if not template_key:
            return None
        return {"doc_template_override": template_key}

    def _resolve_attachments(self, message: str) -> Tuple[str, list[FileAttachment]]:
        return self.file_resolver.extract(message)

    def _replace_file_references(
        self, message: str, attachments: list[FileAttachment]
    ) -> str:
        if not attachments:
            return message
        token_set: set[str] = set()
        for attachment in attachments:
            token = str(attachment.path)
            if attachment.sheet:
                token = f"{token}#{attachment.sheet}"
            token_set.add(token)
        pattern = re.compile(r"@([^\s]+)")

        def replace(match: re.Match[str]) -> str:
            raw = match.group(1)
            cleaned = raw.rstrip(".,;:!?)]}")
            suffix = raw[len(cleaned) :] if cleaned else ""
            if cleaned in token_set:
                return f"[local file]: {cleaned}{suffix}"
            return match.group(0)

        return pattern.sub(replace, message)

    async def _graceful_exit(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        with suppress(Exception):
            await self.agent.reset()
        try:
            self.console.print(
                Panel("Exiting Dogent. See you soon!", title="Goodbye", border_style="cyan")
            )
        except BrokenPipeError:
            return
        except OSError as exc:
            if exc.errno == errno.EPIPE:
                return
            raise

    def _show_attachments(self, attachments: Iterable[FileAttachment]) -> None:
        for attachment in attachments:
            suffix = f"#{attachment.sheet}" if attachment.sheet else ""
            self.console.print(
                Panel(
                    f"Referenced @file {attachment.path}{suffix}",
                    title="📂 File Reference",
                )
            )

    def _show_template_reference(self, template_key: str) -> None:
        self.console.print(
            Panel(
                f"Referenced @@{template_key}",
                title="📂 Doc Template",
            )
        )

    def _vision_enabled(self) -> bool:
        config = self.config_manager.load_project_config()
        raw = config.get("vision_profile")
        if not raw:
            return False
        if isinstance(raw, str) and raw.strip().lower() == "none":
            return False
        return isinstance(raw, str)

    def _blocked_media_attachments(
        self, attachments: Iterable[FileAttachment]
    ) -> list[Path]:
        if not attachments or self._vision_enabled():
            return []
        blocked: list[Path] = []
        for attachment in attachments:
            media_type = classify_media(self.root / attachment.path)
            if media_type in {"image", "video"}:
                blocked.append(attachment.path)
        return blocked

    def _show_vision_disabled_error(self, blocked: list[Path]) -> None:
        lines = [
            "Vision is disabled (vision_profile is not set).",
            "Remove image/video references or configure vision_profile in .dogent/dogent.json.",
        ]
        if blocked:
            lines.append("")
            lines.append("Blocked attachments:")
            lines.extend(f"- {path}" for path in blocked)
        self.console.print(
            Panel("\n".join(lines), title="Vision Disabled", border_style="red")
        )

    def _render_todos(self, show_empty: bool = False) -> None:
        panel = self.todo_manager.render_panel(show_empty=show_empty)
        if panel:
            self.console.print(panel)

    def _format_timestamp(self, ts: Any) -> str:
        if not ts:
            return "-"
        try:
            dt = datetime.fromisoformat(str(ts))
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(ts)

    def _format_metrics(self, entry: dict[str, Any]) -> str:
        duration = entry.get("duration_ms")
        api = entry.get("duration_api_ms")
        cost = entry.get("cost_usd")
        parts: list[str] = []
        if duration is not None:
            parts.append(f"Duration {duration} ms")
        if api is not None:
            parts.append(f"API {api} ms")
        if cost is not None:
            parts.append(f"Cost ${cost:.4f}")
        return " · ".join(parts) if parts else "-"

    def _status_icon(self, status: str) -> str:
        normalized = (status or "").lower()
        mapping = {
            "started": "🟢",
            "running": "🔄",
            "interrupted": "⛔",
            "completed": "✅",
            "error": "❌",
            "aborted": "🛑",
            "needs_clarification": "❓",
            "needs clarification": "❓",
            "clarification": "❓",
        }
        return mapping.get(normalized, "•")

    def _shorten(self, text: Any, limit: int = 120) -> str:
        raw = str(text).replace("\n", " ").strip()
        return raw if len(raw) <= limit else f"{raw[:limit]} …"

    def _arm_lesson_capture_if_needed(self) -> None:
        outcome = getattr(self.agent, "last_outcome", None)
        if not outcome:
            return
        status = str(getattr(outcome, "status", "") or "")
        remaining = str(getattr(outcome, "remaining_todos_markdown", "") or "")
        if status not in {"error", "interrupted"}:
            return
        self._armed_incident = LessonIncident(
            status=status,
            summary=str(getattr(outcome, "summary", "") or ""),
            todos_markdown=remaining.strip(),
        )

    async def _confirm_save_lesson(self) -> bool:
        return await self._prompt_yes_no(
            title="Save lesson?",
            message="Save a lesson from the last failure/interrupt?",
            prompt="Save a lesson from the last failure/interrupt? [Y/n] ",
            default=True,
            show_panel=False,
        )

    async def _draft_lesson(self, incident: LessonIncident | None, user_text: str) -> str:
        try:
            if incident is not None:
                return await self.lesson_drafter.draft_from_incident(incident, user_text)
            return await self.lesson_drafter.draft_from_free_text(user_text)
        except Exception as exc:  # noqa: BLE001
            summary = incident.summary if incident else "(manual)"
            todos = incident.todos_markdown if incident else ""
            return "\n".join(
                [
                    "### Problem",
                    summary,
                    "",
                    "### Cause",
                    "(LLM drafting failed)",
                    "",
                    "### Correct Approach",
                    user_text.strip(),
                    "",
                    "### Remaining Todos",
                    todos or "(none)",
                    "",
                    f"(Drafting error: {exc})",
                ]
            ).strip()

    async def _save_lesson_from_incident(self, incident: LessonIncident, user_correction: str) -> None:
        self.console.print(
            Panel(
                "Drafting lesson entry (this may take a moment)...",
                title="📝 Learn",
                border_style="cyan",
            )
        )
        drafted = await self._draft_lesson(incident, user_correction)
        drafted = self._ensure_user_note_in_lesson(drafted, user_correction)
        path = self.lessons_manager.append_entry(drafted)
        self.console.print(
            Panel(
                f"Saved lesson to {path.relative_to(self.root)}",
                title="📝 Learn",
                border_style="green",
            )
        )

    def _ensure_user_note_in_lesson(self, lesson_md: str, user_note: str) -> str:
        note = user_note.strip()
        if not note:
            return lesson_md
        quote = "\n".join(["> " + line for line in note.splitlines()])
        if quote in lesson_md:
            return lesson_md
        marker = "### Correct Approach"
        insertion = "\n\n**User correction (verbatim):**\n" + quote + "\n"
        if marker not in lesson_md:
            return lesson_md.rstrip() + "\n\n" + marker + insertion

        idx = lesson_md.find(marker)
        header_end = lesson_md.find("\n", idx)
        if header_end == -1:
            header_end = len(lesson_md)
        next_heading = lesson_md.find("\n### ", header_end)
        if next_heading == -1:
            return lesson_md.rstrip() + insertion
        return lesson_md[:next_heading].rstrip() + insertion + lesson_md[next_heading:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dogent CLI - interactive document-writing agent")
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")
    args, _ = parser.parse_known_args()
    if args.version:
        from dogent import __version__

        print(f"dogent {__version__}")
        return
    try:
        asyncio.run(DogentCLI().run())
    except BrokenPipeError:
        return
    except OSError as exc:
        if exc.errno == errno.EPIPE:
            return
        raise


if __name__ == "__main__":
    main()
