from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, Optional

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
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
)

from .config import ConfigManager
from .file_refs import FileAttachment
from .prompts import PromptBuilder
from .history import HistoryManager
from .todo import TodoManager
from .wait_indicator import LLMWaitIndicator
from .document_tools import DOGENT_DOC_TOOL_DISPLAY_NAMES
from .vision_tools import DOGENT_VISION_TOOL_DISPLAY_NAMES
from .web_tools import DOGENT_WEB_TOOL_DISPLAY_NAMES
from .tool_permissions import should_confirm_tool_use

DOGENT_TOOL_DISPLAY_NAMES = {
    **DOGENT_WEB_TOOL_DISPLAY_NAMES,
    **DOGENT_DOC_TOOL_DISPLAY_NAMES,
    **DOGENT_VISION_TOOL_DISPLAY_NAMES,
}

NEEDS_CLARIFICATION_SENTINEL = "[[DOGENT_STATUS:NEEDS_CLARIFICATION]]"


@dataclass(frozen=True)
class RunOutcome:
    status: str  # completed|error|interrupted|needs_clarification|aborted
    summary: str
    todos_snapshot: list[dict[str, object]]
    remaining_todos_markdown: str


class AgentRunner:
    """Maintains a Claude Agent SDK session and streams responses to the CLI."""

    def __init__(
        self,
        config: ConfigManager,
        prompt_builder: PromptBuilder,
        todo_manager: TodoManager,
        history: HistoryManager,
        console: Optional[Console] = None,
        *,
        permission_prompt: Optional[Callable[[str, str], Awaitable[bool]]] = None,
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
        self._clarification_text: str = ""
        self._needs_clarification = False
        self._interrupted: bool = False
        self.last_outcome: RunOutcome | None = None
        self._wait_indicator: LLMWaitIndicator | None = None
        self._permission_prompt = permission_prompt
        self._aborted_reason: str | None = None
        self._abort_requested = False

    async def reset(self) -> None:
        """Close current session so it can be re-created with new settings."""
        async with self._lock:
            if self._client:
                await self._client.disconnect()
            self._client = None
            self._tool_name_by_id = {}

    async def refresh_system_prompt(self) -> None:
        """Rebuild the system prompt and update any active client."""
        settings = self.config.load_settings()
        project_config = self.config.load_project_config()
        system_prompt = self.prompt_builder.build_system_prompt(
            settings=settings, config=project_config
        )
        async with self._lock:
            if self._client:
                self._client.options.system_prompt = system_prompt

    async def send_message(
        self,
        user_message: str,
        attachments: Iterable[FileAttachment],
    ) -> None:
        settings = self.config.load_settings()
        project_config = self.config.load_project_config()
        system_prompt = self.prompt_builder.build_system_prompt(
            settings=settings, config=project_config
        )
        user_prompt = self.prompt_builder.build_user_prompt(
            user_message,
            list(attachments),
            settings=settings,
            config=project_config,
        )
        self._last_summary = None
        self._clarification_text = ""
        self._needs_clarification = False
        self._interrupted = False
        self.last_outcome = None
        self._aborted_reason = None
        self._abort_requested = False
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
            await self._start_wait_indicator()
            async with self._lock:
                if self._client is None:
                    hooks = None
                    if self._permission_prompt is not None:
                        hooks = {
                            "PreToolUse": [
                                HookMatcher(matcher=None, hooks=[self._pre_tool_use_hook])
                            ]
                        }
                    options = self.config.build_options(system_prompt, hooks=hooks)
                    self._client = ClaudeSDKClient(options=options)
                    await self._client.connect()
                else:
                    self._client.options.system_prompt = system_prompt

                await self._client.query(user_prompt)

            await self._stream_responses()
            await self._safe_disconnect()
        except Exception as exc:  # noqa: BLE001
            await self._stop_wait_indicator()
            if self._aborted_reason:
                self._finalize_aborted()
            else:
                todos_snapshot = self.todo_manager.export_items()
                remaining = self.todo_manager.remaining_markdown()
                self.last_outcome = RunOutcome(
                    status="error",
                    summary=str(exc),
                    todos_snapshot=todos_snapshot,
                    remaining_todos_markdown=remaining,
                )
                body_lines = [
                    f"Reason: {exc}",
                    "",
                    "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                    remaining,
                ]
                self.console.print(
                    Panel(
                        Text("\n".join(line for line in body_lines if line).strip()),
                        title="❌ Failed",
                        border_style="red",
                    )
                )
                self.history.append(
                    summary=f"Session error: {exc}",
                    status="error",
                    prompt=None,
                    todos=todos_snapshot,  # type: ignore[arg-type]
                )
            await self._safe_disconnect()
        finally:
            await self._stop_wait_indicator()

    async def _stream_responses(self) -> None:
        if not self._client:
            return
        saw_result = False
        await self._start_wait_indicator()
        async for message in self._client.receive_response():
            if self._interrupted:
                break
            await self._stop_wait_indicator()
            if isinstance(message, AssistantMessage):
                if not self._abort_requested:
                    self._handle_assistant_message(message)
            elif isinstance(message, ResultMessage):
                if not self._interrupted:
                    self._handle_result(message)
                saw_result = True
                break
            if not self._interrupted:
                await self._start_wait_indicator()
        if not saw_result and self._aborted_reason and not self._interrupted:
            self._finalize_aborted()

    async def interrupt(self, reason: str) -> None:
        async with self._lock:
            self._interrupted = True
            await self._safe_disconnect(interrupted=True)
            todos_snapshot = self.todo_manager.export_items()
            remaining = self.todo_manager.remaining_markdown()
            self.last_outcome = RunOutcome(
                status="interrupted",
                summary=reason,
                todos_snapshot=todos_snapshot,
                remaining_todos_markdown=remaining,
            )
            body_lines = [
                reason,
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
            ]
            self.console.print(
                Panel(
                    Text("\n".join(line for line in body_lines if line).strip()),
                    title="⛔ Interrupted",
                    border_style="yellow",
                )
            )
            self.history.append(
                summary=reason,
                status="interrupted",
                prompt=None,
                todos=todos_snapshot,  # type: ignore[arg-type]
            )

    def _finalize_aborted(self) -> None:
        reason = self._aborted_reason or "Aborted."
        todos_snapshot = self.todo_manager.export_items()
        remaining = self.todo_manager.remaining_markdown()
        self.last_outcome = RunOutcome(
            status="aborted",
            summary=reason,
            todos_snapshot=todos_snapshot,
            remaining_todos_markdown=remaining,
        )
        body_lines = [
            reason,
            "",
            "Remaining Todos:" if remaining else "Remaining Todos: (none)",
            remaining,
        ]
        self.console.print(
            Panel(
                Text("\n".join(line for line in body_lines if line).strip()),
                title="🛑 Aborted",
                border_style="yellow",
            )
        )
        self.history.append(
            summary=reason,
            status="aborted",
            prompt=None,
            todos=todos_snapshot,  # type: ignore[arg-type]
        )

    def _handle_assistant_message(self, message: AssistantMessage) -> None:
        reply_parts: list[str] = []
        clarification_found = False
        for block in message.content:
            if isinstance(block, TextBlock):
                cleaned, found = self._strip_clarification_sentinel(block.text)
                clarification_found = clarification_found or found
                if cleaned:
                    reply_parts.append(cleaned)
                    self.console.print(Panel(cleaned, title="💬 Reply"))
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
        if clarification_found:
            self._needs_clarification = True
            if reply_parts:
                self._clarification_text = "\n\n".join(reply_parts)

    def _handle_result(self, message: ResultMessage) -> None:
        cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd is not None else "n/a"
        metrics = (
            f"Duration {message.duration_ms} ms | API {message.duration_api_ms} ms | Cost {cost}"
        )
        todos_snapshot = self.todo_manager.export_items()
        remaining = self.todo_manager.remaining_markdown()
        is_error = bool(getattr(message, "is_error", False))

        result_text = message.result or ""
        self._last_summary = result_text or None

        if self._aborted_reason:
            title = "🛑 Aborted"
            status = "aborted"
            body_lines = [
                self._aborted_reason,
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = self._aborted_reason
        elif is_error:
            title = "❌ Failed"
            status = "error"
            body_lines = [
                "Result/Reason:",
                result_text or "(no result returned)",
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = result_text or "Task failed"
        elif self._needs_clarification:
            title = "❓ Needs clarification"
            status = "needs_clarification"
            summary = self._clarification_text or result_text or "Clarification required."
            body_lines = [
                summary,
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = summary
        elif remaining:
            title = "❌ Failed"
            status = "error"
            body_lines = [
                "Result/Reason:",
                result_text or "(no result returned)",
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = result_text or "Task failed"
        else:
            title = "✅ Completed"
            status = "completed"
            body_lines = [
                result_text,
                "",
                metrics,
            ]
            history_summary = result_text or "Task completed"

        panel_text = "\n".join(line for line in body_lines if line).strip()
        if status == "error":
            border_style = "red"
        elif status == "needs_clarification":
            border_style = "yellow"
        elif status == "completed":
            border_style = "green"
        else:
            border_style = None
        self.console.print(Panel(Text(panel_text), title=title, border_style=border_style))

        self.last_outcome = RunOutcome(
            status=status,
            summary=history_summary,
            todos_snapshot=todos_snapshot,
            remaining_todos_markdown=remaining,
        )
        self.history.append(
            summary=history_summary,
            status=status,
            duration_ms=message.duration_ms,
            api_ms=message.duration_api_ms,
            cost_usd=message.total_cost_usd,
            prompt=None,
            todos=todos_snapshot,  # type: ignore[arg-type]
        )
        if status == "completed":
            self.todo_manager.set_items([])

    def _display_tool_name(self, name: str) -> str:
        return DOGENT_TOOL_DISPLAY_NAMES.get(name, name)

    def _log_tool_use(self, block: ToolUseBlock, summary: str | None = None) -> None:
        title = f"⚙️  {self._display_tool_name(block.name)}"
        body = summary or self._shorten(block.input)
        self.console.print(Panel(Text(str(body)), title=title, border_style="cyan"))

    def _log_tool_result(
        self, name: str, block: ToolResultBlock, summary: str | None = None
    ) -> None:
        is_error = bool(getattr(block, "is_error", False))
        icon = "❌" if is_error else "📥"
        status = "Failed" if is_error else "Success"
        display_name = self._display_tool_name(name)
        title = f"{icon} {status} {display_name}"
        detail = summary or self._format_tool_result_content(block.content)
        if not detail:
            detail = "No details returned." if is_error else "No content returned."
        body = f"{status}: {detail}"
        self.console.print(
            Panel(Text(str(body)), title=title, border_style="red" if is_error else "green")
        )

    def _format_tool_result_content(self, content: object) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return self._shorten(content)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(str(item["text"]))
                        continue
                    if item.get("message"):
                        parts.append(str(item["message"]))
                        continue
                    if item.get("error"):
                        parts.append(str(item["error"]))
                        continue
                    if item.get("text"):
                        parts.append(str(item["text"]))
                        continue
                elif item is None:
                    continue
                else:
                    parts.append(str(item))
            text = "\n".join(part for part in parts if part)
            return self._shorten(text) if text else ""
        return self._shorten(str(content))

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

    async def _start_wait_indicator(self) -> None:
        if self._wait_indicator is not None:
            return
        self._wait_indicator = LLMWaitIndicator(self.console)
        await self._wait_indicator.start()

    async def _stop_wait_indicator(self) -> None:
        if self._wait_indicator is None:
            return
        await self._wait_indicator.stop()
        self._wait_indicator = None

    def _strip_clarification_sentinel(self, text: str) -> tuple[str, bool]:
        if NEEDS_CLARIFICATION_SENTINEL not in text:
            return text, False
        lines: list[str] = []
        found = False
        for line in text.splitlines():
            if NEEDS_CLARIFICATION_SENTINEL in line:
                found = True
                cleaned = line.replace(NEEDS_CLARIFICATION_SENTINEL, "").strip()
                if cleaned:
                    lines.append(cleaned)
            else:
                lines.append(line)
        return "\n".join(lines).strip(), found

    async def _pre_tool_use_hook(
        self,
        input_data: HookInput,
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookJSONOutput:
        if not self.config:
            return {}
        tool_name = input_data.get("tool_name")
        tool_input = input_data.get("tool_input")
        if not tool_name or not isinstance(tool_input, dict):
            return {}
        if self._abort_requested and self._aborted_reason:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": self._aborted_reason,
                }
            }
        allowed_roots = [
            self.config.paths.root.resolve(),
            self.config.paths.global_dir.resolve(),
        ]
        needs_confirm, reason = should_confirm_tool_use(
            tool_name, tool_input, cwd=self.config.paths.root, allowed_roots=allowed_roots
        )
        if not needs_confirm:
            return {}
        if await self._request_permission(tool_name, reason):
            return {}
        self._aborted_reason = f"User denied permission: {reason}"
        self._abort_requested = True
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": self._aborted_reason,
            }
        }

    async def _request_permission(self, tool_name: str, reason: str) -> bool:
        if not self._permission_prompt:
            return False
        was_running = self._wait_indicator is not None
        if was_running:
            await self._stop_wait_indicator()
        try:
            title = f"Permission required: {tool_name}"
            body = reason
            return await self._permission_prompt(title, body)
        finally:
            if was_running:
                await self._start_wait_indicator()
