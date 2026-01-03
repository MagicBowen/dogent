from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import DogentPaths


class SessionLogger:
    """Append JSONL session logs when debug mode is enabled."""

    def __init__(self, paths: DogentPaths, *, enabled: bool) -> None:
        self.paths = paths
        self.enabled = bool(enabled)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._handle = None
        self._path: Path | None = None
        self._last_system_by_source: dict[str, str] = {}

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

    def _ensure_handle(self) -> None:
        if self._handle is not None or not self.enabled:
            return
        logs_dir = self.paths.dogent_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self._path = logs_dir / f"dogent_session_{self._session_id}.json"
        self._handle = self._path.open("a", encoding="utf-8")

    def _write(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._ensure_handle()
        if self._handle is None:
            return
        entry = dict(payload)
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        try:
            self._handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._handle.flush()
        except Exception:
            self.close()
