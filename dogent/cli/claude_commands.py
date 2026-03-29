from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from ..core.session_log import log_exception


@dataclass(frozen=True)
class ClaudeCommandSpec:
    name: str
    canonical: str
    description: str


def load_claude_commands(
    project_root: Path, *, user_root: Optional[Path] = None
) -> list[ClaudeCommandSpec]:
    specs: dict[str, ClaudeCommandSpec] = {}
    user_dir = (user_root or Path.home()) / ".claude"
    for spec in _load_command_specs(user_dir, namespace="claude", include_skills=False):
        specs[spec.name] = spec
    for spec in _load_command_specs(
        project_root / ".claude", namespace="claude", include_skills=True
    ):
        specs[spec.name] = spec
    for spec in _load_command_specs(
        project_root / ".dogent", namespace="dogent", include_skills=True
    ):
        specs[spec.name] = spec
    return list(specs.values())


def load_plugin_commands(plugin_roots: Iterable[Path]) -> list[ClaudeCommandSpec]:
    specs: list[ClaudeCommandSpec] = []
    home = Path.home()
    dogent_plugins_root = (home / ".dogent" / "plugins").resolve()
    claude_plugins_root = (home / ".claude" / "plugins").resolve()
    for root in plugin_roots:
        resolved_root = root.resolve()
        plugin_name = _plugin_name(root)
        if not plugin_name:
            continue
        commands_dir = root / "commands"
        for path in _iter_command_files(commands_dir):
            canonical = f"/{plugin_name}:{path.stem}"
            if _is_under(resolved_root, dogent_plugins_root):
                name = canonical
            elif _is_under(resolved_root, claude_plugins_root):
                name = f"/claude:{plugin_name}:{path.stem}"
            else:
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


def _iter_skill_files(skills_dir: Path) -> Iterable[Path]:
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []
    return sorted(skills_dir.rglob("SKILL.md"))


def _load_command_specs(
    root: Path, *, namespace: str, include_skills: bool
) -> list[ClaudeCommandSpec]:
    specs: list[ClaudeCommandSpec] = []
    commands_dir = root / "commands"
    for path in _iter_command_files(commands_dir):
        command_name = path.stem
        specs.append(_build_command_spec(path, namespace=namespace, command_name=command_name))
    if not include_skills:
        return specs
    skills_dir = root / "skills"
    for path in _iter_skill_files(skills_dir):
        command_name = _skill_command_name(skills_dir, path)
        if not command_name:
            continue
        specs.append(_build_command_spec(path, namespace=namespace, command_name=command_name))
    return specs


def _build_command_spec(
    path: Path, *, namespace: str, command_name: str
) -> ClaudeCommandSpec:
    canonical = f"/{command_name}"
    name = f"/{namespace}:{command_name}"
    description = _command_description(path)
    return ClaudeCommandSpec(name=name, canonical=canonical, description=description)


def _skill_command_name(skills_dir: Path, path: Path) -> str:
    try:
        relative = path.relative_to(skills_dir)
    except Exception:
        return path.parent.name
    parts = list(relative.parts[:-1])
    cleaned = [part.strip() for part in parts if part.strip()]
    return ":".join(cleaned)


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
    except Exception as exc:
        log_exception("cli.commands", exc)
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
        except json.JSONDecodeError as exc:
            log_exception("cli.commands", exc)
            data = {}
        if isinstance(data, dict):
            name = str(data.get("name") or "").strip()
            if name:
                return name
    return root.name


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except Exception:
        return False
