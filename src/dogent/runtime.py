"""Runtime integration with Claude Agent SDK."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from claude_agent_sdk.types import StreamEvent, ToolPermissionContext

from .config import Settings
from .context import Reference
from .guidelines import Guidelines
from .todo import TodoManager


def _load_template(name: str) -> str:
    path = Path(__file__).parent / "prompts" / f"{name}.md"
    return path.read_text(encoding="utf-8")


def build_system_prompt(
    settings: Settings,
    guidelines: Guidelines,
    todo: TodoManager,
    refs: List[Reference],
    cwd: Path,
) -> str:
    tmpl = _load_template("system")
    todo_text = "; ".join(
        [f"{item.id}:{item.status}:{item.title}" for item in todo.list()]
    )
    ctx_texts = [f"{ref.path}:\n{ref.content}" for ref in refs]
    rendered = tmpl.format(
        available_tools="Claude Code preset tools",
        cwd=str(cwd),
        language=settings.language,
        default_format=settings.default_format,
        guidelines=guidelines.summary,
        todo=todo_text or "暂无",
        context_refs="\n\n".join(ctx_texts) if ctx_texts else "无",
    )
    return rendered


def build_options(settings: Settings, cwd: Path, system_prompt: str) -> ClaudeAgentOptions:
    env = {}
    if settings.anthropic_base_url:
        env["ANTHROPIC_BASE_URL"] = settings.anthropic_base_url
    if settings.anthropic_auth_token:
        env["ANTHROPIC_AUTH_TOKEN"] = settings.anthropic_auth_token
    if settings.api_timeout_ms:
        env["API_TIMEOUT_MS"] = str(settings.api_timeout_ms)
    if settings.claude_code_disable_nonessential_traffic:
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = str(
            settings.claude_code_disable_nonessential_traffic
        )
    env.setdefault("ANTHROPIC_MODEL", settings.anthropic_model or "")
    # Only set fallback if it's different from main model.
    fallback_model = (
        settings.anthropic_small_fast_model
        if settings.anthropic_small_fast_model
        and settings.anthropic_small_fast_model != settings.anthropic_model
        else None
    )

    allowed_tools = []
    # Explicitly allow key doc-writing tools
    if settings.allow_fs_tools:
        allowed_tools.extend(["Read", "Write", "Edit", "MultiEdit"])
    if settings.allow_web:
        allowed_tools.extend(["WebSearch", "WebFetch"])

    options = ClaudeAgentOptions(
        tools=["Read", "Write", "Edit", "MultiEdit", "WebSearch", "WebFetch"],
        allowed_tools=allowed_tools,
        # Use Dogent system prompt only (no Claude Code preset text)
        system_prompt=system_prompt,
        model=settings.anthropic_model,
        fallback_model=fallback_model,
        env=env,
        cwd=str(cwd),
        include_partial_messages=True,
        setting_sources=["project", "local", "user"],
        permission_mode="acceptEdits",
        max_budget_usd=settings.max_budget_usd,
        can_use_tool=lambda tool_name, input_data, ctx: _permission_guard(
            tool_name, input_data, ctx, cwd
        ),
    )
    return options


async def _permission_guard(
    tool_name: str,
    input_data: dict,
    ctx: ToolPermissionContext,
    cwd: Path,
) -> PermissionResultAllow | PermissionResultDeny:
    """Guardrails for tools: filesystem scope and delete confirmation."""
    # Allow read-only tools
    if tool_name in {"WebSearch", "WebFetch", "Read", "Grep", "Glob"}:
        return PermissionResultAllow()

    # For write/edit, enforce cwd scope and prompt for deletes
    if tool_name in {"Write", "Edit", "MultiEdit"}:
        file_path = input_data.get("file_path") or input_data.get("path") or ""
        if file_path:
            abs_target = (cwd / file_path).resolve()
            try:
                cwd_abs = cwd.resolve()
            except FileNotFoundError:
                cwd_abs = cwd
            if cwd_abs not in abs_target.parents and abs_target != cwd_abs:
                return PermissionResultDeny(
                    message=f"写入/编辑路径超出当前目录: {file_path}，请确认后重试。"
                )
        if tool_name == "Write" and input_data.get("delete", False):
            return PermissionResultDeny(
                message="删除操作需要用户明确确认，请先确认再重试。"
            )
        return PermissionResultAllow()

    # Bash safeguard: block destructive outside cwd
    if tool_name == "Bash":
        cmd = input_data.get("command", "")
        dangerous = [" rm ", " rm -rf", " mv ", "sudo", "chmod 777"]
        if any(x in cmd for x in dangerous):
            return PermissionResultDeny(
                message="命令包含潜在危险操作，请确认后再执行。"
            )
        return PermissionResultAllow()

    # Default allow
    return PermissionResultAllow()


def build_user_prompt(user_text: str, refs: List[Reference]) -> str:
    ref_texts = [f"[{ref.path}]\n{ref.content}" for ref in refs]
    if ref_texts:
        return f"{user_text}\n\n参考资料：\n" + "\n\n".join(ref_texts)
    return user_text


class AgentRuntime:
    """Manages Claude SDK client lifecycle and streaming."""

    def __init__(
        self,
        cwd: Path,
        settings: Settings,
        guidelines: Guidelines,
        todo: TodoManager,
    ) -> None:
        self.cwd = cwd
        self.settings = settings
        self.guidelines = guidelines
        self.todo = todo
        self._client: Optional[ClaudeSDKClient] = None

    async def get_server_info(self) -> Dict:
        options = build_options(
            self.settings,
            self.cwd,
            build_system_prompt(self.settings, self.guidelines, self.todo, [], self.cwd),
        )
        async with ClaudeSDKClient(options=options) as client:
            info = await client.get_server_info()
            return info or {}

    async def stream_query(
        self, user_text: str, refs: List[Reference]
    ) -> AsyncIterator[Dict[str, str]]:
        """Yield simplified events for UI rendering."""
        system_prompt = build_system_prompt(
            self.settings, self.guidelines, self.todo, refs, self.cwd
        )
        options = build_options(self.settings, self.cwd, system_prompt)
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        try:
            await self._client.query(build_user_prompt(user_text, refs))

            async for message in self._client.receive_messages():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield {"type": "assistant", "text": block.text}
                        elif isinstance(block, ToolUseBlock):
                            yield {
                                "type": "tool_use",
                                "text": f"Tool {block.name}: {block.input}",
                            }
                elif isinstance(message, UserMessage):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            snippet = block.content[:200] if block.content else ""
                            yield {"type": "tool_result", "text": snippet}
                elif isinstance(message, SystemMessage):
                    # skip
                    continue
                elif isinstance(message, ResultMessage):
                    meta = []
                    if message.total_cost_usd:
                        meta.append(f"cost=${message.total_cost_usd:.4f}")
                    if message.duration_ms:
                        meta.append(f"duration_ms={message.duration_ms}")
                    yield {"type": "result", "text": ", ".join(meta)}
                elif isinstance(message, StreamEvent):
                    event = message.event
                    text = event.get("delta", {}).get("text", "")
                    if text:
                        yield {"type": "partial", "text": text}
        finally:
            await self._client.disconnect()
            self._client = None

    async def interrupt(self) -> None:
        if self._client:
            try:
                await self._client.interrupt()
            except Exception:
                # ignore if cannot interrupt
                pass
