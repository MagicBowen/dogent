import json
import tempfile
import unittest
from pathlib import Path

from dogent.web_tools import (
    HttpResponse,
    create_dogent_web_tools,
    extract_text_from_html,
    parse_brave_results,
    parse_google_cse_results,
)


class WebToolsTests(unittest.IsolatedAsyncioTestCase):
    def test_extract_text_from_html_strips_noise(self) -> None:
        html = """
        <html>
          <head><title>Example</title><style>.x{}</style></head>
          <body>
            <header>Nav</header>
            <h1>Hello</h1>
            <script>alert(1)</script>
            <p>World</p>
          </body>
        </html>
        """
        text = extract_text_from_html(html)
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertNotIn("alert(1)", text)
        self.assertNotIn("Nav", text)

    def test_parse_google_cse_results_image_mode(self) -> None:
        payload = {
            "items": [
                {
                    "title": "img",
                    "link": "https://example.com/a.png",
                    "image": {
                        "contextLink": "https://example.com/page",
                        "thumbnailLink": "https://example.com/thumb.png",
                        "width": 100,
                        "height": 80,
                    },
                }
            ]
        }
        results = parse_google_cse_results(payload, mode="image")
        self.assertEqual(results[0]["image_url"], "https://example.com/a.png")
        self.assertEqual(results[0]["page_url"], "https://example.com/page")

    def test_parse_brave_results_web_mode(self) -> None:
        payload = {
            "web": {
                "results": [
                    {"title": "T1", "url": "https://example.com/1", "description": "S1"},
                    {"title": "T2", "url": "https://example.com/2", "description": "S2"},
                ]
            }
        }
        results = parse_brave_results(payload, mode="web")
        self.assertEqual(results[0]["url"], "https://example.com/1")
        self.assertEqual(results[0]["snippet"], "S1")

    async def test_web_fetch_extracts_text(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
            body = b"<html><head><title>T</title></head><body><p>A</p><p>B</p></body></html>"
            return HttpResponse(
                url=url,
                status=200,
                headers={"Content-Type": "text/html; charset=utf-8"},
                body=body,
            )

        tools = create_dogent_web_tools(
            root=Path("."),
            images_path="./images",
            web_profile_name="default",
            web_profile_cfg={"provider": "google_cse", "timeout_s": 1},
            http_get=fake_get,
        )
        web_fetch = next(tool for tool in tools if tool.name == "web_fetch")
        result = await web_fetch.handler({"url": "https://example.com", "mode": "text", "max_chars": 1000})
        text = result["content"][0]["text"]
        self.assertIn("Title: T", text)
        self.assertIn("A", text)
        self.assertIn("B", text)

    async def test_web_search_returns_structured_results(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
            payload = {
                "items": [
                    {"title": "T1", "link": "https://example.com/1", "snippet": "S1"},
                    {"title": "T2", "link": "https://example.com/2", "snippet": "S2"},
                ]
            }
            return HttpResponse(
                url=url,
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
                body=json.dumps(payload).encode("utf-8"),
            )

        tools = create_dogent_web_tools(
            root=Path("."),
            images_path="./images",
            web_profile_name="default",
            web_profile_cfg={"provider": "google_cse", "api_key": "k", "cse_id": "cx"},
            http_get=fake_get,
        )
        web_search = next(tool for tool in tools if tool.name == "web_search")
        result = await web_search.handler({"query": "q", "mode": "web", "num_results": 2})
        text = result["content"][0]["text"]
        parsed = json.loads(text)
        self.assertEqual(parsed["profile"], "default")
        self.assertEqual(len(parsed["results"]), 2)

    async def test_web_search_brave_provider(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
            self.assertIn("X-Subscription-Token", headers)
            payload = {
                "web": {
                    "results": [
                        {"title": "T", "url": "https://example.com", "description": "S"}
                    ]
                }
            }
            return HttpResponse(
                url=url,
                status=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
                body=json.dumps(payload).encode("utf-8"),
            )

        tools = create_dogent_web_tools(
            root=Path("."),
            images_path="./images",
            web_profile_name="brave",
            web_profile_cfg={"provider": "brave", "api_key": "k"},
            http_get=fake_get,
        )
        web_search = next(tool for tool in tools if tool.name == "web_search")
        result = await web_search.handler({"query": "q", "mode": "web", "num_results": 1})
        text = result["content"][0]["text"]
        parsed = json.loads(text)
        self.assertEqual(parsed["provider"], "brave")
        self.assertEqual(parsed["results"][0]["url"], "https://example.com")

    async def test_web_fetch_downloads_image(self) -> None:
        def fake_get(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
            return HttpResponse(
                url=url,
                status=200,
                headers={"Content-Type": "image/png"},
                body=b"PNGDATA",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tools = create_dogent_web_tools(
                root=root,
                images_path="./images",
                web_profile_name="default",
                web_profile_cfg={"provider": "google_cse", "timeout_s": 1},
                http_get=fake_get,
            )
            web_fetch = next(tool for tool in tools if tool.name == "web_fetch")
            result = await web_fetch.handler({"url": "https://example.com/a.png", "mode": "image"})
            text = result["content"][0]["text"]
            self.assertIn("Saved image to:", text)
            images_dir = root / "images"
            self.assertTrue(images_dir.exists())
            self.assertEqual(len(list(images_dir.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
