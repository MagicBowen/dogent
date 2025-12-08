from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Dict, Iterable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from .config import ConfigManager
from .file_refs import FileAttachment
from .prompts import PromptBuilder
from .history import HistoryManager
from .todo import TodoManager


class AgentRunner:
    """Maintains a Claude Agent SDK session and streams responses to the CLI."""

    def __init__(
        self,
        config: ConfigManager,
        prompt_builder: PromptBuilder,
        todo_manager: TodoManager,
        history: HistoryManager,
        console: Optional[Console] = None,
    ) -> None:
        self.config = config
        self.prompt_builder = prompt_builder
        self.todo_manager = todo_manager
        self.history = history
        self.console = console or Console()
        self._client: Optional[ClaudeSDKClient] = None
        self._tool_name_by_id: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._skip_todo_render_once = False
        self._last_summary: str | None = None
        self._interrupted: bool = False

    async def reset(self) -> None:
        """Close current session so it can be re-created with new settings."""
        async with self._lock:
            if self._client:
                await self._client.disconnect()
            self._client = None
            self._tool_name_by_id = {}

    async def send_message(self, user_message: str, attachments: Iterable[FileAttachment]) -> None:
        settings = self.config.load_settings()
        system_prompt = self.prompt_builder.build_system_prompt(settings=settings)
        user_prompt = self.prompt_builder.build_user_prompt(user_message, list(attachments))
        self._last_summary = None
        self._interrupted = False
        preview = self._shorten(user_message, limit=240)
        self.console.print(
            Panel(
                f"Received request:\n{preview}",
                title="⏳ Running",
                border_style="cyan",
            )
        )
        self.history.append(
            summary="User request",
            status="started",
            prompt=user_message,
            todos=self.todo_manager.export_items(),
        )

        try:
            async with self._lock:
                if self._client is None:
                    options = self.config.build_options(system_prompt)
                    self._client = ClaudeSDKClient(options=options)
                    await self._client.connect()
                else:
                    self._client.options.system_prompt = system_prompt

                await self._client.query(user_prompt)

            await self._stream_responses()
            await self._safe_disconnect()
        except Exception as exc:  # noqa: BLE001
            self.console.print(
                Panel(
                    f"[red]Session error: {exc}[/red]\nCheck credentials/network or update the profile with /config.",
                    title="Error",
                )
            )
            await self._safe_disconnect()

    async def _stream_responses(self) -> None:
        if not self._client:
            return
        try:
            async for message in self._client.receive_response():
                if self._interrupted:
                    break
                if isinstance(message, AssistantMessage):
                    self._handle_assistant_message(message)
                elif isinstance(message, ResultMessage):
                    if not self._interrupted:
                        self._handle_result(message)
                    break
        except Exception as exc:  # noqa: BLE001
            self.console.print(
                Panel(
                    f"[red]Streaming error: {exc}[/red]\nVerify credentials, network, or retry.",
                    title="Error",
                )
            )

    async def interrupt(self, reason: str) -> None:
        async with self._lock:
            self._interrupted = True
            await self._safe_disconnect(interrupted=True)
            self.history.append(
                summary=reason,
                status="interrupted",
                prompt=None,
                todos=self.todo_manager.export_items(),
            )

    def _handle_assistant_message(self, message: AssistantMessage) -> None:
        for block in message.content:
            if isinstance(block, TextBlock):
                self.console.print(Panel(block.text, title="💬 Reply"))
                self.console.print()
            elif isinstance(block, ThinkingBlock):
                thinking_text = getattr(block, "thinking", "") or ""
                self.console.print(Panel(thinking_text, title="🤔 Thinking"))
                self.console.print()
            elif isinstance(block, ToolUseBlock):
                self._tool_name_by_id[block.id] = block.name
                if block.name == "TodoWrite":
                    summary = self._summarize_todos(block.input)
                    self._log_tool_use(block, summary=summary)
                    self._skip_todo_render_once = True
                else:
                    self._log_tool_use(block)
                self.console.print()
                if block.name == "TodoWrite":
                    if self.todo_manager.update_from_payload(
                        block.input, source="TodoWrite (input)"
                    ):
                        self._render_todos()
            elif isinstance(block, ToolResultBlock):
                tool_name = self._tool_name_by_id.get(block.tool_use_id, "tool")
                if tool_name == "TodoWrite":
                    summary = self._summarize_todos(block.content)
                    if self.todo_manager.update_from_payload(
                        block.content, source="TodoWrite (result)"
                    ):
                        self._render_todos()
                    self._log_tool_result(tool_name, block, summary=summary)
                else:
                    self._log_tool_result(tool_name, block)
                self.console.print()
        self._render_todos(show_empty=False)

    def _handle_result(self, message: ResultMessage) -> None:
        cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd is not None else "n/a"
        metrics = (
            f"Duration {message.duration_ms} ms | API {message.duration_api_ms} ms | Cost {cost}"
        )
        content_parts = []
        if message.result:
            content_parts.append(message.result)
            self._last_summary = message.result
        content_parts.append(metrics)
        panel_text = "\n\n".join(content_parts)
        self.console.print(Panel(Text(panel_text), title="📝 Session Summary"))
        self.history.append(
            summary=message.result or "Task completed",
            status="completed",
            duration_ms=message.duration_ms,
            api_ms=message.duration_api_ms,
            cost_usd=message.total_cost_usd,
            prompt=None,
            todos=self.todo_manager.export_items(),
        )

    def _log_tool_use(self, block: ToolUseBlock, summary: str | None = None) -> None:
        title = f"⚙️  {block.name}"
        body = summary or self._shorten(block.input)
        self.console.print(Panel(Text(str(body)), title=title, border_style="cyan"))

    def _log_tool_result(
        self, name: str, block: ToolResultBlock, summary: str | None = None
    ) -> None:
        is_error = bool(getattr(block, "is_error", False))
        icon = "❌" if is_error else "📥"
        status = "Failed" if is_error else "Result"
        title = f"{icon} {status} {name}"
        body = summary or self._shorten(block.content)
        if not body:
            body = "No content returned."
        if is_error:
            body = f"Reason: {body}"
        self.console.print(
            Panel(Text(str(body)), title=title, border_style="red" if is_error else "green")
        )

    def _render_todos(self, show_empty: bool = True) -> None:
        if self._skip_todo_render_once:
            self._skip_todo_render_once = False
            return
        panel = self.todo_manager.render_panel(show_empty=show_empty)
        if panel:
            self.console.print(panel)
            self.console.print()

    def _shorten(self, obj: object, limit: int = 400) -> str:
        text = str(obj)
        return text if len(text) <= limit else text[: limit] + " …"

    def _summarize_todos(self, payload: object) -> str:
        items = self.todo_manager._normalize_items(payload)  # type: ignore[attr-defined]
        if not items:
            return "Todo update"
        status_counts: dict[str, int] = {}
        for item in items:
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
        counts = ", ".join(f"{k}:{v}" for k, v in status_counts.items())
        return f"Todo update ({len(items)} items; {counts})"

    async def _safe_disconnect(self, interrupted: bool = False) -> None:
        if not self._client:
            return
        with suppress(Exception):
            if interrupted:
                await self._client.interrupt()
        with suppress(Exception):
            await self._client.disconnect()
        self._client = None
