from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.paths import DogentPaths

LOG_LEVELS = ("error", "warn", "info", "debug")
LOG_LEVEL_PRIORITY = {level: idx for idx, level in enumerate(LOG_LEVELS)}
LOG_TYPE_SESSION = "session"


@dataclass(frozen=True)
class LogSelection:
    enabled_types: frozenset[str]
    enabled_levels: frozenset[str]


def resolve_debug_config(raw: Any) -> LogSelection:
    enabled_types: set[str] = set()
    enabled_levels: set[str] = set()

    def enable_all() -> None:
        enabled_types.add(LOG_TYPE_SESSION)
        enabled_levels.update(LOG_LEVELS)

    def enable_level(level: str) -> None:
        if level not in LOG_LEVEL_PRIORITY:
            return
        idx = LOG_LEVEL_PRIORITY[level]
        enabled_levels.update(LOG_LEVELS[: idx + 1])

    def handle_token(token: str) -> None:
        if token == "all":
            enable_all()
            return
        if token == LOG_TYPE_SESSION:
            enabled_types.add(LOG_TYPE_SESSION)
            return
        if token in LOG_LEVEL_PRIORITY:
            enable_level(token)

    if raw is None or raw is False:
        return LogSelection(frozenset(), frozenset())
    if raw is True:
        enable_all()
        return LogSelection(frozenset(enabled_types), frozenset(enabled_levels))
    if isinstance(raw, str):
        cleaned = raw.strip().lower()
        if cleaned in {"", "none", "null", "off", "false", "0", "no", "n"}:
            return LogSelection(frozenset(), frozenset())
        if cleaned in {"true", "1", "yes", "y", "on"}:
            enable_all()
            return LogSelection(frozenset(enabled_types), frozenset(enabled_levels))
        handle_token(cleaned)
        return LogSelection(frozenset(enabled_types), frozenset(enabled_levels))
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            if not isinstance(item, str):
                continue
            cleaned = item.strip().lower()
            if not cleaned:
                continue
            if cleaned in {"true", "1", "yes", "y", "on", "all"}:
                enable_all()
                continue
            if cleaned in {"none", "null", "off", "false", "0", "no", "n"}:
                continue
            handle_token(cleaned)
        return LogSelection(frozenset(enabled_types), frozenset(enabled_levels))
    return LogSelection(frozenset(), frozenset())


