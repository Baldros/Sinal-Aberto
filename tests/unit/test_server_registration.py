"""Tests MCP tool registration offline, without executing the tools."""

from fastmcp import Client

from sinal_aberto.server import mcp


async def test_tools_registered() -> None:
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    assert {"get_recent_activity", "list_data_sources"} <= set(tools)

    recent = tools["get_recent_activity"]
    props = set((recent.inputSchema or {}).get("properties", {}))
    assert {"city", "region", "time_window"} <= props

    sources = tools["list_data_sources"]
    assert not (sources.inputSchema or {}).get("required")
