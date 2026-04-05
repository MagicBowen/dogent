import os
import json
import tempfile
import unittest
from pathlib import Path

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.sdk_mcp import create_dogent_sdk_mcp_server
from dogent.features.document_tools import create_dogent_doc_tools
from dogent.features.image_tools import create_dogent_image_tools
from dogent.features.ui_tools import create_dogent_ui_tools
from dogent.features.vision_tools import create_dogent_vision_tools
from dogent.features.web_tools import HttpResponse, create_dogent_web_tools
from mcp import types


class ToolAnnotationsTests(unittest.TestCase):
    def test_document_tools_have_annotations(self) -> None:
        tools = {tool.name: tool for tool in create_dogent_doc_tools(Path("."))}

        self.assertTrue(tools["read_document"].annotations.readOnlyHint)
        self.assertFalse(tools["export_document"].annotations.readOnlyHint)
        self.assertFalse(tools["convert_document"].annotations.openWorldHint)

    def test_ui_and_web_tools_have_annotations(self) -> None:
        ui_tool = create_dogent_ui_tools()[0]
        web_tools = {
            tool.name: tool
            for tool in create_dogent_web_tools(
                root=Path("."),
                web_profile_name="demo",
                web_profile_cfg={"provider": "brave", "api_key": "k"},
            )
        }

        self.assertTrue(ui_tool.annotations.readOnlyHint)
        self.assertTrue(web_tools["web_search"].annotations.openWorldHint)
        self.assertFalse(web_tools["web_fetch"].annotations.readOnlyHint)

    def test_vision_tool_has_annotations(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)

            tool = create_dogent_vision_tools(Path(tmp), manager)[0]

            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.openWorldHint)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_sdk_mcp_server_round_trip_returns_successful_tool_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.md").write_text("hello world", encoding="utf-8")
            server_config = create_dogent_sdk_mcp_server(
                name="dogent",
                version="test",
                tools=create_dogent_doc_tools(root),
            )
            server = server_config["instance"]

            list_handler = server.request_handlers[types.ListToolsRequest]
            list_result = self._run_async(list_handler(None))
            self.assertEqual(
                [tool.name for tool in list_result.root.tools],
                ["read_document", "export_document", "convert_document"],
            )
            self.assertTrue(list_result.root.tools[0].annotations.readOnlyHint)

            call_handler = server.request_handlers[types.CallToolRequest]
            call_result = self._run_async(
                call_handler(
                    types.CallToolRequest(
                        method="tools/call",
                        params=types.CallToolRequestParams(
                            name="read_document",
                            arguments={"path": "sample.md"},
                        ),
                    )
                )
            )

            self.assertFalse(call_result.root.isError)
            self.assertEqual(len(call_result.root.content), 1)
            self.assertIn("hello world", call_result.root.content[0].text)

    def test_builtin_ui_and_web_tools_round_trip(self) -> None:
        def fake_http_get(url: str, headers: dict[str, str], timeout_s: float) -> HttpResponse:
            self.assertEqual(timeout_s, 20.0)
            self.assertIn("dogent/", headers.get("User-Agent", ""))
            if "search" in url:
                payload = {
                    "web": {
                        "results": [
                            {
                                "title": "Example",
                                "url": "https://example.com",
                                "description": "Result snippet",
                            }
                        ]
                    }
                }
                return HttpResponse(
                    url=url,
                    status=200,
                    headers={"Content-Type": "application/json"},
                    body=json.dumps(payload).encode("utf-8"),
                )
            raise AssertionError(f"Unexpected URL: {url}")

        tools = []
        tools.extend(create_dogent_ui_tools())
        tools.extend(
            create_dogent_web_tools(
                root=Path("."),
                web_profile_name="demo",
                web_profile_cfg={"provider": "brave", "api_key": "k"},
                http_get=fake_http_get,
            )
        )
        server = create_dogent_sdk_mcp_server("dogent", tools=tools)["instance"]

        list_result = self._run_async(server.request_handlers[types.ListToolsRequest](None))
        self.assertEqual(
            [tool.name for tool in list_result.root.tools],
            ["ui_request", "web_search", "web_fetch"],
        )
        self.assertTrue(list_result.root.tools[0].annotations.readOnlyHint)

        ui_result = self._call_tool(
            server,
            "ui_request",
            {
                "response_type": "clarification",
                "title": "Need input",
                "questions": [
                    {
                        "id": "choice",
                        "question": "Pick one",
                        "options": [{"label": "A", "value": "a"}],
                    }
                ],
            },
        )
        self.assertFalse(ui_result.root.isError)
        self.assertIn("Awaiting user input", ui_result.root.content[0].text)

        web_result = self._call_tool(server, "web_search", {"query": "example"})
        self.assertFalse(web_result.root.isError)
        self.assertIn("Example", web_result.root.content[0].text)

    def test_builtin_vision_and_image_tools_round_trip(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            manager = ConfigManager(DogentPaths(root))
            tools = []
            tools.extend(create_dogent_vision_tools(root, manager))
            tools.extend(create_dogent_image_tools(root, manager))
            server = create_dogent_sdk_mcp_server("dogent", tools=tools)["instance"]

            list_result = self._run_async(
                server.request_handlers[types.ListToolsRequest](None)
            )
            self.assertEqual(
                [tool.name for tool in list_result.root.tools],
                ["analyze_media", "generate_image"],
            )

            vision_result = self._call_tool(
                server, "analyze_media", {"path": "missing.png"}
            )
            self.assertTrue(vision_result.root.isError)
            self.assertIn("File does not exist", vision_result.root.content[0].text)

            image_result = self._call_tool(server, "generate_image", {"prompt": ""})
            self.assertTrue(image_result.root.isError)
            self.assertIn("Missing required field: prompt", image_result.root.content[0].text)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def _call_tool(self, server, name: str, arguments: dict[str, object]):
        return self._run_async(
            server.request_handlers[types.CallToolRequest](
                types.CallToolRequest(
                    method="tools/call",
                    params=types.CallToolRequestParams(name=name, arguments=arguments),
                )
            )
        )

    def _run_async(self, awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
