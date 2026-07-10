from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

try:
    from importlib.resources.abc import Traversable
except ImportError:
    from importlib.abc import Traversable

from ..config.paths import DogentPaths
from ..config.resources import iter_dir, resource_path
from ..core.session_log import log_exception


_SOURCES = ("workspace", "global", "built-in")
_GENERAL_TEMPLATE_KEY = "general"
_GENERAL_TEMPLATE_NAME = "general"
_SKILL_FILE = "SKILL.md"


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
    description: str = ""


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
            description = content.description if content else ""
            if description:
                lines.append(f"- {info.display_name}: {description}")
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
            path = self.paths.doc_templates_dir / name
            return self._load_template_dir(path, source, name)
        if source == "global":
            path = self.paths.global_templates_dir / name
            return self._load_template_dir(path, source, name)
        if source == "built-in":
            return self._load_builtin(name)
        return None

    def _load_template_dir(
        self, root: Path | Traversable, source: str, name: str
    ) -> Optional[TemplateContent]:
        skill_path = root.joinpath(_SKILL_FILE)
        if not self._is_file(skill_path):
            return None
        raw_skill = self._read_text(skill_path)
        if not raw_skill:
            return None
        _, body_lines = self._split_frontmatter(raw_skill)
        body = self._strip_intro_block("\n".join(body_lines).strip())
        description = self._extract_description(raw_skill)
        output_templates = self._load_markdown_texts(
            root,
            directory_name="templates",
            section_title="Output Template",
        )
        legacy_references = self._load_markdown_texts(
            root,
            directory_name="references",
            section_title="Reference",
        )
        parts = [part for part in [body, *output_templates, *legacy_references] if part]
        content = "\n\n".join(parts).strip()
        if not content:
            return None
        return TemplateContent(
            name=name,
            source=source,
            content=content,
            description=description,
        )

    def _list_dir(self, directory: Path, source: str) -> Iterable[TemplateInfo]:
        if not directory.exists() or not directory.is_dir():
            return []
        entries: list[TemplateInfo] = []
        for path in sorted(directory.iterdir()):
            if not path.is_dir():
                continue
            if path.name.lower() == _GENERAL_TEMPLATE_KEY:
                continue
            if not path.joinpath(_SKILL_FILE).is_file():
                continue
            entries.append(TemplateInfo(name=path.name, source=source, path=path))
        return entries

    def _list_built_in(self) -> list[TemplateInfo]:
        entries: list[TemplateInfo] = []
        for entry in iter_dir("templates"):
            if not entry.is_dir():
                continue
            name = entry.name
            if name == _GENERAL_TEMPLATE_NAME:
                continue
            if not self._is_file(entry.joinpath(_SKILL_FILE)):
                continue
            entries.append(TemplateInfo(name=name, source="built-in", path=entry))
        return entries

    def _load_builtin(self, name: str) -> Optional[TemplateContent]:
        root = resource_path("templates", name)
        if root is None:
            return None
        return self._load_template_dir(root, "built-in", name)

    def _load_general(self) -> Optional[TemplateContent]:
        return self._load_builtin(_GENERAL_TEMPLATE_NAME)

    def _load_markdown_texts(
        self,
        root: Path | Traversable,
        *,
        directory_name: str,
        section_title: str,
    ) -> list[str]:
        source_root = root.joinpath(directory_name)
        if not self._is_dir(source_root):
            return []
        entries: list[tuple[str, str]] = []
        for ref in self._iter_markdown_files(source_root, prefix=directory_name):
            text = self._read_text(ref[1]).strip()
            if not text:
                continue
            label = ref[0]
            entries.append((label, f"## {section_title}: {label}\n\n{text}"))
        return [text for _, text in sorted(entries, key=lambda item: item[0])]

    def _iter_markdown_files(
        self, root: Path | Traversable, *, prefix: str
    ) -> list[tuple[str, Path | Traversable]]:
        entries: list[tuple[str, Path | Traversable]] = []
        try:
            children = sorted(root.iterdir(), key=lambda entry: entry.name)
        except Exception as exc:
            log_exception("doc_templates", exc)
            return []
        for child in children:
            rel = f"{prefix}/{child.name}"
            if self._is_dir(child):
                entries.extend(self._iter_markdown_files(child, prefix=rel))
                continue
            if child.name.endswith(".md") and self._is_file(child):
                entries.append((rel, child))
        return entries

    def _extract_description(self, skill_text: str) -> str:
        frontmatter, _ = self._split_frontmatter(skill_text)
        description = self._extract_frontmatter_value(frontmatter, "description")
        return description

    def _split_frontmatter(self, text: str) -> tuple[list[str], list[str]]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return [], lines
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return lines[1:index], lines[index + 1 :]
        return [], lines

    def _extract_frontmatter_value(self, lines: Iterable[str], key: str) -> str:
        frontmatter_lines = list(lines)
        for index, line in enumerate(frontmatter_lines):
            if ":" not in line:
                continue
            raw_key, value = line.split(":", 1)
            if raw_key.strip().lower() != key.lower():
                continue
            cleaned = value.strip().strip('"').strip("'")
            if cleaned in {"|", "|-", ">", ">+" , ">-"}:
                cleaned = ""
            if cleaned:
                return cleaned
            continued = self._collect_indented_frontmatter_lines(
                frontmatter_lines, start=index + 1
            )
            if continued:
                return " ".join(continued)
        return ""

    def _collect_indented_frontmatter_lines(
        self, lines: list[str], *, start: int
    ) -> list[str]:
        values: list[str] = []
        for index in range(start, len(lines)):
            line = lines[index]
            if not line.strip():
                if values:
                    break
                continue
            if not line.startswith((" ", "\t")):
                break
            cleaned = line.strip().strip('"').strip("'")
            if cleaned:
                values.append(cleaned)
        return values

    def _strip_intro_block(self, text: str) -> str:
        if not text:
            return ""
        lines = text.splitlines()
        intro_index = self._find_intro_heading(lines)
        if intro_index != -1:
            next_section = self._find_next_h2(lines, start=intro_index + 1)
            if next_section != -1:
                return "\n".join(lines[next_section:]).strip()
            return ""
        if len(lines) > 10:
            return "\n".join(lines[10:]).strip()
        return text.strip()

    def _find_intro_heading(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            if line.strip().lower() == "## introduction":
                return index
        return -1

    def _find_next_h2(self, lines: list[str], *, start: int) -> int:
        for index in range(start, len(lines)):
            if lines[index].strip().startswith("## "):
                return index
        return -1

    def _read_text(self, path: Path | Traversable) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            log_exception("doc_templates", exc)
            return ""

    def _is_dir(self, path: Path | Traversable) -> bool:
        try:
            return path.is_dir()
        except Exception as exc:
            log_exception("doc_templates", exc)
            return False

    def _is_file(self, path: Path | Traversable) -> bool:
        try:
            return path.is_file()
        except Exception as exc:
            log_exception("doc_templates", exc)
            return False
