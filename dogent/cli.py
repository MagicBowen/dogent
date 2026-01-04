from __future__ import annotations

import argparse
import errno
import asyncio
import base64
import re
import select
import shutil
import subprocess
import sys
import termios
import threading
import time
import tty
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Tuple

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.theme import Theme

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
from .session_log import SessionLogger
from .todo import TodoManager
from .vision import classify_media
from .outline_edit import OutlineEditPayload

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import Application
    from prompt_toolkit.application.current import get_app
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.clipboard import Clipboard, ClipboardData, InMemoryClipboard
    try:
        from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
    except Exception:  # pragma: no cover - optional system clipboard
        PyperclipClipboard = None  # type: ignore
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.data_structures import Point
    from prompt_toolkit.enums import EditingMode
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.key_binding import KeyBindings
    try:
        from prompt_toolkit.key_binding import merge_key_bindings
    except Exception:  # pragma: no cover - optional API
        merge_key_bindings = None  # type: ignore
    from prompt_toolkit.key_binding.vi_state import InputMode
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import (
        ConditionalContainer,
        DynamicContainer,
        HSplit,
        Window,
        VSplit,
    )
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.margins import ScrollbarMargin
    from prompt_toolkit.lexers import Lexer
    from prompt_toolkit.mouse_events import MouseEventType
    try:
        from prompt_toolkit.lexers.pygments import pygments_token_to_classname
    except Exception:  # pragma: no cover - optional pygments helpers
        pygments_token_to_classname = None  # type: ignore
    from prompt_toolkit.selection import SelectionState, SelectionType
    from prompt_toolkit.styles import Style
    try:
        from prompt_toolkit.styles.pygments import style_from_pygments_cls
    except Exception:  # pragma: no cover - optional pygments helpers
        style_from_pygments_cls = None  # type: ignore
    from prompt_toolkit.utils import get_cwidth
    from prompt_toolkit.widgets import Frame, SearchToolbar, TextArea
    from prompt_toolkit.shortcuts.dialogs import (
        button_dialog,
        input_dialog,
        yes_no_dialog,
    )
except ImportError:  # pragma: no cover - optional dependency
    PromptSession = None  # type: ignore
    Application = None  # type: ignore
    get_app = None  # type: ignore
    Buffer = None  # type: ignore
    Clipboard = None  # type: ignore
    ClipboardData = None  # type: ignore
    InMemoryClipboard = None  # type: ignore
    PyperclipClipboard = None  # type: ignore
    Completer = object  # type: ignore
    Completion = object  # type: ignore
    Document = object  # type: ignore
    Point = None  # type: ignore
    EditingMode = None  # type: ignore
    Condition = None  # type: ignore
    ANSI = None  # type: ignore
    KeyBindings = None  # type: ignore
    merge_key_bindings = None  # type: ignore
    InputMode = None  # type: ignore
    Layout = None  # type: ignore
    Window = None  # type: ignore
    VSplit = None  # type: ignore
    HSplit = None  # type: ignore
    ConditionalContainer = None  # type: ignore
    DynamicContainer = None  # type: ignore
    BufferControl = None  # type: ignore
    FormattedTextControl = None  # type: ignore
    ScrollbarMargin = None  # type: ignore
    Lexer = object  # type: ignore
    MouseEventType = None  # type: ignore
    SelectionState = None  # type: ignore
    SelectionType = None  # type: ignore
    Style = None  # type: ignore
    pygments_token_to_classname = None  # type: ignore
    style_from_pygments_cls = None  # type: ignore
    get_cwidth = None  # type: ignore
    TextArea = None  # type: ignore
    Frame = None  # type: ignore
    SearchToolbar = None  # type: ignore
    button_dialog = None  # type: ignore
    input_dialog = None  # type: ignore
    yes_no_dialog = None  # type: ignore

try:
    import pyperclip
except Exception:  # pragma: no cover - optional system clipboard
    pyperclip = None  # type: ignore
try:
    from pygments.lexers import get_lexer_by_name  # type: ignore
    from pygments.util import ClassNotFound  # type: ignore
    from pygments.styles.monokai import MonokaiStyle  # type: ignore
except Exception:  # pragma: no cover - optional pygments
    get_lexer_by_name = None  # type: ignore
    ClassNotFound = Exception  # type: ignore
    MonokaiStyle = None  # type: ignore


DOC_TEMPLATE_TOKEN = "@@"
EDITABLE_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".txt"}


class ClarificationTimeout(Exception):
    pass


class ClarificationCancelled(Exception):
    pass


class SelectionCancelled(Exception):
    pass


CLARIFICATION_SKIP = object()
CLARIFICATION_SKIP_TEXT = "user chose not to answer this question"
INPUT_CANCELLED = object()


_MATH_BLOCK_RE = re.compile(r"(?s)\$\$(.+?)\$\$")
_MATH_INLINE_RE = re.compile(r"(?s)(?<!\$)\$[^$\n]+\$(?!\$)")


def mark_math_for_preview(text: str) -> str:
    def block_sub(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        return f"\\n\\n```math\\n{inner}\\n```\\n\\n"

    text = _MATH_BLOCK_RE.sub(block_sub, text)
    parts = re.split(r"(`[^`]*`)", text)
    for idx in range(0, len(parts), 2):
        parts[idx] = _MATH_INLINE_RE.sub(
            lambda m: f"`[math] {m.group(0)[1:-1].strip()} [/math]`",
            parts[idx],
        )
    return "".join(parts)


_BACKTICK_RE = re.compile(r"`+")


def wrap_markdown_code_block(text: str, *, language: str = "markdown") -> str:
    max_run = 0
    for match in _BACKTICK_RE.finditer(text):
        run_len = len(match.group(0))
        if run_len > max_run:
            max_run = run_len
    fence = "`" * max(3, max_run + 1)
    body = text.rstrip("\n")
    return f"{fence}{language}\n{body}\n{fence}"


def indent_block(text: str, prefix: str) -> str:
    lines = text.splitlines() or [""]
    return "\n".join(prefix + line if line else prefix for line in lines)


def resolve_save_path(root: Path, path_text: str) -> Path:
    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate


class SimpleMarkdownLexer(Lexer):
    RE_INLINE_CODE = re.compile(r"`[^`]+`")
    RE_INLINE_MATH = re.compile(r"(?<!\$)\$[^$\n]+\$(?!\$)")
    RE_STRONG = re.compile(r"\*\*[^*]+\*\*")
    RE_EM = re.compile(r"(?<!\*)\*[^*]+\*(?!\*)")
    RE_TASK = re.compile(r"^(\s*[-*]\s+)(\[(?: |x|X)\])(\s+)(.*)$")
    RE_HEADING = re.compile(r"^(#{1,6})\s+.*$")
    RE_QUOTE = re.compile(r"^\s*>\s+.*$")
    RE_RULE = re.compile(r"^(?:-{3,}|_{3,}|\*{3,})$")

    def lex_document(self, document: Document) -> Callable[[int], list[tuple[str, str]]]:
        lines = document.lines
        styled: list[list[tuple[str, str]]] = []
        in_fence = False
        fence_lexer = None
        in_math_block = False

        def apply_regex(
            segments: list[tuple[str, str]],
            regex: re.Pattern[str],
            style: str,
            *,
            allowed_style: str = "class:md.text",
        ) -> list[tuple[str, str]]:
            out: list[tuple[str, str]] = []
            for seg_style, text in segments:
                if seg_style != allowed_style:
                    out.append((seg_style, text))
                    continue
                last = 0
                for match in regex.finditer(text):
                    start, end = match.span()
                    if start > last:
                        out.append((seg_style, text[last:start]))
                    out.append((style, text[start:end]))
                    last = end
                if last < len(text):
                    out.append((seg_style, text[last:]))
            return out

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_fence:
                    in_fence = False
                    fence_lexer = None
                else:
                    in_fence = True
                    fence_lexer = None
                    tokens = stripped[3:].strip().split()
                    lang = tokens[0].lower() if tokens else ""
                    if lang and get_lexer_by_name is not None:
                        with suppress(Exception):
                            try:
                                fence_lexer = get_lexer_by_name(lang)
                            except ClassNotFound:
                                fence_lexer = None
                styled.append([("class:md.fence", line)])
                continue
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
                styled.append([("class:md.mathblock", line)])
                continue
            if stripped == "$$":
                in_math_block = not in_math_block
                styled.append([("class:md.mathblock", line)])
                continue
            if in_math_block:
                styled.append([("class:md.mathblock", line)])
                continue
            if in_fence:
                if fence_lexer and pygments_token_to_classname:
                    segments: list[tuple[str, str]] = []
                    for token, value in fence_lexer.get_tokens(line):
                        class_name = pygments_token_to_classname(token)
                        if class_name:
                            style = f"class:md.codeblock class:{class_name}"
                        else:
                            style = "class:md.codeblock"
                        segments.append((style, value))
                    styled.append(segments or [("class:md.codeblock", line)])
                else:
                    styled.append([("class:md.codeblock", line)])
                continue
            if self.RE_HEADING.match(line):
                styled.append([("class:md.heading", line)])
                continue
            if self.RE_RULE.match(stripped):
                styled.append([("class:md.rule", line)])
                continue
            if self.RE_QUOTE.match(line):
                styled.append([("class:md.quote", line)])
                continue

            task_match = self.RE_TASK.match(line)
            if task_match:
                prefix, box, space, rest = task_match.groups()
                styled.append(
                    [
                        ("class:md.text", prefix),
                        ("class:md.task", box),
                        ("class:md.text", space),
                        ("class:md.text", rest),
                    ]
                )
                continue

            if "|" in line:
                segments = [
                    ("class:md.pipe" if ch == "|" else "class:md.text", ch)
                    for ch in line
                ]
            else:
                segments = [("class:md.text", line)]

            segments = apply_regex(segments, self.RE_INLINE_CODE, "class:md.inlinecode")
            segments = apply_regex(segments, self.RE_INLINE_MATH, "class:md.inlinemath")
            segments = apply_regex(segments, self.RE_STRONG, "class:md.strong")
            segments = apply_regex(segments, self.RE_EM, "class:md.em")
            styled.append(segments)

        def lex_line(i: int) -> list[tuple[str, str]]:
            if i < len(styled):
                return styled[i]
            return [("class:md.text", "")]

        return lex_line


@dataclass(frozen=True)
class MultilineEditRequest:
    text: str


@dataclass(frozen=True)
class EditorOutcome:
    action: str
    text: str
    saved_path: Path | None = None


@dataclass(frozen=True)
class EditorAnswer:
    text: str
    saved_path: Path | None = None


def _system_clipboard_supported() -> bool:
    if pyperclip is not None:
        return True
    if sys.platform == "darwin":
        return bool(_darwin_clipboard_cmd("pbcopy")) and bool(
            _darwin_clipboard_cmd("pbpaste")
        )
    if sys.platform.startswith("linux"):
        return bool(shutil.which("wl-copy") and shutil.which("wl-paste")) or bool(
            shutil.which("xclip") or shutil.which("xsel")
        )
    if sys.platform.startswith("win"):
        return bool(shutil.which("powershell"))
    return False


def _darwin_clipboard_cmd(name: str) -> str | None:
    path = Path("/usr/bin") / name
    if path.exists():
        return str(path)
    return shutil.which(name)


def _read_system_clipboard() -> str | None:
    if sys.platform == "darwin":
        cmd = _darwin_clipboard_cmd("pbpaste")
        if cmd:
            with suppress(Exception):
                proc = subprocess.run(
                    [cmd], stdout=subprocess.PIPE, check=True
                )
                return proc.stdout.decode("utf-8", errors="replace")
    if pyperclip is not None:
        with suppress(Exception):
            return pyperclip.paste()
    if sys.platform.startswith("linux"):
        if shutil.which("wl-paste"):
            with suppress(Exception):
                proc = subprocess.run(
                    ["wl-paste"], stdout=subprocess.PIPE, check=True
                )
                return proc.stdout.decode("utf-8", errors="replace")
        if shutil.which("xclip"):
            with suppress(Exception):
                proc = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    stdout=subprocess.PIPE,
                    check=True,
                )
                return proc.stdout.decode("utf-8", errors="replace")
        if shutil.which("xsel"):
            with suppress(Exception):
                proc = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    stdout=subprocess.PIPE,
                    check=True,
                )
                return proc.stdout.decode("utf-8", errors="replace")
    if sys.platform.startswith("win") and shutil.which("powershell"):
        with suppress(Exception):
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                stdout=subprocess.PIPE,
                check=True,
            )
            return proc.stdout.decode("utf-8", errors="replace")
    return None


