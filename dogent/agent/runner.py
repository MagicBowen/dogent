from __future__ import annotations

import asyncio
import json
import os
import tempfile
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
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
from claude_agent_sdk.types import (
    PermissionUpdate,
    StreamEvent,
    TERMINAL_TASK_STATUSES,
    TaskNotificationMessage,
    TaskProgressMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
)

from ..config import ConfigManager
from ..core.file_refs import FileAttachment
from ..prompts import PromptBuilder
from ..core.history import HistoryManager
from ..core.todo import TodoManager
from .wait import LLMWaitIndicator
from ..features.document_tools import DOGENT_DOC_TOOL_DISPLAY_NAMES
from ..features.vision_tools import DOGENT_VISION_TOOL_DISPLAY_NAMES
from ..features.image_tools import DOGENT_IMAGE_TOOL_DISPLAY_NAMES
from ..features.web_tools import DOGENT_WEB_TOOL_DISPLAY_NAMES
from ..features.dependency_manager import (
    dependency_summary,
    install_missing_dependencies,
    manual_instructions,
    missing_dependencies_for_tool,
)
from .permissions import (
    evaluate_tool_permission,
    extract_command_paths,
    extract_delete_targets,
    extract_redirection_targets,
)
from ..features.clarification import (
    ClarificationPayload,
    parse_clarification_payload,
)
from ..outline_edit import OutlineEditPayload, parse_outline_edit_payload
from ..features.ui_tools import DOGENT_UI_TOOL_DISPLAY_NAMES
from ..core.session_log import SessionLogger

DOGENT_TOOL_DISPLAY_NAMES = {
    **DOGENT_WEB_TOOL_DISPLAY_NAMES,
    **DOGENT_DOC_TOOL_DISPLAY_NAMES,
    **DOGENT_VISION_TOOL_DISPLAY_NAMES,
    **DOGENT_IMAGE_TOOL_DISPLAY_NAMES,
    **DOGENT_UI_TOOL_DISPLAY_NAMES,
}

FOLLOWUP_STATUSES = {"needs_clarification", "needs_outline_edit", "awaiting_input"}
BACKGROUND_WAIT_MARKERS = (
    "still working",
    "still running",
    "waiting for",
    "wait for the",
    "in the background",
)


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


@dataclass(frozen=True)
class DependencyDecision:
    action: str  # install|manual|cancel


