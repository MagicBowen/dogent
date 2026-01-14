from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

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
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

from ..config import ConfigManager
from ..core.file_refs import FileAttachment
from ..prompts import PromptBuilder
from ..core.history import HistoryManager
from ..core.todo import TodoManager
from .wait import LLMWaitIndicator
from ..features.document_tools import DOGENT_DOC_TOOL_DISPLAY_NAMES
from ..features.vision_tools import DOGENT_VISION_TOOL_DISPLAY_NAMES
from ..features.web_tools import DOGENT_WEB_TOOL_DISPLAY_NAMES
from .permissions import evaluate_tool_permission
from ..features.clarification import (
    ClarificationPayload,
    CLARIFICATION_JSON_TAG,
    extract_clarification_payload,
    has_clarification_tag,
)
from ..outline_edit import (
    OutlineEditPayload,
    OUTLINE_EDIT_JSON_TAG,
    extract_outline_edit_payload,
    has_outline_edit_tag,
)
from ..core.session_log import SessionLogger

DOGENT_TOOL_DISPLAY_NAMES = {
    **DOGENT_WEB_TOOL_DISPLAY_NAMES,
    **DOGENT_DOC_TOOL_DISPLAY_NAMES,
    **DOGENT_VISION_TOOL_DISPLAY_NAMES,
}

NEEDS_CLARIFICATION_SENTINEL = "[[DOGENT_STATUS:NEEDS_CLARIFICATION]]"


@dataclass(frozen=True)
class RunOutcome:
    status: str  # completed|error|interrupted|needs_clarification|needs_outline_edit|awaiting_input|aborted
    summary: str
    todos_snapshot: list[dict[str, object]]
    remaining_todos_markdown: str