def _write_system_clipboard(text: str) -> bool:
    if sys.platform == "darwin":
        cmd = _darwin_clipboard_cmd("pbcopy")
        if cmd:
            with suppress(Exception):
                subprocess.run(
                    [cmd], input=text.encode("utf-8"), check=True
                )
                return True
    if pyperclip is not None:
        with suppress(Exception):
            pyperclip.copy(text)
            return True
    if sys.platform.startswith("linux"):
        if shutil.which("wl-copy"):
            with suppress(Exception):
                subprocess.run(
                    ["wl-copy"], input=text.encode("utf-8"), check=True
                )
                return True
        if shutil.which("xclip"):
            with suppress(Exception):
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode("utf-8"),
                    check=True,
                )
                return True
        if shutil.which("xsel"):
            with suppress(Exception):
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode("utf-8"),
                    check=True,
                )
                return True
    if sys.platform.startswith("win") and shutil.which("powershell"):
        with suppress(Exception):
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Set-Clipboard -Value @'\n"
                    + text
                    + "\n'@",
                ],
                check=True,
            )
            return True
    return False


def _emit_osc52_clipboard(app: Application, text: str) -> None:
    if not text:
        return
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    osc = f"\033]52;c;{payload}\a"
    output = getattr(app, "output", None)
    if output is None:
        return
    writer = getattr(output, "write_raw", None) or getattr(output, "write", None)
    if writer is None:
        return
    with suppress(Exception):
        writer(osc)
        flush = getattr(output, "flush", None)
        if flush is not None:
            flush()


if Clipboard is not None and ClipboardData is not None:
    class SystemClipboard(Clipboard):
        def __init__(self, fallback: Clipboard) -> None:
            self._fallback = fallback

        def get_data(self) -> ClipboardData:
            text = _read_system_clipboard()
            if text is None:
                return self._fallback.get_data()
            return ClipboardData(text)

        def set_data(self, data: ClipboardData) -> None:
            _write_system_clipboard(data.text)
            self._fallback.set_data(data)
