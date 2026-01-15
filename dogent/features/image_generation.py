from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from ..config.paths import DogentPaths
from ..core.session_log import log_exception

DEFAULT_GLM_IMAGE_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"


@dataclass(frozen=True)
class ImageProfile:
    name: str
    provider: str
    model: str
    base_url: str
    api_key: str
    options: dict[str, Any]


class ImageGenerationError(RuntimeError):
    pass


class ImageManager:
    def __init__(self, paths: DogentPaths, console: Console | None = None) -> None:
        self.paths = paths
        self.console = console or Console()

    async def generate(
        self,
        prompt: str,
        size: str,
        watermark_enabled: bool,
        profile_name: str | None,
    ) -> dict[str, Any]:
        profile = self._load_profile(profile_name)
        if profile.provider == "glm-image":
            client = GLMImageClient(profile)
            return await asyncio.to_thread(client.generate, prompt, size, watermark_enabled)
        raise ImageGenerationError(
            f"Unsupported image provider '{profile.provider}'. "
            "Update image_profile in .dogent/dogent.json or ~/.dogent/dogent.json."
        )

    def _load_profile(self, profile_name: str | None) -> ImageProfile:
        if not profile_name or not str(profile_name).strip():
            raise ImageGenerationError(
                "image_profile is not configured. Set image_profile in .dogent/dogent.json."
            )
        data = self._read_json(self.paths.global_config_file)
        if not data:
            raise ImageGenerationError(
                f"No image profiles found at {self.paths.global_config_file} (image_profiles)."
            )
        source = data.get("image_profiles") if isinstance(data, dict) else {}
        if not isinstance(source, dict):
            source = {}
        cfg = source.get(profile_name, {})
        if not isinstance(cfg, dict) or not cfg:
            raise ImageGenerationError(
                f"Image profile '{profile_name}' not found in {self.paths.global_config_file} (image_profiles)."
            )
        provider = str(cfg.get("provider") or profile_name)
        base_url = str(cfg.get("base_url") or DEFAULT_GLM_IMAGE_BASE_URL)
        model = str(cfg.get("model") or "glm-image")
        api_key = str(cfg.get("api_key") or cfg.get("auth_token") or cfg.get("token") or "")
        if not api_key or "replace" in api_key.lower():
            raise ImageGenerationError(
                f"Image profile '{profile_name}' in {self.paths.global_config_file} (image_profiles) "
                "has placeholder credentials. Please update api_key."
            )
        options = {
            key: value
            for key, value in cfg.items()
            if key not in {"provider", "base_url", "model", "api_key", "auth_token", "token"}
        }
        return ImageProfile(
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
            log_exception("image_generation", exc)
            raise ImageGenerationError(
                f"Failed to parse JSON at {path}. Please fix the file and retry."
            ) from exc


class GLMImageClient:
    def __init__(self, profile: ImageProfile) -> None:
        self.profile = profile

    def generate(self, prompt: str, size: str, watermark_enabled: bool) -> dict[str, Any]:
        payload = self._build_payload(prompt, size, watermark_enabled)
        response = self._request(payload)
        return _parse_generation_response(response)

    def _build_payload(self, prompt: str, size: str, watermark_enabled: bool) -> dict[str, Any]:
        return {
            "model": self.profile.model,
            "prompt": prompt,
            "size": size,
            "watermark_enabled": watermark_enabled,
        }

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        request = urllib.request.Request(
            self.profile.base_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.profile.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            log_exception("image_generation", exc)
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise ImageGenerationError(
                f"Image generation request failed ({exc.code}). {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            log_exception("image_generation", exc)
            raise ImageGenerationError(f"Image generation request failed: {exc.reason}") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            log_exception("image_generation", exc)
            raise ImageGenerationError("Image generation API returned invalid JSON.") from exc


def _parse_generation_response(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ImageGenerationError("Image generation response was not a JSON object.")
    if payload.get("error"):
        raise ImageGenerationError(f"Image generation API error: {payload.get('error')}")
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ImageGenerationError("Image generation API returned no images.")
    first = data[0] if isinstance(data[0], dict) else {}
    url = first.get("url") if isinstance(first, dict) else None
    if not url:
        raise ImageGenerationError("Image generation API returned no image URL.")
    return {
        "url": str(url),
        "raw": payload,
    }
