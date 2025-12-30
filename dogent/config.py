from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from importlib import resources

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server

from . import __version__
from .document_tools import DOGENT_DOC_ALLOWED_TOOLS, create_dogent_doc_tools
from .paths import DogentPaths
from .vision_tools import DOGENT_VISION_ALLOWED_TOOLS, create_dogent_vision_tools
from .web_tools import DOGENT_WEB_ALLOWED_TOOLS, create_dogent_web_tools


DEFAULT_PROJECT_CONFIG: Dict[str, Any] = {
    "web_profile": "default",
    "vision_profile": None,
    "doc_template": "general",
    "primary_language": "Chinese",
    "learn_auto": True,
}
GLOBAL_DEFAULTS_KEY = "workspace_defaults"
GLOBAL_LLM_PROFILES_KEY = "llm_profiles"
GLOBAL_WEB_PROFILES_KEY = "web_profiles"
GLOBAL_VISION_PROFILES_KEY = "vision_profiles"


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
        defaults = self._default_project_config()
        global_defaults = self._global_defaults()
        merged_defaults = self._merge_dicts(defaults, global_defaults)
        current = self._read_json(self.paths.config_file)
        merged = self._merge_dicts(merged_defaults, current)
        normalized = self._normalize_project_config(merged)
        self.paths.config_file.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
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

    def _default_project_config(self) -> Dict[str, Any]:
        defaults = dict(DEFAULT_PROJECT_CONFIG)
        template_defaults = self._read_template_json("dogent_default.json")
        return self._merge_dicts(defaults, template_defaults)

    def _read_global_config(self) -> Dict[str, Any]:
        data = self._read_json(self.paths.global_config_file)
        if not isinstance(data, dict):
            return {}
        return self._sanitize_global_config(data)

    def _global_defaults(self) -> Dict[str, Any]:
        data = self._read_global_config()
        defaults = data.get(GLOBAL_DEFAULTS_KEY, {})
        return defaults if isinstance(defaults, dict) else {}

    def _default_global_config(self) -> Dict[str, Any]:
        template = self._read_template_json("dogent_global_default.json")
        if not template:
            template = {
                GLOBAL_DEFAULTS_KEY: self._default_project_config(),
                GLOBAL_LLM_PROFILES_KEY: {},
                GLOBAL_WEB_PROFILES_KEY: {},
                GLOBAL_VISION_PROFILES_KEY: {},
            }
        if not isinstance(template, dict):
            template = {}
        template["$schema"] = "./dogent.schema.json"
        template["version"] = __version__
        return template

    def _sanitize_global_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = dict(data)
        for key in (
            GLOBAL_DEFAULTS_KEY,
            GLOBAL_LLM_PROFILES_KEY,
            GLOBAL_WEB_PROFILES_KEY,
            GLOBAL_VISION_PROFILES_KEY,
        ):
            value = cleaned.get(key)
            if value is None:
                continue
            if not isinstance(value, dict):
                self.console.print(
                    f"[yellow]Ignoring {key} in {self.paths.global_config_file}: expected an object.[/yellow]"
                )
                cleaned.pop(key, None)
                continue
            if key == GLOBAL_DEFAULTS_KEY:
                cleaned[key] = value
            else:
                filtered: Dict[str, Any] = {}
                for name, entry in value.items():
                    if isinstance(entry, dict):
                        filtered[name] = entry
                    else:
                        self.console.print(
                            f"[yellow]Ignoring {key}.{name} in {self.paths.global_config_file}: expected an object.[/yellow]"
                        )
                cleaned[key] = filtered
        return cleaned

    def _merge_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        if not override:
            return dict(base)
        merged: Dict[str, Any] = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dicts(merged[key], value)  # type: ignore[arg-type]
            else:
                merged[key] = value
        return merged

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
        defaults = self._default_project_config()
        global_defaults = self._global_defaults()
        merged = self._merge_dicts(defaults, global_defaults)
        merged = self._merge_dicts(merged, data)
        return self._normalize_project_config(merged)

    def _normalize_project_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize config keys and apply defaults."""
        normalized = dict(data) if data else {}
        raw_llm_profile = normalized.get("llm_profile")
        if isinstance(raw_llm_profile, str):
            cleaned = raw_llm_profile.strip()
            if cleaned:
                normalized["llm_profile"] = cleaned
            else:
                normalized.pop("llm_profile", None)
        elif raw_llm_profile is None:
            normalized.pop("llm_profile", None)
        else:
            normalized.pop("llm_profile", None)
        raw_web_profile = normalized.get("web_profile")
        if raw_web_profile is None:
            normalized["web_profile"] = DEFAULT_PROJECT_CONFIG["web_profile"]
        elif isinstance(raw_web_profile, str) and not raw_web_profile.strip():
            normalized["web_profile"] = DEFAULT_PROJECT_CONFIG["web_profile"]

        raw_learn_auto = normalized.get("learn_auto")
        if raw_learn_auto is None:
            normalized["learn_auto"] = DEFAULT_PROJECT_CONFIG["learn_auto"]
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
            normalized["doc_template"] = DEFAULT_PROJECT_CONFIG["doc_template"]
        elif isinstance(raw_doc_template, str) and not raw_doc_template.strip():
            normalized["doc_template"] = DEFAULT_PROJECT_CONFIG["doc_template"]
        raw_primary_language = normalized.get("primary_language")
        if isinstance(raw_primary_language, str):
            if not raw_primary_language.strip():
                raw_primary_language = None
        elif raw_primary_language is not None:
            raw_primary_language = None

        if raw_primary_language is None:
            normalized["primary_language"] = DEFAULT_PROJECT_CONFIG["primary_language"]
        raw_vision_profile = normalized.get("vision_profile")
        if raw_vision_profile is None:
            normalized["vision_profile"] = DEFAULT_PROJECT_CONFIG["vision_profile"]
        elif isinstance(raw_vision_profile, str):
            cleaned = raw_vision_profile.strip()
            if not cleaned or cleaned.lower() == "none":
                normalized["vision_profile"] = DEFAULT_PROJECT_CONFIG["vision_profile"]
            else:
                normalized["vision_profile"] = cleaned
        else:
            normalized["vision_profile"] = DEFAULT_PROJECT_CONFIG["vision_profile"]
        return normalized

    def build_options(
        self,
        system_prompt: str,
        *,
        can_use_tool=None,
        hooks=None,
        permission_mode: str | None = None,
    ) -> ClaudeAgentOptions:
        """Construct ClaudeAgentOptions for this workspace."""
        settings = self.load_settings()
        project_cfg = self.load_project_config()
        env = self._build_env(settings)

        use_custom_web = bool(settings.web_profile)
        vision_enabled = self._vision_enabled(project_cfg)

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
        if vision_enabled:
            allowed_tools.extend(DOGENT_VISION_ALLOWED_TOOLS)
            tools.extend(create_dogent_vision_tools(self.paths.root, self))
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

        resolved_permission_mode = permission_mode
        if resolved_permission_mode is None:
            resolved_permission_mode = "default" if can_use_tool else "acceptEdits"

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=str(self.paths.root),
            model=settings.model,
            fallback_model=fallback_model,
            permission_mode=resolved_permission_mode,
            allowed_tools=allowed_tools,
            add_dirs=add_dirs,
            env=env,
            mcp_servers=mcp_servers,
            can_use_tool=can_use_tool,
            hooks=hooks,
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
        profiles = self._read_profiles_section(GLOBAL_LLM_PROFILES_KEY)
        if not profiles:
            return {}
        chosen = profiles.get(profile_name, {})
        if not isinstance(chosen, dict):
            return {}
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

    def _read_template_json(self, name: str) -> Dict[str, Any]:
        template_text = self._read_home_template(name)
        if not template_text:
            return {}
        try:
            parsed = json.loads(template_text)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _read_profiles_section(self, key: str) -> Dict[str, Any]:
        data = self._read_global_config()
        section = data.get(key, {})
        return section if isinstance(section, dict) else {}

    def _load_web_profile(self, profile_name: Optional[str]) -> Dict[str, Any]:
        if not profile_name:
            return {}
        profiles = self._read_profiles_section(GLOBAL_WEB_PROFILES_KEY)
        if not profiles:
            return {}
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

    def _vision_enabled(self, config: Dict[str, Any]) -> bool:
        raw = (config or {}).get("vision_profile")
        if not raw:
            return False
        if isinstance(raw, str) and raw.strip().lower() == "none":
            return False
        return isinstance(raw, str)

    def _ensure_home_bootstrap(self) -> None:
        home_dir = self.paths.global_dir
        if not home_dir.exists():
            home_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.global_config_file.exists():
            default_config = self._default_global_config()
            try:
                self.paths.global_config_file.write_text(
                    json.dumps(default_config, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                self.console.print(
                    f"[cyan]Created default config at {self.paths.global_config_file}. Edit it with your credentials.[/cyan]"
                )
            except PermissionError:
                self.console.print(
                    f"[yellow]Cannot write {self.paths.global_config_file}. Please create it manually.[/yellow]"
                )
        else:
            self._maybe_upgrade_global_config()
        if not self.paths.global_schema_file.exists():
            schema = self._read_home_template("dogent_schema.json")
            if schema:
                try:
                    self.paths.global_schema_file.write_text(schema, encoding="utf-8")
                except PermissionError:
                    self.console.print(
                        f"[yellow]Cannot write {self.paths.global_schema_file}. Please create it manually.[/yellow]"
                    )

    def _maybe_upgrade_global_config(self) -> None:
        data = self._read_json(self.paths.global_config_file)
        if not data or not isinstance(data, dict):
            return
        current_version = str(data.get("version") or "").strip()
        compare = self._compare_versions(current_version, __version__)
        if compare > 0:
            self.console.print(
                "[yellow]"
                f"Config {self.paths.global_config_file} version {current_version} is newer than Dogent {__version__}. "
                "Proceeding with caution."
                "[/yellow]"
            )
            return
        if compare == 0:
            return
        defaults = self._default_global_config()
        merged = self._merge_dicts(defaults, data)
        merged["version"] = __version__
        merged["$schema"] = defaults.get("$schema", "./dogent.schema.json")
        try:
            self.paths.global_config_file.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            self.console.print(
                f"[cyan]Upgraded config at {self.paths.global_config_file} to {__version__}.[/cyan]"
            )
        except PermissionError:
            self.console.print(
                f"[yellow]Cannot upgrade {self.paths.global_config_file}. Please update it manually.[/yellow]"
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
                f"Profile '{profile_name}' in {self.paths.global_config_file} (llm_profiles) still has placeholder credentials. "
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
                f"Web profile '{profile_name}' in {self.paths.global_config_file} (web_profiles) still has placeholder credentials "
                f"(provider={provider or 'unknown'}). Please update it before running web tools."
                "[/yellow]"
            )

    def _warn_if_missing_web_profile(self, profile_name: str) -> None:
        self.console.print(
            "[yellow]"
            f"Web profile '{profile_name}' not found in {self.paths.global_config_file} (web_profiles). "
            "Falling back to native WebSearch/WebFetch."
            "[/yellow]"
        )

    def _compare_versions(self, left: str, right: str) -> int:
        left_tuple = self._version_tuple(left)
        right_tuple = self._version_tuple(right)
        max_len = max(len(left_tuple), len(right_tuple))
        left_tuple += (0,) * (max_len - len(left_tuple))
        right_tuple += (0,) * (max_len - len(right_tuple))
        if left_tuple == right_tuple:
            return 0
        return -1 if left_tuple < right_tuple else 1

    def _version_tuple(self, value: str) -> tuple[int, ...]:
        if not value:
            return ()
        numbers = [int(part) for part in re.findall(r"\d+", value)]
        return tuple(numbers)
