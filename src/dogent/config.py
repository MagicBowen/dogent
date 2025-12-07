"""Configuration loading and persistence for Dogent."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .paths import ensure_dogent_dir


CONFIG_FILENAME = "dogent.json"
LEGACY_CONFIG_FILENAME = ".doc-config.yaml"


@dataclass
class Settings:
    anthropic_base_url: Optional[str] = None
    anthropic_auth_token: Optional[str] = None
    anthropic_model: Optional[str] = None
    anthropic_small_fast_model: Optional[str] = None
    api_timeout_ms: Optional[int] = None
    claude_code_disable_nonessential_traffic: Optional[str] = None
    language: str = "zh"
    default_format: str = "markdown"
    image_dir: str = "images"
    max_section_tokens: int = 2048
    research_provider: Optional[str] = None
    max_budget_usd: Optional[float] = None
    sandbox: Optional[Dict[str, Any]] = field(default_factory=dict)
    allow_web: bool = True  # enable web tools by default
    allow_fs_tools: bool = True

    def require(self) -> None:
        """Raise if required secrets are missing."""
        missing = []
        if not self.anthropic_auth_token:
            missing.append("ANTHROPIC_AUTH_TOKEN")
        model_value = self.anthropic_model or self.anthropic_small_fast_model
        if not model_value:
            missing.append("ANTHROPIC_MODEL (or ANTHROPIC_SMALL_FAST_MODEL)")
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")


def _load_env() -> Dict[str, Any]:
    return {
        "anthropic_base_url": os.getenv("ANTHROPIC_BASE_URL"),
        "anthropic_auth_token": os.getenv("ANTHROPIC_AUTH_TOKEN"),
        "anthropic_model": os.getenv("ANTHROPIC_MODEL"),
        "anthropic_small_fast_model": os.getenv("ANTHROPIC_SMALL_FAST_MODEL"),
        "api_timeout_ms": _as_int(os.getenv("API_TIMEOUT_MS")),
        "claude_code_disable_nonessential_traffic": os.getenv(
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
        ),
        "language": os.getenv("DOC_LANGUAGE") or "zh",
        "default_format": os.getenv("DOC_DEFAULT_FORMAT") or "markdown",
        "image_dir": os.getenv("DOC_IMAGE_DIR") or "images",
        "max_section_tokens": _as_int(os.getenv("DOC_MAX_SECTION_TOKENS")) or 2048,
        "research_provider": os.getenv("DOC_RESEARCH_PROVIDER"),
        "max_budget_usd": _as_float(os.getenv("DOC_MAX_BUDGET_USD")),
    }


def _as_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _as_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_settings(cwd: Path) -> Settings:
    """Load settings from config file then env."""
    env_values = _load_env()
    file_values: Dict[str, Any] = {}
    cfg_dir = ensure_dogent_dir(cwd)
    cfg_path = cfg_dir / CONFIG_FILENAME

    with cfg_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f) or {}
        if isinstance(loaded, dict):
            file_values = loaded

    merged = {**env_values, **file_values}
    settings = Settings(**merged)
    return settings


def write_config(cwd: Path, data: Dict[str, Any]) -> Path:
    """Write project config to .dogent/dogent.json."""
    cfg_dir = ensure_dogent_dir(cwd)
    cfg_path = cfg_dir / CONFIG_FILENAME
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_gitignore_entry(cwd, f"{cfg_dir.name}/{CONFIG_FILENAME}")
    return cfg_path


def ensure_gitignore_entry(cwd: Path, entry: str) -> None:
    """Ensure entry exists in .gitignore (create file if missing)."""
    gitignore = cwd / ".gitignore"
    if gitignore.exists():
        existing = gitignore.read_text(encoding="utf-8").splitlines()
    else:
        existing = []
    if entry not in existing:
        existing.append(entry)
        gitignore.write_text("\n".join(existing) + "\n", encoding="utf-8")
