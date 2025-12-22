from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console

from .paths import DogentPaths


@dataclass(frozen=True)
class LessonIncident:
    status: str  # error or interrupted
    summary: str
    todos_markdown: str


class LessonsManager:
    def __init__(self, paths: DogentPaths, console: Optional[Console] = None) -> None:
        self.paths = paths
        self.console = console or Console()

    def ensure_file(self) -> None:
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.lessons_file.exists():
            self.paths.lessons_file.write_text("# Lessons\n\n", encoding="utf-8")

    def read_all(self) -> str:
        if not self.paths.lessons_file.exists():
            return ""
        try:
            return self.paths.lessons_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def append_entry(self, entry_markdown: str) -> Path:
        self.ensure_file()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = entry_markdown.strip()
        if not entry.startswith("## "):
            entry = f"## Lesson ({stamp})\n\n{entry}"
        block = "\n\n---\n\n" + entry + "\n"
        self.paths.lessons_file.write_text(
            self.read_all().rstrip() + block,
            encoding="utf-8",
        )
        return self.paths.lessons_file

    def list_recent_titles(self, limit: int = 5) -> list[str]:
        text = self.read_all()
        if not text:
            return []
        titles: list[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                titles.append(line.removeprefix("## ").strip())
        return titles[-limit:]


def format_remaining_todos_markdown(todos: list[dict[str, str | None]]) -> str:
    if not todos:
        return ""
    lines: list[str] = []
    for todo in todos:
        title = str(todo.get("title") or "").strip()
        status = str(todo.get("status") or "").strip()
        note = str(todo.get("note") or "").strip()
        if not title:
            continue
        suffix = f" — {note}" if note else ""
        lines.append(f"- [{status}] {title}{suffix}")
    return "\n".join(lines)

