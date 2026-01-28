from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .input import Document, Lexer, pygments_token_to_classname

try:
    from pygments.lexers import get_lexer_by_name  # type: ignore
    from pygments.util import ClassNotFound  # type: ignore
    from pygments.styles.monokai import MonokaiStyle  # type: ignore
except Exception:  # pragma: no cover - optional pygments
    get_lexer_by_name = None  # type: ignore
    ClassNotFound = Exception  # type: ignore
    MonokaiStyle = None  # type: ignore


@dataclass(frozen=True)
class MultilineEditRequest:
    text: str


@dataclass(frozen=True)
class EditorOutcome:
    action: str
    text: str
    saved_path: Path | None = None


@dataclass(frozen=True)
class EditorAnswer:
    text: str
    saved_path: Path | None = None


_MATH_BLOCK_RE = re.compile(r"(?s)\$\$(.+?)\$\$")
_MATH_INLINE_RE = re.compile(r"(?s)(?<!\$)\$[^$\n]+\$(?!\$)")
_BACKTICK_RE = re.compile(r"`+")


def mark_math_for_preview(text: str) -> str:
    def block_sub(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        return f"\n\n```math\n{inner}\n```\n\n"

    text = _MATH_BLOCK_RE.sub(block_sub, text)
    parts = re.split(r"(`[^`]*`)", text)
    for idx in range(0, len(parts), 2):
        parts[idx] = _MATH_INLINE_RE.sub(
            lambda m: f"`[math] {m.group(0)[1:-1].strip()} [/math]`",
            parts[idx],
        )
    return "".join(parts)


def wrap_markdown_code_block(text: str, *, language: str = "markdown") -> str:
    max_run = 0
    for match in _BACKTICK_RE.finditer(text):
        run_len = len(match.group(0))
        if run_len > max_run:
            max_run = run_len
    fence = "`" * max(3, max_run + 1)
    body = text.rstrip("\n")
    return f"{fence}{language}\n{body}\n{fence}"


def indent_block(text: str, prefix: str) -> str:
    lines = text.splitlines() or [""]
    return "\n".join(prefix + line if line else prefix for line in lines)


def resolve_save_path(root: Path, path_text: str) -> Path:
    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate


def format_save_error_message(
    save_path: Path,
    exc: OSError,
    *,
    path_text: str | None = None,
    root: Path | None = None,
) -> str:
    display_path = str(save_path)
    if root is not None:
        with suppress(ValueError):
            display_path = str(save_path.relative_to(root))
    reason = exc.strerror or str(exc)
    if reason:
        first_line = f"Could not save to {display_path}: {reason}."
    else:
        first_line = f"Could not save to {display_path}."
    lines = [first_line]
    if path_text and path_text.startswith("/"):
        lines.append(
            "Paths starting with '/' are absolute. Try a workspace-relative path "
            "(e.g. draft/doc.md) or a home path (~/draft/doc.md)."
        )
    else:
        lines.append("Check that the directory exists and is writable.")
    lines.append("Press Enter or Esc to continue.")
    return "\n".join(lines)


class SimpleMarkdownLexer(Lexer):
    RE_INLINE_CODE = re.compile(r"`[^`]+`")
    RE_INLINE_MATH = re.compile(r"(?<!\$)\$[^$\n]+\$(?!\$)")
    RE_STRONG = re.compile(r"\*\*[^*]+\*\*")
    RE_EM = re.compile(r"(?<!\*)\*[^*]+\*(?!\*)")
    RE_TASK = re.compile(r"^(\s*[-*]\s+)(\[(?: |x|X)\])(\s+)(.*)$")
    RE_HEADING = re.compile(r"^(#{1,6})\s+.*$")
    RE_QUOTE = re.compile(r"^\s*>\s+.*$")
    RE_RULE = re.compile(r"^(?:-{3,}|_{3,}|\*{3,})$")

    def lex_document(self, document: Document) -> Callable[[int], list[tuple[str, str]]]:
        lines = document.lines
        styled: list[list[tuple[str, str]]] = []
        in_fence = False
        fence_lexer = None
        in_math_block = False

        def apply_regex(
            segments: list[tuple[str, str]],
            regex: re.Pattern[str],
            style: str,
            *,
            allowed_style: str = "class:md.text",
        ) -> list[tuple[str, str]]:
            out: list[tuple[str, str]] = []
            for seg_style, text in segments:
                if seg_style != allowed_style:
                    out.append((seg_style, text))
                    continue
                last = 0
                for match in regex.finditer(text):
                    start, end = match.span()
                    if start > last:
                        out.append((seg_style, text[last:start]))
                    out.append((style, text[start:end]))
                    last = end
                if last < len(text):
                    out.append((seg_style, text[last:]))
            return out

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_fence:
                    in_fence = False
                    fence_lexer = None
                else:
                    in_fence = True
                    fence_lexer = None
                    tokens = stripped[3:].strip().split()
                    lang = tokens[0].lower() if tokens else ""
                    if lang and get_lexer_by_name is not None:
                        with suppress(Exception):
                            try:
                                fence_lexer = get_lexer_by_name(lang)
                            except ClassNotFound:
                                fence_lexer = None
                styled.append([("class:md.fence", line)])
                continue
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
                styled.append([("class:md.mathblock", line)])
                continue
            if stripped == "$$":
                in_math_block = not in_math_block
                styled.append([("class:md.mathblock", line)])
                continue
            if in_math_block:
                styled.append([("class:md.mathblock", line)])
                continue
            if in_fence:
                if fence_lexer and pygments_token_to_classname:
                    segments: list[tuple[str, str]] = []
                    for token, value in fence_lexer.get_tokens(line):
                        class_name = pygments_token_to_classname(token)
                        if class_name:
                            style = f"class:md.codeblock class:{class_name}"
                        else:
                            style = "class:md.codeblock"
                        segments.append((style, value))
                    styled.append(segments or [("class:md.codeblock", line)])
                else:
                    styled.append([("class:md.codeblock", line)])
                continue
            if self.RE_HEADING.match(line):
                styled.append([("class:md.heading", line)])
                continue
            if self.RE_RULE.match(stripped):
                styled.append([("class:md.rule", line)])
                continue
            if self.RE_QUOTE.match(line):
                styled.append([("class:md.quote", line)])
                continue

            task_match = self.RE_TASK.match(line)
            if task_match:
                prefix, box, space, rest = task_match.groups()
                styled.append(
                    [
                        ("class:md.text", prefix),
                        ("class:md.task", box),
                        ("class:md.text", space),
                        ("class:md.text", rest),
                    ]
                )
                continue

            if "|" in line:
                segments = [
                    ("class:md.pipe" if ch == "|" else "class:md.text", ch)
                    for ch in line
                ]
            else:
                segments = [("class:md.text", line)]

            segments = apply_regex(segments, self.RE_INLINE_CODE, "class:md.inlinecode")
            segments = apply_regex(segments, self.RE_INLINE_MATH, "class:md.inlinemath")
            segments = apply_regex(segments, self.RE_STRONG, "class:md.strong")
            segments = apply_regex(segments, self.RE_EM, "class:md.em")
            styled.append(segments)

        def lex_line(i: int) -> list[tuple[str, str]]:
            if i < len(styled):
                return styled[i]
            return [("class:md.text", "")]

        return lex_line
