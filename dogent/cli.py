from __future__ import annotations

import argparse
import asyncio
import select
import sys
import termios
import threading
import tty
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Tuple

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .agent import AgentRunner
from .commands import CommandRegistry
from .config import ConfigManager
from .file_refs import FileAttachment, FileReferenceResolver
from .history import HistoryManager
from .paths import DogentPaths
from .prompts import PromptBuilder
from .todo import TodoManager

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:  # pragma: no cover - optional dependency
    PromptSession = None  # type: ignore
    Completer = object  # type: ignore
    Completion = object  # type: ignore
    Document = object  # type: ignore


class DogentCompleter(Completer):
    """Suggests slash commands and @file paths while typing."""

    def __init__(self, root: Path, commands: list[str]) -> None:
        self.root = root
        self.commands = commands

    def get_completions(self, document: Document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd in self._match_commands(text):
                yield Completion(cmd, start_position=-len(text))
            return

        if "@" in text:
            for comp in self._match_files(text):
                yield comp

    def _match_commands(self, text: str) -> list[str]:
        return [c for c in self.commands if c.startswith(text)] or self.commands

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


class DogentCLI:
    """Interactive CLI interface for Dogent."""

    def __init__(self, root: Path | None = None, console: Console | None = None) -> None:
        self.console = console or Console()
        self.root = root or Path.cwd()
        self.registry = CommandRegistry()
        self.paths = DogentPaths(self.root)
        self.todo_manager = TodoManager(console=self.console)
        self.config_manager = ConfigManager(self.paths, console=self.console)
        self.file_resolver = FileReferenceResolver(self.root)
        self.history_manager = HistoryManager(self.paths)
        self.prompt_builder = PromptBuilder(
            self.paths, self.todo_manager, self.history_manager, console=self.console
        )
        self.agent = AgentRunner(
            config=self.config_manager,
            prompt_builder=self.prompt_builder,
            todo_manager=self.todo_manager,
            history=self.history_manager,
            console=self.console,
        )
        self._register_commands()
        self.session: PromptSession | None = None
        self._shutting_down = False
        if PromptSession is not None:
            bindings = KeyBindings()

            @bindings.add("enter", eager=True)
            def _(event):  # type: ignore
                """Accept completion if menu is open, else submit."""
                buf = event.current_buffer
                if buf.complete_state and buf.complete_state.current_completion:
                    buf.apply_completion(buf.complete_state.current_completion)
                    return
                buf.validate_and_handle()

            @bindings.add("escape", "enter", eager=True)
            def _(event):  # type: ignore
                """Insert newline with Alt/Option+Enter."""
                event.current_buffer.insert_text("\n")

            self.session = PromptSession(
                completer=DogentCompleter(self.root, self.registry.names()),
                complete_while_typing=True,
                key_bindings=bindings,
            )

    def _register_commands(self) -> None:
        """Register built-in CLI commands; keeps CLI extensible."""
        self.registry.register(
            "/init",
            self._cmd_init,
            "Create .dogent scaffolding (dogent.md) without overwriting existing files.",
        )
        self.registry.register(
            "/config",
            self._cmd_config,
            "Create .dogent/dogent.json (llm_profile and web_profile) and reload settings.",
        )
        self.registry.register(
            "/history",
            self._cmd_history,
            "Show recent history entries and the latest todo snapshot.",
        )
        self.registry.register(
            "/clear",
            self._cmd_clear,
            "Clear history and memory files for a fresh start.",
        )
        self.registry.register(
            "/help",
            self._cmd_help,
            "Show Dogent usage, models, API, and available commands.",
        )
        self.registry.register(
            "/exit",
            self._cmd_exit,
            "Exit Dogent CLI gracefully.",
        )

    def _print_banner(self, settings) -> None:
        art = r"""
 ██████╗  ██████╗  ██████╗ ███████╗███╗   ██╗████████╗
 ██╔══██╗██╔═══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
 ██║  ██║██║   ██║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
 ██║  ██║██║   ██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
 ██████╔╝╚██████╔╝╚██████╔╝███████╗██║ ╚████║   ██║   
 ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
"""
        model = settings.model or "<not set>"
        fast_model = settings.small_model or "<not set>"
        base_url = settings.base_url or "<not set>"
        web_label = settings.web_profile or "default (native)"
        commands = ", ".join(self.registry.names()) or "No commands registered"
        helper_lines = [
            f"Model: {model}",
            f"Fast Model: {fast_model}",
            f"API: {base_url}",
            f"LLM Profile: {settings.profile or '<not set>'}",
            f"Web Profile: {web_label}",
            f"Commands: {commands}",
            "Esc interrupts current task • Alt/Option+Enter inserts a newline • Ctrl+C exits cleanly",
        ]
        body = Align.center(art.strip("\n"))
        helper = Align.center("\n".join(helper_lines))
        content = Group(body, helper)
        self.console.print(
            Panel(
                Align.center(content),
                title="Dogent",
                subtitle=None,
                expand=True,
                padding=(1, 2),
            )
        )

    async def _cmd_init(self, _: str) -> bool:
        created = self.config_manager.create_init_files()
        if created:
            rel_paths = "\n".join(str(path.relative_to(self.root)) for path in created)
            message = f"Created:\n{rel_paths}"
            style = "green"
        else:
            message = "No files created (templates already exist)."
            style = "yellow"
        self.console.print(
            Panel(message, title="Init", border_style=style)
        )
        return True

    async def _cmd_config(self, _: str) -> bool:
        self.config_manager.create_config_template()
        await self.agent.reset()
        settings = self.config_manager.load_settings()
        body = (
            f"Wrote .dogent/dogent.json with llm_profile reference.\n"
            f"LLM Profile: {settings.profile or '<not set>'}"
        )
        self.console.print(
            Panel(body, title="Config", border_style="green")
        )
        return True

    async def _cmd_history(self, _: str) -> bool:
        entries = self.history_manager.read_entries()
        if not entries:
            self.console.print(
                Panel(
                    "No history yet. Run a task to populate history.",
                    title="📜 History",
                    border_style="yellow",
                )
            )
            return True

        table = Table(
            show_header=True,
            expand=True,
            box=box.MINIMAL_DOUBLE_HEAD,
            header_style="bold",
        )
        table.add_column("When", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta", no_wrap=True)
        table.add_column("Summary", style="white")
        table.add_column("Metrics", style="dim")

        for entry in reversed(entries[-5:]):
            timestamp = self._format_timestamp(entry.get("timestamp"))
            status = entry.get("status") or "-"
            summary = self._shorten(entry.get("summary") or "-")
            metrics = self._format_metrics(entry)
            table.add_row(
                timestamp,
                f"{self._status_icon(status)} {status}",
                summary,
                metrics,
            )

        todo_panel = self.todo_manager.render_snapshot_panel(
            self.history_manager.latest_todos(), title="✅ Todo Snapshot"
        )
        self.console.print(Panel(table, title="📜 History", border_style="cyan"))
        self.console.print(todo_panel)
        return True

    async def _cmd_clear(self, _: str) -> bool:
        cleared: list[str] = []
        self.history_manager.clear()
        cleared.append(str(self.paths.history_file.relative_to(self.root)))
        if self.paths.memory_file.exists():
            with suppress(Exception):
                self.paths.memory_file.unlink()
            if not self.paths.memory_file.exists():
                cleared.append(str(self.paths.memory_file.relative_to(self.root)))
        self.todo_manager.set_items([])
        if cleared:
            body = "Cleared:\n" + "\n".join(cleared)
            style = "green"
        else:
            body = "No history or memory files found to clear."
            style = "yellow"
        self.console.print(Panel(body, title="🧹 Clear", border_style=style))
        return True

    async def _cmd_exit(self, _: str) -> bool:
        await self._graceful_exit()
        return False

    async def _cmd_help(self, _: str) -> bool:
        settings = self.config_manager.load_settings()
        commands = "\n".join(self.registry.descriptions()) or "No commands registered"
        body = "\n".join(
            [
                f"Model: {settings.model or '<not set>'}",
                f"Fast Model: {settings.small_model or '<not set>'}",
                f"API: {settings.base_url or '<not set>'}",
                f"LLM Profile: {settings.profile or '<not set>'}",
                f"Web Profile: {settings.web_profile or 'default (native)'}",
                "",
                "Commands:",
                commands,
                "",
                "Shortcuts:",
                "- Esc: interrupt current task",
                "- Alt/Option+Enter: insert newline",
                "- Ctrl+C: exit gracefully",
            ]
        )
        self.console.print(Panel(body, title="💡 Help", border_style="cyan"))
        return True

    async def run(self) -> None:
        settings = self.config_manager.load_settings()
        self._print_banner(settings)
        while True:
            try:
                raw = await self._read_input()
            except (EOFError, KeyboardInterrupt):
                await self._graceful_exit()
                break
            if not raw:
                continue
            text = raw.strip()
            if text.startswith("/"):
                should_continue = await self._handle_command(text)
                if not should_continue:
                    break
                continue
            message, attachments = self._resolve_attachments(text)
            if attachments:
                self._show_attachments(attachments)
            try:
                await self._run_with_interrupt(message, attachments)
            except KeyboardInterrupt:
                await self._graceful_exit()
                break

    async def _run_with_interrupt(self, message: str, attachments: list[FileAttachment]) -> None:
        """Run a task while listening for Esc without stealing future input."""
        stop_event = threading.Event()
        agent_task = asyncio.create_task(self.agent.send_message(message, attachments))
        esc_task = asyncio.create_task(self._wait_for_escape(stop_event))
        try:
            done, _ = await asyncio.wait(
                {agent_task, esc_task}, return_when=asyncio.FIRST_COMPLETED
            )
        except KeyboardInterrupt:
            await self._interrupt_running_task(
                reason="Ctrl+C detected, interrupting the current task...",
                agent_task=agent_task,
                esc_task=esc_task,
                stop_event=stop_event,
            )
            return

        if esc_task in done and esc_task.result():
            await self._interrupt_running_task(
                reason="Esc detected, interrupting the current task...",
                agent_task=agent_task,
                esc_task=esc_task,
                stop_event=stop_event,
            )
        else:
            stop_event.set()
            esc_task.cancel()
            with suppress(asyncio.CancelledError):
                await esc_task
        if agent_task.done() and not agent_task.cancelled():
            with suppress(Exception):
                await agent_task

    async def _wait_for_escape(self, stop_event: threading.Event) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._read_escape_key(stop_event))

    def _read_escape_key(self, stop_event: threading.Event) -> bool:
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            return False
        try:
            while not stop_event.is_set():
                rlist, _, _ = select.select([fd], [], [], 0.2)
                if not rlist:
                    continue
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    return True
        except Exception:
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return False

    async def _interrupt_running_task(
        self,
        reason: str,
        agent_task: asyncio.Task,
        esc_task: asyncio.Task,
        stop_event: threading.Event,
    ) -> None:
        stop_event.set()
        self.console.print(f"[yellow]{reason}[/yellow]")
        await self.agent.interrupt(reason)
        if not agent_task.done():
            agent_task.cancel()
            with suppress(asyncio.CancelledError):
                await agent_task
        if not esc_task.done():
            esc_task.cancel()
            with suppress(asyncio.CancelledError):
                await esc_task

    async def _handle_command(self, command: str) -> bool:
        cmd = self.registry.get(command)
        if not cmd:
            available = "\n".join(self.registry.descriptions())
            self.console.print(
                Panel(
                    f"Unknown command: {command}\nAvailable commands:\n{available}",
                    title="Unknown Command",
                    border_style="red",
                )
            )
            return True
        return await cmd.handler(command)

    async def _read_input(self) -> str:
        loop = asyncio.get_event_loop()
        if self.session:
            prompt_callable = getattr(self.session, "prompt_async", None)
            if callable(prompt_callable):
                return await prompt_callable("dogent> ")
            return await loop.run_in_executor(None, lambda: self.session.prompt("dogent> "))
        return await loop.run_in_executor(
            None, lambda: Prompt.ask("[bold cyan]dogent>[/bold cyan]")
        )

    def _resolve_attachments(self, message: str) -> Tuple[str, list[FileAttachment]]:
        return self.file_resolver.extract(message)

    async def _graceful_exit(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        with suppress(Exception):
            await self.agent.reset()
        self.console.print(Panel("Exiting Dogent. See you soon!", title="Goodbye", border_style="cyan"))

    def _show_attachments(self, attachments: Iterable[FileAttachment]) -> None:
        for attachment in attachments:
            self.console.print(
                Panel(
                    f"File loaded @file {attachment.path} {'(truncated)' if attachment.truncated else ''}",
                    title="📂 File Reference",
                )
            )

    def _render_todos(self, show_empty: bool = False) -> None:
        panel = self.todo_manager.render_panel(show_empty=show_empty)
        if panel:
            self.console.print(panel)

    def _format_timestamp(self, ts: Any) -> str:
        if not ts:
            return "-"
        try:
            dt = datetime.fromisoformat(str(ts))
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(ts)

    def _format_metrics(self, entry: dict[str, Any]) -> str:
        duration = entry.get("duration_ms")
        api = entry.get("duration_api_ms")
        cost = entry.get("cost_usd")
        parts: list[str] = []
        if duration is not None:
            parts.append(f"Duration {duration} ms")
        if api is not None:
            parts.append(f"API {api} ms")
        if cost is not None:
            parts.append(f"Cost ${cost:.4f}")
        return " · ".join(parts) if parts else "-"

    def _status_icon(self, status: str) -> str:
        normalized = (status or "").lower()
        mapping = {
            "started": "⏳",
            "running": "🔄",
            "interrupted": "⛔",
            "completed": "✅",
            "error": "❌",
        }
        return mapping.get(normalized, "•")

    def _shorten(self, text: Any, limit: int = 120) -> str:
        raw = str(text).replace("\n", " ").strip()
        return raw if len(raw) <= limit else f"{raw[:limit]} …"


def main() -> None:
    parser = argparse.ArgumentParser(description="Dogent CLI - interactive document-writing agent")
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")
    args, _ = parser.parse_known_args()
    if args.version:
        from dogent import __version__

        print(f"dogent {__version__}")
        return
    asyncio.run(DogentCLI().run())


if __name__ == "__main__":
    main()
