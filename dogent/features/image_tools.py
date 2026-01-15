from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from claude_agent_sdk import SdkMcpTool, tool

from .image_generation import ImageGenerationError, ImageManager
from ..core.session_log import log_exception

if False:  # pragma: no cover
    from ..config import ConfigManager

DOGENT_IMAGE_ALLOWED_TOOLS = ["mcp__dogent__generate_image"]
DOGENT_IMAGE_TOOL_DISPLAY_NAMES = {
    "mcp__dogent__generate_image": "dogent_generate_image",
}

DEFAULT_IMAGE_SIZE = "1280x1280"


def create_dogent_image_tools(root: Path, config: "ConfigManager") -> list[SdkMcpTool]:
    schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text prompt for image generation.",
            },
            "size": {
                "type": "string",
                "description": "Image size as WIDTHxHEIGHT (default 1280x1280).",
                "default": DEFAULT_IMAGE_SIZE,
            },
            "watermark_enabled": {
                "type": "boolean",
                "description": "Whether to apply watermark (default true).",
                "default": True,
            },
            "output_path": {
                "type": "string",
                "description": "Workspace-relative output file path (optional).",
            },
        },
        "required": ["prompt"],
        "additionalProperties": False,
    }

    image_manager = ImageManager(config.paths, console=config.console)

    @tool("generate_image", "Generate an image from a text prompt.", schema)
    async def generate_image_tool(args: dict[str, Any]) -> dict[str, Any]:
        raw_prompt = str(args.get("prompt") or "").strip()
        if not raw_prompt:
            return _error("Missing required field: prompt")

        raw_size = str(args.get("size") or DEFAULT_IMAGE_SIZE).strip()
        try:
            size = _normalize_size(raw_size)
        except ValueError as exc:
            return _error(str(exc))

        watermark = _normalize_bool(args.get("watermark_enabled"), default=True)
        output_path_raw = str(args.get("output_path") or "").strip()

        project_cfg = config.load_project_config()
        profile_name = project_cfg.get("image_profile")
        if not isinstance(profile_name, str):
            profile_name = None

        try:
            result = await image_manager.generate(
                raw_prompt, size, watermark, profile_name
            )
        except ImageGenerationError as exc:
            log_exception("image_tools", exc)
            return _error(str(exc))

        url = result.get("url")
        if not url:
            return _error("Image generation did not return a URL.")

        try:
            image_bytes, content_type = _download_image(str(url))
        except ImageGenerationError as exc:
            log_exception("image_tools", exc)
            return _error(str(exc))

        try:
            output_path = _resolve_output_path(
                root, output_path_raw, content_type, require_file=True
            )
        except ValueError as exc:
            log_exception("image_tools", exc)
            return _error(str(exc))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_path.write_bytes(image_bytes)
        except OSError as exc:
            log_exception("image_tools", exc)
            return _error(f"Failed to write image file: {exc}")

        payload = {
            "url": str(url),
            "path": _readable_path(root, output_path),
            "content_type": content_type,
        }
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=True)}]}

    return [generate_image_tool]


def _normalize_size(raw: str) -> str:
    if "x" not in raw:
        raise ValueError("size must be formatted as WIDTHxHEIGHT (e.g., 1280x1280)")
    parts = raw.lower().split("x", maxsplit=1)
    if len(parts) != 2:
        raise ValueError("size must be formatted as WIDTHxHEIGHT (e.g., 1280x1280)")
    try:
        width = int(parts[0])
        height = int(parts[1])
    except ValueError as exc:
        raise ValueError("size must be formatted as WIDTHxHEIGHT (e.g., 1280x1280)") from exc
    for value in (width, height):
        if value < 512 or value > 2048:
            raise ValueError("size must be between 512 and 2048 pixels")
        if value % 32 != 0:
            raise ValueError("size values must be multiples of 32")
    return f"{width}x{height}"


def _normalize_bool(raw: Any, *, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        cleaned = raw.strip().lower()
        if cleaned in {"1", "true", "yes", "y", "on"}:
            return True
        if cleaned in {"0", "false", "no", "n", "off"}:
            return False
    return bool(raw)


def _download_image(url: str) -> tuple[bytes, str | None]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise ImageGenerationError(
            f"Image download failed ({exc.code}). {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError(f"Image download failed: {exc.reason}") from exc
    if not data:
        raise ImageGenerationError("Image download returned empty data.")
    return data, content_type


def _resolve_output_path(
    root: Path,
    raw_output_path: str,
    content_type: str | None,
    *,
    require_file: bool,
) -> Path:
    extension = _extension_for_content_type(content_type)
    if raw_output_path:
        path = Path(raw_output_path)
        if path.is_absolute():
            raise ValueError("output_path must be workspace-relative.")
        resolved = (root / path).resolve()
        root_resolved = root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("output_path must stay within the workspace.") from exc
        if resolved.exists() and resolved.is_dir():
            filename = _default_image_name(extension)
            return resolved / filename
        if not resolved.suffix:
            resolved = resolved.with_suffix(extension)
        return resolved

    images_dir = (root / "assets" / "images").resolve()
    filename = _default_image_name(extension)
    output = images_dir / filename
    if require_file:
        return output
    return output


def _default_image_name(extension: str) -> str:
    stamp = int(time.time())
    return f"dogent_image_{stamp}{extension}"


def _extension_for_content_type(content_type: str | None) -> str:
    if not content_type:
        return ".png"
    cleaned = content_type.split(";", maxsplit=1)[0].strip().lower()
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
    }
    if cleaned in mapping:
        return mapping[cleaned]
    guessed = mimetypes.guess_extension(cleaned) if cleaned else None
    if guessed:
        return guessed
    return ".png"


def _readable_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "is_error": True}
