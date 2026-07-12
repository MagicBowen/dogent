from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Mapping

from rich.cells import cell_len, get_character_cell_size, set_cell_size
from rich.console import Console
from rich.live import Live
from rich.text import Text


DEFAULT_CONTEXT_WINDOW_TOKENS = 256_000
EXTENDED_CONTEXT_WINDOW_TOKENS = 1_000_000
CONTEXT_OVERRIDE_ENV = "CLAUDE_CODE_MAX_CONTEXT_TOKENS"
DISABLE_COMPACT_ENV = "DISABLE_COMPACT"
STATUS_MODEL_COLOR = "bright_cyan"
STATUS_CONTEXT_COLOR = "bright_cyan"
STATUS_PROGRESS_COLOR = "green"
STATUS_PATH_COLOR = "bright_blue"
STATUS_SEPARATOR_COLOR = "bright_black"

CapacityLookup = Callable[[str], Awaitable[int | None]]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    return None


def _positive_int(value: object) -> int | None:
    parsed = _non_negative_int(value)
    return parsed if parsed and parsed > 0 else None


def _sanitize(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _take_cells(text: str, width: int, *, from_end: bool = False) -> str:
    if width <= 0:
        return ""
    if cell_len(text) <= width:
        return text
    if from_end:
        chars: list[str] = []
        used = 0
        for char in reversed(text):
            size = get_character_cell_size(char)
            if used + size > width:
                break
            chars.append(char)
            used += size
        return "".join(reversed(chars))
    return set_cell_size(text, width).rstrip()


def _end_truncate(text: str, width: int) -> str:
    if cell_len(text) <= width:
        return text
    if width <= 1:
        return "…" if width == 1 else ""
    return _take_cells(text, width - 1) + "…"


def _middle_truncate(text: str, width: int) -> str:
    if cell_len(text) <= width:
        return text
    if width <= 1:
        return "…" if width == 1 else ""
    left_width = (width - 1) // 2
    right_width = width - 1 - left_width
    return _take_cells(text, left_width) + "…" + _take_cells(
        text, right_width, from_end=True
    )


def _workspace_label(root: Path) -> str:
    resolved = root.expanduser().resolve()
    home = Path.home().expanduser().resolve()
    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return _sanitize(str(resolved), "/")
    return "~" if not relative.parts else f"~/{relative.as_posix()}"


def context_capacity_from_hints(
    model: str | None,
    environ: Mapping[str, str] | None = None,
) -> int | None:
    env = environ if environ is not None else os.environ
    if _truthy(env.get(DISABLE_COMPACT_ENV)):
        override = env.get(CONTEXT_OVERRIDE_ENV)
        if override is not None:
            try:
                parsed = int(override.strip())
            except (TypeError, ValueError):
                parsed = 0
            if parsed > 0:
                return parsed
    if re.search(r"\[1m\]\s*$", model or "", flags=re.IGNORECASE):
        return EXTENDED_CONTEXT_WINDOW_TOKENS
    return None


def usage_input_tokens(usage: object) -> int | None:
    if not isinstance(usage, dict):
        return None
    explicit_total = _non_negative_int(usage.get("total_input_tokens"))
    if explicit_total is not None:
        return explicit_total
    input_tokens = _non_negative_int(usage.get("input_tokens", 0))
    cache_create = _non_negative_int(usage.get("cache_creation_input_tokens", 0))
    cache_read = _non_negative_int(usage.get("cache_read_input_tokens", 0))
    if input_tokens is None or cache_create is None or cache_read is None:
        return None
    cache_tokens = cache_create + cache_read
    if cache_tokens and input_tokens >= cache_tokens:
        return input_tokens
    return input_tokens + cache_tokens


@dataclass(frozen=True)
class StatusSnapshot:
    model: str
    workspace: str
    context_tokens: int | None
    context_capacity: int

    @property
    def context_percent(self) -> int | None:
        if self.context_tokens is None or self.context_capacity <= 0:
            return None
        percent = round(self.context_tokens * 100 / self.context_capacity)
        return max(0, min(100, percent))


class StatusBarState:
    def __init__(
        self,
        model: str | None,
        workspace: Path,
        *,
        environ: Mapping[str, str] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._configured_model = _sanitize(model, "model unavailable")
        self._resolved_model: str | None = None
        self._workspace = _workspace_label(workspace)
        self._environ = environ if environ is not None else os.environ
        self._capacity = (
            context_capacity_from_hints(self._configured_model, self._environ)
            or DEFAULT_CONTEXT_WINDOW_TOKENS
        )
        self._context_tokens: int | None = None
        self._generation = 0
        self._model_revision = 0
        self._capacity_cache: dict[str, int] = {}
        self._on_change = on_change

    @property
    def generation(self) -> int:
        return self._generation

    def set_on_change(self, callback: Callable[[], None] | None) -> None:
        self._on_change = callback

    def snapshot(self) -> StatusSnapshot:
        model = self._configured_model
        if self._resolved_model and not re.search(
            r"\[1m\]\s*$", self._configured_model, flags=re.IGNORECASE
        ):
            model = self._resolved_model
        return StatusSnapshot(
            model=model,
            workspace=self._workspace,
            context_tokens=self._context_tokens,
            context_capacity=self._capacity,
        )

    def update_from_assistant(
        self,
        model: str | None,
        usage: object,
        generation: int,
    ) -> bool:
        if generation != self._generation:
            return False
        resolved_model = _sanitize(model, "")
        tokens = usage_input_tokens(usage)
        changed = False
        if resolved_model and resolved_model != self._resolved_model:
            self._resolved_model = resolved_model
            changed = True
        if tokens is not None and tokens != self._context_tokens:
            self._context_tokens = tokens
            changed = True
        if changed:
            self._changed()
        return changed

    def reset_context(self, generation: int) -> None:
        self._generation = generation
        self._context_tokens = None
        self._changed()

    def set_configured_model(self, model: str | None, generation: int) -> None:
        self._configured_model = _sanitize(model, "model unavailable")
        self._resolved_model = None
        self._context_tokens = None
        self._generation = generation
        self._model_revision += 1
        self._capacity = (
            context_capacity_from_hints(self._configured_model, self._environ)
            or DEFAULT_CONTEXT_WINDOW_TOKENS
        )
        self._changed()

    async def resolve_capacity(self, lookup: CapacityLookup | None) -> int:
        configured_model = self._configured_model
        model_revision = self._model_revision
        hinted = context_capacity_from_hints(
            configured_model, self._environ
        )
        if hinted is not None:
            if self._capacity_request_current(configured_model, model_revision):
                self._set_capacity(hinted)
            return hinted
        lookup_model = self._model_for_lookup(configured_model)
        cached = self._capacity_cache.get(lookup_model)
        if cached is not None:
            if self._capacity_request_current(configured_model, model_revision):
                self._set_capacity(cached)
            return cached
        if lookup is not None:
            try:
                capacity = await lookup(lookup_model)
            except Exception:
                capacity = None
            parsed = _positive_int(capacity)
            if parsed is not None:
                self._capacity_cache[lookup_model] = parsed
                if self._capacity_request_current(configured_model, model_revision):
                    self._set_capacity(parsed)
                return parsed
        if self._capacity_request_current(configured_model, model_revision):
            self._set_capacity(DEFAULT_CONTEXT_WINDOW_TOKENS)
        return DEFAULT_CONTEXT_WINDOW_TOKENS

    def _model_for_lookup(self, model: str) -> str:
        return re.sub(
            r"\[1m\]\s*$", "", model, flags=re.IGNORECASE
        )

    def _capacity_request_current(self, model: str, revision: int) -> bool:
        return model == self._configured_model and revision == self._model_revision

    def _set_capacity(self, capacity: int) -> None:
        if capacity == self._capacity:
            return
        self._capacity = capacity
        self._changed()

    def _changed(self) -> None:
        if self._on_change is not None:
            self._on_change()


class StatusBarFormatter:
    def __init__(self, state: StatusBarState, *, use_unicode: bool = True) -> None:
        self.state = state
        self.use_unicode = use_unicode

    def plain(self, width: int, activity: str | None = None) -> str:
        width = max(1, width)
        snapshot = self.state.snapshot()
        model = _sanitize(snapshot.model, "model unavailable")
        workspace = _sanitize(snapshot.workspace, "/")
        activity = _sanitize(activity, "") if activity else ""
        percent = snapshot.context_percent
        percent_text = "--" if percent is None else f"{percent}%"
        wide_minimum = 100 if activity else 80
        if width >= wide_minimum:
            meter = self._meter(percent)
            star = "✦" if self.use_unicode else "*"
            separator = "│" if self.use_unicode else "|"
            folder = "📁 " if self.use_unicode else ""
            if activity:
                wait_label = activity if width >= 120 else "Waiting"
                wait_icon = "⏳ " if self.use_unicode else ""
                model = f"{model} · {wait_icon}{wait_label}"
            prefix = (
                f"{star} {model}  {separator}  Context [{meter}] {percent_text}  "
                f"{separator}  {folder}"
            )
            path_width = max(8, width - cell_len(prefix))
            line = prefix + _middle_truncate(workspace, path_width)
        elif width >= 42:
            separator = "│" if self.use_unicode else "|"
            waiting = ""
            if activity:
                waiting = " · ⏳ Waiting" if self.use_unicode else " · Waiting"
            suffix = f" {separator} Ctx {percent_text}{waiting} {separator} "
            model_width = min(24, max(8, (width - cell_len(suffix)) // 2))
            model = _end_truncate(model, model_width)
            path_width = max(5, width - cell_len(model + suffix))
            line = model + suffix + _middle_truncate(workspace, path_width)
        else:
            folder = Path(workspace).name or workspace
            suffix = f" | {percent_text} | "
            if activity:
                model = f"{'⏳ ' if self.use_unicode else ''}{model}"
            model_width = max(4, (width - cell_len(suffix)) // 2)
            model = _end_truncate(model, model_width)
            folder_width = max(3, width - cell_len(model + suffix))
            line = model + suffix + _end_truncate(folder, folder_width)
        line = _end_truncate(line, width)
        return line + " " * max(0, width - cell_len(line))

    def rich(self, width: int, activity: str | None = None) -> Text:
        line = self.plain(width, activity)
        text = Text(no_wrap=True, overflow="ellipsis")
        for role, segment in self._segments(line):
            style = ""
            if role == "model":
                style = f"bold {STATUS_MODEL_COLOR}"
            elif role == "context":
                style = f"bold {STATUS_CONTEXT_COLOR}"
            elif role == "progress":
                style = f"bold {STATUS_PROGRESS_COLOR}"
            elif role == "path":
                style = f"bold {STATUS_PATH_COLOR}"
            elif role == "separator":
                style = STATUS_SEPARATOR_COLOR
            text.append(segment, style=style)
        return text

    def prompt_fragments(
        self, width: int, activity: str | None = None
    ) -> list[tuple[str, str]]:
        line = self.plain(width, activity)
        styles = {
            "model": "bold ansicyan",
            "context": "bold ansicyan",
            "progress": "bold ansigreen",
            "path": "bold ansiblue",
            "separator": "ansibrightblack",
        }
        return [(styles[role], segment) for role, segment in self._segments(line)]

    def _meter(self, percent: int | None) -> str:
        filled = 0 if percent is None else min(20, max(0, percent * 20 // 100))
        if not self.use_unicode:
            return "#" * filled + "-" * (20 - filled)
        return "█" * filled + "░" * (20 - filled)

    def _segments(self, line: str) -> list[tuple[str, str]]:
        separator = "│" if "│" in line else "|"
        first = line.find(separator)
        second = line.find(separator, first + 1) if first >= 0 else -1
        if first < 0:
            return [("model", line)]
        if second < 0:
            return [("model", line[:first]), ("separator", line[first:])]
        context = line[first + 1 : second]
        context_parts: list[tuple[str, str]] = []
        cursor = 0
        for match in re.finditer(r"\[[^\]]+\]|(?<!\w)(?:--|\d+%)(?!\w)", context):
            if match.start() > cursor:
                context_parts.append(("context", context[cursor : match.start()]))
            context_parts.append(("progress", match.group(0)))
            cursor = match.end()
        if cursor < len(context):
            context_parts.append(("context", context[cursor:]))
        return [
            ("model", line[:first]),
            ("separator", line[first : first + 1]),
            *context_parts,
            ("separator", line[second : second + 1]),
            ("path", line[second + 1 :]),
        ]


class _LiveStatusRenderable:
    def __init__(self, controller: "StatusBarController") -> None:
        self.controller = controller

    def __rich_console__(self, _console, options):
        yield self.controller._renderable(options.max_width)


class StatusBarController:
    def __init__(
        self,
        state: StatusBarState,
        console: Console,
        *,
        enabled: bool,
    ) -> None:
        self.state = state
        self.console = console
        self.enabled = enabled
        encoding = (getattr(console, "encoding", None) or "utf-8").lower()
        self.formatter = StatusBarFormatter(
            state, use_unicode="utf" in encoding
        )
        self._live: Live | None = None
        self._activity: str | None = None
        self._suspended = False
        self._live_renderable = _LiveStatusRenderable(self)
        self.state.set_on_change(self.refresh)

    @property
    def live_active(self) -> bool:
        return self._live is not None

    @property
    def suspended(self) -> bool:
        return self._suspended

    def prompt_toolbar(self):
        if self._suspended:
            return []
        return self.formatter.prompt_fragments(
            self.console.width, self._activity
        )

    def start_live(self) -> None:
        if not self.enabled or self._suspended or self._live is not None:
            return
        self._live = Live(
            self._live_renderable,
            console=self.console,
            auto_refresh=False,
            transient=True,
        )
        self._live.start(refresh=True)

    def stop_live(self) -> None:
        live = self._live
        self._live = None
        if live is not None:
            live.stop()

    def suspend(self) -> None:
        self._suspended = True
        self.stop_live()

    def resume(self) -> None:
        self._suspended = False
        self.start_live()

    def set_activity(self, text: str | None) -> None:
        self._activity = _sanitize(text, "") if text else None
        self.refresh()

    def refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._live_renderable, refresh=True)
        try:
            from prompt_toolkit.application.current import get_app

            get_app().invalidate()
        except Exception:
            pass

    def status_window(self):
        if not self.enabled or self._suspended:
            return None
        try:
            from prompt_toolkit.layout.controls import FormattedTextControl
            from prompt_toolkit.layout.containers import Window
        except ImportError:
            return None
        return Window(
            FormattedTextControl(lambda: self.prompt_toolbar()),
            height=1,
            dont_extend_height=True,
        )

    def _renderable(self, width: int | None = None):
        bar = self.formatter.rich(
            width or self.console.width, self._activity
        )
        return bar


async def lookup_model_capacity(
    model: str,
    *,
    base_url: str | None,
    auth_token: str | None,
    timeout: float = 2.0,
) -> int | None:
    if not model or model == "model unavailable" or not auth_token:
        return None
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            auth_token=auth_token,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
        )
        try:
            info = await asyncio.wait_for(
                client.models.retrieve(model_id=model), timeout=timeout
            )
        finally:
            await client.close()
    except Exception:
        return None
    return _positive_int(getattr(info, "max_input_tokens", None))
