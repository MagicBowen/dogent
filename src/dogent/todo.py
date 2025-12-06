"""Todo list utilities for Dogent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from rich.table import Table
from rich.panel import Panel


@dataclass
class TodoItem:
    id: int
    title: str
    status: str = "pending"  # pending | in_progress | done
    details: Optional[str] = None
    section: Optional[str] = None


class TodoManager:
    def __init__(self) -> None:
        self._items: List[TodoItem] = []
        self._next_id = 1

    def add(self, title: str, details: Optional[str] = None, section: Optional[str] = None) -> TodoItem:
        item = TodoItem(id=self._next_id, title=title, details=details, section=section)
        self._next_id += 1
        self._items.append(item)
        return item

    def update_status(self, item_id: int, status: str) -> None:
        for item in self._items:
            if item.id == item_id:
                item.status = status
                return

    def list(self) -> List[TodoItem]:
        return list(self._items)

    def render_panel(self) -> Panel:
        table = Table(title="Todo", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Status", style="green", width=12)
        table.add_column("Title")
        table.add_column("Section", width=12)
        if not self._items:
            table.add_row("-", "-", "No tasks yet", "")
        else:
            for item in self._items:
                status_style = {
                    "done": "[green]done[/green]",
                    "in_progress": "[cyan]in_progress[/cyan]",
                    "pending": "[yellow]pending[/yellow]",
                }.get(item.status, item.status)
                table.add_row(
                    str(item.id),
                    status_style,
                    item.title,
                    item.section or "",
                )
        return Panel(table, title="Tasks", border_style="cyan")

    def render_summary_counts(self) -> str:
        total = len(self._items)
        done = len([i for i in self._items if i.status == "done"])
        pending = len([i for i in self._items if i.status == "pending"])
        progress = len([i for i in self._items if i.status == "in_progress"])
        return f"Total:{total} Pending:{pending} InProgress:{progress} Done:{done}"