@dataclass(frozen=True)
class PermissionDecision:
    allow: bool
    remember: bool = False
    message: str | None = None


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
        permission_prompt: Optional[
            Callable[[str, str], Awaitable[bool | PermissionDecision]]
        ] = None,
        session_logger: SessionLogger | None = None,
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
        self._clarification_seen = False
        self._outline_edit_text: str = ""
        self._needs_outline_edit = False
        self._outline_edit_seen = False
        self._interrupted: bool = False
        self.last_outcome: RunOutcome | None = None
        self._wait_indicator: LLMWaitIndicator | None = None
        self._permission_prompt = permission_prompt
        self._session_logger = session_logger
        self._aborted_reason: str | None = None
        self._abort_requested = False
        self._abort_finalized = False
        self._abort_interrupt_sent = False
        self._permission_prompt_active = False
        self._clarification_payload: ClarificationPayload | None = None
        self._outline_edit_payload: OutlineEditPayload | None = None

    async def reset(self) -> None:
        """Close current session so it can be re-created with new settings."""
        with suppress(Exception):
            await self._stop_wait_indicator()
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

    def set_permission_prompt(
        self,
        permission_prompt: Optional[
            Callable[[str, str], Awaitable[bool | PermissionDecision]]
        ],
    ) -> None:
        """Update the permission prompt callback for subsequent runs."""
        self._permission_prompt = permission_prompt

    def pop_clarification_payload(self) -> ClarificationPayload | None:
        payload = self._clarification_payload
        self._clarification_payload = None
        return payload

    def pop_outline_edit_payload(self) -> OutlineEditPayload | None:
        payload = self._outline_edit_payload
        self._outline_edit_payload = None
        return payload

    async def send_message(
        self,
        user_message: str,
        attachments: Iterable[FileAttachment],
        *,
        config_override: Dict[str, Any] | None = None,
    ) -> None:
        interaction_status: str | None = None
        settings = self.config.load_settings()
        project_config = self.config.load_project_config()
        prompt_config = dict(project_config)
        if config_override:
            prompt_config.update(config_override)
        system_prompt = self.prompt_builder.build_system_prompt(
            settings=settings, config=prompt_config
        )
        user_prompt = self.prompt_builder.build_user_prompt(
            user_message,
            list(attachments),
            settings=settings,
            config=prompt_config,
        )
        self._last_summary = None
        self._clarification_text = ""
        self._needs_clarification = False
        self._clarification_seen = False
        self._outline_edit_text = ""
        self._needs_outline_edit = False
        self._outline_edit_seen = False
        self._interrupted = False
        self.last_outcome = None
        self._aborted_reason = None
        self._abort_requested = False
        self._abort_finalized = False
        self._abort_interrupt_sent = False
        self._clarification_payload = None
        self._outline_edit_payload = None
        preview = (
            user_message
            if self._is_clarification_answers(user_message)
            else self._shorten(user_message, limit=240)
        )
        if self._session_logger:
            self._session_logger.start_interaction("agent", summary=preview)
            self._session_logger.log_system_prompt("agent", system_prompt)
            self._session_logger.log_user_prompt("agent", user_prompt)
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
            prompt=user_prompt,
            todos=self.todo_manager.export_items(),
        )

        try:
            await self._start_wait_indicator()
            async with self._lock:
                if self._client is None:
                    can_use_tool = None
                    if self._permission_prompt is not None:
                        can_use_tool = self._can_use_tool
                    options = self.config.build_options(system_prompt, can_use_tool=can_use_tool)
                    self._client = ClaudeSDKClient(options=options)
                    await self._client.connect()
                else:
                    self._client.options.system_prompt = system_prompt

                await self._client.query(user_prompt)

            await self._stream_responses()
            if not self._needs_clarification:
                await self._safe_disconnect()
            if self.last_outcome:
                interaction_status = self.last_outcome.status
            else:
                interaction_status = "completed"
        except Exception as exc:  # noqa: BLE001
            await self._stop_wait_indicator()
            if self._session_logger:
                self._session_logger.log_exception("agent", exc)
            interaction_status = "error"
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
            if self._session_logger:
                self._session_logger.end_interaction("agent", status=interaction_status)

    async def abort(self, reason: str) -> None:
        async with self._lock:
            self._aborted_reason = reason
            await self._safe_disconnect()
            self._finalize_aborted()

    async def _stream_responses(self) -> None:
        if not self._client:
            return
        saw_result = False
        drain_after_interrupt = False
        await self._start_wait_indicator()
        async for message in self._client.receive_response():
            if self._interrupted:
                break
            await self._stop_wait_indicator()
            if self._abort_requested and not drain_after_interrupt:
                await self._interrupt_client_on_abort()
                drain_after_interrupt = True
            if drain_after_interrupt:
                if isinstance(message, ResultMessage):
                    saw_result = True
                    break
                continue
            if isinstance(message, AssistantMessage):
                if not self._abort_requested:
                    self._handle_assistant_message(message)
                if (self._needs_clarification or self._needs_outline_edit) and self._client:
                    with suppress(Exception):
                        await self._client.interrupt()
                    drain_after_interrupt = True
                    continue
            elif isinstance(message, ResultMessage):
                if not self._interrupted:
                    self._handle_result(message)
                saw_result = True
                break
            if not self._interrupted and not drain_after_interrupt:
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
        if self._abort_finalized:
            return
        self._abort_finalized = True
        reason = self._aborted_reason or "Aborted."
        todos_snapshot = self.todo_manager.export_items()
        remaining = self.todo_manager.remaining_markdown()
        self.todo_manager.set_items([], source="aborted")
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
        text_blocks: list[str] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                if block.text:
                    if self._session_logger:
                        self._session_logger.log_assistant_text("agent", block.text)
                    text_blocks.append(block.text)
            elif isinstance(block, ThinkingBlock):
                thinking_text = getattr(block, "thinking", "") or ""
                if self._session_logger:
                    self._session_logger.log_assistant_thinking("agent", thinking_text)
                if has_clarification_tag(thinking_text):
                    self._process_clarification_text(thinking_text, show_reply=False)
                else:
                    self.console.print(Panel(thinking_text, title="🤔 Thinking"))
                    self.console.print()
            elif isinstance(block, ToolUseBlock):
                self._tool_name_by_id[block.id] = block.name
                if self._session_logger:
                    self._session_logger.log_tool_use(
                        "agent",
                        name=block.name,
                        tool_id=block.id,
                        input_data=block.input,
                    )
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
                if self._session_logger:
                    self._session_logger.log_tool_result(
                        "agent",
                        name=tool_name,
                        tool_id=block.tool_use_id,
                        content=block.content,
                        is_error=getattr(block, "is_error", None),
                    )
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
        handled = False
        full_text = ""
        if text_blocks:
            full_text = "\n\n".join(
                part.strip() for part in text_blocks if part and part.strip()
            ).strip()
            if full_text:
                handled = self._process_outline_edit_text(full_text, show_reply=True)
                if not handled:
                    handled = self._process_clarification_text(full_text, show_reply=True)
        _ = handled

    def _process_outline_edit_text(self, full_text: str, *, show_reply: bool) -> bool:
        payload, errors = extract_outline_edit_payload(full_text)
        if payload:
            self._outline_edit_payload = payload
            self._needs_outline_edit = True
            self._outline_edit_seen = True
            note = payload.title or "Outline edit required."
            self._outline_edit_text = note
            self.console.print(Panel(note, title="📝 Outline Edit"))
            self.console.print()
            return True
        tag_present = has_outline_edit_tag(full_text)
        if not tag_present:
            return False
        invalid_payload = tag_present and bool(errors)
        if invalid_payload:
            warning = "Outline edit payload invalid. Falling back to plain text."
            body = f"{warning}\n\n{full_text}"
            self.console.print(Panel(body, title="Outline Edit", border_style="yellow"))
            self.console.print()
        outline_found = False
        if tag_present and not invalid_payload:
            full_text = full_text.replace(OUTLINE_EDIT_JSON_TAG, "").strip()
            outline_found = True
        if full_text and show_reply and not invalid_payload:
            self.console.print(Panel(full_text, title="💬 Reply"))
            self.console.print()
        if outline_found:
            self._needs_outline_edit = True
            self._outline_edit_seen = True
            if full_text:
                self._outline_edit_text = full_text
        return outline_found

    def _process_clarification_text(self, full_text: str, *, show_reply: bool) -> bool:
        payload, errors = extract_clarification_payload(full_text)
        if payload:
            self._clarification_payload = payload
            self._needs_clarification = True
            self._clarification_seen = True
            note = payload.preface or payload.title or "Clarification required."
            self._clarification_text = note
            self.console.print(Panel(note, title="❓ Clarification Needed"))
            self.console.print()
            return True
        tag_present = has_clarification_tag(full_text)
        invalid_payload = tag_present and bool(errors)
        if invalid_payload:
            warning = "Clarification payload invalid. Falling back to plain text."
            body = f"{warning}\n\n{full_text}"
            self.console.print(Panel(body, title="Clarification", border_style="yellow"))
            self.console.print()
        clarification_found = False
        if tag_present and not invalid_payload:
            full_text = full_text.replace(CLARIFICATION_JSON_TAG, "").strip()
            clarification_found = True
        cleaned, found = self._strip_clarification_sentinel(full_text)
        clarification_found = clarification_found or found
        if cleaned and show_reply and not invalid_payload:
            self.console.print(Panel(cleaned, title="💬 Reply"))
            self.console.print()
        if clarification_found:
            self._needs_clarification = True
            self._clarification_seen = True
            if cleaned:
                self._clarification_text = cleaned
        return clarification_found

    def _handle_result(self, message: ResultMessage) -> None:
        if self._abort_finalized:
            return
        cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd is not None else "n/a"
        metrics = (
            f"Duration {message.duration_ms} ms | API {message.duration_api_ms} ms | Cost {cost}"
        )
        todos_snapshot = self.todo_manager.export_items()
        remaining = self.todo_manager.remaining_markdown()
        is_error = bool(getattr(message, "is_error", False))

        result_text = message.result or ""
        self._last_summary = result_text or None
        if self._session_logger:
            self._session_logger.log_result(
                "agent",
                result=result_text or None,
                is_error=bool(getattr(message, "is_error", False)),
            )
        if result_text and not self._needs_clarification and not self._clarification_seen:
            if has_clarification_tag(result_text) or NEEDS_CLARIFICATION_SENTINEL in result_text:
                self._process_clarification_text(result_text, show_reply=False)
        if result_text and not self._needs_outline_edit and not self._outline_edit_seen:
            if has_outline_edit_tag(result_text):
                self._process_outline_edit_text(result_text, show_reply=False)

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
        elif self._needs_outline_edit:
            title = "📝 Outline Edit"
            status = "needs_outline_edit"
            summary = (
                self._outline_edit_text
                or result_text
                or "Outline edit required."
            )
            body_lines = [
                summary,
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = summary
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
        elif remaining:
            title = "🕓 Awaiting input"
            status = "awaiting_input"
            body_lines = [
                result_text or "Awaiting input.",
                "",
                "Remaining Todos:" if remaining else "Remaining Todos: (none)",
                remaining,
                "",
                metrics,
            ]
            history_summary = result_text or "Awaiting input."
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
        elif status in {"needs_clarification", "needs_outline_edit", "awaiting_input"}:
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

    def _is_clarification_answers(self, message: str) -> bool:
        return message.lstrip().startswith("Clarification answers:")

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
        if self._permission_prompt_active:
            return
        if self._abort_requested or self._abort_finalized:
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

    async def _can_use_tool(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        del context
        if not self.config:
            return PermissionResultAllow()
        if self._abort_requested and self._aborted_reason:
            return PermissionResultDeny(message=self._aborted_reason, interrupt=True)
        allowed_roots = [self.config.paths.root.resolve()]
        delete_whitelist = [self.config.paths.memory_file.resolve()]
        project_cfg = self.config.load_project_config()
        authorizations = project_cfg.get("authorizations")
        if not isinstance(authorizations, dict):
            authorizations = None
        check = evaluate_tool_permission(
            tool_name,
            input_data,
            cwd=self.config.paths.root,
            allowed_roots=allowed_roots,
            delete_whitelist=delete_whitelist,
            authorizations=authorizations,
        )
        if not check.needs_confirm:
            return PermissionResultAllow()
        decision = await self._request_permission(tool_name, check.reason)
        if decision.allow:
            if decision.remember and check.targets:
                with suppress(Exception):
                    self.config.add_authorizations(tool_name, check.targets)
            return PermissionResultAllow()
        await self._handle_permission_denied(check.reason, message=decision.message)
        return PermissionResultDeny(
            message=self._aborted_reason or "User denied permission.",
            interrupt=True,
        )

    async def _handle_permission_denied(
        self, reason: str, *, message: str | None = None
    ) -> None:
        if message:
            self._aborted_reason = message
        else:
            self._aborted_reason = f"User denied permission: {reason}"
        self._abort_requested = True
        await self._stop_wait_indicator()
        await self._interrupt_client_on_abort()
        self._finalize_aborted()

    async def _interrupt_client_on_abort(self) -> None:
        if self._abort_interrupt_sent:
            return
        if not self._client:
            return
        self._abort_interrupt_sent = True
        with suppress(Exception):
            await self._client.interrupt()

    async def _request_permission(
        self, tool_name: str, reason: str
    ) -> PermissionDecision:
        if not self._permission_prompt:
            return PermissionDecision(False)
        was_running = self._wait_indicator is not None
        self._permission_prompt_active = True
        if was_running:
            await self._stop_wait_indicator()
        decision = PermissionDecision(False)
        try:
            title = f"Permission required: {tool_name}"
            body = reason
            result = await self._permission_prompt(title, body)
            if isinstance(result, PermissionDecision):
                decision = result
            else:
                decision = PermissionDecision(bool(result))
            return decision
        finally:
            self._permission_prompt_active = False
            if was_running and decision.allow:
                await self._start_wait_indicator()
