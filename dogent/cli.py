from __future__ import annotations

import asyncio
import argparse
import sys
import tty
import termios
from contextlib import suppress
from pathlib import Path
from typing import Iterable, Tuple, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .agent import AgentRunner
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
        self.available_commands = ["/init", "/config", "/exit"]
        self.paths = DogentPaths(self.root)
        self.todo_manager = TodoManager(console=self.console)
        self.config_manager = ConfigManager(self.paths, console=self.console)
        self.file_resolver = FileReferenceResolver(self.root)
        self.history_manager = HistoryManager(self.paths)
        self.prompt_builder = PromptBuilder(self.paths, self.todo_manager, self.history_manager)
        self.agent = AgentRunner(
            config=self.config_manager,
            prompt_builder=self.prompt_builder,
            todo_manager=self.todo_manager,
            history=self.history_manager,
            console=self.console,
        )
        self.session: PromptSession | None = None
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

            self.session = PromptSession(
                completer=DogentCompleter(self.root, self.available_commands),
                complete_while_typing=True,
                key_bindings=bindings,
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
        model = settings.model or "<未设置>"
        fast_model = settings.small_model or "<未设置>"
        base_url = settings.base_url or "<未设置>"
        body = f"{art}\n模型: {model} | 快速模型: {fast_model} | API: {base_url}\n使用 /init, /config, /exit。按 Esc 可中断当前任务。"
        self.console.print(
            Panel(body, title="Dogent", subtitle=None, expand=True, padding=(1, 2))
        )

    async def run(self) -> None:
        settings = self.config_manager.load_settings()
        self._print_banner(settings)
        while True:
            try:
                raw = await self._read_input()
            except (EOFError, KeyboardInterrupt):
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
            await self._run_with_interrupt(message, attachments)

    async def _run_with_interrupt(self, message: str, attachments: list[FileAttachment]) -> None:
        agent_task = asyncio.create_task(self.agent.send_message(message, attachments))
        esc_task = asyncio.create_task(self._wait_for_escape())
        done, pending = await asyncio.wait(
            {agent_task, esc_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if esc_task in done and esc_task.result():
            self.console.print("[yellow]检测到 Esc，正在中断当前任务…[/yellow]")
            await self.agent.interrupt("用户按下 Esc 中断")
            if not agent_task.done():
                agent_task.cancel()
                with suppress(asyncio.CancelledError):
                    await agent_task
        else:
            esc_task.cancel()
        if agent_task.done() and not agent_task.cancelled():
            with suppress(Exception):
                await agent_task

    async def _wait_for_escape(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_escape_key)

    def _read_escape_key(self) -> bool:
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            return False
        try:
            while True:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    return True
        except Exception:
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    async def _handle_command(self, command: str) -> bool:
        if command == "/exit":
            self.console.print("退出 Dogent。")
            return False
        if command == "/init":
            created = self.config_manager.create_init_files()
            if created:
                files = "\n".join([str(p) for p in created])
                self.console.print(Panel(f"已创建模板：\n{files}"))
            else:
                self.console.print(Panel("未创建新文件，模板已存在。"))
            return True
        if command == "/config":
            self.config_manager.create_config_template()
            await self.agent.reset()
            self.console.print(
                Panel(
                    f"已生成 {self.paths.config_file}，如需修改凭据或模型请编辑后重试。",
                    title="配置",
                )
            )
            return True
        self.console.print("未知命令，支持 /init, /config, /exit")
        return True

    async def _read_input(self) -> str:
        loop = asyncio.get_event_loop()
        if self.session:
            return await loop.run_in_executor(
                None, lambda: self.session.prompt("dogent> ")
            )
        return await loop.run_in_executor(
            None, lambda: Prompt.ask("[bold cyan]dogent>[/bold cyan]")
        )

    def _resolve_attachments(self, message: str) -> Tuple[str, list[FileAttachment]]:
        return self.file_resolver.extract(message)

    def _show_attachments(self, attachments: Iterable[FileAttachment]) -> None:
        for attachment in attachments:
            self.console.print(
                Panel(
                    f"已加载 @file {attachment.path} {'(截断)' if attachment.truncated else ''}",
                    title="📂 File Reference",
                )
            )

    def _render_todos(self, show_empty: bool = False) -> None:
        panel = self.todo_manager.render_panel(show_empty=show_empty)
        if panel:
            self.console.print(panel)


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
