from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass
class TodoItem:
    title: str
    status: str = "pending"
    note: Optional[str] = None


class TodoManager:
    """Tracks todo items produced by the TodoWrite tool."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.items: List[TodoItem] = []
        self.last_source: Optional[str] = None

    def set_items(self, items: Iterable[TodoItem], source: str | None = None) -> None:
        self.items = list(items)
        self.last_source = source

    def update_from_payload(self, payload: Any, source: str | None = None) -> bool:
        """Update todos from arbitrary payload; returns True if updated."""
        items = self._normalize_items(payload)
        if items is None:
            return False
        self.set_items(items, source)
        return True

    def render_plain(self) -> str:
        if not self.items:
            return "无 todo，等待 TodoWrite 工具填充。"
        lines = []
        for item in self.items:
            note = f" — {item.note}" if item.note else ""
            status = self._status_icon(item.status)
            lines.append(f"- {status} {item.title}{note}")
        return "\n".join(lines)

    def render_table(self) -> Table:
        table = Table(title="当前 Todo")
        table.add_column("状态", style="cyan", no_wrap=True)
        table.add_column("内容", style="white")
        table.add_column("备注", style="dim")
        if not self.items:
            table.add_row("-", "无 todo，等待 TodoWrite", "")
            return table
        for item in self.items:
            icon = self._status_icon(item.status)
            table.add_row(f"{icon} {item.status}", item.title, item.note or "")
        return table

    def render_panel(self, show_empty: bool = True) -> Optional[Panel]:
        if not self.items and not show_empty:
            return None
        if not self.items:
            return Panel("暂无 Todo，等待 TodoWrite 更新。", title="✅ Todo", border_style="cyan")
        lines: list[str] = []
        for item in self.items:
            icon = self._status_icon(item.status)
            note = f" — {item.note}" if item.note else ""
            lines.append(f"{icon} {item.title}{note}")
        text = Text("\n".join(lines))
        return Panel(text, title="✅ Todo", border_style="cyan")

    def _normalize_items(self, payload: Any) -> Optional[List[TodoItem]]:
        """Accept varied payloads and return a normalized list of TodoItem."""
        if payload is None:
            return None
        if isinstance(payload, str):
            parsed = self._try_parse_json(payload)
            if parsed is None:
                return None
            return self._normalize_items(parsed)
        if isinstance(payload, dict):
            if "items" in payload:
                return self._normalize_items(payload.get("items"))
            if "todos" in payload:
                return self._normalize_items(payload.get("todos"))
            if "title" in payload or "content" in payload or "task" in payload or "text" in payload:
                return [self._build_item(payload)]
            return None
        if isinstance(payload, list):
            items: List[TodoItem] = []
            for element in payload:
                normalized = self._normalize_items(element)
                if not normalized:
                    continue
                items.extend(normalized)
            return items or None
        return None

    def _status_icon(self, status: str) -> str:
        normalized = (status or "").lower()
        mapping = {
            "pending": "⏳",
            "todo": "⏳",
            "doing": "🔄",
            "in_progress": "🔄",
            "in progress": "🔄",
            "active": "🔄",
            "done": "✅",
            "complete": "✅",
            "completed": "✅",
            "blocked": "⛔",
            "review": "👀",
        }
        return mapping.get(normalized, "•")

    def _build_item(self, data: dict[str, Any]) -> TodoItem:
        title_raw = (
            data.get("title")
            or data.get("content")
            or data.get("task")
            or data.get("text")
            or ""
        )
        title = str(title_raw).strip()
        if title.startswith("正在"):
            title = title.lstrip("正在").lstrip()
        return TodoItem(
            title=title,
            status=str(data.get("status") or "pending"),
            note=(data.get("note") or data.get("detail")),
        )

    def _try_parse_json(self, text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
