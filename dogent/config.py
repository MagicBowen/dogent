from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from importlib import resources

from claude_agent_sdk import ClaudeAgentOptions

from .paths import DogentPaths


@dataclass
class DogentSettings:
    base_url: Optional[str]
    auth_token: Optional[str]
    model: Optional[str]
    small_model: Optional[str]
    api_timeout_ms: Optional[int]
    disable_nonessential_traffic: bool
    profile: Optional[str]
    images_path: str


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
        """Create .dogent/dogent.json referencing a profile without embedding secrets."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        template_text = self._read_home_template("dogent_default.json")
        if not template_text:
            template_text = json.dumps(
                {"profile": "deepseek", "images_path": "./images"},
                indent=2,
                ensure_ascii=False,
            )
        self.paths.config_file.write_text(template_text, encoding="utf-8")

    def load_settings(self) -> DogentSettings:
        """Merge project config, profile, and environment variables."""
        project_cfg = self.load_project_config()
        profile_name = project_cfg.get("profile")
        profile_cfg = self._load_profile(profile_name)
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
            "images_path": project_cfg.get("images_path") or "./images",
        }
        return DogentSettings(**resolved)

    def load_project_config(self) -> Dict[str, Any]:
        """Read the workspace-level dogent.json file."""
        return self._read_json(self.paths.config_file)

    def build_options(self, system_prompt: str) -> ClaudeAgentOptions:
        """Construct ClaudeAgentOptions for this workspace."""
        settings = self.load_settings()
        env = self._build_env(settings)

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
            "WebFetch",
            "WebSearch",
            "TodoWrite",
            "BashOutput",
            "SlashCommand",
            "NotebookEdit",
        ]

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

    def _ensure_home_bootstrap(self) -> None:
        home_dir = self.paths.global_dir
        if not home_dir.exists():
            home_dir.mkdir(parents=True, exist_ok=True)
        self._copy_package_dir(
            "dogent", self.paths.global_prompts_dir, subdir="prompts"
        )
        self._copy_package_dir(
            "dogent", self.paths.global_templates_dir, subdir="templates"
        )
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
        return template or "# Dogent Writing Constraints\n"

    def _default_profile_template(self) -> str:
        template = self._read_home_template("claude_default.json")
        if template:
            return template
        # Minimal placeholder to avoid duplication if resources are missing
        return json.dumps({"profiles": {"default": {}}}, indent=2)

    def _read_home_template(self, name: str) -> str:
        home_template = self.paths.global_templates_dir / name
        if home_template.exists():
            try:
                return home_template.read_text(encoding="utf-8")
            except Exception:
                return ""
        try:
            data = resources.files("dogent").joinpath("templates").joinpath(name)
            return data.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _copy_package_dir(self, package: str, destination: Path, subdir: str) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        try:
            source_root = resources.files(package).joinpath(subdir)
            for entry in source_root.iterdir():
                if entry.is_dir():
                    continue
                target = destination / entry.name
                if target.exists():
                    continue
                content = entry.read_text(encoding="utf-8")
                target.write_text(content, encoding="utf-8")
        except Exception:
            self.console.print(
                f"[yellow]Warning: could not copy default templates from {package}[/yellow]"
            )
