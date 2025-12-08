from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional


CommandHandler = Callable[[str], Awaitable[bool]]


@dataclass
class Command:
    name: str
    handler: CommandHandler
    description: str


class CommandRegistry:
    """Registry for CLI slash commands."""

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}

    def register(self, name: str, handler: CommandHandler, description: str) -> None:
        if not name.startswith("/"):
            name = f"/{name}"
        self._commands[name] = Command(name=name, handler=handler, description=description)

    def get(self, name: str) -> Optional[Command]:
        if not name.startswith("/"):
            name = f"/{name}"
        return self._commands.get(name)

    def names(self) -> List[str]:
        return list(self._commands.keys())

    def descriptions(self) -> List[str]:
        return [f"{cmd.name} — {cmd.description}" for cmd in self._commands.values()]
