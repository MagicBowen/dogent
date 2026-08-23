import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.features.vision_tools import create_dogent_vision_tools
from dogent.features.vision import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekVisionClient,
    GLM4VClient,
    VisionAnalysisError,
    VisionManager,
    VisionProfile,
    classify_media,
)


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
            paths.global_config_file.write_text(
                '{"vision_profiles":{"glm-4.6v":{"provider":"glm-4.6v","api_key":"replace-me"}}}',
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
            paths.global_config_file.write_text(
                '{"vision_profiles":{"glm-4.6v":{"provider":"glm-4.6v","api_key":"k","model":"glm-4.6v"}}}',
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

    async def test_deepseek_defaults_dispatch_and_parse_json(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.global_dir.mkdir(parents=True, exist_ok=True)
            paths.global_config_file.write_text(
                json.dumps(
                    {
                        "vision_profiles": {
                            "custom-deepseek": {
                                "provider": "deepseek",
                                "api_key": "deepseek-key",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            manager = VisionManager(paths)
            profile = manager._load_profile("custom-deepseek")
            self.assertEqual(profile.base_url, DEFAULT_DEEPSEEK_BASE_URL)
            self.assertEqual(profile.model, DEFAULT_DEEPSEEK_MODEL)

            media = Path(tmp) / "photo.png"
            media.write_bytes(b"image")
            response = {
                "choices": [
                    {
                        "message": {
                            "content": "```json\n{\"summary\":\"deepseek\",\"tags\":[],\"text\":\"\"}\n```"
                        }
                    }
                ]
            }
            with mock.patch.object(
                DeepSeekVisionClient, "_request", return_value=response
            ) as request:
                result = await manager.analyze(
                    media, "image", "custom-deepseek"
                )
            self.assertEqual(result["summary"], "deepseek")
            request.assert_called_once()
            self.assertTrue(
                request.call_args.args[0]["messages"][0]["content"][0][
                    "image_url"
                ]["url"].startswith("data:image/png;base64,")
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_deepseek_placeholder_key_fails(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.global_dir.mkdir(parents=True, exist_ok=True)
            paths.global_config_file.write_text(
                json.dumps(
                    {
                        "vision_profiles": {
                            "deepseek": {
                                "provider": "deepseek",
                                "api_key": "replace-me",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            manager = VisionManager(paths)
            with self.assertRaisesRegex(VisionAnalysisError, "placeholder"):
                await manager.analyze(
                    Path(tmp) / "photo.png", "image", "deepseek"
                )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


class VisionClientTests(unittest.TestCase):
    def _profile(self, provider: str) -> VisionProfile:
        if provider == "deepseek":
            return VisionProfile(
                name="deepseek",
                provider=provider,
                model=DEFAULT_DEEPSEEK_MODEL,
                base_url=DEFAULT_DEEPSEEK_BASE_URL,
                api_key="key",
                options={},
            )
        return VisionProfile(
            name="glm",
            provider="glm-4.6v",
            model="glm-4.6v",
            base_url="https://glm.example/chat/completions",
            api_key="key",
            options={},
        )

    def test_deepseek_supported_images_use_mime_data_urls(self) -> None:
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        client = DeepSeekVisionClient(self._profile("deepseek"))
        with tempfile.TemporaryDirectory() as tmp:
            for extension, mime_type in mime_types.items():
                with self.subTest(extension=extension):
                    path = Path(tmp) / f"image{extension}"
                    path.write_bytes(b"image")
                    payload = client._build_payload(path, "image")
                    content = payload["messages"][0]["content"]
                    self.assertEqual(
                        content[0]["image_url"]["url"],
                        f"data:{mime_type};base64,aW1hZ2U=",
                    )
                    self.assertEqual(content[1]["type"], "text")
                    self.assertTrue(content[1]["text"])

    def test_deepseek_rejects_video_and_unsupported_images_before_request(self) -> None:
        client = DeepSeekVisionClient(self._profile("deepseek"))
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"video")
            bitmap = Path(tmp) / "image.bmp"
            bitmap.write_bytes(b"image")
            with mock.patch.object(client, "_request") as request:
                with self.assertRaisesRegex(VisionAnalysisError, "images only"):
                    client.analyze(video, "video")
                with self.assertRaisesRegex(
                    VisionAnalysisError, "JPEG, PNG, GIF, and WebP"
                ):
                    client.analyze(bitmap, "image")
            request.assert_not_called()

    def test_deepseek_translates_http_invalid_json_and_missing_choices(self) -> None:
        client = DeepSeekVisionClient(self._profile("deepseek"))
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "image.png"
            image.write_bytes(b"image")
            http_error = HTTPError(
                client.profile.base_url,
                429,
                "rate limited",
                {},
                BytesIO(b"quota exceeded"),
            )
            with mock.patch("urllib.request.urlopen", side_effect=http_error):
                with self.assertRaisesRegex(
                    VisionAnalysisError, "429.*quota exceeded"
                ):
                    client.analyze(image, "image")

            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = b"not-json"
            with mock.patch("urllib.request.urlopen", return_value=response):
                with self.assertRaisesRegex(VisionAnalysisError, "invalid JSON"):
                    client.analyze(image, "image")

            with mock.patch.object(client, "_request", return_value={}):
                with self.assertRaisesRegex(VisionAnalysisError, "no choices"):
                    client.analyze(image, "image")

            with mock.patch.object(
                client, "_request", return_value={"error": {"message": "denied"}}
            ):
                with self.assertRaisesRegex(VisionAnalysisError, "API error.*denied"):
                    client.analyze(image, "image")

            with mock.patch.object(
                client,
                "_request",
                return_value={
                    "choices": [{"message": {"content": "not structured JSON"}}]
                },
            ):
                with self.assertRaisesRegex(
                    VisionAnalysisError, "did not contain JSON"
                ):
                    client.analyze(image, "image")

    def test_glm_payload_still_supports_raw_image_and_video_base64(self) -> None:
        client = GLM4VClient(self._profile("glm"))
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "image.png"
            video = Path(tmp) / "video.mp4"
            image.write_bytes(b"image")
            video.write_bytes(b"video")
            image_payload = client._build_payload(image, "image")
            video_payload = client._build_payload(video, "video")
            self.assertEqual(
                image_payload["messages"][0]["content"][0],
                {"image_url": {"url": "aW1hZ2U="}, "type": "image_url"},
            )
            self.assertEqual(
                video_payload["messages"][0]["content"][0],
                {"video_url": {"url": "dmlkZW8="}, "type": "video_url"},
            )


class VisionToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_rejects_invalid_media_type_override(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            media = paths.root / "photo.png"
            media.write_bytes(b"image")
            tool = create_dogent_vision_tools(paths.root, config)[0]
            with mock.patch(
                "dogent.features.vision_tools.VisionManager.analyze",
                new=mock.AsyncMock(),
            ) as analyze:
                result = await tool.handler(
                    {"path": "photo.png", "media_type": "audio"}
                )
            self.assertTrue(result.get("is_error"))
            self.assertIn("media_type override", result["content"][0]["text"])
            analyze.assert_not_awaited()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_tool_reports_deepseek_video_rejection_before_request(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"vision_profile": "deepseek"}), encoding="utf-8"
            )
            paths.global_config_file.write_text(
                json.dumps(
                    {
                        "vision_profiles": {
                            "deepseek": {
                                "provider": "deepseek",
                                "api_key": "key",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            media = paths.root / "clip.mp4"
            media.write_bytes(b"video")
            tool = create_dogent_vision_tools(paths.root, config)[0]
            with mock.patch.object(DeepSeekVisionClient, "_request") as request:
                result = await tool.handler({"path": "clip.mp4"})
            self.assertTrue(result.get("is_error"))
            self.assertIn("images only", result["content"][0]["text"])
            request.assert_not_called()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    async def test_tool_returns_placeholder_error(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            config = ConfigManager(paths)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"vision_profile": "glm-4.6v"}),
                encoding="utf-8",
            )
            paths.global_config_file.write_text(
                '{"vision_profiles":{"glm-4.6v":{"provider":"glm-4.6v","api_key":"replace-me"}}}',
                encoding="utf-8",
            )
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
                "dogent.features.vision_tools.VisionManager.analyze", new=mock.AsyncMock()
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