class SessionLogger:
    """Write Markdown logs when debug logging is enabled."""

    def __init__(self, paths: DogentPaths, debug_config: Any) -> None:
        self.paths = paths
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._started_at = datetime.now(timezone.utc)
        self._path: Path | None = None
        self._header = ""
        self._last_system_by_source: dict[str, str] = {}
        self._interaction_counter = 0
        self._active_interaction_id: int | None = None
        self.enabled = False
        self._enabled_types: set[str] = set()
        self._enabled_levels: set[str] = set()
        self.configure(debug_config)

    @property
    def path(self) -> Path | None:
        return self._path

    def configure(self, debug_config: Any) -> None:
        selection = resolve_debug_config(debug_config)
        self._enabled_types = set(selection.enabled_types)
        self._enabled_levels = set(selection.enabled_levels)
        self.enabled = bool(self._enabled_types or self._enabled_levels)

    def close(self) -> None:
        self.enabled = False

    def start_interaction(self, source: str, *, summary: str | None = None) -> int | None:
        if not self._session_enabled():
            return None
        self._interaction_counter += 1
        self._active_interaction_id = self._interaction_counter
        self._write(
            {
                "role": "system",
                "source": source,
                "event": "session.interaction.start",
                "type": LOG_TYPE_SESSION,
                "interaction_id": self._active_interaction_id,
                "content": {"summary": summary},
            }
        )
        return self._active_interaction_id

    def end_interaction(self, source: str, *, status: str | None = None) -> None:
        if not self._session_enabled():
            self._active_interaction_id = None
            return
        if self._active_interaction_id is None:
            return
        self._write(
            {
                "role": "system",
                "source": source,
                "event": "session.interaction.end",
                "type": LOG_TYPE_SESSION,
                "interaction_id": self._active_interaction_id,
                "content": {"status": status},
            }
        )
        self._active_interaction_id = None

    def log_system_prompt(self, source: str, prompt: str) -> None:
        if not self._session_enabled() or not prompt:
            return
        if self._last_system_by_source.get(source) == prompt:
            return
        self._last_system_by_source[source] = prompt
        self._write(
            {
                "role": "system",
                "source": source,
                "event": "prompt.system",
                "type": LOG_TYPE_SESSION,
                "content": prompt,
            }
        )

    def log_user_prompt(self, source: str, prompt: str) -> None:
        if not self._session_enabled() or not prompt:
            return
        self._write(
            {
                "role": "user",
                "source": source,
                "event": "prompt.user",
                "type": LOG_TYPE_SESSION,
                "content": prompt,
            }
        )

    def log_assistant_text(self, source: str, text: str) -> None:
        if not self._session_enabled() or not text:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.text",
                "type": LOG_TYPE_SESSION,
                "content": text,
            }
        )

    def log_assistant_thinking(self, source: str, thinking: str) -> None:
        if not self._session_enabled() or not thinking:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.thinking",
                "type": LOG_TYPE_SESSION,
                "content": thinking,
            }
        )

    def log_tool_use(self, source: str, *, name: str, tool_id: str, input_data: Any) -> None:
        if not self._session_enabled():
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.tool_use",
                "type": LOG_TYPE_SESSION,
                "content": {
                    "name": name,
                    "tool_id": tool_id,
                    "input": input_data,
                },
            }
        )

    def log_tool_result(
        self,
        source: str,
        *,
        name: str,
        tool_id: str,
        content: Any,
        is_error: bool | None,
    ) -> None:
        if not self._session_enabled():
            return
        self._write(
            {
                "role": "tool",
                "source": source,
                "event": "assistant.tool_result",
                "type": LOG_TYPE_SESSION,
                "content": {
                    "name": name,
                    "tool_id": tool_id,
                    "result": content,
                    "is_error": bool(is_error),
                },
            }
        )

    def log_result(self, source: str, *, result: str | None, is_error: bool | None) -> None:
        if not self._session_enabled():
            return
        if result is None and is_error is None:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.result",
                "type": LOG_TYPE_SESSION,
                "content": {
                    "result": result,
                    "is_error": bool(is_error),
                },
            }
        )

    def log_level(self, source: str, level: str, event: str, content: Any | None = None) -> None:
        if not self._level_enabled(level):
            return
        self._write(
            {
                "role": "system",
                "source": source,
                "event": event,
                "level": level,
                "content": content,
            }
        )

    def log_exception(self, source: str, exc: BaseException) -> None:
        if not self._level_enabled("error"):
            return
        location = None
        tb = exc.__traceback__
        if tb is not None:
            frames = traceback.extract_tb(tb)
            if frames:
                last = frames[-1]
                location = f"{last.filename}:{last.lineno} in {last.name}"
        trace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self.log_level(
            source,
            "error",
            "exception",
            {
                "type": type(exc).__name__,
                "message": str(exc),
                "location": location,
                "traceback": trace_text,
            },
        )

    def _session_enabled(self) -> bool:
        return self.enabled and LOG_TYPE_SESSION in self._enabled_types

    def _level_enabled(self, level: str) -> bool:
        return self.enabled and level in self._enabled_levels

    def _ensure_path(self) -> None:
        if self._path is not None or not self.enabled:
            return
        logs_dir = self.paths.dogent_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._path = logs_dir / f"dogent_session_{self._session_id}.md"
        self._header = self._header_text()
        if not self._path.exists():
            self._path.write_text(self._header, encoding="utf-8")
            return
        try:
            existing = self._path.read_text(encoding="utf-8")
        except Exception:
            self._path.write_text(self._header, encoding="utf-8")
            return
        if not existing.startswith(self._header):
            self._path.write_text(self._header + existing, encoding="utf-8")

    def _header_text(self) -> str:
        return (
            "# Dogent Session Log\n\n"
            f"- Session: {self._session_id}\n"
            f"- Started: {self._started_at.isoformat()}\n\n"
            "---\n\n"
        )

    def _write(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._ensure_path()
        if self._path is None:
            return
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            role = str(payload.get("role", ""))
            source = str(payload.get("source", ""))
            event = str(payload.get("event", ""))
            log_type = str(
                payload.get("type") or payload.get("level") or LOG_TYPE_SESSION
            )
            interaction_id = payload.get("interaction_id", self._active_interaction_id)
            header = f"## {timestamp} · {log_type}/{source} · {event}"
            if interaction_id is not None:
                header = f"{header} · interaction {interaction_id}"
            header = f"{header}\n"
            content = payload.get("content", "")
            entry = f"{header}{self._format_content_block(content)}\n\n"
            self._prepend_entry(entry)
        except Exception:
            self.close()

    def _prepend_entry(self, entry: str) -> None:
        if self._path is None:
            return
        try:
            existing = self._path.read_text(encoding="utf-8")
        except Exception:
            return
        header = self._header or ""
        if header and existing.startswith(header):
            tail = existing[len(header) :]
            content = f"{header}{entry}{tail}"
        else:
            content = f"{header}{entry}{existing}"
        self._path.write_text(content, encoding="utf-8")

    def _format_content_block(self, content: Any) -> str:
        if isinstance(content, (dict, list)):
            body = json.dumps(content, indent=2, ensure_ascii=False)
            language = "json"
        else:
            body = "" if content is None else str(content)
            language = "markdown"
        body = body.rstrip()
        return f"```{language}\n{body}\n```"


_ACTIVE_LOGGER: SessionLogger | None = None


def set_active_logger(logger: SessionLogger | None) -> None:
    global _ACTIVE_LOGGER
    _ACTIVE_LOGGER = logger


def get_active_logger() -> SessionLogger | None:
    return _ACTIVE_LOGGER


def log_exception(source: str, exc: BaseException) -> None:
    logger = _ACTIVE_LOGGER
    if logger is not None:
        logger.log_exception(source, exc)


def log_error(source: str, event: str, content: Any | None = None) -> None:
    logger = _ACTIVE_LOGGER
    if logger is not None:
        logger.log_level(source, "error", event, content)


def log_warn(source: str, event: str, content: Any | None = None) -> None:
    logger = _ACTIVE_LOGGER
    if logger is not None:
        logger.log_level(source, "warn", event, content)


def log_info(source: str, event: str, content: Any | None = None) -> None:
    logger = _ACTIVE_LOGGER
    if logger is not None:
        logger.log_level(source, "info", event, content)


def log_debug(source: str, event: str, content: Any | None = None) -> None:
    logger = _ACTIVE_LOGGER
    if logger is not None:
        logger.log_level(source, "debug", event, content)
