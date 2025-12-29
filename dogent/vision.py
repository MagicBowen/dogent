from __future__ import annotations

import asyncio
import base64
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from .paths import DogentPaths

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}

DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


def classify_media(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return None


@dataclass(frozen=True)
class VisionProfile:
    name: str
    provider: str
    model: str
    base_url: str
    api_key: str
    options: dict[str, Any]


class VisionAnalysisError(RuntimeError):
    pass


class VisionManager:
    def __init__(self, paths: DogentPaths, console: Console | None = None) -> None:
        self.paths = paths
        self.console = console or Console()

    async def analyze(self, path: Path, media_type: str, profile_name: str | None) -> dict[str, Any]:
        profile = self._load_profile(profile_name)
        if profile.provider == "glm-4.6v":
            client = GLM4VClient(profile)
            return await asyncio.to_thread(client.analyze, path, media_type)
        raise VisionAnalysisError(
            f"Unsupported vision provider '{profile.provider}'. "
            "Update vision_profile in .dogent/dogent.json or ~/.dogent/vision.json."
        )

    def _load_profile(self, profile_name: str | None) -> VisionProfile:
        if not profile_name or not str(profile_name).strip():
            raise VisionAnalysisError(
                "vision_profile is not configured. Set vision_profile in .dogent/dogent.json."
            )
        data = self._read_json(self.paths.global_vision_file)
        if not data:
            raise VisionAnalysisError(
                f"No vision profiles found at {self.paths.global_vision_file}."
            )
        profiles = data.get("profiles") if isinstance(data, dict) else None
        if isinstance(profiles, dict):
            source = profiles
        elif isinstance(data, dict):
            source = data
        else:
            source = {}
        cfg = source.get(profile_name, {})
        if not isinstance(cfg, dict) or not cfg:
            raise VisionAnalysisError(
                f"Vision profile '{profile_name}' not found in {self.paths.global_vision_file}."
            )
        provider = str(cfg.get("provider") or profile_name)
        base_url = str(cfg.get("base_url") or DEFAULT_GLM_BASE_URL)
        model = str(cfg.get("model") or "glm-4.6v")
        api_key = str(cfg.get("api_key") or cfg.get("auth_token") or cfg.get("token") or "")
        if not api_key or "replace" in api_key.lower():
            raise VisionAnalysisError(
                f"Vision profile '{profile_name}' in {self.paths.global_vision_file} "
                "has placeholder credentials. Please update api_key."
            )
        options = {
            key: value
            for key, value in cfg.items()
            if key not in {"provider", "base_url", "model", "api_key", "auth_token", "token"}
        }
        return VisionProfile(
            name=str(profile_name),
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            options=options,
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise VisionAnalysisError(
                f"Failed to parse JSON at {path}. Please fix the file and retry."
            ) from exc


class GLM4VClient:
    def __init__(self, profile: VisionProfile) -> None:
        self.profile = profile

    def analyze(self, path: Path, media_type: str) -> dict[str, Any]:
        payload = self._build_payload(path, media_type)
        response = self._request(payload)
        content = _extract_message_content(response)
        return _parse_json_payload(content)

    def _build_payload(self, path: Path, media_type: str) -> dict[str, Any]:
        if media_type not in {"image", "video"}:
            raise VisionAnalysisError(f"Unsupported media type: {media_type}")
        encoded = _encode_file(path)
        prompt = (
            "Analyze the provided media. Return ONLY valid JSON. "
            "Schema: {\"summary\": string, \"tags\": [string], \"text\": string}. "
            "summary: concise single-paragraph description. "
            "tags: short keywords. "
            "text: OCR/transcript if present, otherwise empty."
        )
        media_key = "image_url" if media_type == "image" else "video_url"
        return {
            "model": self.profile.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {media_key: {"url": encoded}, "type": media_key},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.profile.base_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.profile.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise VisionAnalysisError(
                f"Vision request failed ({exc.code}). {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise VisionAnalysisError(f"Vision request failed: {exc.reason}") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise VisionAnalysisError("Vision API returned invalid JSON.") from exc


def _encode_file(path: Path) -> str:
    raw = path.read_bytes()
    return base64.b64encode(raw).decode("ascii")


def _extract_message_content(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        raise VisionAnalysisError("Vision API response was not a JSON object.")
    if payload.get("error"):
        raise VisionAnalysisError(f"Vision API error: {payload.get('error')}")
    choices = payload.get("choices")
    if not choices or not isinstance(choices, list):
        raise VisionAnalysisError("Vision API returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _parse_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise VisionAnalysisError("Vision output did not contain JSON.")
    snippet = cleaned[start : end + 1]
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise VisionAnalysisError("Vision output was not valid JSON.") from exc
    if not isinstance(data, dict):
        raise VisionAnalysisError("Vision output JSON must be an object.")
    return data
