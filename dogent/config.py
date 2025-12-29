from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from importlib import resources

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server

from . import __version__
from .document_tools import DOGENT_DOC_ALLOWED_TOOLS, create_dogent_doc_tools
from .paths import DogentPaths
from .web_tools import DOGENT_WEB_ALLOWED_TOOLS, create_dogent_web_tools


@dataclass
class DogentSettings:
    base_url: Optional[str]
    auth_token: Optional[str]
    model: Optional[str]
    small_model: Optional[str]
    api_timeout_ms: Optional[int]
    disable_nonessential_traffic: bool
    profile: Optional[str]
    web_profile: Optional[str]
    web_mode: str


class ConfigManager:
    """Handles Dogent configuration files and Claude Agent SDK options."""

    def __init__(self, paths: DogentPaths, console: Optional[Console] = None) -> None:
        self.paths = paths
        self.console = console or Console()
        self._ensure_home_bootstrap()

    def create_init_files(self) -> list[Path]:
        """Create .dogent scaffolding and templates. Returns created files."""
        created: list[Path] = []
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)

        if not self.paths.doc_preferences.exists():
            self.paths.doc_preferences.write_text(self._doc_template(), encoding="utf-8")
            created.append(self.paths.doc_preferences)
        # history file ensured by HistoryManager on use; memory is on-demand.
        return created

    def create_config_template(self) -> None:
        """Create or update .dogent/dogent.json without overwriting existing user settings."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        template_text = self._read_home_template("dogent_default.json")

        defaults: Dict[str, Any] = {}
        if template_text:
            try:
                parsed = json.loads(template_text)
                if isinstance(parsed, dict):
                    defaults = parsed
            except json.JSONDecodeError:
                defaults = {}
        if not defaults:
            defaults = {
                "llm_profile": "deepseek",
                "web_profile": "default",
                "doc_template": "general",
                "primary_language": "Chinese",
                "learn_auto": True,
            }

        current = self._read_json(self.paths.config_file)
        if not current:
            merged = dict(defaults)
        else:
            merged = dict(current)
            for key, value in defaults.items():
                if key not in merged:
                    merged[key] = value

        raw_web_profile = merged.get("web_profile")
        if raw_web_profile is None:
            merged["web_profile"] = "default"
        elif isinstance(raw_web_profile, str) and not raw_web_profile.strip():
            merged["web_profile"] = "default"

        if "learn_auto" not in merged or merged.get("learn_auto") is None:
            merged["learn_auto"] = True

        if "doc_template" not in merged or merged.get("doc_template") is None:
            merged["doc_template"] = "general"
        else:
            raw_doc_template = merged.get("doc_template")
            if isinstance(raw_doc_template, str) and not raw_doc_template.strip():
                merged["doc_template"] = "general"

        raw_primary_language = merged.get("primary_language")
        if isinstance(raw_primary_language, str):
            if not raw_primary_language.strip():
                raw_primary_language = None
        elif raw_primary_language is not None:
            raw_primary_language = None

        if raw_primary_language is None:
            merged["primary_language"] = "Chinese"

        self.paths.config_file.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def set_learn_auto(self, enabled: bool) -> None:
        """Persist workspace auto-learn toggle in .dogent/dogent.json."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.config_file.exists():
            self.create_config_template()
        data = self._read_json(self.paths.config_file) or {}
        if not isinstance(data, dict):
            data = {}
        data["learn_auto"] = bool(enabled)
        raw_web_profile = data.get("web_profile")
        if raw_web_profile is None:
            data["web_profile"] = "default"
        elif isinstance(raw_web_profile, str) and not raw_web_profile.strip():
            data["web_profile"] = "default"
        self.paths.config_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def set_doc_template(self, doc_template: Optional[str]) -> None:
        """Persist workspace doc_template selection in .dogent/dogent.json."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.config_file.exists():
            self.create_config_template()
        data = self._read_json(self.paths.config_file) or {}
        if not isinstance(data, dict):
            data = {}
        value = (doc_template or "").strip()
        data["doc_template"] = value if value else "general"
        self.paths.config_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def set_primary_language(self, primary_language: Optional[str]) -> None:
        """Persist workspace primary language selection in .dogent/dogent.json."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.config_file.exists():
            self.create_config_template()
        data = self._read_json(self.paths.config_file) or {}
        if not isinstance(data, dict):
            data = {}
        value = (primary_language or "").strip()
        data["primary_language"] = value if value else "Chinese"
        self.paths.config_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def render_template(self, name: str, context: Optional[Dict[str, str]] = None) -> str:
        """Render a workspace template with simple {key} replacements."""
        text = self._read_home_template(name)
        if not text:
            return ""
        if not context:
            return text
        rendered = text
        for key, value in context.items():
            rendered = rendered.replace("{" + key + "}", value)
        return rendered

    def load_settings(self) -> DogentSettings:
        """Merge project config, profile, and environment variables."""
        project_cfg = self.load_project_config()
        profile_name = project_cfg.get("llm_profile")
        profile_cfg = self._load_profile(profile_name)
        self._warn_if_placeholder_profile(profile_name, profile_cfg)
        raw_web_profile = project_cfg.get("web_profile")
        web_profile_name = self._normalize_web_profile(raw_web_profile)
        web_profile_cfg: Dict[str, Any] = {}
        if web_profile_name:
            web_profile_cfg = self._load_web_profile(web_profile_name)
            if not web_profile_cfg:
                self._warn_if_missing_web_profile(web_profile_name)
                web_profile_name = None
            else:
                self._warn_if_placeholder_web_profile(web_profile_name, web_profile_cfg)
        env_cfg = self._env_settings()

        anthropic_cfg: Dict[str, Any] = {}
        anthropic_cfg.update(profile_cfg)
        anthropic_cfg.update(project_cfg.get("anthropic", {}))

        resolved = {
            "base_url": anthropic_cfg.get("base_url") or env_cfg.get("base_url"),
            "auth_token": anthropic_cfg.get("auth_token") or env_cfg.get("auth_token"),
            "model": anthropic_cfg.get("model") or env_cfg.get("model"),
            "small_model": anthropic_cfg.get("small_fast_model")
            or env_cfg.get("small_fast_model"),
            "api_timeout_ms": anthropic_cfg.get("api_timeout_ms")
            or env_cfg.get("api_timeout_ms"),
            "disable_nonessential_traffic": bool(
                anthropic_cfg.get("disable_nonessential_traffic")
                if anthropic_cfg.get("disable_nonessential_traffic") is not None
                else env_cfg.get("disable_nonessential_traffic")
            ),
            "profile": profile_name,
            "web_profile": web_profile_name,
            "web_mode": "custom" if web_profile_name else "native",
        }
        return DogentSettings(**resolved)

    def load_project_config(self) -> Dict[str, Any]:
        """Read the workspace-level dogent.json file."""
        data = self._read_json(self.paths.config_file)
        return self._normalize_project_config(data)

    def _normalize_project_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize config keys and apply defaults."""
        if not data:
            return {
                "web_profile": "default",
                "doc_template": "general",
                "primary_language": "Chinese",
                "vision_profile": "glm-4.6v",
                "learn_auto": True,
            }
        normalized = dict(data)
        raw_web_profile = normalized.get("web_profile")
        if raw_web_profile is None:
            normalized["web_profile"] = "default"
        elif isinstance(raw_web_profile, str) and not raw_web_profile.strip():
            normalized["web_profile"] = "default"

        raw_learn_auto = normalized.get("learn_auto")
        if raw_learn_auto is None:
            normalized["learn_auto"] = True
        elif isinstance(raw_learn_auto, str):
            normalized["learn_auto"] = raw_learn_auto.strip().lower() in {
                "1",
                "true",
                "yes",
                "y",
                "on",
            }
        else:
            normalized["learn_auto"] = bool(raw_learn_auto)
        raw_doc_template = normalized.get("doc_template")
        if raw_doc_template is None:
            normalized["doc_template"] = "general"
        elif isinstance(raw_doc_template, str) and not raw_doc_template.strip():
            normalized["doc_template"] = "general"
        raw_primary_language = normalized.get("primary_language")
        if isinstance(raw_primary_language, str):
            if not raw_primary_language.strip():
                raw_primary_language = None
        elif raw_primary_language is not None:
            raw_primary_language = None

        if raw_primary_language is None:
            normalized["primary_language"] = "Chinese"
        raw_vision_profile = normalized.get("vision_profile")
        if raw_vision_profile is None:
            normalized["vision_profile"] = "glm-4.6v"
        elif isinstance(raw_vision_profile, str):
            cleaned = raw_vision_profile.strip()
            normalized["vision_profile"] = cleaned or "glm-4.6v"
        else:
            normalized["vision_profile"] = "glm-4.6v"
        return normalized

    def build_options(self, system_prompt: str) -> ClaudeAgentOptions:
        """Construct ClaudeAgentOptions for this workspace."""
        settings = self.load_settings()
        env = self._build_env(settings)

        use_custom_web = bool(settings.web_profile)

        allowed_tools = [
            "Read",
            "Write",
            "Edit",
            "Ls",
            "ListFiles",
            "Bash",
            "Grep",
            "Glob",
            "Task",
            "WebFetch" if not use_custom_web else None,
            "WebSearch" if not use_custom_web else None,
            "TodoWrite",
            "BashOutput",
            "SlashCommand",
            "NotebookEdit",
        ]
        allowed_tools = [t for t in allowed_tools if t]
        allowed_tools.extend(DOGENT_DOC_ALLOWED_TOOLS)
        doc_tools = create_dogent_doc_tools(self.paths.root)
        tools = list(doc_tools)
        if use_custom_web:
            allowed_tools.extend(DOGENT_WEB_ALLOWED_TOOLS)
            tools.extend(
                create_dogent_web_tools(
                    root=self.paths.root,
                    web_profile_name=settings.web_profile,
                    web_profile_cfg=self._load_web_profile(settings.web_profile),
                )
            )
        mcp_servers = {
            "dogent": create_sdk_mcp_server(
                name="dogent", version=__version__, tools=tools
            )
        }

        add_dirs = []
        if self.paths.claude_dir.exists():
            add_dirs.append(str(self.paths.claude_dir))

        fallback_model = (
            settings.small_model
            if settings.small_model and settings.small_model != settings.model
            else None
        )

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=str(self.paths.root),
            model=settings.model,
            fallback_model=fallback_model,
            permission_mode="acceptEdits",
            allowed_tools=allowed_tools,
            add_dirs=add_dirs,
            env=env,
            mcp_servers=mcp_servers,
        )
        return options

    def _build_env(self, settings: DogentSettings) -> Dict[str, str]:
        env: Dict[str, str] = {}
        if settings.base_url:
            env["ANTHROPIC_BASE_URL"] = settings.base_url
        if settings.auth_token:
            env["ANTHROPIC_AUTH_TOKEN"] = settings.auth_token
        if settings.model:
            env["ANTHROPIC_MODEL"] = settings.model
        if settings.small_model:
            env["ANTHROPIC_SMALL_FAST_MODEL"] = settings.small_model
        if settings.api_timeout_ms is not None:
            env["API_TIMEOUT_MS"] = str(settings.api_timeout_ms)
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = (
            "1" if settings.disable_nonessential_traffic else "0"
        )
        return env

    def _env_settings(self) -> Dict[str, Any]:
        return {
            "base_url": os.getenv("ANTHROPIC_BASE_URL"),
            "auth_token": os.getenv("ANTHROPIC_AUTH_TOKEN"),
            "model": os.getenv("ANTHROPIC_MODEL"),
            "small_fast_model": os.getenv("ANTHROPIC_SMALL_FAST_MODEL"),
            "api_timeout_ms": self._to_int(os.getenv("API_TIMEOUT_MS")),
            "disable_nonessential_traffic": self._to_bool(
                os.getenv("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")
            ),
        }

    def _load_profile(self, profile_name: Optional[str]) -> Dict[str, Any]:
        if not profile_name:
            return {}
        profile_data = self._read_profile_file()
        if not profile_data:
            return {}
        profiles = profile_data.get("profiles") or profile_data
        chosen = profiles.get(profile_name, {})
        mapped = {
            "base_url": chosen.get("ANTHROPIC_BASE_URL") or chosen.get("base_url"),
            "auth_token": chosen.get("ANTHROPIC_AUTH_TOKEN") or chosen.get("auth_token"),
            "model": chosen.get("ANTHROPIC_MODEL") or chosen.get("model"),
            "small_fast_model": chosen.get("ANTHROPIC_SMALL_FAST_MODEL")
            or chosen.get("small_fast_model"),
            "api_timeout_ms": chosen.get("API_TIMEOUT_MS")
            or chosen.get("api_timeout_ms"),
            "disable_nonessential_traffic": chosen.get(
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
            )
            or chosen.get("disable_nonessential_traffic"),
        }
        return mapped

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.console.print(
                f"[red]Failed to parse JSON config at {path}. Using defaults.[/red]"
            )
            return {}

    def _read_profile_file(self) -> Dict[str, Any]:
        """Read profile config from claude.json only."""
        path = self.paths.global_profile_file
        if path.exists():
            data = self._read_json(path)
            if data:
                return data
        return {}

    def _read_web_file(self) -> Dict[str, Any]:
        path = self.paths.global_web_file
        if path.exists():
            data = self._read_json(path)
            if data:
                return data
        return {}

    def _load_web_profile(self, profile_name: Optional[str]) -> Dict[str, Any]:
        if not profile_name:
            return {}
        data = self._read_web_file()
        if not data:
            return {}
        profiles = data.get("profiles") or data
        chosen = profiles.get(profile_name, {})
        if not isinstance(chosen, dict):
            return {}
        return chosen
    
    def _normalize_web_profile(self, raw: Any) -> Optional[str]:
        if raw is None:
            return None
        if isinstance(raw, str):
            cleaned = raw.strip()
            if not cleaned:
                return None
            if cleaned.lower() == "default":
                return None
            return cleaned
        return None

    def _ensure_home_bootstrap(self) -> None:
        home_dir = self.paths.global_dir
        if not home_dir.exists():
            home_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.global_profile_file.exists():
            default = self._default_profile_template()
            try:
                self.paths.global_profile_file.write_text(default, encoding="utf-8")
                self.console.print(
                    f"[cyan]Created default config at {self.paths.global_profile_file}. Edit it with your credentials.[/cyan]"
                )
            except PermissionError:
                self.console.print(
                    f"[yellow]Cannot write {self.paths.global_profile_file}. Please create it manually with your credentials.[/yellow]"
                )
        if not self.paths.global_web_file.exists():
            default = self._default_web_template()
            try:
                self.paths.global_web_file.write_text(default, encoding="utf-8")
                self.console.print(
                    f"[cyan]Created default web config at {self.paths.global_web_file}. Edit it with your search API credentials.[/cyan]"
                )
            except PermissionError:
                self.console.print(
                    f"[yellow]Cannot write {self.paths.global_web_file}. Please create it manually with your search API credentials.[/yellow]"
                )
        if not self.paths.global_vision_file.exists():
            default = self._default_vision_template()
            try:
                self.paths.global_vision_file.write_text(default, encoding="utf-8")
                self.console.print(
                    f"[cyan]Created default vision config at {self.paths.global_vision_file}. Edit it with your vision API credentials.[/cyan]"
                )
            except PermissionError:
                self.console.print(
                    f"[yellow]Cannot write {self.paths.global_vision_file}. Please create it manually with your vision API credentials.[/yellow]"
                )

    def _to_bool(self, value: Optional[str]) -> bool:
        if value is None:
            return False
        return value.lower() in {"1", "true", "yes", "y"}

    def _to_int(self, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _doc_template(self) -> str:
        template = self._read_home_template("dogent_default.md")
        if template:
            return template.replace("{doc_template}", "general")
        return "# Dogent Writing Constraints\n"

    def _default_profile_template(self) -> str:
        template = self._read_home_template("claude_default.json")
        if template:
            return template
        # Minimal placeholder to avoid duplication if resources are missing
        return json.dumps({"profiles": {"default": {}}}, indent=2)

    def _default_web_template(self) -> str:
        template = self._read_home_template("web_default.json")
        if template:
            return template
        return json.dumps({"profiles": {"default": {"provider": "google_cse"}}}, indent=2)

    def _default_vision_template(self) -> str:
        template = self._read_home_template("vision_default.json")
        if template:
            return template
        return json.dumps({"profiles": {"glm-4.6v": {"provider": "glm-4.6v"}}}, indent=2)

    def _read_home_template(self, name: str) -> str:
        try:
            data = resources.files("dogent").joinpath("templates").joinpath(name)
            return data.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _warn_if_placeholder_profile(
        self, profile_name: Optional[str], profile_cfg: Dict[str, Any]
    ) -> None:
        if not profile_name or not profile_cfg:
            return
        token = profile_cfg.get("auth_token")
        if token is None or (isinstance(token, str) and "replace" in token.lower()):
            self.console.print(
                "[yellow]"
                f"Profile '{profile_name}' in {self.paths.global_profile_file} still has placeholder credentials. "
                "Please update it before running Dogent."
                "[/yellow]"
            )

    def _warn_if_placeholder_web_profile(
        self, profile_name: Optional[str], profile_cfg: Dict[str, Any]
    ) -> None:
        if not profile_name or not profile_cfg:
            return
        provider = str(profile_cfg.get("provider") or "")
        key_fields = ("api_key", "key", "token", "subscription_key")
        placeholder = False
        for field in key_fields:
            value = profile_cfg.get(field)
            if isinstance(value, str) and "replace" in value.lower():
                placeholder = True
                break
        if placeholder:
            self.console.print(
                "[yellow]"
                f"Web profile '{profile_name}' in {self.paths.global_web_file} still has placeholder credentials "
                f"(provider={provider or 'unknown'}). Please update it before running web tools."
                "[/yellow]"
            )

    def _warn_if_missing_web_profile(self, profile_name: str) -> None:
        self.console.print(
            "[yellow]"
            f"Web profile '{profile_name}' not found in {self.paths.global_web_file}. "
            "Falling back to native WebSearch/WebFetch."
            "[/yellow]"
        )
