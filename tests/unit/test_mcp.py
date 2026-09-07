"""Unit tests for the Grafana MCP server and client integration."""
import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from main import app
from integrations.grafana_mcp.client import GrafanaMCPClient


@pytest.mark.asyncio
async def test_mcp_initialize():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["serverInfo"]["name"] == "mcp-grafana-guardian"
        assert "tools" in data["result"]["capabilities"]


@pytest.mark.asyncio
async def test_mcp_tools_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert response.status_code == 200
        tools = response.json()["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "query_prometheus" in tool_names
        assert "query_loki" in tool_names
        assert "list_datasources" in tool_names
        assert len(tools) == 6


@pytest.mark.asyncio
async def test_mcp_tool_call_query_prometheus():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "query_prometheus",
                    "arguments": {"expr": "production_guardian_storage_utilization"},
                },
            },
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert "content" in result
        assert len(result["content"]) > 0


@pytest.mark.asyncio
async def test_root_landing_page():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Production Guardian API" in response.text
        assert "/api/docs" in response.text
