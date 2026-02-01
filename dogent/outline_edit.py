from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutlineEditPayload:
    title: str
    outline_text: str


def parse_outline_edit_payload(payload: Any) -> tuple[OutlineEditPayload | None, list[str]]:
    if not isinstance(payload, dict):
        return None, ["Outline edit payload must be a JSON object."]
    coerced = _coerce_payload(payload)
    if coerced is not None:
        return coerced, []
    return None, ["Outline edit payload is missing required fields."]


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
