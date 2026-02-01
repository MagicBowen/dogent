from __future__ import annotations

from typing import Any

from claude_agent_sdk import SdkMcpTool, tool


DOGENT_UI_ALLOWED_TOOLS = ["mcp__dogent__ui_request"]
DOGENT_UI_TOOL_DISPLAY_NAMES = {
    "mcp__dogent__ui_request": "dogent_ui_request",
}


def create_dogent_ui_tools() -> list[SdkMcpTool]:
    option_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["label", "value"],
        "properties": {
            "label": {"type": "string", "minLength": 1},
            "value": {"type": "string", "minLength": 1},
        },
    }
    question_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "question", "options"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "question": {"type": "string", "minLength": 1},
            "options": {"type": "array", "items": option_schema},
            "recommended": {"type": ["string", "null"]},
            "allow_freeform": {"type": "boolean"},
            "placeholder": {"type": "string"},
        },
    }
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["response_type", "title"],
        "properties": {
            "response_type": {
                "type": "string",
                "enum": ["clarification", "outline_edit"],
                "description": "UI request type.",
            },
            "title": {"type": "string", "minLength": 1},
            "preface": {"type": "string"},
            "questions": {
                "type": "array",
                "minItems": 1,
                "items": question_schema,
            },
            "outline_text": {"type": "string"},
        },
    }

    @tool(
        "ui_request",
        "Request Dogent UI interaction for clarification or outline editing.",
        schema,
    )
    async def ui_request_tool(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "UI request received. Awaiting user input.",
                }
            ]
        }

    return [ui_request_tool]
