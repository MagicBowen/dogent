from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

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


class ConfigManager:
    """Handles Dogent configuration files and Claude Agent SDK options."""

    def __init__(self, paths: DogentPaths, console: Optional[Console] = None) -> None:
        self.paths = paths
        self.console = console or Console()

    def create_init_files(self) -> None:
        """Create .dogent scaffolding and templates."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        self.paths.images_dir.mkdir(parents=True, exist_ok=True)

        if not self.paths.doc_preferences.exists():
            self.paths.doc_preferences.write_text(
                self._doc_template(), encoding="utf-8"
            )

        if not self.paths.memory_file.exists():
            self.paths.memory_file.write_text(
                "# 临时记录\n\n- 在这里记录写作中的临时想法，完成后清理。\n",
                encoding="utf-8",
            )

    def create_config_template(self) -> None:
        """Create .dogent/dogent.json referencing a profile without embedding secrets."""
        self.paths.dogent_dir.mkdir(parents=True, exist_ok=True)
        template = {
            "profile": "deepseek"
        }
        self.paths.config_file.write_text(
            json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_settings(self) -> DogentSettings:
        """Merge project config, profile, and environment variables."""
        project_cfg = self._read_json(self.paths.config_file)
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
        }
        return DogentSettings(**resolved)

    def build_options(self, system_prompt: str) -> ClaudeAgentOptions:
        """Construct ClaudeAgentOptions for this workspace."""
        settings = self.load_settings()
        env = self._build_env(settings)

        allowed_tools = [
            "Read",
            "Write",
            "ListFiles",
            "Bash",
            "Search",
            "TodoWrite",
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
        """Read profile config from claude.json or claude.md, preferring JSON."""
        primary = self.paths.global_profile_file
        candidates = [primary, primary.with_suffix(".md")]
        for path in candidates:
            if not path.exists():
                continue
            if path.suffix == ".json":
                data = self._read_json(path)
                if data:
                    return data
            else:
                data = self._extract_json_from_text(path)
                if data:
                    return data
        return {}

    def _extract_json_from_text(self, path: Path) -> Dict[str, Any]:
        try:
            text = path.read_text(encoding="utf-8")
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                maybe = json.loads(text[start : end + 1])
                return maybe if isinstance(maybe, dict) else {}
        except Exception:
            return {}
        return {}

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
        return (
            "# Dogent 文档约束\n\n"
            "- 文档类型：\n"
            "- 目标篇幅（字数或页数）：\n"
            "- 目标读者与背景：\n"
            "- 语气与风格：\n"
            "- 语言（默认中文）：\n"
            "- 输出格式（默认 Markdown）：\n"
            "- 结构要求（章节、图表、代码、Mermaid 图等）：\n"
            "- 参考资料与引用格式：\n"
            "- 图片与图示需求（下载到 ./images 并在文中引用）：\n"
            "- 其他偏好与禁忌：\n"
        )
