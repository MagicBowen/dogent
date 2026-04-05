from __future__ import annotations

import json
from typing import Any, get_args, get_origin, is_typeddict

import jsonschema
from claude_agent_sdk import SdkMcpTool
from mcp import types
from mcp.server import Server


def create_dogent_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> dict[str, Any]:
    """Create Dogent's in-process MCP server using the current low-level MCP contract."""

    server = Server(name, version=version)
    tool_defs = tools or []
    tool_map = {tool_def.name: tool_def for tool_def in tool_defs}
    schema_map = {tool_def.name: _build_schema(tool_def) for tool_def in tool_defs}
    cached_tool_list = [
        types.Tool(
            name=tool_def.name,
            description=tool_def.description,
            inputSchema=schema_map[tool_def.name],
            annotations=tool_def.annotations,
        )
        for tool_def in tool_defs
    ]

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        return cached_tool_list

    async def call_tool(req: types.CallToolRequest) -> types.ServerResult:
        try:
            tool_name = req.params.name
            arguments = req.params.arguments or {}
            tool_def = tool_map.get(tool_name)
            if tool_def is None:
                return _error_result(f"Tool '{tool_name}' not found")

            jsonschema.validate(instance=arguments, schema=schema_map[tool_name])
            result = await tool_def.handler(arguments)
            return types.ServerResult(
                types.CallToolResult(
                    content=_convert_tool_content(result),
                    isError=bool(result.get("is_error", False)),
                )
            )
        except jsonschema.ValidationError as exc:
            return _error_result(f"Input validation error: {exc.message}")
        except Exception as exc:  # noqa: BLE001
            return _error_result(str(exc))

    server.request_handlers[types.CallToolRequest] = call_tool
    return {"type": "sdk", "name": name, "instance": server}


def _error_result(message: str) -> types.ServerResult:
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=message)],
            isError=True,
        )
    )


def _build_schema(tool_def: SdkMcpTool[Any]) -> dict[str, Any]:
    if isinstance(tool_def.input_schema, dict):
        if (
            "type" in tool_def.input_schema
            and "properties" in tool_def.input_schema
            and isinstance(tool_def.input_schema["type"], str)
        ):
            return tool_def.input_schema
        properties = {}
        for param_name, param_type in tool_def.input_schema.items():
            properties[param_name] = _python_type_to_json_schema(param_type)
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties.keys()),
        }
    if is_typeddict(tool_def.input_schema):
        return _typeddict_to_json_schema(tool_def.input_schema)
    return {"type": "object", "properties": {}}


def _python_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    origin = get_origin(py_type)
    if getattr(origin, "_name", None) in ("NotRequired", "Required", "ReadOnly"):
        return _python_type_to_json_schema(get_args(py_type)[0])
    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    if origin is list:
        args = get_args(py_type)
        items = _python_type_to_json_schema(args[0]) if args else {}
        return {"type": "array", "items": items}
    if origin is dict:
        return {"type": "object"}
    return {"type": "string"}


def _typeddict_to_json_schema(td_class: type[Any]) -> dict[str, Any]:
    annotations = getattr(td_class, "__annotations__", {})
    properties = {
        key: _python_type_to_json_schema(value) for key, value in annotations.items()
    }
    required = list(getattr(td_class, "__required_keys__", set()))
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _convert_tool_content(result: dict[str, Any]) -> list[Any]:
    content: list[Any] = []
    for item in result.get("content") or []:
        item_type = item.get("type")
        if item_type == "text":
            content.append(types.TextContent(type="text", text=item["text"]))
        elif item_type == "image":
            content.append(
                types.ImageContent(
                    type="image",
                    data=item["data"],
                    mimeType=item["mimeType"],
                )
            )
        elif item_type == "resource_link":
            parts = []
            link_name = item.get("name")
            uri = item.get("uri")
            desc = item.get("description")
            if link_name:
                parts.append(link_name)
            if uri:
                parts.append(str(uri))
            if desc:
                parts.append(desc)
            content.append(
                types.TextContent(
                    type="text",
                    text="\n".join(parts) if parts else "Resource link",
                )
            )
        elif item_type == "resource":
            resource = item.get("resource") or {}
            if "text" in resource:
                content.append(types.TextContent(type="text", text=resource["text"]))
        else:
            content.append(
                types.TextContent(
                    type="text",
                    text=json.dumps(item, ensure_ascii=True),
                )
            )
    return content
