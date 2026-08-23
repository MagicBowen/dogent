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

        self.assertTrue(self._annotation(tools["read_document"], "readOnlyHint"))
        self.assertFalse(self._annotation(tools["export_document"], "readOnlyHint"))
        self.assertFalse(self._annotation(tools["convert_document"], "openWorldHint"))

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

        self.assertTrue(self._annotation(ui_tool, "readOnlyHint"))
        self.assertTrue(self._annotation(web_tools["web_search"], "openWorldHint"))
        self.assertFalse(self._annotation(web_tools["web_fetch"], "readOnlyHint"))

    def test_vision_tool_has_annotations(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)

            tool = create_dogent_vision_tools(Path(tmp), manager)[0]

            self.assertTrue(self._annotation(tool, "readOnlyHint"))
            self.assertFalse(self._annotation(tool, "openWorldHint"))
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

            list_result = self._list_tools(server)
            self.assertEqual(
                [tool.name for tool in self._result_root(list_result).tools],
                ["read_document", "export_document", "convert_document"],
            )
            self.assertTrue(
                self._annotation(
                    self._result_root(list_result).tools[0], "readOnlyHint"
                )
            )

            call_result = self._call_tool(
                server,
                "read_document",
                {"path": "sample.md"},
            )

            result = self._result_root(call_result)
            self.assertFalse(self._is_error(result))
            self.assertEqual(len(result.content), 1)
            self.assertIn("hello world", result.content[0].text)

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

        list_result = self._list_tools(server)
        self.assertEqual(
            [tool.name for tool in self._result_root(list_result).tools],
            ["ui_request", "web_search", "web_fetch"],
        )
        self.assertTrue(
            self._annotation(self._result_root(list_result).tools[0], "readOnlyHint")
        )

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
        ui_root = self._result_root(ui_result)
        self.assertFalse(self._is_error(ui_root))
        self.assertIn("Awaiting user input", ui_root.content[0].text)

        web_result = self._call_tool(server, "web_search", {"query": "example"})
        web_root = self._result_root(web_result)
        self.assertFalse(self._is_error(web_root))
        self.assertIn("Example", web_root.content[0].text)

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

            list_result = self._list_tools(server)
            self.assertEqual(
                [tool.name for tool in self._result_root(list_result).tools],
                ["analyze_media", "generate_image"],
            )

            vision_result = self._call_tool(
                server, "analyze_media", {"path": "missing.png"}
            )
            vision_root = self._result_root(vision_result)
            self.assertTrue(self._is_error(vision_root))
            self.assertIn("File does not exist", vision_root.content[0].text)

            image_result = self._call_tool(server, "generate_image", {"prompt": ""})
            image_root = self._result_root(image_result)
            self.assertTrue(self._is_error(image_root))
            self.assertIn("Missing required field: prompt", image_root.content[0].text)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def _call_tool(self, server, name: str, arguments: dict[str, object]):
        if hasattr(server, "request_handlers"):
            return self._run_async(
                server.request_handlers[types.CallToolRequest](
                    types.CallToolRequest(
                        method="tools/call",
                        params=types.CallToolRequestParams(
                            name=name, arguments=arguments
                        ),
                    )
                )
            )
        entry = server.get_request_handler("tools/call")
        self.assertIsNotNone(entry)
        return self._run_async(
            entry.handler(
                None,
                types.CallToolRequestParams(name=name, arguments=arguments),
            )
        )

    def _list_tools(self, server):
        if hasattr(server, "request_handlers"):
            return self._run_async(
                server.request_handlers[types.ListToolsRequest](None)
            )
        entry = server.get_request_handler("tools/list")
        self.assertIsNotNone(entry)
        return self._run_async(entry.handler(None, types.PaginatedRequestParams()))

    def _annotation(self, value, name: str):
        annotations = getattr(value, "annotations", value)
        return annotations.model_dump(by_alias=True).get(name)

    def _is_error(self, result) -> bool:
        if hasattr(result, "isError"):
            return bool(result.isError)
        return bool(result.is_error)

    def _result_root(self, result):
        return getattr(result, "root", result)

    def _run_async(self, awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
