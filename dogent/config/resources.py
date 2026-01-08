from __future__ import annotations

from importlib import resources
from importlib.abc import Traversable
from typing import Iterable, Optional

RESOURCES_DIR = "resources"
PROMPTS_DIR = "prompts"
SCHEMA_DIR = "schema"
TEMPLATES_DIR = "templates"


def resource_path(*parts: str) -> Optional[Traversable]:
    try:
        data = resources.files("dogent")
    except Exception:
        return None
    for part in parts:
        data = data.joinpath(part)
    return data


def read_text(*parts: str) -> str:
    data = resource_path(*parts)
    if not data:
        return ""
    try:
        return data.read_text(encoding="utf-8")
    except Exception:
        return ""


def iter_dir(*parts: str) -> Iterable[Traversable]:
    root = resource_path(*parts)
    if not root:
        return []
    try:
        return list(root.iterdir())
    except Exception:
        return []


def read_config_text(name: str) -> str:
    return read_text(RESOURCES_DIR, name)


def read_prompt_text(name: str) -> str:
    return read_text(PROMPTS_DIR, name)


def read_template_text(name: str) -> str:
    return read_text(TEMPLATES_DIR, name)


def read_schema_text(scope: Optional[str], name: str) -> str:
    if scope:
        return read_text(SCHEMA_DIR, scope, name)
    return read_text(SCHEMA_DIR, name)
