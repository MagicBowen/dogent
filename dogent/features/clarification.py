from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from ..config.resources import read_schema_text
from ..core.session_log import log_exception


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


def parse_clarification_payload(payload: Any) -> tuple[ClarificationPayload | None, list[str]]:
    if not isinstance(payload, dict):
        return None, ["Clarification payload must be a JSON object."]
    coerced = _coerce_payload(payload)
    if coerced is not None:
        return coerced, []
    errors = validate_clarification_payload(payload)
    if errors:
        return None, errors
    return None, ["Clarification payload is missing required fields."]


def validate_clarification_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["Clarification payload must be a JSON object."]
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception as exc:
        log_exception("clarification", exc)
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
    if question_text is None:
        question_text = raw.get("header")
    options_raw = raw.get("options", [])
    if isinstance(question_id, (int, float)):
        question_id = str(question_id)
    if question_id is None and isinstance(question_text, str):
        question_id = question_text
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
            label = item.get("label") or item.get("description") or item.get("value")
            value = item.get("value") or label
        else:
            return None
        if not isinstance(label, str) or not label.strip():
            return None
        if not isinstance(value, str) or not value.strip():
            return None
        options.append(ClarificationOption(label=label.strip(), value=value.strip()))
    return options