@dataclass(frozen=True)
class HumanPromptRequest:
    kind: str  # permission|question
    title: str
    message: str = ""
    input_data: dict[str, Any] | None = None
    agent_id: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    queued_count: int = 0

    @property
    def agent_label(self) -> str:
        if not self.agent_id:
            return "Main agent"
        return f"Sub-agent {self.agent_id[:8]}"


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
            Callable[[HumanPromptRequest], Awaitable[bool | PermissionDecision]]
        ] = None,
        dependency_prompt: Optional[
            Callable[[str, str], Awaitable[DependencyDecision]]
        ] = None,
        sdk_question_prompt: Optional[
            Callable[[HumanPromptRequest], Awaitable[dict[str, Any] | None]]
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
        self._human_prompt_lock = asyncio.Lock()
        self._human_prompt_pending = 0
        self._resume_wait_after_human_prompts = False
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
        self._dependency_prompt = dependency_prompt
        self._sdk_question_prompt = sdk_question_prompt
        self._session_logger = session_logger
        self._task_temp_files: set[Path] = set()
        self._temp_roots: list[Path] = self._resolve_temp_roots()
        self._aborted_reason: str | None = None
        self._abort_requested = False
        self._abort_finalized = False
        self._abort_interrupt_sent = False
        self._permission_prompt_active = False
        self._clarification_payload: ClarificationPayload | None = None
        self._outline_edit_payload: OutlineEditPayload | None = None
        self._dependency_installing = False
        self._dependency_manual_instructions: str | None = None
        self._dependency_install_phase: str | None = None
        self._dependency_download_path: str | None = None
        self._dependency_missing: list[str] = []
        self._partial_reply_stream_active = False
        self._partial_reply_seen = False
        self._last_task_progress: dict[str, str] = {}
        self._background_task_ids: set[str] = set()
        self._finalized_task_ids: set[str] = set()
        self._background_reconciliation_attempted = False
        self._turn_count: int = 0

    async def reset(self) -> None:
        """Close current session so it can be re-created with new settings."""
        with suppress(Exception):
            await self._stop_wait_indicator()
        async with self._lock:
            if self._client:
                await self._client.disconnect()
            self._client = None
            self._tool_name_by_id = {}
            self._interrupted = False
            self.last_outcome = None
            self._aborted_reason = None
            self._abort_requested = False
            self._abort_finalized = False
            self._abort_interrupt_sent = False
            self._needs_clarification = False
            self._needs_outline_edit = False
            self._clarification_text = ""
            self._clarification_seen = False
            self._outline_edit_text = ""
            self._outline_edit_seen = False
            self._clarification_payload = None
            self._outline_edit_payload = None
            self._dependency_installing = False
            self._dependency_manual_instructions = None
            self._dependency_install_phase = None
            self._dependency_download_path = None
            self._dependency_missing = []
            self._partial_reply_stream_active = False
            self._partial_reply_seen = False
            self._last_task_progress = {}
            self._background_task_ids = set()
            self._finalized_task_ids = set()
            self._background_reconciliation_attempted = False
            self._task_temp_files.clear()
            self._last_summary = None
            self._skip_todo_render_once = False
            self._turn_count = 0

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
            Callable[[HumanPromptRequest], Awaitable[bool | PermissionDecision]]
        ],
    ) -> None:
        """Update the permission prompt callback for subsequent runs."""
        self._permission_prompt = permission_prompt

    def set_dependency_prompt(
        self,
        dependency_prompt: Optional[
            Callable[[str, str], Awaitable[DependencyDecision]]
        ],
    ) -> None:
        """Update the dependency install prompt callback for subsequent runs."""
        self._dependency_prompt = dependency_prompt

    def set_sdk_question_prompt(
        self,
        sdk_question_prompt: Optional[
            Callable[[HumanPromptRequest], Awaitable[dict[str, Any] | None]]
        ],
    ) -> None:
        """Update the SDK-native AskUserQuestion callback for subsequent runs."""
        self._sdk_question_prompt = sdk_question_prompt

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
        record_user_input: bool = True,
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
        self._task_temp_files.clear()
        self._partial_reply_stream_active = False
        self._partial_reply_seen = False
        self._last_task_progress = {}
        self._background_task_ids = set()
        self._finalized_task_ids = set()
        self._background_reconciliation_attempted = False
        self._turn_count += 1
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
        user_input = None
        if record_user_input and not self._is_clarification_answers(user_message):
            user_input = user_message
        self.history.append(
            summary="User request",
            status="started",
            prompt=user_prompt,
            user_input=user_input,
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
        finally:
            await self._stop_wait_indicator()
            self._task_temp_files.clear()
            if self._session_logger:
                self._session_logger.end_interaction("agent", status=interaction_status)

    def _should_keep_client_for_followup(self) -> bool:
        if self._needs_clarification or self._needs_outline_edit:
            return True
        if self.last_outcome is None:
            return False
        return self.last_outcome.status in FOLLOWUP_STATUSES

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
        reconcile_background_tasks = False
        await self._start_wait_indicator()
        async for message in self._client.receive_response():
            if self._interrupted:
                await self._stop_wait_indicator()
                if isinstance(message, ResultMessage):
                    break
                continue
            await self._stop_wait_indicator()
            if self._abort_requested and not drain_after_interrupt:
                await self._interrupt_client_on_abort()
                drain_after_interrupt = True
            if drain_after_interrupt:
                if isinstance(message, ResultMessage):
                    saw_result = True
                    break
                continue
            if isinstance(message, StreamEvent):
                if not self._abort_requested:
                    self._handle_stream_event(message)
                continue
            if self._is_rate_limit_event(message):
                self._handle_rate_limit_event(message)
                continue
            if isinstance(message, TaskStartedMessage):
                self._handle_task_started(message)
                continue
            if isinstance(message, TaskProgressMessage):
                self._handle_task_progress(message)
                continue
            if isinstance(message, TaskNotificationMessage):
                self._handle_task_notification(message)
                continue
            if isinstance(message, TaskUpdatedMessage):
                self._handle_task_updated(message)
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
                if not self._interrupted and self._should_reconcile_background_result(
                    message
                ):
                    reconcile_background_tasks = True
                    saw_result = True
                    break
                if not self._interrupted:
                    self._handle_result(message)
                saw_result = True
                break
            if not self._interrupted and not drain_after_interrupt:
                await self._start_wait_indicator()
        if not saw_result and self._aborted_reason and not self._interrupted:
            self._finalize_aborted()
        if reconcile_background_tasks:
            await self._reconcile_background_tasks()

    def _should_reconcile_background_result(self, message: ResultMessage) -> bool:
        if self._background_reconciliation_attempted:
            return False
        if message.is_error or self._abort_requested or self._interrupted:
            return False
        if not self._background_task_ids:
            return False
        active_ids = self._background_task_ids - self._finalized_task_ids
        result_text = (message.result or "").lower()
        claims_to_be_waiting = any(
            marker in result_text for marker in BACKGROUND_WAIT_MARKERS
        )
        return bool(active_ids or claims_to_be_waiting)

    async def _reconcile_background_tasks(self) -> None:
        if not self._client:
            return
        self._background_reconciliation_attempted = True
        active_ids = sorted(self._background_task_ids - self._finalized_task_ids)
        if active_ids:
            state = f"Still active task IDs: {', '.join(active_ids)}."
        else:
            state = "All background tasks have now reported terminal status."
        prompt = (
            "Dogent requires a complete final response for the current user request. "
            f"{state} Wait for any active background agents using the available task "
            "tools, collect every sub-agent result, and then provide one consolidated "
            "answer that includes the main-agent work and all sub-agent findings. Do "
            "not finish by saying that agents are still working or that you are waiting."
        )
        self.console.print(
            Panel(
                "Collecting completed background-agent results before finalizing.",
                title="🧵 Consolidating",
                border_style="cyan",
            )
        )
        self.console.print()
        await self._start_wait_indicator()
        async with self._lock:
            if not self._client or self._abort_requested or self._interrupted:
                return
            await self._client.query(prompt)
        await self._stream_responses()

    async def interrupt(self, reason: str) -> None:
        async with self._lock:
            self._interrupted = True
            self._finish_partial_reply_stream()
            if self._dependency_installing:
                message = self._dependency_interrupt_message(reason)
                reason = message
            if self._client:
                with suppress(Exception):
                    await self._client.interrupt()
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
        self._finish_partial_reply_stream()
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
        self._finish_partial_reply_stream()
        text_blocks: list[str] = []
        ui_request_seen = False
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
                if block.name == "mcp__dogent__ui_request":
                    self._log_tool_use(block)
                    if self._handle_ui_request(block.input):
                        ui_request_seen = True
                    self.console.print()
                    continue
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
        full_text = ""
        if text_blocks:
            full_text = "\n\n".join(
                part.strip() for part in text_blocks if part and part.strip()
            ).strip()
            if full_text and not ui_request_seen and not self._partial_reply_seen:
                self.console.print(Panel(full_text, title="💬 Reply"))
                self.console.print()
        self._partial_reply_seen = False

    def _handle_ui_request(self, payload: object) -> bool:
        if not isinstance(payload, dict):
            self._log_ui_request_error("UI request payload must be a JSON object.")
            return False
        response_type = payload.get("response_type")
        if response_type is None and isinstance(payload.get("type"), str):
            response_type = payload.get("type")
            payload = {**payload, "response_type": response_type}
        raw_oneof = payload.get("oneOf")
        if isinstance(raw_oneof, str):
            try:
                parsed_oneof = json.loads(raw_oneof)
            except Exception:
                parsed_oneof = None
            if isinstance(parsed_oneof, dict):
                if response_type and "response_type" not in parsed_oneof:
                    parsed_oneof["response_type"] = response_type
                payload = parsed_oneof
                response_type = payload.get("response_type") or payload.get("type")
        if response_type == "clarification":
            parsed, errors = parse_clarification_payload(payload)
            if parsed:
                self._clarification_payload = parsed
                self._needs_clarification = True
                self._clarification_seen = True
                note = parsed.preface or parsed.title or "Clarification required."
                self._clarification_text = note
                self.console.print(Panel(note, title="❓ Clarification Needed"))
                self.console.print()
                return True
            self._log_ui_request_error("Invalid clarification payload.", errors)
            return False
        if response_type == "outline_edit":
            parsed, errors = parse_outline_edit_payload(payload)
            if parsed:
                self._outline_edit_payload = parsed
                self._needs_outline_edit = True
                self._outline_edit_seen = True
                note = parsed.title or "Outline edit required."
                self._outline_edit_text = note
                self.console.print(Panel(note, title="📝 Outline Edit"))
                self.console.print()
                return True
            self._log_ui_request_error("Invalid outline edit payload.", errors)
            return False
        self._log_ui_request_error("UI request missing valid response_type.")
        return False

    def _log_ui_request_error(self, message: str, errors: list[str] | None = None) -> None:
        lines = [message]
        if errors:
            lines.extend(f"- {error}" for error in errors)
        body = "\n".join(lines)
        self.console.print(Panel(body, title="UI Request", border_style="red"))
        self.console.print()

    def _handle_result(self, message: ResultMessage) -> None:
        if self._abort_finalized:
            return
        self._finish_partial_reply_stream()
        cost = f"${message.total_cost_usd:.4f}" if message.total_cost_usd is not None else "n/a"
        metrics = (
            f"Duration {message.duration_ms} ms | API {message.duration_api_ms} ms | Cost {cost}"
        )
        api_error_status = getattr(message, "api_error_status", None)
        if api_error_status is not None:
            metrics = f"{metrics} | HTTP {api_error_status}"
        usage_lines = self._format_usage_lines(getattr(message, "usage", None))
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
                usage=getattr(message, "usage", None),
                structured_output=getattr(message, "structured_output", None),
            )
            if api_error_status is not None:
                self._session_logger.log_runtime_event(
                    "agent",
                    "result.api_error",
                    {"status": api_error_status},
                )
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
            if usage_lines:
                body_lines.extend(["", *usage_lines])
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
            if usage_lines:
                body_lines.extend(["", *usage_lines])
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
            if usage_lines:
                body_lines.extend(["", *usage_lines])
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
            if usage_lines:
                body_lines.extend(["", *usage_lines])
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
            if usage_lines:
                body_lines.extend(["", *usage_lines])
            history_summary = result_text or "Awaiting input."
        else:
            title = "✅ Completed"
            status = "completed"
            body_lines = [
                result_text,
                "",
                metrics,
            ]
            if usage_lines:
                body_lines.extend(["", *usage_lines])
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

    async def _can_use_tool(
        self,
        tool_name: str,
        input_data: dict,
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        if not self.config:
            return PermissionResultAllow()
        if self._abort_requested and self._aborted_reason:
            return PermissionResultDeny(message=self._aborted_reason, interrupt=True)
        if tool_name == "AskUserQuestion":
            updated_input = await self._request_sdk_questions(input_data, context)
            if updated_input is not None:
                return PermissionResultAllow(updated_input=updated_input)
            await self._handle_permission_denied(
                "SDK-native clarification required.",
                message="Clarification cancelled by user.",
            )
            return PermissionResultDeny(
                message=self._aborted_reason or "Clarification cancelled by user.",
                interrupt=True,
            )
        if not await self._ensure_tool_dependencies(tool_name, input_data):
            return PermissionResultDeny(
                message=self._aborted_reason or "Missing dependencies.",
                interrupt=True,
            )
        allowed_roots = [self.config.paths.root.resolve()]
        read_roots = list(allowed_roots)
        read_roots.append(self.config.paths.global_plugins_dir.resolve())
        read_roots.append((Path.home() / ".claude").resolve())
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
            read_roots=read_roots,
            delete_whitelist=delete_whitelist,
            temp_whitelist=list(self._task_temp_files),
            authorizations=authorizations,
        )
        if not check.needs_confirm:
            self._track_temp_files(tool_name, input_data)
            return PermissionResultAllow()
        decision = await self._request_permission(
            tool_name, input_data, context, check.reason
        )
        if decision.allow:
            updated_permissions = None
            if decision.remember:
                updated_permissions = self._session_permission_updates(context.suggestions)
            if decision.remember and check.targets:
                with suppress(Exception):
                    self.config.add_authorizations(tool_name, check.targets)
            self._track_temp_files(tool_name, input_data)
            return PermissionResultAllow(updated_permissions=updated_permissions)
        if context.agent_id:
            await self._start_wait_indicator()
            return PermissionResultDeny(
                message=decision.message
                or f"User denied permission for sub-agent {context.agent_id}.",
                interrupt=True,
            )
        await self._handle_permission_denied(check.reason, message=decision.message)
        return PermissionResultDeny(
            message=self._aborted_reason or "User denied permission.",
            interrupt=True,
        )

    def _session_permission_updates(
        self, suggestions: Iterable[PermissionUpdate]
    ) -> list[PermissionUpdate] | None:
        updates: list[PermissionUpdate] = []
        for suggestion in suggestions:
            try:
                updates.append(replace(suggestion, destination="session"))
            except Exception:
                continue
        return updates or None

    def _resolve_temp_roots(self) -> list[Path]:
        roots: list[Path] = []
        env_tmp = os.environ.get("TMPDIR")
        if env_tmp:
            roots.append(Path(env_tmp))
        roots.append(Path(tempfile.gettempdir()))
        seen: set[str] = set()
        resolved: list[Path] = []
        for root in roots:
            try:
                resolved_root = root.expanduser().resolve()
            except Exception:
                continue
            key = str(resolved_root)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(resolved_root)
        return resolved

    def _is_temp_path(self, path: Path) -> bool:
        resolved = path.resolve()
        for root in self._temp_roots:
            try:
                resolved.relative_to(root)
                return True
            except Exception:
                continue
        return False

    def _track_temp_files(self, tool_name: str, input_data: dict) -> None:
        if tool_name in {"Write", "Edit"}:
            path = self._resolve_tool_path(input_data)
            if not path or not self._is_temp_path(path):
                return
            if not path.exists():
                self._task_temp_files.add(path.resolve())
            return
        if tool_name not in {"Bash", "BashOutput"}:
            return
        command = str(input_data.get("command") or "")
        if not command or extract_delete_targets(command, cwd=self.config.paths.root):
            return
        redirections = extract_redirection_targets(command, cwd=self.config.paths.root)
        for target in redirections:
            if self._is_temp_path(target) and not target.exists():
                self._task_temp_files.add(target.resolve())

    def _resolve_tool_path(self, input_data: dict) -> Path | None:
        for key in ("file_path", "path"):
            value = input_data.get(key)
            if isinstance(value, str) and value.strip():
                raw = value.strip()
                path = Path(raw)
                if path.is_absolute():
                    return path.resolve()
                return (self.config.paths.root / path).resolve()
        return None

    async def _ensure_tool_dependencies(
        self, tool_name: str, input_data: dict
    ) -> bool:
        missing = missing_dependencies_for_tool(tool_name, input_data)
        if not missing:
            return True
        summary = dependency_summary(missing)
        instructions = manual_instructions(missing)
        was_running = self._wait_indicator is not None
        if was_running:
            await self._stop_wait_indicator()
        decision = DependencyDecision("install")
        self._dependency_installing = True
        self._dependency_manual_instructions = instructions
        self._dependency_install_phase = "download"
        self._dependency_download_path = None
        self._dependency_missing = list(missing)
        try:
            if self._dependency_prompt:
                decision = await self._request_dependency_install(tool_name, summary)
            if decision.action == "manual":
                self._dependency_installing = False
                await self.interrupt(f"Install manually.\n\n{instructions}")
                return False
            if decision.action == "cancel":
                self._dependency_installing = False
                await self.interrupt("Dependency installation cancelled.")
                return False
            ok, error = await install_missing_dependencies(
                missing,
                self.console,
                status_cb=self._update_dependency_install_status,
            )
            if not ok:
                detail = f"{error}\n\n{instructions}" if error else instructions
                await self._fail_dependency_install(detail)
                return False
            still_missing = missing_dependencies_for_tool(tool_name, input_data)
            if still_missing:
                await self._fail_dependency_install(
                    manual_instructions(still_missing)
                )
                return False
            return True
        finally:
            self._dependency_installing = False
            self._dependency_manual_instructions = None
            self._dependency_install_phase = None
            self._dependency_download_path = None
            self._dependency_missing = []
            if (
                was_running
                and not self._abort_requested
                and not self._abort_finalized
                and not self._interrupted
            ):
                await self._start_wait_indicator()

    def _dependency_interrupt_message(self, reason: str) -> str:
        missing = self._dependency_missing
        instructions = manual_instructions(
            missing,
            download_path=self._dependency_download_path,
            install_phase=self._dependency_install_phase,
        )
        if instructions:
            return f"Dependency installation interrupted.\n\n{instructions}"
        return reason

    def _update_dependency_install_status(
        self, _dep: str, phase: str, download_path: str | None
    ) -> None:
        self._dependency_install_phase = phase
        self._dependency_download_path = download_path

    async def _fail_dependency_install(self, message: str) -> None:
        await self._stop_wait_indicator()
        self._interrupted = True
        todos_snapshot = self.todo_manager.export_items()
        remaining = self.todo_manager.remaining_markdown()
        self.last_outcome = RunOutcome(
            status="error",
            summary=message,
            todos_snapshot=todos_snapshot,
            remaining_todos_markdown=remaining,
        )
        body_lines = [
            f"Reason: {message}",
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
            summary=f"Dependency install failed: {message}",
            status="error",
            prompt=None,
            todos=todos_snapshot,  # type: ignore[arg-type]
        )
        if self._client:
            with suppress(Exception):
                await self._client.interrupt()

    async def _abort_with_message(self, message: str) -> None:
        self._aborted_reason = message
        self._abort_requested = True
        await self._stop_wait_indicator()
        await self._interrupt_client_on_abort()
        self._finalize_aborted()

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

    def _permission_prompt_request(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        context: ToolPermissionContext,
        reason: str,
    ) -> HumanPromptRequest:
        action = context.display_name or self._display_tool_name(tool_name)
        lines = [action]
        sdk_title = (context.title or "").strip()
        if sdk_title and sdk_title != action:
            lines.append(sdk_title)
        description = (context.description or "").strip()
        if description:
            lines.append(description)
        blocked_path = (context.blocked_path or "").strip()
        if blocked_path:
            lines.extend(["", blocked_path])
        decision_reason = (context.decision_reason or "").strip()
        if decision_reason and decision_reason != reason:
            lines.extend(["", f"SDK reason: {decision_reason}"])
        lines.extend(["", f"Reason: {reason}"])
        request = HumanPromptRequest(
            kind="permission",
            title="",
            message="\n".join(lines),
            input_data=dict(input_data),
            agent_id=context.agent_id,
            tool_use_id=context.tool_use_id,
            tool_name=tool_name,
        )
        return replace(
            request, title=f"Permission required · {request.agent_label}"
        )

    async def _request_permission(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        context: ToolPermissionContext,
        reason: str,
    ) -> PermissionDecision:
        if not self._permission_prompt:
            return PermissionDecision(False)
        request = self._permission_prompt_request(
            tool_name, input_data, context, reason
        )
        decision = PermissionDecision(False)
        self._human_prompt_pending += 1
        try:
            async with self._human_prompt_lock:
                if self._abort_requested or self._interrupted:
                    return decision
                await asyncio.sleep(0)
                request = replace(
                    request, queued_count=max(0, self._human_prompt_pending - 1)
                )
                await self._begin_human_prompt(request)
                result = await self._permission_prompt(request)
                if isinstance(result, PermissionDecision):
                    decision = result
                else:
                    decision = PermissionDecision(bool(result))
                self._log_human_prompt_decision(request, decision.allow)
                return decision
        finally:
            await self._finish_human_prompt(decision.allow)

    async def _request_sdk_questions(
        self, input_data: dict[str, Any], context: ToolPermissionContext
    ) -> dict[str, Any] | None:
        if not self._sdk_question_prompt:
            return None
        request = HumanPromptRequest(
            kind="question",
            title="",
            input_data=dict(input_data),
            agent_id=context.agent_id,
            tool_use_id=context.tool_use_id,
            tool_name="AskUserQuestion",
        )
        request = replace(request, title=f"Clarification · {request.agent_label}")
        result: dict[str, Any] | None = None
        self._human_prompt_pending += 1
        try:
            async with self._human_prompt_lock:
                if self._abort_requested or self._interrupted:
                    return None
                await asyncio.sleep(0)
                request = replace(
                    request, queued_count=max(0, self._human_prompt_pending - 1)
                )
                await self._begin_human_prompt(request)
                result = await self._sdk_question_prompt(request)
                self._log_human_prompt_decision(request, result is not None)
                return result
        finally:
            await self._finish_human_prompt(result is not None)

    async def _begin_human_prompt(self, request: HumanPromptRequest) -> None:
        if self._wait_indicator is not None:
            self._resume_wait_after_human_prompts = True
            await self._stop_wait_indicator()
        self._permission_prompt_active = True
        if self._session_logger:
            self._session_logger.log_runtime_event(
                "agent",
                "human_prompt.requested",
                {
                    "kind": request.kind,
                    "agent_id": request.agent_id,
                    "tool_use_id": request.tool_use_id,
                    "tool_name": request.tool_name,
                },
            )

    def _log_human_prompt_decision(
        self, request: HumanPromptRequest, allowed: bool
    ) -> None:
        if self._session_logger:
            self._session_logger.log_runtime_event(
                "agent",
                "human_prompt.resolved",
                {
                    "kind": request.kind,
                    "agent_id": request.agent_id,
                    "tool_use_id": request.tool_use_id,
                    "tool_name": request.tool_name,
                    "allowed": allowed,
                },
            )

    async def _finish_human_prompt(self, continue_running: bool) -> None:
        self._human_prompt_pending = max(0, self._human_prompt_pending - 1)
        self._permission_prompt_active = self._human_prompt_pending > 0
        if self._human_prompt_pending:
            return
        should_resume = self._resume_wait_after_human_prompts
        self._resume_wait_after_human_prompts = False
        if (
            should_resume
            and continue_running
            and not self._abort_requested
            and not self._abort_finalized
            and not self._interrupted
        ):
            await self._start_wait_indicator()

    def _handle_stream_event(self, message: StreamEvent) -> None:
        event = getattr(message, "event", None)
        if not isinstance(event, dict):
            return
        if self._session_logger:
            self._session_logger.log_runtime_event(
                "agent",
                "assistant.stream_event",
                {
                    "event": event,
                    "parent_tool_use_id": getattr(message, "parent_tool_use_id", None),
                },
            )
        if event.get("type") != "content_block_delta":
            return
        delta = event.get("delta")
        if not isinstance(delta, dict) or delta.get("type") != "text_delta":
            return
        text = str(delta.get("text") or "")
        if not text:
            return
        if not self._partial_reply_stream_active:
            self.console.print("Streaming reply: ", end="")
            self._partial_reply_stream_active = True
        self.console.print(text, end="")
        self._partial_reply_seen = True

    def _finish_partial_reply_stream(self) -> None:
        if not self._partial_reply_stream_active:
            return
        self.console.print()
        self.console.print()
        self._partial_reply_stream_active = False

    def _format_usage_lines(self, usage: object) -> list[str]:
        usage_data = self._coerce_dict(usage)
        if not usage_data:
            return []
        summary: list[str] = []
        input_tokens = usage_data.get("input_tokens")
        output_tokens = usage_data.get("output_tokens")
        cache_read = usage_data.get("cache_read_input_tokens")
        cache_create = usage_data.get("cache_creation_input_tokens")
        if input_tokens is not None:
            summary.append(f"Input tokens: {input_tokens}")
        if output_tokens is not None:
            summary.append(f"Output tokens: {output_tokens}")
        if cache_read is not None:
            summary.append(f"Cache read tokens: {cache_read}")
        if cache_create is not None:
            summary.append(f"Cache creation tokens: {cache_create}")
        if not summary:
            return []
        return ["Usage:", *[f"- {line}" for line in summary]]

    def _coerce_dict(self, payload: object) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            return dict(payload)
        if payload is None:
            return None
        with suppress(Exception):
            return dict(payload)  # type: ignore[arg-type]
        return None

    def _handle_task_started(self, message: TaskStartedMessage) -> None:
        self._finish_partial_reply_stream()
        detail = {
            "task_id": message.task_id,
            "task_type": getattr(message, "task_type", None),
            "description": message.description,
            "tool_use_id": getattr(message, "tool_use_id", None),
            "data": getattr(message, "data", None),
        }
        if self._session_logger:
            self._session_logger.log_runtime_event("agent", "task.started", detail)
        self._background_task_ids.add(message.task_id)
        self._last_task_progress[message.task_id] = message.description
        body = message.description or f"Task {message.task_id} started."
        self.console.print(
            Panel(body, title="🧵 Background Task", border_style="cyan")
        )
        self.console.print()

    def _handle_task_progress(self, message: TaskProgressMessage) -> None:
        detail = {
            "task_id": message.task_id,
            "description": message.description,
            "last_tool_name": getattr(message, "last_tool_name", None),
            "usage": self._coerce_dict(getattr(message, "usage", None)),
            "data": getattr(message, "data", None),
        }
        if self._session_logger:
            self._session_logger.log_runtime_event("agent", "task.progress", detail)
        previous = self._last_task_progress.get(message.task_id)
        if message.description and message.description != previous:
            self._finish_partial_reply_stream()
            body_lines = [message.description]
            usage_lines = self._format_usage_lines(getattr(message, "usage", None))
            if usage_lines:
                body_lines.extend(["", *usage_lines])
            self.console.print(
                Panel("\n".join(body_lines), title="🧵 Task Progress", border_style="cyan")
            )
            self.console.print()
            self._last_task_progress[message.task_id] = message.description

    def _handle_task_notification(self, message: TaskNotificationMessage) -> None:
        self._finish_partial_reply_stream()
        detail = {
            "task_id": message.task_id,
            "status": message.status,
            "summary": message.summary,
            "output_file": message.output_file,
            "usage": self._coerce_dict(getattr(message, "usage", None)),
            "data": getattr(message, "data", None),
        }
        if self._session_logger:
            self._session_logger.log_runtime_event("agent", "task.notification", detail)
        self._last_task_progress.pop(message.task_id, None)
        if message.task_id in self._finalized_task_ids:
            return
        self._finalized_task_ids.add(message.task_id)
        title = "🧵 Task Complete"
        border_style = "green"
        if message.status == "failed":
            title = "🧵 Task Failed"
            border_style = "red"
        elif message.status == "stopped":
            title = "🧵 Task Stopped"
            border_style = "yellow"
        lines = [message.summary or f"Task {message.task_id} {message.status}."]
        if getattr(message, "output_file", None):
            lines.extend(["", f"Output: {message.output_file}"])
        usage_lines = self._format_usage_lines(getattr(message, "usage", None))
        if usage_lines:
            lines.extend(["", *usage_lines])
        self.console.print(
            Panel("\n".join(lines), title=title, border_style=border_style)
        )
        self.console.print()

    def _handle_task_updated(self, message: TaskUpdatedMessage) -> None:
        patch = self._coerce_dict(message.patch) or {}
        status = str(message.status or patch.get("status") or "").strip().lower()
        detail = {
            "task_id": message.task_id,
            "status": status or None,
            "patch": patch,
            "session_id": message.session_id,
            "uuid": message.uuid,
            "data": getattr(message, "data", None),
        }
        if self._session_logger:
            self._session_logger.log_runtime_event("agent", "task.updated", detail)
        if status not in TERMINAL_TASK_STATUSES:
            return
        previous = self._last_task_progress.pop(message.task_id, "")
        if message.task_id in self._finalized_task_ids:
            return
        self._finalized_task_ids.add(message.task_id)
        self._finish_partial_reply_stream()
        if status == "failed":
            title = "🧵 Task Failed"
            border_style = "red"
        elif status in {"killed", "stopped"}:
            title = "🧵 Task Stopped"
            border_style = "yellow"
        else:
            title = "🧵 Task Complete"
            border_style = "green"
        summary = str(patch.get("summary") or previous or "").strip()
        body = summary or f"Task {message.task_id} {status}."
        self.console.print(Panel(body, title=title, border_style=border_style))
        self.console.print()

    def _is_rate_limit_event(self, message: object) -> bool:
        return bool(
            getattr(message, "subtype", None) == "rate_limit"
            or hasattr(message, "rate_limit_info")
        )

    def _handle_rate_limit_event(self, message: object) -> None:
        info = getattr(message, "rate_limit_info", None)
        if info is None:
            info = getattr(message, "data", None)
        detail = self._coerce_dict(info)
        if self._session_logger:
            self._session_logger.log_runtime_event("agent", "rate_limit", detail)
        if not detail:
            return
        status = str(detail.get("status") or "").strip().lower()
        if status not in {"allowed_warning", "rejected"}:
            return
        self._finish_partial_reply_stream()
        lines = [f"Status: {status}"]
        limit_type = detail.get("rate_limit_type")
        if limit_type:
            lines.append(f"Limit: {limit_type}")
        utilization = detail.get("utilization")
        if utilization is not None:
            lines.append(f"Utilization: {utilization}")
        resets_at = detail.get("resets_at")
        if resets_at is not None:
            lines.append(f"Resets at: {resets_at}")
        title = "⚠️ Rate Limit Warning" if status == "allowed_warning" else "⛔ Rate Limited"
        border_style = "yellow" if status == "allowed_warning" else "red"
        self.console.print(
            Panel("\n".join(lines), title=title, border_style=border_style)
        )
        self.console.print()

    async def _request_dependency_install(
        self, tool_name: str, message: str
    ) -> DependencyDecision:
        if not self._dependency_prompt:
            return DependencyDecision("install")
        was_running = self._wait_indicator is not None
        self._permission_prompt_active = True
        if was_running:
            await self._stop_wait_indicator()
        decision = DependencyDecision("cancel")
        try:
            title = f"Dependencies required: {tool_name}"
            decision = await self._dependency_prompt(title, message)
            return decision
        finally:
            self._permission_prompt_active = False
            if was_running and not self._abort_requested and not self._abort_finalized:
                await self._start_wait_indicator()
