from __future__ import annotations

import json
from datetime import datetime, timezone
import traceback
from pathlib import Path
from typing import Any

from ..config.paths import DogentPaths


class SessionLogger:
    """Append Markdown session logs when debug mode is enabled."""

    def __init__(self, paths: DogentPaths, *, enabled: bool) -> None:
        self.paths = paths
        self.enabled = bool(enabled)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._started_at = datetime.now(timezone.utc)
        self._handle = None
        self._path: Path | None = None
        self._last_system_by_source: dict[str, str] = {}
        self._header_written = False

    @property
    def path(self) -> Path | None:
        return self._path

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.flush()
            except Exception:
                pass
            try:
                self._handle.close()
            except Exception:
                pass
            self._handle = None
        self.enabled = False

    def log_system_prompt(self, source: str, prompt: str) -> None:
        if not self.enabled or not prompt:
            return
        if self._last_system_by_source.get(source) == prompt:
            return
        self._last_system_by_source[source] = prompt
        self._write(
            {
                "role": "system",
                "source": source,
                "event": "prompt.system",
                "content": prompt,
            }
        )

    def log_user_prompt(self, source: str, prompt: str) -> None:
        if not self.enabled or not prompt:
            return
        self._write(
            {
                "role": "user",
                "source": source,
                "event": "prompt.user",
                "content": prompt,
            }
        )

    def log_assistant_text(self, source: str, text: str) -> None:
        if not self.enabled or not text:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.text",
                "content": text,
            }
        )

    def log_assistant_thinking(self, source: str, thinking: str) -> None:
        if not self.enabled or not thinking:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.thinking",
                "content": thinking,
            }
        )

    def log_tool_use(self, source: str, *, name: str, tool_id: str, input_data: Any) -> None:
        if not self.enabled:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.tool_use",
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
        if not self.enabled:
            return
        self._write(
            {
                "role": "tool",
                "source": source,
                "event": "assistant.tool_result",
                "content": {
                    "name": name,
                    "tool_id": tool_id,
                    "result": content,
                    "is_error": bool(is_error),
                },
            }
        )

    def log_result(self, source: str, *, result: str | None, is_error: bool | None) -> None:
        if not self.enabled:
            return
        if result is None and is_error is None:
            return
        self._write(
            {
                "role": "assistant",
                "source": source,
                "event": "assistant.result",
                "content": {
                    "result": result,
                    "is_error": bool(is_error),
                },
            }
        )

    def log_exception(self, source: str, exc: BaseException) -> None:
        if not self.enabled:
            return
        location = None
        tb = exc.__traceback__
        if tb is not None:
            frames = traceback.extract_tb(tb)
            if frames:
                last = frames[-1]
                location = f"{last.filename}:{last.lineno} in {last.name}"
        trace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._write(
            {
                "role": "system",
                "source": source,
                "event": "exception",
                "content": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "location": location,
                    "traceback": trace_text,
                },
            }
        )

    def _ensure_handle(self) -> None:
        if self._handle is not None or not self.enabled:
            return
        logs_dir = self.paths.dogent_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._path = logs_dir / f"dogent_session_{self._session_id}.md"
        self._handle = self._path.open("a", encoding="utf-8")
        if not self._header_written and self._handle is not None:
            self._handle.write("# Dogent Session Log\n\n")
            self._handle.write(f"- Session: {self._session_id}\n")
            self._handle.write(f"- Started: {self._started_at.isoformat()}\n\n")
            self._handle.write("---\n\n")
            self._header_written = True

    def _write(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._ensure_handle()
        if self._handle is None:
            return
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            role = str(payload.get("role", ""))
            source = str(payload.get("source", ""))
            event = str(payload.get("event", ""))
            content = payload.get("content", "")
            self._handle.write(f"## {timestamp} · {role}/{source} · {event}\n")
            self._handle.write(self._format_content_block(content))
            self._handle.write("\n\n")
            self._handle.flush()
        except Exception:
            self.close()

    def _format_content_block(self, content: Any) -> str:
        if isinstance(content, (dict, list)):
            body = json.dumps(content, indent=2, ensure_ascii=False)
            language = "json"
        else:
            body = "" if content is None else str(content)
            language = "markdown"
        body = body.rstrip()
        return f"```{language}\n{body}\n```"
