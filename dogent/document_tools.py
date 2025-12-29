from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import SdkMcpTool, tool

from .document_io import (
    DEFAULT_MAX_CHARS,
    convert_document_async,
    export_markdown_async,
    read_document,
)


DOGENT_DOC_ALLOWED_TOOLS = [
    "mcp__dogent__read_document",
    "mcp__dogent__export_document",
    "mcp__dogent__convert_document",
]
DOGENT_DOC_TOOL_DISPLAY_NAMES = {
    "mcp__dogent__read_document": "dogent_read_document",
    "mcp__dogent__export_document": "dogent_export_document",
    "mcp__dogent__convert_document": "dogent_convert_document",
}


def create_dogent_doc_tools(root: Path) -> list[SdkMcpTool]:
    read_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path."},
            "sheet": {"type": "string", "description": "Optional sheet name for XLSX."},
            "max_chars": {
                "type": "integer",
                "description": "Max characters to return.",
                "default": DEFAULT_MAX_CHARS,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    export_schema = {
        "type": "object",
        "properties": {
            "md_path": {
                "type": "string",
                "description": "Workspace-relative Markdown file path.",
            },
            "output_path": {
                "type": "string",
                "description": "Workspace-relative output path ending in .pdf or .docx.",
            },
            "format": {
                "type": "string",
                "description": "Target format: pdf or docx.",
            },
            "title": {
                "type": "string",
                "description": "Optional document title (PDF only).",
            },
        },
        "required": ["md_path", "output_path", "format"],
        "additionalProperties": False,
    }

    convert_schema = {
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Workspace-relative source path (.docx, .pdf, or .md).",
            },
            "output_path": {
                "type": "string",
                "description": "Workspace-relative output path (.docx, .pdf, or .md).",
            },
            "extract_media_dir": {
                "type": "string",
                "description": "Optional directory to extract images when converting DOCX to Markdown.",
            },
        },
        "required": ["input_path", "output_path"],
        "additionalProperties": False,
    }

    @tool("read_document", "Read a document and return text content.", read_schema)
    async def read_document_tool(args: dict[str, Any]) -> dict[str, Any]:
        raw_path = str(args.get("path") or "").strip()
        if not raw_path:
            return _error("Missing required field: path")
        sheet = args.get("sheet")
        max_chars = int(args.get("max_chars") or DEFAULT_MAX_CHARS)
        try:
            path = _resolve_workspace_path(root, raw_path, must_exist=True)
        except ValueError as exc:
            return _error(str(exc))

        result = read_document(path, sheet=str(sheet) if sheet else None, max_chars=max_chars)
        if result.error:
            return _error(result.error)

        lines = [
            f"Path: {_readable_path(root, path)}",
            f"Format: {result.format}",
        ]
        if result.metadata:
            lines.append(f"Metadata: {json.dumps(result.metadata, ensure_ascii=True)}")
        if result.truncated:
            lines.append("Note: content was truncated.")
        lines.append("")
        lines.append(result.content or "(no content)")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    @tool("export_document", "Export a Markdown file to PDF or DOCX.", export_schema)
    async def export_document_tool(args: dict[str, Any]) -> dict[str, Any]:
        raw_md_path = str(args.get("md_path") or "").strip()
        raw_output_path = str(args.get("output_path") or "").strip()
        fmt = str(args.get("format") or "").strip().lower()
        title = str(args.get("title") or "").strip() or None

        if not raw_md_path:
            return _error("Missing required field: md_path")
        if not raw_output_path:
            return _error("Missing required field: output_path")
        if fmt not in {"pdf", "docx"}:
            return _error("format must be 'pdf' or 'docx'")

        try:
            md_path = _resolve_workspace_path(root, raw_md_path, must_exist=True)
            output_path = _resolve_workspace_path(root, raw_output_path, must_exist=False)
        except ValueError as exc:
            return _error(str(exc))

        if md_path.suffix.lower() != ".md":
            return _error("md_path must point to a .md file")
        if output_path.suffix.lower() != f".{fmt}":
            return _error("output_path extension must match format")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            await export_markdown_async(
                md_path,
                output_path=output_path,
                format=fmt,
                title=title,
            )
        except Exception as exc:  # noqa: BLE001
            return _error(f"Export failed: {exc}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Exported {_readable_path(root, md_path)} -> "
                        f"{_readable_path(root, output_path)}"
                    ),
                }
            ]
        }

    @tool(
        "convert_document",
        "Convert between DOCX, PDF, and Markdown files.",
        convert_schema,
    )
    async def convert_document_tool(args: dict[str, Any]) -> dict[str, Any]:
        raw_input_path = str(args.get("input_path") or "").strip()
        raw_output_path = str(args.get("output_path") or "").strip()
        raw_extract_dir = str(args.get("extract_media_dir") or "").strip()

        if not raw_input_path:
            return _error("Missing required field: input_path")
        if not raw_output_path:
            return _error("Missing required field: output_path")

        try:
            input_path = _resolve_workspace_path(root, raw_input_path, must_exist=True)
            output_path = _resolve_workspace_path(root, raw_output_path, must_exist=False)
        except ValueError as exc:
            return _error(str(exc))

        extract_dir = None
        if raw_extract_dir:
            try:
                extract_dir = _resolve_workspace_path(
                    root, raw_extract_dir, must_exist=False
                )
            except ValueError as exc:
                return _error(str(exc))

        try:
            result = await convert_document_async(
                input_path,
                output_path=output_path,
                extract_media_dir=extract_dir,
            )
        except Exception as exc:  # noqa: BLE001
            return _error(f"Conversion failed: {exc}")

        lines = [
            f"Converted {_readable_path(root, input_path)} -> {_readable_path(root, output_path)}",
        ]
        if extract_dir:
            lines.append(f"Extracted media: {_readable_path(root, extract_dir)}")
        if result.notes:
            lines.append("Notes:")
            lines.extend(f"- {note}" for note in result.notes)
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    return [read_document_tool, export_document_tool, convert_document_tool]


def _resolve_workspace_path(root: Path, raw: str, *, must_exist: bool) -> Path:
    path = Path(raw)
    if path.is_absolute():
        raise ValueError("Path must be workspace-relative.")
    resolved = (root / path).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Path must stay within the workspace.") from exc
    if must_exist and not resolved.exists():
        raise ValueError("File does not exist.")
    return resolved


def _readable_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "is_error": True}
