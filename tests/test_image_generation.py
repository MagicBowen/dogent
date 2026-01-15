import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.features.image_generation import (
    GLMImageClient,
    ImageGenerationError,
    ImageManager,
)
from dogent.features.image_tools import create_dogent_image_tools


class ImageManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_profile_fails(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ImageManager(paths)
            with self.assertRaises(ImageGenerationError):
                await manager.generate("prompt", "1280x1280", True, "glm-image")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_placeholder_key_fails(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.global_dir.mkdir(parents=True, exist_ok=True)
            paths.global_config_file.write_text(
                '{"image_profiles":{"glm-image":{"provider":"glm-image","api_key":"replace-me"}}}',
                encoding="utf-8",
            )
            manager = ImageManager(paths)
            with self.assertRaises(ImageGenerationError):
                await manager.generate("prompt", "1280x1280", True, "glm-image")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_success_parses_response(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.global_dir.mkdir(parents=True, exist_ok=True)
            paths.global_config_file.write_text(
                '{"image_profiles":{"glm-image":{"provider":"glm-image","api_key":"k","model":"glm-image"}}}',
                encoding="utf-8",
            )
            manager = ImageManager(paths)
            response = {"data": [{"url": "https://example.com/image.png"}]}
            with mock.patch.object(GLMImageClient, "_request", return_value=response):
                result = await manager.generate("prompt", "1280x1280", True, "glm-image")
            self.assertEqual(result.get("url"), "https://example.com/image.png")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class ImageToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_validates_size(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            tool = create_dogent_image_tools(paths.root, config)[0]
            result = await tool.handler({"prompt": "hello", "size": "bad"})
            self.assertTrue(result.get("is_error"))
            self.assertIn("size must be formatted", result.get("content")[0]["text"].lower())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_tool_saves_default_path(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"image_profile": "glm-image"}),
                encoding="utf-8",
            )
            config = ConfigManager(paths)
            tool = create_dogent_image_tools(paths.root, config)[0]
            with mock.patch(
                "dogent.features.image_tools.ImageManager.generate", new=mock.AsyncMock()
            ) as generate, mock.patch(
                "dogent.features.image_tools._download_image", return_value=(b"png", "image/png")
            ), mock.patch(
                "dogent.features.image_tools.time.time", return_value=123456
            ):
                generate.return_value = {"url": "https://example.com/image.png"}
                result = await tool.handler({"prompt": "hello"})

            payload = json.loads(result.get("content")[0]["text"])
            self.assertEqual(payload.get("path"), "assets/images/dogent_image_123456.png")
            saved_path = paths.root / payload.get("path")
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.read_bytes(), b"png")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
