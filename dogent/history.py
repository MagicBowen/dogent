from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .paths import DogentPaths


class HistoryManager:
    """Appends structured progress entries to .dogent/history.json."""

    def __init__(self, paths: DogentPaths) -> None:
        self.paths = paths
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_history_file()

    def append(
        self,
        summary: str,
        status: str,
        prompt: Optional[str] = None,
        todos: Optional[list[dict[str, str]]] = None,
        duration_ms: Optional[int] = None,
        api_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "summary": summary,
            "prompt": prompt,
            "todos": todos or [],
            "duration_ms": duration_ms,
            "duration_api_ms": api_ms,
            "cost_usd": cost_usd,
        }
        entries = self.read_entries()
        entries.append(entry)
        self._write_entries(entries)

    def read_entries(self) -> list[dict[str, Any]]:
        if not self.paths.history_file.exists():
            return []
        try:
            data = json.loads(self.paths.history_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def read_raw(self) -> str:
        """Return raw history file contents for template injection."""
        if not self.paths.history_file.exists():
            return ""
        try:
            return self.paths.history_file.read_text(encoding="utf-8")
        except Exception:
            return ""

    def to_prompt_block(self, limit: int = 5) -> str:
        entries = self.read_entries()
        if not entries:
            return "No prior history."
        latest = entries[-limit:]
        lines = []
        for entry in latest:
            ts = entry.get("timestamp", "")
            status = entry.get("status", "")
            summary = entry.get("summary", "")
            lines.append(f"- [{status}] {summary} ({ts})")
        return "\n".join(lines)

    def latest_todos(self) -> list[dict[str, Any]]:
        """Return the most recently recorded todo list."""
        entries = self.read_entries()
        for entry in reversed(entries):
            todos = entry.get("todos")
            if todos is not None:
                return todos or []
        return []

    def _write_entries(self, entries: list[dict[str, Any]]) -> None:
        self.paths.history_file.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _ensure_history_file(self) -> None:
        if not self.paths.history_file.exists():
            self._write_entries([])

    def clear(self) -> None:
        """Clear all recorded history entries."""
        self._write_entries([])
