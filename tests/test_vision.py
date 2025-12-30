import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dogent.config import ConfigManager
from dogent.paths import DogentPaths
from dogent.vision_tools import create_dogent_vision_tools
from dogent.vision import GLM4VClient, VisionAnalysisError, VisionManager, classify_media


class VisionManagerTests(unittest.IsolatedAsyncioTestCase):
    def test_classify_media(self) -> None:
        self.assertEqual(classify_media(Path("photo.png")), "image")
        self.assertEqual(classify_media(Path("clip.mp4")), "video")
        self.assertIsNone(classify_media(Path("notes.txt")))

    async def test_missing_profile_fails(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = VisionManager(paths)
            media = Path(tmp) / "photo.png"
            media.write_bytes(b"fake")
            with self.assertRaises(VisionAnalysisError):
                await manager.analyze(media, "image", "glm-4.6v")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_placeholder_key_fails(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            vision_dir = paths.global_dir
            vision_dir.mkdir(parents=True, exist_ok=True)
            paths.global_vision_file.write_text(
                '{"profiles":{"glm-4.6v":{"provider":"glm-4.6v","api_key":"replace-me"}}}',
                encoding="utf-8",
            )
            manager = VisionManager(paths)
            media = Path(tmp) / "photo.png"
            media.write_bytes(b"fake")
            with self.assertRaises(VisionAnalysisError):
                await manager.analyze(media, "image", "glm-4.6v")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_success_parses_json(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            vision_dir = paths.global_dir
            vision_dir.mkdir(parents=True, exist_ok=True)
            paths.global_vision_file.write_text(
                '{"profiles":{"glm-4.6v":{"provider":"glm-4.6v","api_key":"k","model":"glm-4.6v"}}}',
                encoding="utf-8",
            )
            manager = VisionManager(paths)
            media = Path(tmp) / "photo.png"
            media.write_bytes(b"fake")

            response = {
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"ok","tags":["tag"],"text":""}'
                        }
                    }
                ]
            }
            with mock.patch.object(GLM4VClient, "_request", return_value=response):
                result = await manager.analyze(media, "image", "glm-4.6v")
            self.assertEqual(result.get("summary"), "ok")
            self.assertEqual(result.get("tags"), ["tag"])
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class VisionToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_returns_placeholder_error(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            media = paths.root / "photo.png"
            media.write_bytes(b"fake")
            tool = create_dogent_vision_tools(paths.root, config)[0]
            result = await tool.handler({"path": "photo.png"})
            self.assertTrue(result.get("is_error"))
            text = result.get("content")[0]["text"]
            self.assertIn("placeholder", text.lower())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_tool_success_returns_json_text(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            media = paths.root / "photo.png"
            media.write_bytes(b"fake")
            tool = create_dogent_vision_tools(paths.root, config)[0]

            with mock.patch(
                "dogent.vision_tools.VisionManager.analyze", new=mock.AsyncMock()
            ) as analyze:
                analyze.return_value = {"summary": "ok", "tags": [], "text": ""}
                result = await tool.handler({"path": "photo.png"})

            text = result.get("content")[0]["text"]
            payload = json.loads(text)
            self.assertEqual(payload.get("summary"), "ok")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
