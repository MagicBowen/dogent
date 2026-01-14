from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from rich.console import Console

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, TextBlock
from claude_agent_sdk.types import ClaudeAgentOptions

from ..config import ConfigManager
from ..features.doc_templates import DocumentTemplateManager
from ..config.paths import DogentPaths
from ..config.resources import read_config_text, read_prompt_text
from ..core.session_log import SessionLogger, log_exception
from ..agent.wait import LLMWaitIndicator


@dataclass(frozen=True)
class WizardResult:
    doc_template: str | None
    primary_language: str | None
    dogent_md: str


class InitWizard:
    """Runs the /init LLM wizard to generate dogent.md content."""

    def __init__(
        self,
        config: ConfigManager,
        paths: DogentPaths,
        templates: DocumentTemplateManager,
        console: Optional[Console] = None,
        session_logger: SessionLogger | None = None,
    ) -> None:
        self.config = config
        self.paths = paths
        self.templates = templates
        self.console = console or Console()
        self._session_logger = session_logger
        wizard_template = self._load_template_file("dogent_default.md")
        if wizard_template:
            wizard_template = wizard_template.replace("{doc_template}", "general")
        system_prompt = self._load_prompt("init_wizard_system.md")
        templates_overview = self.templates.describe_templates().strip()
        if not templates_overview:
            templates_overview = "No templates available."
        self._system_prompt = (
            system_prompt.replace("{wizard_template}", wizard_template)
            .replace("{working_dir}", str(self.paths.root))
            .replace("{templates_overview}", templates_overview)
        )

    async def generate(self, user_prompt: str) -> WizardResult:
        system_prompt = self._system_prompt
        if self._session_logger:
            self._session_logger.log_system_prompt("init_wizard", system_prompt)
        options = self._build_options(system_prompt)
        client = ClaudeSDKClient(options=options)
        await client.connect()
        indicator = LLMWaitIndicator(self.console, label="Waiting for init wizard")
        await indicator.start()
        try:
            built_prompt = self._build_user_prompt(user_prompt)
            if self._session_logger:
                self._session_logger.log_user_prompt("init_wizard", built_prompt)
            await client.query(built_prompt)
            parts: list[str] = []
            last_result: str | None = None
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock) and block.text:
                            if self._session_logger:
                                self._session_logger.log_assistant_text(
                                    "init_wizard", block.text
                                )
                            parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    last_result = message.result or None
                    if self._session_logger:
                        self._session_logger.log_result(
                            "init_wizard",
                            result=last_result,
                            is_error=bool(getattr(message, "is_error", False)),
                        )
                    break
            text = "\n".join(part.strip("\n") for part in parts if part.strip())
            if not text:
                text = (last_result or "").strip()
            parsed = self._parse_wizard_payload(text)
            if parsed:
                return parsed
            return WizardResult(
                doc_template=None,
                primary_language=None,
                dogent_md=text.strip(),
            )
        finally:
            await indicator.stop()
            await client.disconnect()

    @staticmethod
    def _parse_wizard_payload(text: str) -> WizardResult | None:
        payload = InitWizard._load_json_payload(text)
        if not isinstance(payload, dict):
            return None
        dogent_md = payload.get("dogent_md")
        if not isinstance(dogent_md, str) or not dogent_md.strip():
            return None
        doc_template = payload.get("doc_template")
        if isinstance(doc_template, str):
            doc_template = doc_template.strip()
        else:
            doc_template = None
        primary_language = payload.get("primary_language")
        if not isinstance(primary_language, str) or not primary_language.strip():
            primary_language = None
        return WizardResult(
            doc_template=doc_template or None,
            primary_language=primary_language,
            dogent_md=dogent_md.strip(),
        )

    @staticmethod
    def _load_json_payload(text: str) -> object | None:
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception as exc:
            log_exception("cli.wizard", exc)
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            snippet = text[start : end + 1]
            try:
                return json.loads(snippet)
            except Exception as exc:
                log_exception("cli.wizard", exc)
                return None

    def _build_user_prompt(self, user_prompt: str) -> str:
        return (
            "User prompt: \n"
            f"{user_prompt.strip()}\n"
        )

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

    def _load_prompt(self, name: str) -> str:
        return read_prompt_text(name)

    def _load_template_file(self, name: str) -> str:
        return read_config_text(name)
