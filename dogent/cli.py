from __future__ import annotations

import argparse
import asyncio
import select
import sys
import termios
import threading
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

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:  # pragma: no cover - optional dependency
    PromptSession = None  # type: ignore
    Completer = object  # type: ignore
    Completion = object  # type: ignore
    Document = object  # type: ignore


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
    start_yx = rowcol_to_yx.get((row, start_col))
    if not start_yx:
        return None
    _, start_x = start_yx
    start_x -= x_offset
    offset_x = cursor.x - start_x
    if offset_x < 0:
        offset_x = 0
    target_col = min(start_col + offset_x, len(lines[row]))
    return document.translate_row_col_to_index(row, target_col)


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
        self.agent = AgentRunner(
            config=self.config_manager,
            prompt_builder=self.prompt_builder,
            todo_manager=self.todo_manager,
            history=self.history_manager,
            console=self.console,
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
        commands = ", ".join(self.registry.names()) or "No commands registered"
        helper_lines = [
            f"Model: {model}",
            f"Fast Model: {fast_model}",
            f"API: {base_url}",
            f"LLM Profile: {settings.profile or '<not set>'}",
            f"Web Profile: {web_label}",
            f"Commands: {commands}",
            "Esc interrupts current task • Alt/Option+Enter inserts a newline • Ctrl+C exits cleanly",
        ]
        body = Align.center(art.strip("\n"))
        helper = Align.center("\n".join(helper_lines))
        content = Group(body, helper)
        self.console.print(
            Panel(
                Align.center(content),
                title="Dogent",
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

    async def _cmd_exit(self, _: str) -> bool:
        await self._graceful_exit()
        return False

    async def _cmd_help(self, _: str) -> bool:
        settings = self.config_manager.load_settings()
        commands = "\n".join(self.registry.descriptions()) or "No commands registered"
        body = "\n".join(
            [
                f"Model: {settings.model or '<not set>'}",
                f"Fast Model: {settings.small_model or '<not set>'}",
                f"API: {settings.base_url or '<not set>'}",
                f"LLM Profile: {settings.profile or '<not set>'}",
                f"Web Profile: {settings.web_profile or 'default (native)'}",
                "",
                "Commands:",
                commands,
                "",
                "Shortcuts:",
                "- Esc: interrupt current task",
                "- Alt/Option+Enter: insert newline",
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
            message, attachments = self._resolve_attachments(text)
            if attachments:
                self._show_attachments(attachments)
            if self._armed_incident and self.auto_learn_enabled:
                if await self._confirm_save_lesson():
                    await self._save_lesson_from_incident(self._armed_incident, message)
                self._armed_incident = None
            try:
                await self._run_with_interrupt(message, attachments)
            except KeyboardInterrupt:
                await self._graceful_exit()
                break

    async def _run_with_interrupt(self, message: str, attachments: list[FileAttachment]) -> None:
        """Run a task while listening for Esc without stealing future input."""
        stop_event = threading.Event()
        agent_task = asyncio.create_task(self.agent.send_message(message, attachments))
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
        self._arm_lesson_capture_if_needed()

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
                rlist, _, _ = select.select([fd], [], [], 0.2)
                if not rlist:
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

    def _resolve_attachments(self, message: str) -> Tuple[str, list[FileAttachment]]:
        return self.file_resolver.extract(message)

    async def _graceful_exit(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        with suppress(Exception):
            await self.agent.reset()
        self.console.print(Panel("Exiting Dogent. See you soon!", title="Goodbye", border_style="cyan"))

    def _show_attachments(self, attachments: Iterable[FileAttachment]) -> None:
        for attachment in attachments:
            self.console.print(
                Panel(
                    f"File loaded @file {attachment.path} {'(truncated)' if attachment.truncated else ''}",
                    title="📂 File Reference",
                )
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
            "needs_clarification": "❓",
            "needs clarification": "❓",
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
        answer = (await self._read_input("Save a lesson from the last failure/interrupt? [Y/n] ")).strip()
        if not answer:
            return True
        lowered = answer.lower()
        if lowered.startswith("y"):
            return True
        if lowered.startswith("n"):
            return False
        return True

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
    asyncio.run(DogentCLI().run())


if __name__ == "__main__":
    main()