else:  # pragma: no cover - prompt_toolkit unavailable
    SystemClipboard = None  # type: ignore


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
        elif command == "/edit":
            return self._match_edit_paths(arg_prefix)
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

    def _match_edit_paths(self, partial: str) -> Iterable[Completion]:
        if partial.startswith("/"):
            return []
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
                if path.suffix.lower() not in EDITABLE_EXTENSIONS:
                    continue
                candidate = path.name
            if not candidate.startswith(prefix):
                continue
            rel = path.relative_to(self.root)
            display = f"{rel}/" if path.is_dir() else str(rel)
            results.append(
                Completion(
                    display,
                    start_position=-len(partial),
                    display=display,
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
        self.file_resolver = FileReferenceResolver(self.root)
        self.history_manager = HistoryManager(self.paths)
        project_cfg = self.config_manager.load_project_config()
        self.session_logger = SessionLogger(
            self.paths, enabled=bool(project_cfg.get("debug", False))
        )
        self.init_wizard = InitWizard(
            config=self.config_manager,
            paths=self.paths,
            templates=self.doc_templates,
            console=self.console,
            session_logger=self.session_logger,
        )
        self.lessons_manager = LessonsManager(self.paths, console=self.console)
        self.prompt_builder = PromptBuilder(
            self.paths, self.todo_manager, self.history_manager, console=self.console
        )
        self._selection_prompt_active = threading.Event()
        self._multiline_editor_allowed = threading.Event()
        self._interactive_prompts = interactive_prompts
        self.agent = AgentRunner(
            config=self.config_manager,
            prompt_builder=self.prompt_builder,
            todo_manager=self.todo_manager,
            history=self.history_manager,
            console=self.console,
            permission_prompt=self._prompt_tool_permission,
            session_logger=self.session_logger,
        )
        self.lesson_drafter: LessonDrafter = lesson_drafter or ClaudeLessonDrafter(
            config=self.config_manager,
            paths=self.paths,
            console=self.console,
            session_logger=self.session_logger,
        )
        self.auto_learn_enabled: bool = bool(project_cfg.get("learn_auto", True))
        self._armed_incident: LessonIncident | None = None
        self._register_commands()
        self.session: PromptSession | None = None
        self._shutting_down = False
        self._pending_editor_submission: EditorOutcome | None = None
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

            @bindings.add("c-e", eager=True)
            def _(event):  # type: ignore
                if not self._multiline_editor_allowed.is_set():
                    event.current_buffer.cursor_position = len(event.current_buffer.text)
                    return
                event.app.exit(result=MultilineEditRequest(event.current_buffer.text))

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
            "/edit",
            self._cmd_edit,
            "Edit a local text file in the markdown editor: /edit <path>.",
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
            "/exit",
            self._cmd_exit,
            "Exit Dogent CLI gracefully.",
        )        
        self.registry.register(
            "/help",
            self._cmd_help,
            "Show Dogent usage, models, API, and available commands.",
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
            "Shortcuts: Esc interrupt • Ctrl+E editor (Ctrl+P preview, Ctrl+Q return) • Alt/Option+Enter newline",
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

    async def _cmd_edit(self, command: str) -> bool:
        parts = command.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else ""
        if not arg:
            if not self._can_use_multiline_editor():
                self.console.print(
                    Panel(
                        "Markdown editor is unavailable in this environment.",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            editor_outcome = await self._open_multiline_editor(
                "",
                title="Edit (new file)",
                context="file_edit",
                file_path=None,
            )
            return await self._handle_edit_outcome(editor_outcome, None)
        target = self._resolve_edit_path(arg)
        if target is None:
            self.console.print(
                Panel(
                    "Path must be inside the workspace.",
                    title="📝 Edit",
                    border_style="red",
                )
            )
            return True
        if not self._is_editable_extension(target):
            self.console.print(
                Panel(
                    "Unsupported file type. Use a plain text format like .md or .txt.",
                    title="📝 Edit",
                    border_style="red",
                )
            )
            return True
        if not self._can_use_multiline_editor():
            self.console.print(
                Panel(
                    "Markdown editor is unavailable in this environment.",
                    title="📝 Edit",
                    border_style="red",
                )
            )
            return True

        initial_text = ""
        if target.exists():
            if target.is_dir():
                self.console.print(
                    Panel(
                        "Path points to a directory, not a file.",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            try:
                initial_text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.console.print(
                    Panel(
                        "File is not valid UTF-8 text.",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            except OSError as exc:
                self.console.print(
                    Panel(
                        f"Failed to read file: {exc}",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
        else:
            try:
                should_create = await self._prompt_yes_no(
                    title="📝 Edit",
                    message=f"{self._display_relpath(target)} does not exist. Create it?",
                    prompt="Create file? [Y/n] ",
                    default=True,
                    show_panel=True,
                )
            except SelectionCancelled:
                return True
            if not should_create:
                return True
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
            except OSError as exc:
                self.console.print(
                    Panel(
                        f"Failed to create file: {exc}",
                        title="📝 Edit",
                        border_style="red",
                    )
                )

        title = f"Edit {self._display_relpath(target)}"
        editor_outcome = await self._open_multiline_editor(
            initial_text,
            title=title,
            context="file_edit",
            file_path=target,
        )
        return await self._handle_edit_outcome(editor_outcome, target)

    async def _handle_edit_outcome(
        self, editor_outcome: EditorOutcome, target: Path | None
    ) -> bool:
        action = editor_outcome.action
        if action == "discard":
            label = (
                f"Discarded changes for {self._display_relpath(target)}."
                if target is not None
                else "Discarded changes."
            )
            self.console.print(
                Panel(
                    label,
                    title="📝 Edit",
                    border_style="yellow",
                )
            )
            return True
        if action in {"save", "submit"}:
            save_path = editor_outcome.saved_path or target
            if save_path is None:
                return True
            if not self._is_within_root(save_path):
                self.console.print(
                    Panel(
                        "Save path must be inside the workspace.",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            if not self._is_editable_extension(save_path):
                self.console.print(
                    Panel(
                        "Unsupported file type. Use a plain text format like .md or .txt.",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            try:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_text(editor_outcome.text, encoding="utf-8")
            except OSError as exc:
                self.console.print(
                    Panel(
                        f"Failed to save file: {exc}",
                        title="📝 Edit",
                        border_style="red",
                    )
                )
                return True
            self.console.print(
                Panel(
                    f"Saved: {self._display_relpath(save_path)}",
                    title="📝 Edit",
                    border_style="green",
                )
            )
            if action == "save":
                return True
            try:
                prompt_text = await self._prompt_file_usage(save_path)
            except (EOFError, KeyboardInterrupt):
                return True
            if prompt_text is None:
                return True
            prompt_text = (prompt_text or "").strip()
            message, template_override = self._extract_template_override(prompt_text)
            template_override = self._normalize_template_override(template_override)
            if template_override:
                self._show_template_reference(template_override)
            rel_path = self._display_relpath(save_path)
            if message:
                message = f"{message} @{rel_path}"
            else:
                message = f"@{rel_path}"
            message, attachments = self._resolve_attachments(message)
            message = self._replace_file_references(message, attachments)
            if attachments:
                self._show_attachments(attachments)
            await self._run_with_interrupt(
                message,
                attachments,
                config_override=self._build_prompt_override(template_override),
            )
            return True
        return True

    async def _run_init(self, command_text: str, *, force_wizard: bool = False) -> bool:
        parts = command_text.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else ""
        doc_template_key = "general"
        content = ""
        mode_label = "default"
        wizard_prompt = ""

        if force_wizard:
            mode_label = "wizard"
        elif not arg or arg.lower() == "general":
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

        if mode_label == "wizard":
            self.console.print(
                Panel(
                    "Running init wizard to draft dogent.md...",
                    title="Init Wizard",
                    border_style="cyan",
                )
            )
            wizard_prompt = arg
            wizard_result = await self.init_wizard.generate(arg)
            content = wizard_result.dogent_md
            if wizard_result.doc_template:
                doc_template_key = wizard_result.doc_template
            if wizard_result.primary_language:
                self.config_manager.set_primary_language(wizard_result.primary_language)
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
            try:
                if await self._confirm_overwrite(doc_path):
                    doc_path.write_text(content.rstrip() + "\n", encoding="utf-8")
                    wrote_doc = True
                    overwritten = True
            except SelectionCancelled:
                self.console.print(
                    Panel("Init cancelled.", title="Init", border_style="yellow")
                )
                return True
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
        if mode_label == "wizard" and wizard_prompt:
            await self._maybe_start_writing_from_init(wizard_prompt)
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

    def _resolve_edit_path(self, path_text: str) -> Path | None:
        candidate = Path(path_text).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            resolved = candidate.resolve(strict=False)
        except Exception:
            return None
        root_resolved = self.root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            return None
        return resolved

    def _is_editable_extension(self, path: Path) -> bool:
        return path.suffix.lower() in EDITABLE_EXTENSIONS

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return False
        return True

    def _display_relpath(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    async def _confirm_overwrite(self, path: Path) -> bool:
        rel = path.relative_to(self.root)
        prompt = f"{rel} exists. Overwrite? [y/N] "
        return await self._prompt_yes_no(
            title="Init",
            message="",
            prompt=prompt,
            default=False,
            show_panel=False,
        )

    async def _prompt_tool_permission(self, title: str, message: str) -> bool:
        try:
            return await self._prompt_yes_no(
                title=title,
                message=message,
                prompt="Allow? [y/N] ",
                default=False,
                show_panel=True,
            )
        except SelectionCancelled:
            return False

    def _build_start_writing_prompt(self, init_prompt: str) -> str:
        cleaned = init_prompt.strip().replace("\n", " ").strip()
        return (
            "The user has initialized the current dogent project, and the user's "
            f'initialization prompt is "{cleaned}". Please continue to fulfill the '
            "user's needs."
        )

    async def _maybe_start_writing_from_init(self, init_prompt: str) -> None:
        try:
            should_start = await self._prompt_yes_no(
                title="Init",
                message="Start writing now?",
                prompt="Start writing now? [y/N] ",
                default=False,
                show_panel=True,
            )
        except SelectionCancelled:
            return
        if not should_start:
            return
        message = self._build_start_writing_prompt(init_prompt)
        await self._run_with_interrupt(message, [])

    async def _prompt_yes_no(
        self,
        *,
        title: str,
        message: str,
        prompt: str,
        default: bool,
        show_panel: bool,
    ) -> bool:
        self._selection_prompt_active.set()
        try:
            if show_panel and message:
                self.console.print(Panel(message, title=title, border_style="yellow"))
            if self._can_use_inline_choice():
                prompt_text = self._clean_yes_no_prompt(prompt)
                result = await self._prompt_yes_no_inline(prompt_text, default)
            else:
                result = await self._prompt_yes_no_text(prompt, default)
            if result is None:
                raise SelectionCancelled
            return result
        finally:
            self._selection_prompt_active.clear()

    def _can_use_inline_choice(self) -> bool:
        if not self._interactive_prompts:
            return False
        if (
            Application is None
            or Buffer is None
            or BufferControl is None
            or FormattedTextControl is None
            or Layout is None
            or Window is None
            or VSplit is None
            or KeyBindings is None
            or Style is None
        ):
            return False
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _can_use_multiline_editor(self) -> bool:
        if not self._can_use_inline_choice():
            return False
        if (
            ANSI is None
            or Condition is None
            or ConditionalContainer is None
            or DynamicContainer is None
            or HSplit is None
            or Lexer is None
            or Frame is None
            or SearchToolbar is None
            or SelectionState is None
            or SelectionType is None
            or TextArea is None
            or EditingMode is None
            or button_dialog is None
            or input_dialog is None
            or yes_no_dialog is None
            or (InMemoryClipboard is None and PyperclipClipboard is None)
        ):
            return False
        return True

    def _editor_mode(self) -> str:
        config = self.config_manager.load_project_config()
        raw = config.get("editor_mode")
        if isinstance(raw, str) and raw.strip().lower() == "vi":
            return "vi"
        return "default"

    def _format_saved_path_note(self, path: Path, *, purpose: str) -> str:
        try:
            display = str(path.relative_to(self.root))
        except ValueError:
            display = str(path)
        return f"Saved file: {display} (this file stores the {purpose}.)"

    def _format_editor_submission(self, text: str, *, saved_path: Path | None, purpose: str | None) -> str:
        block = wrap_markdown_code_block(text, language="markdown")
        if saved_path and purpose:
            note = self._format_saved_path_note(saved_path, purpose=purpose)
            return f"{note}\n\n{block}"
        return block

    def _render_markdown_preview(self, text: str, width: int) -> str:
        theme = Theme(
            {
                "markdown.h1": "bold #1f4f82",
                "markdown.h2": "bold #2a5d9f",
                "markdown.h3": "bold #356dba",
                "markdown.code_block": "bold #e6e6e6 on #2d2d2d",
                "markdown.code": "bold #1b1b1b on #f0f0f0",
            }
        )
        preview_console = Console(
            width=width,
            record=True,
            force_terminal=True,
            color_system=self.console.color_system or "truecolor",
            theme=theme,
            legacy_windows=False,
        )
        preview_text = mark_math_for_preview(text or "")
        code_width = max(20, width - 1)
        preview_text = self._pad_preview_code_blocks(preview_text, code_width)
        preview_console.print(
            Markdown(preview_text, code_theme="monokai", hyperlinks=False)
        )
        return preview_console.export_text(styles=True)

    def _pad_preview_code_blocks(self, text: str, width: int) -> str:
        lines = text.splitlines()
        in_fence = False
        padded: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                padded.append(line)
                continue
            if in_fence:
                display_width = sum(get_cwidth(ch) for ch in line) if get_cwidth else len(line)
                pad_len = max(0, width - display_width)
                if pad_len:
                    line = line + (" " * pad_len)
            padded.append(line)
        return "\n".join(padded)

    async def _open_multiline_editor(
        self, initial_text: str, *, title: str, context: str, file_path: Path | None = None
    ) -> EditorOutcome:
        if not self._can_use_multiline_editor():
            return EditorOutcome(action="submit", text=initial_text)
        was_active = self._selection_prompt_active.is_set()
        if not was_active:
            self._selection_prompt_active.set()
        try:
            editor_title = f"Markdown editor - {title}"
            preview_title = "Markdown preview (read-only)"
            editor_mode = self._editor_mode()
            editing_mode = EditingMode.VI if editor_mode == "vi" else EditingMode.EMACS
            editor = TextArea(
                text=initial_text,
                multiline=True,
                wrap_lines=True,
                scrollbar=True,
                lexer=SimpleMarkdownLexer(),
            )
            preview_text = ""
            preview_scroll = 0
            preview_line_count = 0
            mode = "edit"
            current_file = file_path if context == "file_edit" else None
            submit_hint = "Ctrl+Enter"
            submit_bound = False
            app: Application | None = None
            def _build_clipboard() -> object:
                fallback = InMemoryClipboard()
                if SystemClipboard is not None and _system_clipboard_supported():
                    return SystemClipboard(fallback)
                if PyperclipClipboard is not None:
                    with suppress(Exception):
                        return PyperclipClipboard()
                return fallback

            clipboard = _build_clipboard()
            selection_active = Condition(
                lambda: editor.buffer.selection_state is not None
            )
            return_prompt_active = False
            return_selection = 0
            return_future: asyncio.Future[str] | None = None
            save_prompt_active = False
            save_selection = 0
            save_future: asyncio.Future[str] | None = None
            overwrite_prompt_active = False
            overwrite_selection = 0
            overwrite_future: asyncio.Future[str] | None = None
            overwrite_path: Path | None = None
            edit_active = Condition(
                lambda: mode == "edit"
                and not return_prompt_active
                and not save_prompt_active
                and not overwrite_prompt_active
            )
            preview_active = Condition(lambda: mode == "preview")
            return_prompt_filter = Condition(lambda: return_prompt_active)
            save_prompt_filter = Condition(lambda: save_prompt_active)
            overwrite_prompt_filter = Condition(lambda: overwrite_prompt_active)
            command_mode = False
            command_buffer = Buffer(document=Document(text=""))
            command_filter = Condition(
                lambda: editing_mode == EditingMode.VI and command_mode and mode == "edit"
            )
            emacs_only = Condition(lambda: editing_mode == EditingMode.EMACS)
            vi_edit = Condition(lambda: editing_mode == EditingMode.VI and mode == "edit")
            vi_normal = Condition(
                lambda: editing_mode == EditingMode.VI
                and mode == "edit"
                and _vi_mode(app) == "NORMAL"
                and not command_mode
                and not return_prompt_active
                and not save_prompt_active
                and not overwrite_prompt_active
            )

            def is_dirty() -> bool:
                return editor.text != initial_text

            def _vi_mode(app_ref: Application | None) -> str:
                if app_ref is None:
                    return "NORMAL"
                try:
                    current = str(app_ref.vi_state.input_mode).upper()
                except Exception:
                    return "NORMAL"
                if "INSERT" in current:
                    return "INSERT"
                if "REPLACE" in current:
                    return "REPLACE"
                if "VISUAL" in current:
                    return "VISUAL"
                return "NORMAL"

            def _vi_state_label(app_ref: Application | None) -> str:
                return f"VI: {_vi_mode(app_ref)}"

            def status_text() -> str:
                row = editor.document.cursor_position_row + 1
                col = editor.document.cursor_position_col + 1
                dirty_mark = "*" if is_dirty() else ""
                mode_label = mode.upper()
                prefix = ""
                if editing_mode == EditingMode.VI and mode == "edit":
                    prefix = f"{_vi_state_label(app)} | "
                return f"{prefix}{mode_label} {dirty_mark} {title} | Ln {row}, Col {col}"

            def footer_text() -> str:
                if editing_mode == EditingMode.VI:
                    vi_label = _vi_state_label(app)
                    line1 = f"{vi_label} | {mode.upper()}"
                    if "INSERT" in vi_label:
                        if context == "file_edit":
                            line2 = "Esc: Normal | Ctrl+P preview | :w save | :wq submit | :q :q! :preview"
                        else:
                            line2 = "Esc: Normal | Ctrl+P preview | :w :wq :q :q! :preview"
                        return f"{line1}\n{line2}"
                    line2 = "i: Insert | v: Visual | /: Search | : Commands"
                    if context == "file_edit":
                        line3 = "Ctrl+P preview | :w save | :wq submit | :q :q! :preview"
                    else:
                        line3 = "Ctrl+P preview | :w :wq :q :q! :preview"
                    return f"{line1}\n{line2}\n{line3}"
                if context == "file_edit":
                    line1 = (
                        f"Submit: {submit_hint} (save + send) | Return: Ctrl+Q | "
                        "Preview: Ctrl+P"
                    )
                else:
                    line1 = f"Submit: {submit_hint} | Return: Ctrl+Q | Preview: Ctrl+P"
                line2 = "Line: Ctrl+A/E | Word: Option+Left/Right (Alt+B/F)"
                line3 = (
                    "Select: Shift+Arrows | Word select: Ctrl+W | Clear: Ctrl+G | "
                    "Copy/Cut/Paste: Ctrl+C/X/V"
                )
                return f"{line1}\n{line2}\n{line3}"

            def _ensure_selection(buffer: Buffer) -> None:
                if buffer.selection_state is None:
                    buffer.selection_state = SelectionState(
                        original_cursor_position=buffer.cursor_position,
                        type=SelectionType.CHARACTERS,
                    )

            def _extend_selection(buffer: Buffer, new_position: int) -> None:
                _ensure_selection(buffer)
                buffer.cursor_position = max(0, min(len(buffer.text), new_position))

            def _line_start_position(doc: Document) -> int:
                row = doc.cursor_position_row
                return doc.translate_row_col_to_index(row, 0)

            def _line_end_position(doc: Document) -> int:
                row = doc.cursor_position_row
                line = doc.lines[row] if row < len(doc.lines) else ""
                return doc.translate_row_col_to_index(row, len(line))

            def _move_word(buffer: Buffer, *, direction: str, select: bool) -> None:
                doc = buffer.document
                if direction == "left":
                    offset = doc.find_previous_word_beginning(count=1)
                else:
                    offset = doc.find_next_word_beginning(count=1)
                if offset:
                    new_pos = buffer.cursor_position + offset
                    if select:
                        _extend_selection(buffer, new_pos)
                    else:
                        buffer.cursor_position = new_pos

            last_selection_range: tuple[int, int] | None = None
            last_selection_text = ""

            def _sync_selection_clipboard(app: Application) -> None:
                nonlocal last_selection_range, last_selection_text
                buffer = editor.buffer
                if buffer.selection_state is None:
                    last_selection_range = None
                    last_selection_text = ""
                    return
                start, end = editor.document.selection_range()
                if start == end:
                    last_selection_range = None
                    last_selection_text = ""
                    return
                text = editor.text[start:end]
                if last_selection_range == (start, end) and text == last_selection_text:
                    return
                last_selection_range = (start, end)
                last_selection_text = text
                if not text:
                    return
                data = ClipboardData(text)
                _write_system_clipboard(text)
                _emit_osc52_clipboard(app, text)
                app.clipboard.set_data(data)

            def _preview_width(app: Application) -> int:
                columns = None
                with suppress(Exception):
                    columns = app.output.get_size().columns
                if not columns:
                    columns = self.console.width or 80
                scrollbar_width = 1 if ScrollbarMargin else 0
                return max(20, columns - 4 - scrollbar_width)

            def _preview_height(app: Application) -> int:
                info = getattr(preview_window, "render_info", None)
                if info and getattr(info, "window_height", 0):
                    return max(1, info.window_height)
                with suppress(Exception):
                    rows = app.output.get_size().rows
                if not rows:
                    return 10
                return max(1, rows - 6)

            def _preview_max_scroll(app: Application) -> int:
                height = _preview_height(app)
                return max(0, preview_line_count - height)

            def _preview_can_scroll() -> bool:
                return mode == "preview"

            def _preview_scroll_mouse(delta: int) -> None:
                if get_app is None:
                    return
                _scroll_preview(get_app(), delta)

            def _preview_cursor_position() -> Point | None:
                if Point is None:
                    return None
                max_line = max(0, preview_line_count - 1)
                return Point(x=0, y=min(preview_scroll, max_line))

            class PreviewControl(FormattedTextControl):
                def mouse_handler(self, mouse_event):  # type: ignore[no-untyped-def]
                    if MouseEventType and _preview_can_scroll():
                        if mouse_event.event_type == MouseEventType.SCROLL_UP:
                            _preview_scroll_mouse(-3)
                            return None
                        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                            _preview_scroll_mouse(3)
                            return None
                    return super().mouse_handler(mouse_event)

            preview_control = PreviewControl(
                lambda: ANSI(preview_text),
                focusable=True,
                show_cursor=False,
                get_cursor_position=_preview_cursor_position,
            )
            preview_margins = [ScrollbarMargin()] if ScrollbarMargin else None
            try:
                preview_window = Window(
                    content=preview_control,
                    wrap_lines=False,
                    right_margins=preview_margins,
                    get_vertical_scroll=lambda _window: preview_scroll,
                    style="class:preview",
                )
            except TypeError:
                preview_window = Window(
                    content=preview_control,
                    wrap_lines=False,
                    get_vertical_scroll=lambda _window: preview_scroll,
                    style="class:preview",
                )
            editor_frame = Frame(editor, title=editor_title)
            preview_frame = Frame(preview_window, title=preview_title, style="class:preview")

            if context == "file_edit":
                return_options = [
                    ("Save", "save"),
                    ("Submit", "submit"),
                    ("Save As", "save_as"),
                    ("Save As + Submit", "save_as_submit"),
                    ("Discard", "discard"),
                    ("Cancel", "cancel"),
                ]
            else:
                return_options = [
                    ("Discard", "discard"),
                    ("Submit", "submit"),
                    ("Save & Submit", "save"),
                ]
                if context == "outline":
                    return_options.append(("Abandon task", "abandon"))
                return_options.append(("Cancel", "cancel"))

            def _return_prompt_text() -> str:
                lines = ["Unsaved changes. Choose an action:"]
                for idx, option in enumerate(return_options):
                    marker = ">" if idx == return_selection else " "
                    lines.append(f"{marker} {option[0]}")
                lines.append("Use ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.")
                return "\n".join(lines)

            return_prompt_window = Window(
                content=FormattedTextControl(_return_prompt_text),
                height=max(4, len(return_options) + 3),
                style="class:return_prompt",
                wrap_lines=True,
            )
            return_prompt_container = ConditionalContainer(
                return_prompt_window, filter=return_prompt_filter
            )

            save_buffer = Buffer(document=Document(text=""))
            save_prompt_label = Window(
                content=FormattedTextControl("Save to file: "),
                height=1,
                dont_extend_width=True,
                style="class:save_prompt",
            )
            save_input_window = Window(
                BufferControl(buffer=save_buffer),
                height=1,
                style="class:save_prompt",
            )

            def _save_options_text() -> str:
                options = ["OK", "Cancel"]
                lines: list[str] = []
                for idx, option in enumerate(options):
                    marker = ">" if idx == save_selection else " "
                    lines.append(f"{marker} {option}")
                lines.append("Use ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.")
                return "\n".join(lines)

            save_options_window = Window(
                content=FormattedTextControl(_save_options_text),
                height=3,
                style="class:save_prompt",
                wrap_lines=True,
            )
            save_prompt_container = ConditionalContainer(
                HSplit([VSplit([save_prompt_label, save_input_window]), save_options_window]),
                filter=save_prompt_filter,
            )

            def _overwrite_prompt_text() -> str:
                options = ["Overwrite", "Cancel"]
                target = str(overwrite_path) if overwrite_path else "File"
                lines = [f"{target} exists. Overwrite?"]
                for idx, option in enumerate(options):
                    marker = ">" if idx == overwrite_selection else " "
                    lines.append(f"{marker} {option}")
                lines.append("Use ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.")
                return "\n".join(lines)

            overwrite_prompt_window = Window(
                content=FormattedTextControl(_overwrite_prompt_text),
                height=4,
                style="class:save_prompt",
                wrap_lines=True,
            )
            overwrite_prompt_container = ConditionalContainer(
                overwrite_prompt_window, filter=overwrite_prompt_filter
            )

            command_prompt_window = Window(
                content=FormattedTextControl(":"),
                height=1,
                dont_extend_width=True,
                style="class:command",
            )
            command_input_window = Window(
                BufferControl(buffer=command_buffer),
                height=1,
                style="class:command",
            )
            command_container = ConditionalContainer(
                VSplit([command_prompt_window, command_input_window]),
                filter=command_filter,
            )

            edit_root = HSplit(
                [
                    editor_frame,
                    Window(
                        height=1,
                        content=FormattedTextControl(status_text),
                        style="class:status",
                        wrap_lines=True,
                    ),
                    Window(
                        content=FormattedTextControl(footer_text),
                        style="class:footer",
                        wrap_lines=True,
                        dont_extend_height=True,
                    ),
                    command_container,
                    return_prompt_container,
                    save_prompt_container,
                    overwrite_prompt_container,
                ]
            )
            preview_footer = Window(
                height=1,
                content=FormattedTextControl(
                    "Preview mode • Scroll: Wheel/↑/↓ PgUp/PgDn Home/End • Esc return"
                ),
                style="class:preview_footer",
                wrap_lines=True,
            )
            preview_root = HSplit([preview_frame, preview_footer])

            def current_root() -> object:
                return preview_root if mode == "preview" else edit_root

            body = DynamicContainer(current_root)
            layout = Layout(
                body,
                focused_element=editor,
            )
            bindings = KeyBindings()

            def _accept(event) -> None:  # type: ignore[no-untyped-def]
                if context == "file_edit":
                    event.app.create_background_task(_submit_file_edit(event.app))
                    return
                event.app.exit(result=EditorOutcome(action="submit", text=editor.text))

            if editing_mode == EditingMode.EMACS:
                for key, hint in (("c-enter", "Ctrl+Enter"), ("c-j", "Ctrl+J")):
                    try:
                        bindings.add(key, filter=edit_active)(_accept)
                    except ValueError:
                        continue
                    submit_bound = True
                    submit_hint = hint
                    break
            if not submit_bound:
                submit_hint = "Ctrl+Enter"

            async def _prompt_save_path(app: Application) -> str | None:
                nonlocal save_prompt_active, save_selection, save_future
                save_prompt_active = True
                save_selection = 0
                save_buffer.text = ""
                save_future = asyncio.get_event_loop().create_future()
                app.layout.focus(save_input_window)
                app.invalidate()
                result = await save_future
                save_prompt_active = False
                save_future = None
                app.layout.focus(editor)
                app.invalidate()
                if result != "ok":
                    return None
                path_text = save_buffer.text.strip()
                if not path_text:
                    return None
                return path_text

            async def _confirm_overwrite(app: Application, path: Path) -> bool:
                nonlocal overwrite_prompt_active, overwrite_selection, overwrite_future, overwrite_path
                overwrite_prompt_active = True
                overwrite_selection = 0
                overwrite_path = path
                overwrite_future = asyncio.get_event_loop().create_future()
                app.invalidate()
                result = await overwrite_future
                overwrite_prompt_active = False
                overwrite_future = None
                overwrite_path = None
                app.layout.focus(editor)
                app.invalidate()
                return result == "overwrite"

            async def _return_flow(app: Application) -> None:
                if not is_dirty():
                    app.exit(result=EditorOutcome(action="discard", text=initial_text))
                    return
                nonlocal return_prompt_active, return_selection, return_future
                return_prompt_active = True
                return_selection = 0
                return_future = asyncio.get_event_loop().create_future()
                app.invalidate()
                result = await return_future
                return_prompt_active = False
                return_future = None
                app.invalidate()
                if result == "discard":
                    app.exit(result=EditorOutcome(action="discard", text=initial_text))
                    return
                if context == "file_edit":
                    if result in {"save", "submit"}:
                        save_path = current_file
                        if save_path is None:
                            path_text = await _prompt_save_path(app)
                            if not path_text:
                                return
                            save_path = resolve_save_path(self.root, path_text)
                        if save_path.exists() and save_path != current_file:
                            if not await _confirm_overwrite(app, save_path):
                                return
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        save_path.write_text(editor.text, encoding="utf-8")
                        app.exit(
                            result=EditorOutcome(
                                action="submit" if result == "submit" else "save",
                                text=editor.text,
                                saved_path=save_path,
                            )
                        )
                        return
                    if result in {"save_as", "save_as_submit"}:
                        path_text = await _prompt_save_path(app)
                        if not path_text:
                            return
                        save_path = resolve_save_path(self.root, path_text)
                        if save_path.exists():
                            if not await _confirm_overwrite(app, save_path):
                                return
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        save_path.write_text(editor.text, encoding="utf-8")
                        app.exit(
                            result=EditorOutcome(
                                action="submit" if result == "save_as_submit" else "save",
                                text=editor.text,
                                saved_path=save_path,
                            )
                        )
                        return
                if result == "submit":
                    app.exit(result=EditorOutcome(action="submit", text=editor.text))
                    return
                if result == "save":
                    path_text = await _prompt_save_path(app)
                    if not path_text:
                        return
                    save_path = resolve_save_path(self.root, path_text)
                    if save_path.exists():
                        if not await _confirm_overwrite(app, save_path):
                            return
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_text(editor.text, encoding="utf-8")
                    app.exit(
                        result=EditorOutcome(
                            action="submit", text=editor.text, saved_path=save_path
                        )
                    )
                    return
                if result == "abandon":
                    app.exit(result=EditorOutcome(action="abandon", text=initial_text))
                    return

            async def _submit_file_edit(app: Application) -> None:
                save_path = current_file
                if save_path is None:
                    path_text = await _prompt_save_path(app)
                    if not path_text:
                        return
                    save_path = resolve_save_path(self.root, path_text)
                if save_path.exists() and save_path != current_file:
                    if not await _confirm_overwrite(app, save_path):
                        return
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_text(editor.text, encoding="utf-8")
                app.exit(
                    result=EditorOutcome(
                        action="submit", text=editor.text, saved_path=save_path
                    )
                )

            async def _run_command(app: Application, command_text: str) -> None:
                nonlocal command_mode, initial_text, preview_text, preview_line_count, preview_scroll, mode
                command_mode = False
                if InputMode is not None:
                    app.vi_state.input_mode = InputMode.NAVIGATION
                app.layout.focus(editor)
                app.invalidate()
                cmd_text = command_text.strip()
                if not cmd_text:
                    return
                parts = cmd_text.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                async def _save_path(path_text: str | None, *, exit_after: bool) -> None:
                    nonlocal initial_text
                    resolved = path_text
                    save_path = None
                    if not resolved:
                        if context == "file_edit" and current_file is not None:
                            save_path = current_file
                        else:
                            resolved = await _prompt_save_path(app)
                            if not resolved:
                                return
                    if save_path is None:
                        save_path = resolve_save_path(self.root, resolved)
                    if save_path.exists() and save_path != current_file:
                        if not await _confirm_overwrite(app, save_path):
                            return
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_text(editor.text, encoding="utf-8")
                    if exit_after:
                        app.exit(
                            result=EditorOutcome(
                                action="submit", text=editor.text, saved_path=save_path
                            )
                        )
                        return
                    initial_text = editor.text
                    app.invalidate()

                if cmd in {"q", "quit"}:
                    if is_dirty():
                        app.create_background_task(_return_flow(app))
                        return
                    app.exit(result=EditorOutcome(action="discard", text=initial_text))
                    return
                if cmd in {"q!", "quit!"}:
                    app.exit(result=EditorOutcome(action="discard", text=initial_text))
                    return
                if cmd in {"w", "write"}:
                    await _save_path(arg or None, exit_after=False)
                    return
                if cmd in {"wq", "x", "wq!", "x!"}:
                    await _save_path(arg or None, exit_after=True)
                    return
                if cmd in {"preview", "p"}:
                    if mode != "preview":
                        width = _preview_width(app)
                        preview_text = self._render_markdown_preview(editor.text, width)
                        preview_lines = preview_text.splitlines() if preview_text else []
                        preview_line_count = len(preview_lines) if preview_lines else 1
                        preview_scroll = 0
                        mode = "preview"
                        app.layout.focus(preview_window)
                        app.invalidate()
                    return

            @bindings.add(":", filter=vi_normal, eager=True)
            def _enter_command_mode(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal command_mode
                command_mode = True
                command_buffer.text = ""
                if InputMode is not None:
                    event.app.vi_state.input_mode = InputMode.INSERT
                event.app.layout.focus(command_input_window)
                event.app.invalidate()

            @bindings.add("enter", filter=command_filter, eager=True)
            def _command_enter(event) -> None:  # type: ignore[no-untyped-def]
                text = command_buffer.text
                command_buffer.text = ""
                if InputMode is not None:
                    event.app.vi_state.input_mode = InputMode.NAVIGATION
                event.app.create_background_task(_run_command(event.app, text))

            @bindings.add("escape", filter=command_filter, eager=True)
            @bindings.add("c-c", filter=command_filter, eager=True)
            def _command_cancel(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal command_mode
                command_mode = False
                command_buffer.text = ""
                if InputMode is not None:
                    event.app.vi_state.input_mode = InputMode.NAVIGATION
                event.app.layout.focus(editor)
                event.app.invalidate()

            @bindings.add("c-q", filter=edit_active & emacs_only, eager=True)
            def _return(event) -> None:  # type: ignore[no-untyped-def]
                if return_prompt_active:
                    return
                event.app.create_background_task(_return_flow(event.app))

            def _toggle_preview_mode(app: Application) -> None:
                nonlocal preview_text, mode, preview_line_count, preview_scroll
                if mode == "preview":
                    mode = "edit"
                    app.layout.focus(editor)
                else:
                    mode = "preview"
                    width = _preview_width(app)
                    preview_text = self._render_markdown_preview(editor.text, width)
                    preview_lines = preview_text.splitlines() if preview_text else []
                    preview_line_count = len(preview_lines) if preview_lines else 1
                    preview_scroll = 0
                    app.layout.focus(preview_window)
                app.invalidate()

            @bindings.add("c-p", filter=edit_active & emacs_only, eager=True)
            def _toggle_preview(event) -> None:  # type: ignore[no-untyped-def]
                _toggle_preview_mode(event.app)

            @bindings.add("c-p", filter=edit_active & vi_edit, eager=True)
            def _toggle_preview_vi(event) -> None:  # type: ignore[no-untyped-def]
                _toggle_preview_mode(event.app)

            def _scroll_preview(app: Application, delta: int) -> None:
                nonlocal preview_scroll
                max_scroll = _preview_max_scroll(app)
                preview_scroll = max(0, min(max_scroll, preview_scroll + delta))
                app.invalidate()

            def _scroll_preview_to(app: Application, position: int) -> None:
                nonlocal preview_scroll
                max_scroll = _preview_max_scroll(app)
                preview_scroll = max(0, min(max_scroll, position))
                app.invalidate()

            @bindings.add("c-w", filter=edit_active & emacs_only, eager=True)
            def _select_word(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                doc = buffer.document
                start_offset = doc.find_previous_word_beginning(count=1)
                end_offset = doc.find_next_word_ending(count=1)
                start_pos = doc.cursor_position + (start_offset or 0)
                end_pos = doc.cursor_position + (end_offset or 0)
                buffer.cursor_position = end_pos
                buffer.selection_state = SelectionState(
                    original_cursor_position=start_pos,
                    type=SelectionType.CHARACTERS,
                )

            @bindings.add("c-l", filter=edit_active & emacs_only, eager=True)
            def _select_line(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                text = buffer.document.text
                pos = buffer.cursor_position
                start = text.rfind("\n", 0, pos) + 1
                end = text.find("\n", pos)
                if end == -1:
                    end = len(text)
                buffer.cursor_position = end
                buffer.selection_state = SelectionState(
                    original_cursor_position=start,
                    type=SelectionType.CHARACTERS,
                )

            @bindings.add("s-left", filter=edit_active & emacs_only, eager=True)
            def _select_left(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                doc = buffer.document
                _extend_selection(buffer, doc.get_cursor_left_position())

            @bindings.add("s-right", filter=edit_active & emacs_only, eager=True)
            def _select_right(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                doc = buffer.document
                _extend_selection(buffer, doc.get_cursor_right_position())

            @bindings.add("s-up", filter=edit_active & emacs_only, eager=True)
            def _select_up(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                doc = buffer.document
                _extend_selection(buffer, doc.get_cursor_up_position())

            @bindings.add("s-down", filter=edit_active & emacs_only, eager=True)
            def _select_down(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                doc = buffer.document
                _extend_selection(buffer, doc.get_cursor_down_position())

            @bindings.add("s-home", filter=edit_active & emacs_only, eager=True)
            def _select_home(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                _extend_selection(buffer, _line_start_position(buffer.document))

            @bindings.add("s-end", filter=edit_active & emacs_only, eager=True)
            def _select_end(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                _extend_selection(buffer, _line_end_position(buffer.document))

            @bindings.add("c-g", filter=edit_active & emacs_only, eager=True)
            def _clear_selection(event) -> None:  # type: ignore[no-untyped-def]
                event.current_buffer.exit_selection()

            @bindings.add("escape", filter=selection_active, eager=True)
            def _clear_selection_esc(event) -> None:  # type: ignore[no-untyped-def]
                event.current_buffer.exit_selection()

            @bindings.add("c-c", filter=selection_active & emacs_only, eager=True)
            def _copy_selection(event) -> None:  # type: ignore[no-untyped-def]
                data = event.current_buffer.copy_selection()
                _write_system_clipboard(data.text)
                _emit_osc52_clipboard(event.app, data.text)
                event.app.clipboard.set_data(data)

            @bindings.add("c-c", filter=edit_active & emacs_only, eager=True)
            def _copy_no_selection(event) -> None:  # type: ignore[no-untyped-def]
                event.current_buffer.exit_selection()

            @bindings.add("c-x", filter=selection_active & emacs_only, eager=True)
            def _cut_selection(event) -> None:  # type: ignore[no-untyped-def]
                data = event.current_buffer.cut_selection()
                _write_system_clipboard(data.text)
                _emit_osc52_clipboard(event.app, data.text)
                event.app.clipboard.set_data(data)

            @bindings.add("c-v", filter=edit_active & emacs_only, eager=True)
            def _paste(event) -> None:  # type: ignore[no-untyped-def]
                text = _read_system_clipboard()
                if text is not None:
                    event.current_buffer.insert_text(text)
                else:
                    data = event.app.clipboard.get_data()
                    event.current_buffer.paste_clipboard_data(data)

            @bindings.add("s-insert", filter=edit_active, eager=True)
            def _paste_shift_insert(event) -> None:  # type: ignore[no-untyped-def]
                text = _read_system_clipboard()
                if text is not None:
                    event.current_buffer.insert_text(text)
                else:
                    data = event.app.clipboard.get_data()
                    event.current_buffer.paste_clipboard_data(data)

            @bindings.add("escape", "left", filter=edit_active & emacs_only, eager=True)
            @bindings.add("escape", "b", filter=edit_active & emacs_only, eager=True)
            def _word_left(event) -> None:  # type: ignore[no-untyped-def]
                _move_word(
                    event.current_buffer,
                    direction="left",
                    select=event.current_buffer.selection_state is not None,
                )

            @bindings.add("escape", "right", filter=edit_active & emacs_only, eager=True)
            @bindings.add("escape", "f", filter=edit_active & emacs_only, eager=True)
            def _word_right(event) -> None:  # type: ignore[no-untyped-def]
                _move_word(
                    event.current_buffer,
                    direction="right",
                    select=event.current_buffer.selection_state is not None,
                )

            @bindings.add("c-left", filter=edit_active & emacs_only, eager=True)
            def _ctrl_word_left(event) -> None:  # type: ignore[no-untyped-def]
                _move_word(event.current_buffer, direction="left", select=False)

            @bindings.add("c-right", filter=edit_active & emacs_only, eager=True)
            def _ctrl_word_right(event) -> None:  # type: ignore[no-untyped-def]
                _move_word(event.current_buffer, direction="right", select=False)

            @bindings.add("home", filter=edit_active & emacs_only, eager=True)
            def _line_start(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                buffer.cursor_position = _line_start_position(buffer.document)

            @bindings.add("end", filter=edit_active & emacs_only, eager=True)
            def _line_end(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                buffer.cursor_position = _line_end_position(buffer.document)

            @bindings.add("escape", "backspace", filter=edit_active & emacs_only, eager=True)
            def _delete_prev_word(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                offset = buffer.document.find_previous_word_beginning(count=1)
                if offset:
                    buffer.delete_before_cursor(count=-offset)

            @bindings.add("escape", "d", filter=edit_active & emacs_only, eager=True)
            def _delete_next_word(event) -> None:  # type: ignore[no-untyped-def]
                buffer = event.current_buffer
                offset = buffer.document.find_next_word_ending(count=1)
                if offset:
                    buffer.delete(count=offset)

            @bindings.add("backspace", filter=selection_active, eager=True)
            @bindings.add("delete", filter=selection_active, eager=True)
            def _delete_selection(event) -> None:  # type: ignore[no-untyped-def]
                event.current_buffer.cut_selection()

            @bindings.add("tab", filter=edit_active & emacs_only, eager=True)
            def _insert_tab(event) -> None:  # type: ignore[no-untyped-def]
                event.current_buffer.insert_text("    ")

            @bindings.add("escape", filter=preview_active, eager=True)
            def _preview_escape(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal mode
                mode = "edit"
                event.app.layout.focus(editor)
                event.app.invalidate()

            @bindings.add("up", filter=preview_active, eager=True)
            def _preview_up(event) -> None:  # type: ignore[no-untyped-def]
                _scroll_preview(event.app, -1)

            @bindings.add("down", filter=preview_active, eager=True)
            def _preview_down(event) -> None:  # type: ignore[no-untyped-def]
                _scroll_preview(event.app, 1)

            @bindings.add("pageup", filter=preview_active, eager=True)
            def _preview_page_up(event) -> None:  # type: ignore[no-untyped-def]
                _scroll_preview(event.app, -10)

            @bindings.add("pagedown", filter=preview_active, eager=True)
            def _preview_page_down(event) -> None:  # type: ignore[no-untyped-def]
                _scroll_preview(event.app, 10)

            @bindings.add("home", filter=preview_active, eager=True)
            def _preview_home(event) -> None:  # type: ignore[no-untyped-def]
                _scroll_preview_to(event.app, 0)

            @bindings.add("end", filter=preview_active, eager=True)
            def _preview_end(event) -> None:  # type: ignore[no-untyped-def]
                max_scroll = _preview_max_scroll(event.app)
                _scroll_preview_to(event.app, max_scroll)

            try:
                @bindings.add("scroll-up", filter=preview_active, eager=True)
                def _preview_scroll_up(event) -> None:  # type: ignore[no-untyped-def]
                    _scroll_preview(event.app, -3)

                @bindings.add("scroll-down", filter=preview_active, eager=True)
                def _preview_scroll_down(event) -> None:  # type: ignore[no-untyped-def]
                    _scroll_preview(event.app, 3)
            except ValueError:
                pass

            @bindings.add("up", filter=return_prompt_filter, eager=True)
            def _return_up(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal return_selection
                return_selection = (return_selection - 1) % len(return_options)
                event.app.invalidate()

            @bindings.add("down", filter=return_prompt_filter, eager=True)
            def _return_down(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal return_selection
                return_selection = (return_selection + 1) % len(return_options)
                event.app.invalidate()

            @bindings.add("enter", filter=return_prompt_filter, eager=True)
            def _return_enter(event) -> None:  # type: ignore[no-untyped-def]
                if return_future and not return_future.done():
                    return_future.set_result(return_options[return_selection][1])

            @bindings.add("escape", filter=return_prompt_filter, eager=True)
            def _return_cancel(event) -> None:  # type: ignore[no-untyped-def]
                if return_future and not return_future.done():
                    return_future.set_result("cancel")

            @bindings.add("c-c", filter=return_prompt_filter, eager=True)
            def _return_cancel_sigint(event) -> None:  # type: ignore[no-untyped-def]
                if return_future and not return_future.done():
                    return_future.set_result("cancel")

            @bindings.add("up", filter=save_prompt_filter, eager=True)
            def _save_up(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal save_selection
                save_selection = (save_selection - 1) % 2
                event.app.invalidate()

            @bindings.add("down", filter=save_prompt_filter, eager=True)
            def _save_down(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal save_selection
                save_selection = (save_selection + 1) % 2
                event.app.invalidate()

            @bindings.add("enter", filter=save_prompt_filter, eager=True)
            def _save_enter(event) -> None:  # type: ignore[no-untyped-def]
                if save_future and not save_future.done():
                    save_future.set_result("ok" if save_selection == 0 else "cancel")

            @bindings.add("escape", filter=save_prompt_filter, eager=True)
            @bindings.add("c-c", filter=save_prompt_filter, eager=True)
            def _save_cancel(event) -> None:  # type: ignore[no-untyped-def]
                if save_future and not save_future.done():
                    save_future.set_result("cancel")

            @bindings.add("up", filter=overwrite_prompt_filter, eager=True)
            def _overwrite_up(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal overwrite_selection
                overwrite_selection = (overwrite_selection - 1) % 2
                event.app.invalidate()

            @bindings.add("down", filter=overwrite_prompt_filter, eager=True)
            def _overwrite_down(event) -> None:  # type: ignore[no-untyped-def]
                nonlocal overwrite_selection
                overwrite_selection = (overwrite_selection + 1) % 2
                event.app.invalidate()

            @bindings.add("enter", filter=overwrite_prompt_filter, eager=True)
            def _overwrite_enter(event) -> None:  # type: ignore[no-untyped-def]
                if overwrite_future and not overwrite_future.done():
                    overwrite_future.set_result(
                        "overwrite" if overwrite_selection == 0 else "cancel"
                    )

            @bindings.add("escape", filter=overwrite_prompt_filter, eager=True)
            @bindings.add("c-c", filter=overwrite_prompt_filter, eager=True)
            def _overwrite_cancel(event) -> None:  # type: ignore[no-untyped-def]
                if overwrite_future and not overwrite_future.done():
                    overwrite_future.set_result("cancel")

            base_style = Style.from_dict(
                {
                    "": "bg:#1e1e1e #d4d4d4",
                    "frame.border": "#3a3a3a",
                    "frame.label": "bold #c5c5c5",
                    "status": "bg:#262626 #d4d4d4",
                    "footer": "bg:#232323 #b5b5b5",
                    "preview": "bg:#f7f7f2 #1b1b1b",
                    "preview_footer": "bg:#efefea #1b1b1b",
                    "return_prompt": "bg:#2a2a2a #d4d4d4",
                    "save_prompt": "bg:#2a2a2a #d4d4d4",
                    "md.text": "#d4d4d4",
                    "md.heading": "bold #61afef",
                    "md.strong": "bold #e5c07b",
                    "md.em": "italic #c678dd",
                    "md.inlinecode": "bg:#2d2d2d #98c379",
                    "md.codeblock": "bg:#2d2d2d #98c379",
                    "md.fence": "bg:#2d2d2d #5c6370",
                    "md.mathblock": "bg:#2b2b44 #d7d7ff",
                    "md.inlinemath": "bg:#2b2b44 #d7d7ff",
                    "md.quote": "italic #abb2bf",
                    "md.task": "bold #56b6c2",
                    "md.pipe": "#5c6370",
                    "md.rule": "#5c6370",
                }
            )
            style = base_style
            if style_from_pygments_cls and MonokaiStyle:
                try:
                    pygments_style = style_from_pygments_cls(MonokaiStyle)
                    style = Style.merge([pygments_style, base_style])
                except Exception:
                    style = base_style

            app = Application(
                layout=layout,
                key_bindings=bindings,
                mouse_support=True,
                full_screen=True,
                style=style,
                clipboard=clipboard,
                editing_mode=editing_mode,
                after_render=_sync_selection_clipboard,
            )
            return await app.run_async()
        finally:
            if not was_active:
                self._selection_prompt_active.clear()

    def _clean_yes_no_prompt(self, prompt: str) -> str:
        cleaned = prompt.replace("[y/N]", "").replace("[Y/n]", "")
        cleaned = cleaned.replace("[Y/N]", "").replace("[y/n]", "")
        return cleaned.strip()

    async def _prompt_yes_no_inline(
        self, prompt_text: str, default: bool
    ) -> bool | None:
        selection = 0 if default else 1
        options = ["yes", "no"]

        def _fragments():
            lines = []
            if prompt_text:
                lines.append(("class:prompt", f"{prompt_text}\n\n"))
            for idx, option in enumerate(options):
                marker = ">" if idx == selection else " "
                style = "class:selected" if idx == selection else "class:choice"
                lines.append((style, f"{marker} {option}\n"))
            lines.append(
                (
                    "class:prompt",
                    "\nUse ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.",
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
            event.app.exit(result=options[selection])

        @bindings.add("escape")
        def _cancel(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        @bindings.add("c-c")
        def _cancel_sigint(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        @bindings.add("y")
        @bindings.add("Y")
        def _yes(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="yes")

        @bindings.add("n")
        def _no(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result="no")

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
        result = await app.run_async()
        if result is None:
            return None
        return result == "yes"

    async def _prompt_yes_no_text(self, prompt: str, default: bool) -> bool | None:
        prompt_hint = " (type esc or press Ctrl+C to cancel) "
        prompt_text = prompt if prompt.endswith(" ") else f"{prompt} "
        prompt_text = f"{prompt_text}{prompt_hint}"
        try:
            response_raw = await self._read_input(
                prompt=prompt_text, allow_multiline_editor=False
            )
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip().lower()
        if response in {"esc", "escape", "cancel"}:
            return None
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

    async def _collect_outline_edit(
        self, payload: OutlineEditPayload
    ) -> tuple[str | None, str | None]:
        if not self._can_use_inline_choice():
            outline_title = payload.title or "Outline"
            outline_body = payload.outline_text.strip()
            self.console.print(
                Panel(
                    Markdown(outline_body or "(Outline is empty.)"),
                    title=outline_title,
                    border_style="cyan",
                )
            )
            self.console.print()
        try:
            action = await self._prompt_outline_action(payload)
        except SelectionCancelled:
            return None, "cancelled"
        if action == "adopt":
            return "Outline approved, continue.", None
        if action == "save":
            saved_path = await self._save_outline_for_edit(payload.outline_text)
            if saved_path is None:
                return None, "cancelled"
            self.console.print(
                Panel(
                    "\n".join(
                        [
                            f"Outline saved to {saved_path}.",
                            "Edit the file, then resume the writing task from the CLI.",
                        ]
                    ),
                    title="Outline Saved",
                    border_style="cyan",
                )
            )
            return None, "paused"
        title = payload.title or "Outline"
        editor_outcome = await self._open_multiline_editor(
            payload.outline_text, title=title, context="outline"
        )
        if editor_outcome.action == "abandon":
            return None, "abandon"
        if editor_outcome.action == "submit":
            outline_text = editor_outcome.text
            saved_path = editor_outcome.saved_path
            message = self._format_editor_submission(
                outline_text, saved_path=saved_path, purpose="outline"
            )
            return message, None
        message = self._format_editor_submission(
            payload.outline_text, saved_path=None, purpose=None
        )
        return message, None

    async def _prompt_outline_action(self, payload: OutlineEditPayload) -> str:
        options = [
            ("Adopt outline", "adopt"),
            ("Edit immediately", "edit"),
            ("Save to file then edit", "save"),
        ]
        title = payload.title or "Outline"
        if self._can_use_inline_choice():
            selection = await self._prompt_outline_action_inline(
                title=title,
                outline_text=payload.outline_text,
                options=[label for label, _ in options],
            )
        else:
            prompt_text = f"{title}\n\nChoose how to proceed:"
            selection = await self._prompt_text_choice(
                title="Outline",
                prompt_text=prompt_text,
                options=[label for label, _ in options],
            )
        if selection is None:
            raise SelectionCancelled
        return options[selection][1]

    async def _prompt_outline_action_inline(
        self, *, title: str, outline_text: str, options: list[str]
    ) -> int | None:
        selection = 0
        outline_scroll = 0
        outline_body = outline_text.strip() or "(Outline is empty.)"

        columns = shutil.get_terminal_size((80, 20)).columns
        scrollbar_width = 1 if ScrollbarMargin else 0
        outline_width = max(20, columns - 4 - scrollbar_width)
        outline_rendered = self._render_markdown_preview(outline_body, outline_width)
        outline_lines = outline_rendered.splitlines() if outline_rendered else []
        outline_line_count = len(outline_lines) if outline_lines else 1

        def _outline_cursor_position() -> Point | None:
            if Point is None:
                return None
            max_line = max(0, outline_line_count - 1)
            return Point(x=0, y=min(outline_scroll, max_line))

        def _scroll_outline(app: Application, delta: int) -> None:
            nonlocal outline_scroll
            max_scroll = _outline_max_scroll(app)
            outline_scroll = max(0, min(max_scroll, outline_scroll + delta))
            app.invalidate()

        def _outline_max_scroll(app: Application) -> int:
            info = getattr(outline_window, "render_info", None)
            height = getattr(info, "window_height", 0) if info else 0
            if height <= 0:
                height = max(1, shutil.get_terminal_size((80, 20)).lines - 6)
            return max(0, outline_line_count - height)

        class OutlineControl(FormattedTextControl):
            def mouse_handler(self, mouse_event):  # type: ignore[no-untyped-def]
                if MouseEventType:
                    if mouse_event.event_type == MouseEventType.SCROLL_UP:
                        _scroll_outline(get_app(), -3)
                        return None
                    if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                        _scroll_outline(get_app(), 3)
                        return None
                return super().mouse_handler(mouse_event)

        outline_control = OutlineControl(
            lambda: ANSI(outline_rendered),
            focusable=True,
            show_cursor=False,
            get_cursor_position=_outline_cursor_position,
        )
        outline_margins = [ScrollbarMargin()] if ScrollbarMargin else None
        try:
            outline_window = Window(
                content=outline_control,
                wrap_lines=False,
                right_margins=outline_margins,
                get_vertical_scroll=lambda _window: outline_scroll,
                style="class:outline",
            )
        except TypeError:
            outline_window = Window(
                content=outline_control,
                wrap_lines=False,
                get_vertical_scroll=lambda _window: outline_scroll,
                style="class:outline",
            )
        outline_frame = Frame(outline_window, title=title, style="class:outline")

        def _options_fragments():
            lines = [("class:prompt", "Choose how to proceed:\n")]
            for idx, option in enumerate(options):
                marker = ">" if idx == selection else " "
                style = "class:selected" if idx == selection else "class:choice"
                lines.append((style, f"{marker} {option}\n"))
            lines.append(
                (
                    "class:prompt",
                    "Tab: switch pane • Enter: confirm • Esc/Ctrl+C: cancel",
                )
            )
            return lines

        options_control = FormattedTextControl(
            _options_fragments, focusable=True, show_cursor=False
        )
        options_window = Window(options_control, dont_extend_height=True)
        footer = Window(
            height=1,
            content=FormattedTextControl(
                "Tab: options • Scroll outline: Wheel/↑/↓ PgUp/PgDn Home/End"
            ),
            style="class:footer",
            wrap_lines=True,
        )
        root = HSplit([outline_frame, options_window, footer])
        layout = Layout(root, focused_element=outline_window)
        bindings = KeyBindings()
        app: Application | None = None

        def _focus_outline(event) -> None:  # type: ignore[no-untyped-def]
            event.app.layout.focus(outline_window)
            event.app.invalidate()

        def _focus_options(event) -> None:  # type: ignore[no-untyped-def]
            event.app.layout.focus(options_control)
            event.app.invalidate()

        def _is_outline_active() -> bool:
            return app is not None and app.layout.current_control == outline_control

        def _is_options_active() -> bool:
            return app is not None and app.layout.current_control == options_control

        outline_active = Condition(_is_outline_active)
        options_active = Condition(_is_options_active)

        @bindings.add("tab")
        def _toggle_focus(event) -> None:  # type: ignore[no-untyped-def]
            if _is_outline_active():
                _focus_options(event)
            else:
                _focus_outline(event)

        with suppress(ValueError):
            @bindings.add("s-tab")
            def _toggle_focus_back(event) -> None:  # type: ignore[no-untyped-def]
                if _is_options_active():
                    _focus_outline(event)
                else:
                    _focus_options(event)

        @bindings.add("up", filter=outline_active)
        def _outline_up(event) -> None:  # type: ignore[no-untyped-def]
            _scroll_outline(event.app, -1)

        @bindings.add("down", filter=outline_active)
        def _outline_down(event) -> None:  # type: ignore[no-untyped-def]
            _scroll_outline(event.app, 1)

        @bindings.add("pageup", filter=outline_active)
        def _outline_page_up(event) -> None:  # type: ignore[no-untyped-def]
            _scroll_outline(event.app, -10)

        @bindings.add("pagedown", filter=outline_active)
        def _outline_page_down(event) -> None:  # type: ignore[no-untyped-def]
            _scroll_outline(event.app, 10)

        @bindings.add("home", filter=outline_active)
        def _outline_home(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal outline_scroll
            outline_scroll = 0
            event.app.invalidate()

        @bindings.add("end", filter=outline_active)
        def _outline_end(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal outline_scroll
            outline_scroll = _outline_max_scroll(event.app)
            event.app.invalidate()

        @bindings.add("up", filter=options_active)
        def _options_up(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = (selection - 1) % len(options)
            event.app.invalidate()

        @bindings.add("down", filter=options_active)
        def _options_down(event) -> None:  # type: ignore[no-untyped-def]
            nonlocal selection
            selection = (selection + 1) % len(options)
            event.app.invalidate()

        @bindings.add("enter", filter=options_active)
        def _options_accept(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=selection)

        @bindings.add("escape")
        def _cancel(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        style = Style.from_dict(
            {
                "outline": "bg:#f7f7f2 #1b1b1b",
                "outline.border": "#c9c9c9",
                "outline.label": "bold #1b1b1b",
                "prompt": "",
                "choice": "",
                "selected": "reverse",
                "footer": "bg:#efefea #1b1b1b",
                "scrollbar.background": "bg:#e0e0e0 #e0e0e0",
                "scrollbar.button": "bg:#b0b0b0 #b0b0b0",
            }
        )
        app = Application(
            layout=layout,
            key_bindings=bindings,
            mouse_support=True,
            full_screen=True,
            style=style,
        )
        was_active = self._selection_prompt_active.is_set()
        if not was_active:
            self._selection_prompt_active.set()
        try:
            return await app.run_async()
        finally:
            if not was_active:
                self._selection_prompt_active.clear()

    async def _save_outline_for_edit(self, outline_text: str) -> Path | None:
        choice = await self._prompt_outline_save_mode()
        if choice is None:
            return None
        if choice == "auto":
            filename = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            filename = await self._prompt_outline_filename()
            if not filename:
                return None
        save_path = resolve_save_path(self.root, filename)
        if save_path.exists():
            if not await self._prompt_yes_no(
                title="Overwrite?",
                message=f"{save_path} exists. Overwrite?",
                prompt="Overwrite? [y/N] ",
                default=False,
                show_panel=True,
            ):
                return None
        save_path.write_text(outline_text, encoding="utf-8")
        return save_path

    async def _prompt_outline_save_mode(self) -> str | None:
        options = [
            ("Auto-generate filename", "auto"),
            ("Enter filename", "manual"),
        ]
        prompt_text = "Save outline to a file:"
        if self._can_use_inline_choice():
            selection = await self._prompt_inline_choice(
                title="Save Outline",
                prompt_text=prompt_text,
                options=[label for label, _ in options],
            )
        else:
            selection = await self._prompt_text_choice(
                title="Save Outline",
                prompt_text=prompt_text,
                options=[label for label, _ in options],
            )
        if selection is None:
            return None
        return options[selection][1]

    async def _prompt_outline_filename(self) -> str | None:
        try:
            response = await self._read_input(
                prompt="Filename: ", allow_multiline_editor=False
            )
        except (EOFError, KeyboardInterrupt):
            return None
        value = (response or "").strip()
        return value or None

    async def _prompt_inline_choice(
        self, *, title: str, prompt_text: str, options: list[str]
    ) -> int | None:
        selection = 0

        def _fragments():
            lines = [
                ("class:prompt", f"{title}\n"),
                ("class:prompt", f"{prompt_text}\n\n"),
            ]
            for idx, option in enumerate(options):
                marker = ">" if idx == selection else " "
                style = "class:selected" if idx == selection else "class:choice"
                lines.append((style, f"{marker} {option}\n"))
            lines.append(
                (
                    "class:prompt",
                    "\nUse ↑/↓ to select, Enter to confirm, Esc/Ctrl+C to cancel.",
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

    async def _prompt_text_choice(
        self, *, title: str, prompt_text: str, options: list[str]
    ) -> int | None:
        lines = [title, prompt_text, ""]
        for idx, option in enumerate(options, start=1):
            marker = "*" if idx == 1 else " "
            lines.append(f"{marker} {idx}) {option}")
        lines.append("")
        lines.append("Enter a number to select, or type esc to cancel.")
        lines.append("Press Ctrl+C to cancel.")
        self.console.print(Panel("\n".join(lines), title=title))
        try:
            response_raw = await self._read_input(
                prompt="Choice: ", allow_multiline_editor=False
            )
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip()
        if not response:
            return 0
        if response.lower() == "esc":
            return None
        if response.isdigit():
            choice = int(response)
            if 1 <= choice <= len(options):
                return choice - 1
        return 0

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
        label_text = question.question.rstrip()
        if label_text.endswith((".", "。")):
            label_text = label_text[:-1].rstrip()

        async def _ask() -> dict[str, str]:
            def _skip_answer() -> dict[str, str]:
                return {
                    "id": question.question_id,
                    "question": question.question,
                    "answer": CLARIFICATION_SKIP_TEXT,
                }

            def _freeform_answer_payload(answer: object | None) -> dict[str, str]:
                if answer is None:
                    raise ClarificationCancelled
                if answer is CLARIFICATION_SKIP:
                    return _skip_answer()
                if isinstance(answer, EditorAnswer):
                    return {
                        "id": question.question_id,
                        "question": question.question,
                        "answer": answer.text,
                        "editor": "true",
                    }
                return {
                    "id": question.question_id,
                    "question": question.question,
                    "answer": str(answer),
                    "editor": "false",
                }

            if not options and question.allow_freeform:
                answer = await self._prompt_freeform_answer(
                    question,
                    label=label_text,
                    skip_on_editor_cancel=True,
                )
                return _freeform_answer_payload(answer)
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
            if selected is CLARIFICATION_SKIP:
                return _skip_answer()
            choice = options[selected]
            if question.allow_freeform and choice.value == freeform_value:
                answer = await self._prompt_freeform_answer(
                    question,
                    label=label_text,
                    skip_on_editor_cancel=True,
                )
                return _freeform_answer_payload(answer)
            answer_text = choice.label
            if choice.value and choice.value != choice.label:
                answer_text = f"{choice.label} ({choice.value})"
            return {
                "id": question.question_id,
                "question": question.question,
                "answer": answer_text,
            }

        self._selection_prompt_active.set()
        try:
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
        finally:
            self._selection_prompt_active.clear()

    async def _prompt_clarification_choice_inline(
        self,
        *,
        title: str,
        question: str,
        options: list[ClarificationOption],
        selected: int,
    ) -> int | object | None:
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
                    "\nUse ↑/↓ to select, Enter to input, Esc to skip, Ctrl+C to cancel.",
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
        def _skip(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=CLARIFICATION_SKIP)

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
    ) -> int | object | None:
        lines = [title, question, ""]
        for idx, option in enumerate(options, start=1):
            marker = "*" if idx - 1 == selected else " "
            lines.append(f"{marker} {idx}) {option.label}")
        lines.append("")
        lines.append(
            "Enter a number to select, type esc to skip, or press Enter for default."
        )
        lines.append("Press Ctrl+C to cancel all questions.")
        self.console.print(Panel("\n".join(lines), title="Clarification"))
        try:
            response_raw = await self._read_input(
                prompt="Choice: ", allow_multiline_editor=False
            )
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip()
        if not response:
            return selected
        if response.lower() == "esc":
            return CLARIFICATION_SKIP
        if response.isdigit():
            choice = int(response)
            if 1 <= choice <= len(options):
                return choice - 1
        return selected

    async def _prompt_freeform_answer(
        self,
        question: ClarificationQuestion,
        *,
        label: str | None = None,
        force_editor: bool = False,
        skip_on_editor_cancel: bool = False,
    ) -> str | EditorAnswer | object | None:
        prompt = f"{label}: " if label else "Your answer: "
        if question.placeholder and not label:
            prompt = f"Your answer ({question.placeholder}): "
        if force_editor and self._can_use_multiline_editor():
            title = question.question.strip() or label or "Your answer"
            editor_outcome = await self._open_multiline_editor(
                "", title=title, context="clarification"
            )
            if editor_outcome.action != "submit":
                return CLARIFICATION_SKIP if skip_on_editor_cancel else None
            response = editor_outcome.text.rstrip()
            if not response:
                return CLARIFICATION_SKIP
            return EditorAnswer(response, saved_path=editor_outcome.saved_path)
        if self._can_use_inline_choice():
            result = await self._prompt_freeform_answer_inline(
                prompt, skip_on_editor_cancel=skip_on_editor_cancel
            )
        else:
            result = await self._prompt_freeform_answer_text(prompt)
        if result is None:
            return None
        if result is CLARIFICATION_SKIP:
            return CLARIFICATION_SKIP
        if isinstance(result, EditorAnswer):
            if not result.text:
                return CLARIFICATION_SKIP
            return result
        response = str(result).strip()
        return response or CLARIFICATION_SKIP

    async def _prompt_freeform_answer_text(self, prompt: str) -> str | object | None:
        try:
            response_raw = await self._read_input(
                prompt=prompt, allow_multiline_editor=True, editor_context="clarification"
            )
        except (EOFError, KeyboardInterrupt):
            return None
        response = (response_raw or "").strip()
        if response.lower() in {"esc", "escape", "cancel"}:
            return CLARIFICATION_SKIP
        if not response:
            return CLARIFICATION_SKIP
        return response

    async def _run_freeform_inline_app(
        self, prompt: str, initial_text: str
    ) -> str | object | None:
        buffer = Buffer(document=Document(text=initial_text))
        control = BufferControl(buffer=buffer)
        prompt_control = FormattedTextControl([("class:prompt", prompt)])
        prompt_window = Window(prompt_control, dont_extend_width=True, height=1)
        input_window = Window(control, height=1, dont_extend_height=True)
        hint_text = "• Enter: submit • Esc: skip  • Ctrl+C: cancel • Ctrl+E: editor"
        hint_window = Window(
            FormattedTextControl([("class:prompt", hint_text)]),
            height=1,
            dont_extend_height=True,
        )
        layout = Layout(
            HSplit([VSplit([prompt_window, input_window]), hint_window]),
            focused_element=input_window,
        )
        bindings = KeyBindings()

        @bindings.add("enter")
        def _accept(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=buffer.text)

        @bindings.add("escape")
        def _skip(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=CLARIFICATION_SKIP)

        @bindings.add("c-c")
        def _cancel(event) -> None:  # type: ignore[no-untyped-def]
            event.app.exit(result=None)

        @bindings.add("c-e", eager=True)
        def _open_editor(event) -> None:  # type: ignore[no-untyped-def]
            if not self._can_use_multiline_editor():
                return
            event.app.exit(result=MultilineEditRequest(buffer.text))

        style = Style.from_dict({"prompt": ""})
        app = Application(
            layout=layout,
            key_bindings=bindings,
            mouse_support=True,
            full_screen=False,
            style=style,
        )
        return await app.run_async()

    async def _prompt_freeform_answer_inline(
        self, prompt: str, *, skip_on_editor_cancel: bool = False
    ) -> str | object | None:
        initial_text = ""
        title = prompt.strip() or "Answer"
        while True:
            result = await self._run_freeform_inline_app(prompt, initial_text)
            if isinstance(result, MultilineEditRequest):
                if not self._can_use_multiline_editor():
                    return result.text
                editor_outcome = await self._open_multiline_editor(
                    result.text, title=title, context="clarification"
                )
                if editor_outcome.action != "submit":
                    if skip_on_editor_cancel:
                        return CLARIFICATION_SKIP
                    initial_text = editor_outcome.text
                    continue
                response = editor_outcome.text.rstrip()
                if not response:
                    return CLARIFICATION_SKIP
                return EditorAnswer(response, saved_path=editor_outcome.saved_path)
            return result

    def _format_clarification_answers(
        self, payload: ClarificationPayload, answers: list[dict[str, str]]
    ) -> str:
        lines = ["Clarification answers:"]
        for answer in answers:
            qid = answer.get("id", "")
            question = answer.get("question", "")
            response = answer.get("answer", "")
            is_editor = answer.get("editor") == "true"
            label = f"{qid}: {question}".strip(": ")
            lines.append(f"- {label}")
            if is_editor:
                lines.append("  Answer:")
                block = wrap_markdown_code_block(response, language="markdown")
                lines.append(indent_block(block, "  "))
            else:
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
                "- Ctrl+E: open markdown editor (Ctrl+P preview, Ctrl+Enter submit, Ctrl+Q return)",
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
        try:
            while True:
                try:
                    raw = await self._read_input(
                        allow_multiline_editor=True,
                        capture_editor_submission=True,
                    )
                except (EOFError, KeyboardInterrupt):
                    await self._graceful_exit()
                    break
                if not raw:
                    continue
                if raw.startswith("!"):
                    self._pending_editor_submission = None
                    await self._run_shell_command(raw)
                    continue
                text = raw.strip()
                if text.startswith("/"):
                    self._pending_editor_submission = None
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
                if self._pending_editor_submission and message:
                    message = self._format_editor_submission(
                        message,
                        saved_path=self._pending_editor_submission.saved_path,
                        purpose="user request",
                    )
                self._pending_editor_submission = None
                if not await self._maybe_auto_init_for_request(message):
                    continue
                blocked = self._blocked_media_attachments(attachments)
                if blocked:
                    self._show_vision_disabled_error(blocked)
                    continue
                if self._armed_incident and self.auto_learn_enabled:
                    try:
                        if await self._confirm_save_lesson():
                            await self._save_lesson_from_incident(
                                self._armed_incident, message
                            )
                    except SelectionCancelled:
                        self._armed_incident = None
                        continue
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
        except Exception as exc:  # noqa: BLE001
            if self.session_logger:
                self.session_logger.log_exception("cli", exc)
            raise
        finally:
            await self._graceful_exit()

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
            outline_payload = self.agent.pop_outline_edit_payload()
            if outline_payload:
                outline_message, abort_reason = await self._collect_outline_edit(
                    outline_payload
                )
                if abort_reason == "abandon":
                    await self.agent.interrupt("Outline editing abandoned by user.")
                    return
                if abort_reason == "paused":
                    await self.agent.interrupt("Outline saved; edit the file and resume.")
                    return
                if abort_reason == "cancelled":
                    await self.agent.interrupt("Outline selection cancelled by user.")
                    return
                if outline_message:
                    next_message = outline_message
                    next_attachments = []
                    continue
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

    async def _maybe_auto_init_for_request(self, message: str) -> bool:
        if self.paths.config_file.exists():
            return True
        try:
            should_init = await self._prompt_yes_no(
                title="Init",
                message="This workspace is not initialized. Initialize now?",
                prompt="Initialize now? [Y/n] ",
                default=True,
                show_panel=True,
            )
        except SelectionCancelled:
            return False
        if not should_init:
            return True
        await self._run_init(command_text=f"/init {message}", force_wizard=True)
        return False

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
                if self._selection_prompt_active.is_set():
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    while self._selection_prompt_active.is_set() and not stop_event.is_set():
                        time.sleep(0.05)
                    if stop_event.is_set():
                        break
                    try:
                        tty.setcbreak(fd)
                    except Exception:
                        return False
                    continue
                rlist, _, _ = select.select([fd], [], [], 0.2)
                if not rlist:
                    continue
                if self._selection_prompt_active.is_set():
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

    async def _read_input(
        self,
        prompt: str = "dogent> ",
        *,
        allow_multiline_editor: bool = False,
        capture_editor_submission: bool = False,
        editor_context: str = "prompt",
    ) -> str:
        loop = asyncio.get_event_loop()
        default_text = ""
        while True:
            if self.session:
                prompt_callable = getattr(self.session, "prompt_async", None)
                prompt_kwargs = {}
                if default_text:
                    prompt_kwargs["default"] = default_text
                if allow_multiline_editor and self._can_use_multiline_editor():
                    self._multiline_editor_allowed.set()
                else:
                    self._multiline_editor_allowed.clear()
                try:
                    if callable(prompt_callable):
                        result = await prompt_callable(prompt, **prompt_kwargs)
                    else:
                        result = await loop.run_in_executor(
                            None, lambda: self.session.prompt(prompt, **prompt_kwargs)
                        )
                finally:
                    self._multiline_editor_allowed.clear()
                if isinstance(result, MultilineEditRequest):
                    if not allow_multiline_editor or not self._can_use_multiline_editor():
                        if capture_editor_submission:
                            self._pending_editor_submission = None
                        return result.text
                    title = prompt.strip() or "Prompt"
                    editor_outcome = await self._open_multiline_editor(
                        result.text, title=title, context=editor_context
                    )
                    if editor_outcome.action == "discard":
                        if capture_editor_submission:
                            self._pending_editor_submission = None
                        default_text = editor_outcome.text
                        continue
                    if editor_outcome.action == "submit":
                        if capture_editor_submission:
                            self._pending_editor_submission = editor_outcome
                        return editor_outcome.text
                    if capture_editor_submission:
                        self._pending_editor_submission = None
                    default_text = editor_outcome.text
                    continue
                if capture_editor_submission:
                    self._pending_editor_submission = None
                return result
            result = await loop.run_in_executor(
                None,
                lambda: Prompt.ask(
                    "[bold cyan]dogent>[/bold cyan]" if prompt == "dogent> " else prompt
                ),
            )
            if capture_editor_submission:
                self._pending_editor_submission = None
            return result

    async def _prompt_file_usage(self, save_path: Path) -> str | None:
        prompt_label = (
            f"prompt for how dogent uses {self._display_relpath(save_path)}: "
        )
        hint = "Enter: send • Esc: cancel"
        loop = asyncio.get_event_loop()
        default_text = ""
        while True:
            if self.session:
                prompt_callable = getattr(self.session, "prompt_async", None)
                prompt_kwargs: dict[str, Any] = {"bottom_toolbar": hint}
                if default_text:
                    prompt_kwargs["default"] = default_text
                if self._can_use_multiline_editor():
                    self._multiline_editor_allowed.set()
                else:
                    self._multiline_editor_allowed.clear()
                bindings = KeyBindings()

                @bindings.add("escape", eager=True)
                def _cancel(event) -> None:  # type: ignore[no-untyped-def]
                    event.app.exit(result=INPUT_CANCELLED)

                merged_bindings = bindings
                if merge_key_bindings and getattr(self.session, "key_bindings", None):
                    merged_bindings = merge_key_bindings(
                        [self.session.key_bindings, bindings]
                    )
                orig_bindings = getattr(self.session, "key_bindings", None)
                orig_toolbar = getattr(self.session, "bottom_toolbar", None)
                try:
                    prompt_kwargs["key_bindings"] = merged_bindings
                    if callable(prompt_callable):
                        result = await prompt_callable(prompt_label, **prompt_kwargs)
                    else:
                        result = await loop.run_in_executor(
                            None,
                            lambda: self.session.prompt(prompt_label, **prompt_kwargs),
                        )
                finally:
                    self.session.key_bindings = orig_bindings
                    self.session.bottom_toolbar = orig_toolbar
                    self._multiline_editor_allowed.clear()
                if result is INPUT_CANCELLED:
                    return None
                if isinstance(result, MultilineEditRequest):
                    if not self._can_use_multiline_editor():
                        return result.text
                    title = prompt_label.strip() or "Prompt"
                    editor_outcome = await self._open_multiline_editor(
                        result.text, title=title, context="prompt"
                    )
                    if editor_outcome.action == "discard":
                        default_text = editor_outcome.text
                        continue
                    if editor_outcome.action == "submit":
                        return editor_outcome.text
                    default_text = editor_outcome.text
                    continue
                return result
            self.console.print(hint)
            result = await loop.run_in_executor(
                None,
                lambda: Prompt.ask(
                    "[bold cyan]dogent>[/bold cyan]"
                    if prompt_label == "dogent> "
                    else prompt_label
                ),
            )
            return result

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
        with suppress(Exception):
            self.session_logger.close()
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
                    f"Referenced @{attachment.path}{suffix}",
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
            "awaiting_input": "🕓",
            "awaiting input": "🕓",
            "needs_clarification": "❓",
            "needs clarification": "❓",
            "clarification": "❓",
            "needs_outline_edit": "📝",
            "needs outline edit": "📝",
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
