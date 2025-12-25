from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Optional, Protocol

from rich.console import Console

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock
from claude_agent_sdk.types import ClaudeAgentOptions

from .config import ConfigManager
from .lessons import LessonIncident
from .paths import DogentPaths
from .prompts import TemplateRenderer


class LessonDrafter(Protocol):
    async def draft_from_incident(self, incident: LessonIncident, user_correction: str) -> str: ...

    async def draft_from_free_text(self, free_text: str) -> str: ...


@dataclass(frozen=True)
class DraftContext:
    incident_status: str
    incident_summary: str
    user_correction: str


class ClaudeLessonDrafter:
    def __init__(
        self,
        config: ConfigManager,
        paths: DogentPaths,
        console: Optional[Console] = None,
    ) -> None:
        self.config = config
        self.paths = paths
        self.console = console or Console()
        self.renderer = TemplateRenderer(console=self.console)
        self._template = self._load_template("lesson_draft.md")

    async def draft_from_incident(self, incident: LessonIncident, user_correction: str) -> str:
        summary = incident.summary.strip()
        remaining = incident.todos_markdown.strip()
        if remaining:
            summary = summary + "\n\nRemaining Todos at exit:\n" + remaining
        ctx = DraftContext(
            incident_status=incident.status,
            incident_summary=summary,
            user_correction=user_correction.strip(),
        )
        return await self._run_llm(self._render(ctx))

    async def draft_from_free_text(self, free_text: str) -> str:
        ctx = DraftContext(
            incident_status="manual",
            incident_summary="(none; user-provided)",
            user_correction=free_text.strip(),
        )
        return await self._run_llm(self._render(ctx))

    def _render(self, ctx: DraftContext) -> str:
        context = {
            "incident_status": ctx.incident_status,
            "incident_summary": ctx.incident_summary,
            "user_correction": ctx.user_correction,
            "remaining_todos": " ",
        }
        return self.renderer.render(
            self._template,
            lambda key: context.get(key),
            template_name="lesson draft",
        ).strip()

    def _load_template(self, name: str) -> str:
        base = resources.files("dogent").joinpath("prompts")
        return base.joinpath(name).read_text(encoding="utf-8")

    def _build_options(self, system_prompt: str) -> ClaudeAgentOptions:
        settings = self.config.load_settings()
        env = self.config._build_env(settings)  # type: ignore[attr-defined]
        model = settings.small_model or settings.model
        return ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=str(self.paths.root),
            model=model,
            permission_mode="acceptEdits",
            allowed_tools=[],
            env=env,
        )

    async def _run_llm(self, user_prompt: str) -> str:
        system_prompt = (
            "You write concise, reusable engineering lessons in Markdown.\n"
            "Return ONLY Markdown (no code fences). Start with a '## ' heading.\n"
            "Then include sections: ### Problem, ### Cause, ### Correct Approach.\n"
            "The title must be a specific actionable rule derived from the user correction.\n"
            "Be brief: prefer bullets; avoid long prose.\n"
            "The Correct Approach MUST include the user's correction verbatim as a short quote block.\n"
        )
        options = self._build_options(system_prompt)
        client = ClaudeSDKClient(options=options)
        await client.connect()
        try:
            await client.query(user_prompt)
            parts: list[str] = []
            last_result: str | None = None
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text:
                            parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    last_result = message.result or None
                    break
            text = "\n".join(part.strip("\n") for part in parts if part.strip())
            if not text:
                text = (last_result or "").strip()
            return text
        finally:
            await client.disconnect()
