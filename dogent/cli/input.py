from __future__ import annotations

import base64
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from typing import Callable, Iterable

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


DOC_TEMPLATE_TOKEN = "@@"
EDITABLE_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".txt"}


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
