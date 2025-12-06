"""Image download helper."""

from __future__ import annotations

import httpx
from pathlib import Path
from typing import Optional


def ensure_image_dir(cwd: Path, image_dir: str = "images") -> Path:
    path = cwd / image_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


async def download_image(url: str, cwd: Path, image_dir: str = "images") -> Optional[str]:
    """Download an image to the images directory and return relative path."""
    ensure_image_dir(cwd, image_dir)
    filename = url.split("/")[-1] or "image"
    target = cwd / image_dir / filename
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        target.write_bytes(resp.content)
    return str(Path(image_dir) / filename)
