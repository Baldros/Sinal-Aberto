"""Tests MCP tool registration offline, without executing the tools."""

from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from sinal_aberto import __version__
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


async def test_health_route() -> None:
    transport = ASGITransport(app=mcp.http_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sinal-aberto",
        "version": __version__,
    }
