from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


OUTLINE_EDIT_JSON_TAG = "[[DOGENT_OUTLINE_EDIT_JSON]]"


@dataclass(frozen=True)
class OutlineEditPayload:
    title: str
    outline_text: str


def extract_outline_edit_payload(text: str) -> tuple[OutlineEditPayload | None, list[str]]:
    tagged, remainder = _split_tagged_payload_text(text, OUTLINE_EDIT_JSON_TAG)
    if not tagged:
        return None, []
    if not remainder:
        return None, ["No JSON payload found after outline edit tag."]
    try:
        raw_payload = json.loads(remainder)
    except Exception:
        return None, ["Outline edit payload is not valid JSON."]
    if not isinstance(raw_payload, dict):
        return None, ["Outline edit payload must be a JSON object."]
    payload = _coerce_payload(raw_payload)
    if payload is not None:
        return payload, []
    return None, ["Outline edit payload is missing required fields."]


def has_outline_edit_tag(text: str) -> bool:
    tagged, _ = _split_tagged_payload_text(text, OUTLINE_EDIT_JSON_TAG)
    return tagged


def _split_tagged_payload_text(text: str, tag: str) -> tuple[bool, str]:
    lines = text.splitlines()

    def _first_non_empty(source: list[str]) -> tuple[int, str]:
        for idx, line in enumerate(source):
            if line.strip():
                return idx, line.strip()
        return -1, ""

    def _strip_outer_fence(source: list[str]) -> tuple[list[str], bool]:
        idx, line = _first_non_empty(source)
        if idx == -1 or not line.startswith("```"):
            return source, False
        end = None
        for j in range(idx + 1, len(source)):
            if source[j].strip() == "```":
                end = j
                break
        inner = source[idx + 1 : end] if end is not None else source[idx + 1 :]
        return inner, True

    content_lines, _ = _strip_outer_fence(lines)
    first_index, first_line = _first_non_empty(content_lines)
    if first_index == -1 or first_line != tag:
        return False, ""
    remainder_lines = content_lines[first_index + 1 :]
    remainder_lines, _ = _strip_outer_fence(remainder_lines)
    remainder = "\n".join(remainder_lines).strip()
    return True, remainder


def _coerce_payload(payload: dict[str, Any]) -> OutlineEditPayload | None:
    if payload.get("response_type") != "outline_edit":
        return None
    title = payload.get("title")
    outline_text = payload.get("outline_text")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(outline_text, str) or not outline_text.strip():
        return None
    return OutlineEditPayload(title=title.strip(), outline_text=outline_text)
