from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import SdkMcpTool, tool
from typing import TYPE_CHECKING
from .vision import VisionAnalysisError, VisionManager, classify_media

if TYPE_CHECKING:
    from ..config import ConfigManager


DOGENT_VISION_ALLOWED_TOOLS = ["mcp__dogent__analyze_media"]
DOGENT_VISION_TOOL_DISPLAY_NAMES = {
    "mcp__dogent__analyze_media": "dogent_analyze_media",
}


def create_dogent_vision_tools(root: Path, config: "ConfigManager") -> list[SdkMcpTool]:
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative media path."},
            "media_type": {
                "type": "string",
                "description": "Optional override: image or video.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    vision_manager = VisionManager(config.paths, console=config.console)

    @tool("analyze_media", "Analyze an image or video file.", schema)
    async def analyze_media_tool(args: dict[str, Any]) -> dict[str, Any]:
        raw_path = str(args.get("path") or "").strip()
        if not raw_path:
            return _error("Missing required field: path")
        requested_type = str(args.get("media_type") or "").strip().lower()

        try:
            path = _resolve_workspace_path(root, raw_path, must_exist=True)
        except ValueError as exc:
            return _error(str(exc))

        media_type = requested_type if requested_type in {"image", "video"} else None
        if media_type is None:
            media_type = classify_media(path)
        if not media_type:
            return _error("Unsupported media type. Use image or video files.")

        project_cfg = config.load_project_config()
        profile_name = project_cfg.get("vision_profile")
        if not isinstance(profile_name, str):
            profile_name = None

        try:
            result = await vision_manager.analyze(path, media_type, profile_name)
        except VisionAnalysisError as exc:
            return _error(str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error(f"Vision analysis failed: {exc}")

        return {"content": [{"type": "text", "text": _format_result(result)}]}

    return [analyze_media_tool]


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


def _format_result(result: dict[str, Any]) -> str:
    return json_dumps(result)


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


def _error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "is_error": True}
