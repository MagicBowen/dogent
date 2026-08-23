from __future__ import annotations

from typing import Any

from claude_agent_sdk import SdkMcpTool, create_sdk_mcp_server


def create_dogent_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> dict[str, Any]:
    """Create an in-process MCP server through the SDK's version bridge."""

    return create_sdk_mcp_server(name=name, version=version, tools=tools)
