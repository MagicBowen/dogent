from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from ..config.resources import read_schema_text

CLARIFICATION_JSON_TAG = "[[DOGENT_CLARIFICATION_JSON]]"


@dataclass(frozen=True)
class ClarificationOption:
    label: str
    value: str


@dataclass(frozen=True)
class ClarificationQuestion:
    question_id: str
    question: str
    options: list[ClarificationOption]
    recommended: str | None
    allow_freeform: bool
    placeholder: str | None


@dataclass(frozen=True)
class ClarificationPayload:
    title: str
    preface: str | None
    questions: list[ClarificationQuestion]


def extract_clarification_payload(text: str) -> tuple[ClarificationPayload | None, list[str]]:
    tagged, remainder = _split_tagged_payload_text(text, CLARIFICATION_JSON_TAG)
    if not tagged:
        return None, []
    if not remainder:
        return None, ["No JSON payload found after clarification tag."]
    try:
        raw_payload = json.loads(remainder)
    except Exception:
        return None, ["Clarification payload is not valid JSON."]
    if not isinstance(raw_payload, dict):
        return None, ["Clarification payload must be a JSON object."]
    payload = _coerce_payload(raw_payload)
    if payload is not None:
        return payload, []
    errors = validate_clarification_payload(raw_payload)
    if errors:
        return None, errors
    return None, ["Clarification payload is missing required fields."]


def validate_clarification_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["Clarification payload must be a JSON object."]
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return ["jsonschema is not available to validate clarification payload."]
    schema = _load_schema()
    validator = Draft7Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.path)):
        path = ".".join(str(part) for part in error.path)
        prefix = f"{path}: " if path else ""
        errors.append(prefix + error.message)
    return errors


def recommended_index(question: ClarificationQuestion) -> int:
    if question.recommended:
        for idx, option in enumerate(question.options):
            if option.value == question.recommended:
                return idx
    return 0


def has_clarification_tag(text: str) -> bool:
    tagged, _ = _split_tagged_payload_text(text, CLARIFICATION_JSON_TAG)
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


def _load_schema() -> dict[str, Any]:
    text = read_schema_text(None, "clarification.schema.json")
    return json.loads(text)


def _coerce_payload(payload: dict[str, Any]) -> ClarificationPayload | None:
    response_type = payload.get("response_type")
    if response_type != "clarification":
        return None
    title = payload.get("title")
    questions_raw = payload.get("questions")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(questions_raw, list) or not questions_raw:
        return None
    preface = payload.get("preface")
    if preface is not None and not isinstance(preface, str):
        preface = None
    questions: list[ClarificationQuestion] = []
    for item in questions_raw:
        question = _coerce_question(item)
        if question is None:
            return None
        questions.append(question)
    return ClarificationPayload(
        title=title.strip(),
        preface=preface.strip() if isinstance(preface, str) and preface.strip() else None,
        questions=questions,
    )


def _coerce_question(raw: Any) -> ClarificationQuestion | None:
    if not isinstance(raw, dict):
        return None
    question_id = raw.get("id")
    if question_id is None:
        question_id = raw.get("question_id")
    question_text = raw.get("question")
    if question_text is None:
        question_text = raw.get("prompt")
    options_raw = raw.get("options", [])
    if isinstance(question_id, (int, float)):
        question_id = str(question_id)
    if not isinstance(question_id, str) or not question_id.strip():
        return None
    if not isinstance(question_text, str) or not question_text.strip():
        return None
    if not isinstance(options_raw, list):
        return None
    options = _coerce_options(options_raw)
    if options is None:
        return None
    recommended = raw.get("recommended")
    if isinstance(recommended, int):
        if 0 <= recommended < len(options):
            recommended = options[recommended].value
        else:
            recommended = None
    elif isinstance(recommended, dict):
        recommended = recommended.get("value") or recommended.get("label")
    if isinstance(recommended, str):
        recommended = recommended.strip() or None
    elif recommended is not None:
        recommended = None
    allow_freeform = bool(raw.get("allow_freeform", False))
    placeholder = raw.get("placeholder")
    if placeholder is not None and not isinstance(placeholder, str):
        placeholder = None
    return ClarificationQuestion(
        question_id=question_id.strip(),
        question=question_text.strip(),
        options=options,
        recommended=recommended,
        allow_freeform=allow_freeform,
        placeholder=placeholder.strip() if isinstance(placeholder, str) and placeholder.strip() else None,
    )


def _coerce_options(raw: Iterable[Any]) -> list[ClarificationOption] | None:
    options: list[ClarificationOption] = []
    for item in raw:
        if isinstance(item, str):
            label = item
            value = item
        elif isinstance(item, dict):
            label = item.get("label")
            value = item.get("value") or label
        else:
            return None
        if not isinstance(label, str) or not label.strip():
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        options.append(ClarificationOption(label=label.strip(), value=value.strip()))
    return options
