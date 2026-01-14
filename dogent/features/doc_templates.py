from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from ..config.paths import DogentPaths
from ..config.resources import iter_dir, read_template_text
from ..core.session_log import log_exception


_SOURCES = ("workspace", "global", "built-in")
_GENERAL_TEMPLATE_KEY = "general"
_GENERAL_TEMPLATE_FILE = "doc_general"


@dataclass(frozen=True)
class TemplateInfo:
    name: str
    source: str
    path: object

    @property
    def display_name(self) -> str:
        if self.source == "workspace":
            return self.name
        return f"{self.source}:{self.name}"


@dataclass(frozen=True)
class TemplateContent:
    name: str
    source: str
    content: str


class DocumentTemplateManager:
    """Loads and resolves document templates from workspace, global, or built-in sources."""

    def __init__(self, paths: DogentPaths) -> None:
        self.paths = paths

    def list_templates(self) -> list[TemplateInfo]:
        templates: list[TemplateInfo] = []
        templates.extend(self._list_dir(self.paths.doc_templates_dir, "workspace"))
        templates.extend(self._list_dir(self.paths.global_templates_dir, "global"))
        templates.extend(self._list_built_in())
        return templates

    def list_display_names(self) -> list[str]:
        grouped: list[str] = []
        templates = self.list_templates()
        grouped.append(_GENERAL_TEMPLATE_KEY)
        for source in _SOURCES:
            entries = [info.display_name for info in templates if info.source == source]
            grouped.extend(sorted(entries))
        seen: set[str] = set()
        deduped: list[str] = []
        for name in grouped:
            if name not in seen:
                seen.add(name)
                deduped.append(name)
        return deduped

    def names_for_source(self, source: str) -> list[str]:
        return [info.name for info in self.list_templates() if info.source == source]

    def resolve(self, key: Optional[str]) -> Optional[TemplateContent]:
        if not key:
            return None
        cleaned = key.strip()
        if not cleaned:
            return None
        if cleaned.lower() == _GENERAL_TEMPLATE_KEY:
            return self._load_general()

        prefixed = self._parse_prefixed(cleaned)
        if prefixed:
            source, name = prefixed
            return self._load_specific(source, name)
        return self._load_specific("workspace", cleaned)

    def describe_templates(self) -> str:
        """Return a concise list of available templates with introductions."""
        lines: list[str] = []
        for info in self.list_templates():
            content = self._load_specific(info.source, info.name)
            intro = self._extract_intro(content.content) if content else ""
            if intro:
                lines.append(f"- {info.display_name}: {intro}")
            else:
                lines.append(f"- {info.display_name}")
        return "\n".join(lines)

    def _parse_prefixed(self, key: str) -> Optional[tuple[str, str]]:
        if ":" not in key:
            return None
        prefix, name = key.split(":", 1)
        if prefix in {"global", "built-in"} and name:
            return prefix, name
        return None

    def _load_specific(self, source: str, name: str) -> Optional[TemplateContent]:
        if source == "workspace":
            path = self.paths.doc_templates_dir / f"{name}.md"
            return self._load_path(path, source, name)
        if source == "global":
            path = self.paths.global_templates_dir / f"{name}.md"
            return self._load_path(path, source, name)
        if source == "built-in":
            return self._load_builtin(name)
        return None

    def _load_path(
        self, path: Path, source: str, name: str
    ) -> Optional[TemplateContent]:
        if not path.exists() or not path.is_file():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            log_exception("doc_templates", exc)
            return None
        return TemplateContent(name=name, source=source, content=text.strip())

    def _list_dir(self, directory: Path, source: str) -> Iterable[TemplateInfo]:
        if not directory.exists() or not directory.is_dir():
            return []
        entries: list[TemplateInfo] = []
        for path in sorted(directory.glob("*.md")):
            if path.stem.lower() == _GENERAL_TEMPLATE_KEY:
                continue
            entries.append(TemplateInfo(name=path.stem, source=source, path=path))
        return entries

    def _list_built_in(self) -> list[TemplateInfo]:
        entries: list[TemplateInfo] = []
        for entry in iter_dir("templates"):
            if entry.is_dir() or not entry.name.endswith(".md"):
                continue
            name = Path(entry.name).stem
            if name == _GENERAL_TEMPLATE_FILE:
                continue
            entries.append(TemplateInfo(name=name, source="built-in", path=entry))
        return entries

    def _load_builtin(self, name: str) -> Optional[TemplateContent]:
        text = read_template_text(f"{name}.md")
        if not text:
            return None
        return TemplateContent(name=name, source="built-in", content=text.strip())

    def _load_general(self) -> Optional[TemplateContent]:
        return self._load_builtin(_GENERAL_TEMPLATE_FILE)

    def _extract_intro(self, content: str) -> str:
        lines = content.splitlines()
        capture = False
        captured: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## ") and capture:
                break
            if stripped == "## Introduction":
                capture = True
                continue
            if capture and stripped:
                captured.append(stripped)
        if captured:
            return " ".join(captured).strip()
        fallback = [line.strip() for line in lines[:5] if line.strip()]
        return " ".join(fallback).strip()
