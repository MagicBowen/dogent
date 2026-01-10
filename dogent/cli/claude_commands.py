from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class ClaudeCommandSpec:
    name: str
    canonical: str
    description: str


def load_claude_commands(
    project_root: Path, *, user_root: Optional[Path] = None
) -> list[ClaudeCommandSpec]:
    specs: dict[str, ClaudeCommandSpec] = {}
    user_dir = (user_root or Path.home()) / ".claude" / "commands"
    project_dir = project_root / ".claude" / "commands"
    for commands_dir in (user_dir, project_dir):
        for path in _iter_command_files(commands_dir):
            canonical = f"/{path.stem}"
            name = f"/claude:{path.stem}"
            description = _command_description(path)
            specs[name] = ClaudeCommandSpec(
                name=name, canonical=canonical, description=description
            )
    return list(specs.values())


def load_plugin_commands(plugin_roots: Iterable[Path]) -> list[ClaudeCommandSpec]:
    specs: list[ClaudeCommandSpec] = []
    for root in plugin_roots:
        plugin_name = _plugin_name(root)
        if not plugin_name:
            continue
        commands_dir = root / "commands"
        for path in _iter_command_files(commands_dir):
            canonical = f"/{plugin_name}:{path.stem}"
            name = f"/claude:{plugin_name}:{path.stem}"
            description = _command_description(path)
            specs.append(
                ClaudeCommandSpec(name=name, canonical=canonical, description=description)
            )
    return specs


def _iter_command_files(commands_dir: Path) -> Iterable[Path]:
    if not commands_dir.exists() or not commands_dir.is_dir():
        return []
    return sorted(commands_dir.rglob("*.md"))


def _command_description(path: Path) -> str:
    text = _read_text(path)
    if not text:
        return "Claude command"
    frontmatter, body = _split_frontmatter(text)
    description = _extract_description(frontmatter)
    if not description:
        description = _first_non_empty_line(body)
    return description or "Claude command"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return lines[1:idx], lines[idx + 1 :]
    return [], lines


def _extract_description(frontmatter: Iterable[str]) -> str:
    for line in frontmatter:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() != "description":
            continue
        cleaned = value.strip().strip('"').strip("'")
        if cleaned:
            return cleaned
    return ""


def _first_non_empty_line(lines: Iterable[str]) -> str:
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def _plugin_name(root: Path) -> str:
    manifest = root / ".claude-plugin" / "plugin.json"
    raw = _read_text(manifest)
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            name = str(data.get("name") or "").strip()
            if name:
                return name
    return root.name
