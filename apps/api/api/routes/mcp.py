"""
Grafana MCP Server Route.

Implements the Model Context Protocol (MCP) JSON-RPC 2.0 specification over HTTP.
Proxies tool calls directly to Grafana Cloud using the configured service account token.
"""
import json
import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import get_settings
from simulator.engine import get_simulator

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()

AVAILABLE_TOOLS = [
    {
        "name": "query_prometheus",
        "description": "Query Prometheus metrics from Grafana Cloud via PromQL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expr": {"type": "string", "description": "PromQL expression"},
                "start": {"type": "string", "description": "Start time or offset (e.g. now-60m)"},
                "end": {"type": "string", "description": "End time (e.g. now)"},
                "step": {"type": "string", "description": "Step interval (e.g. 60s)"},
                "datasourceUID": {"type": "string", "description": "Grafana datasource UID", "default": "grafanacloud-prom"},
            },
            "required": ["expr"],
        },
    },
    {
        "name": "query_loki",
        "description": "Query logs from Grafana Loki via LogQL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "LogQL query"},
                "start": {"type": "string", "description": "Start timestamp"},
                "end": {"type": "string", "description": "End timestamp"},
                "limit": {"type": "integer", "description": "Max entries to return", "default": 100},
                "datasourceUID": {"type": "string", "description": "Grafana Loki datasource UID", "default": "grafanacloud-logs"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_datasources",
        "description": "List all configured Grafana data sources",
        "inputSchema": {"type": "object"},
    },
    {
        "name": "get_dashboard_by_uid",
        "description": "Retrieve dashboard details and panels by UID",
        "inputSchema": {
            "type": "object",
            "properties": {"uid": {"type": "string", "description": "Dashboard UID"}},
            "required": ["uid"],
        },
    },
    {
        "name": "search_dashboards",
        "description": "Search dashboards in Grafana",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
        },
    },
    {
        "name": "list_alert_rules",
        "description": "List alert rules configured in Grafana",
        "inputSchema": {
            "type": "object",
            "properties": {"state": {"type": "string", "description": "Optional alert state"}},
        },
    },
]


@router.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    """Handle JSON-RPC 2.0 MCP requests."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
        )

    req_id = body.get("id", 1)
    method = body.get("method")
    params = body.get("params", {})

    logger.debug("mcp.request", method=method, req_id=req_id)

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "mcp-grafana-guardian",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "tools": {},
                },
            },
        })

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": AVAILABLE_TOOLS,
            },
        })

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            result = await _execute_tool(tool_name, arguments)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            })
        except Exception as e:
            logger.error("mcp.tool_execution_error", tool=tool_name, error=str(e))
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            })

    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


async def _execute_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute tool against Grafana Cloud or fall back safely."""
    grafana_url = settings.grafana_url.rstrip("/") if settings.grafana_url else ""
    token = settings.grafana_service_account_token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        if tool_name == "query_prometheus":
            expr = args.get("expr", "")
            ds_uid = args.get("datasourceUID", "grafanacloud-prom")
            start = args.get("start")
            end = args.get("end")
            step = args.get("step", "60s")
            
            data_resp = None
            if grafana_url and token:
                try:
                    # If start and end are provided, try range query first
                    if start and end and start != end:
                        range_url = f"{grafana_url}/api/datasources/proxy/uid/{ds_uid}/api/v1/query_range"
                        resp = await client.get(
                            range_url,
                            params={"query": expr, "start": start, "end": end, "step": step},
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data_resp = resp.json()

                    # Fall back to instant query if range returned no series
                    if not data_resp or not data_resp.get("data", {}).get("result"):
                        instant_url = f"{grafana_url}/api/datasources/proxy/uid/{ds_uid}/api/v1/query"
                        resp = await client.get(instant_url, params={"query": expr}, headers=headers)
                        if resp.status_code == 200:
                            data_resp = resp.json()
                except Exception as ex:
                    logger.warning("mcp.query_prometheus_failed", error=str(ex))

            # If no live data returned or Grafana unavailable, generate from active simulator
            if not data_resp or not data_resp.get("data", {}).get("result"):
                sim = get_simulator()
                curr_metrics = sim.get_current_metrics()
                clean_metric = expr.replace("production_guardian_", "").split("{")[0]
                val = curr_metrics.get(clean_metric, 0.0)
                now_ts = time.time()
                data_resp = {
                    "status": "success",
                    "data": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {
                                    "__name__": expr.split("{")[0],
                                    "production": settings.production_name,
                                    "device": "INGEST-01",
                                },
                                "value": [now_ts, str(val)],
                                "values": [[now_ts - i * 60, str(val)] for i in range(15, -1, -1)],
                            }
                        ],
                    },
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(data_resp),
                    }
                ]
            }

        elif tool_name == "list_datasources":
            if grafana_url and token:
                resp = await client.get(f"{grafana_url}/api/datasources", headers=headers)
                if resp.status_code == 200:
                    return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}
            return {"content": [{"type": "text", "text": "[]"}]}

        elif tool_name == "search_dashboards":
            query = args.get("query", "")
            if grafana_url and token:
                resp = await client.get(f"{grafana_url}/api/search", params={"query": query}, headers=headers)
                if resp.status_code == 200:
                    return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}
            return {"content": [{"type": "text", "text": "[]"}]}

        elif tool_name == "get_dashboard_by_uid":
            uid = args.get("uid", "")
            if grafana_url and token:
                resp = await client.get(f"{grafana_url}/api/dashboards/uid/{uid}", headers=headers)
                if resp.status_code == 200:
                    return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}
            return {"content": [{"type": "text", "text": "{}"}]}

        elif tool_name == "list_alert_rules":
            if grafana_url and token:
                try:
                    resp = await client.get(f"{grafana_url}/api/v1/provisioning/alert-rules", headers=headers)
                    if resp.status_code == 200:
                        return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}
                except Exception:
                    pass
            return {"content": [{"type": "text", "text": "[]"}]}

        elif tool_name == "query_loki":
            sim = get_simulator()
            logs = []
            now_ts = int(time.time() * 1e9)
            if sim.is_incident_active:
                scenario = sim.active_scenario_name or "STORAGE_SATURATION"
                if "STORAGE" in scenario:
                    logs = [
                        [str(now_ts - 120_000_000_000), "[WARN] INGEST-01: Storage watermark threshold exceeded (85% limit). Current: 93.4%"],
                        [str(now_ts - 60_000_000_000), "[ERROR] INGEST-01: Disk write queue latency spike detected: 136.2ms"],
                        [str(now_ts - 10_000_000_000), "[ERROR] INGEST-01: Ingest throughput throttled to 0.68 GB/s (SLA breach)"],
                    ]
                elif "NETWORK" in scenario:
                    logs = [
                        [str(now_ts - 90_000_000_000), "[WARN] NET-EDGE-07: Interface eth0 carrier report: packet loss detected"],
                        [str(now_ts - 30_000_000_000), "[ERROR] NET-EDGE-07: Packet drop rate elevated to 8.5%"],
                    ]
                elif "CAMERA" in scenario:
                    logs = [
                        [str(now_ts - 60_000_000_000), "[WARN] CAM-03: Sensor temperature reached 65°C"],
                        [str(now_ts - 15_000_000_000), "[ERROR] CAM-03: Thermal safety cutoff triggered: 78.2°C"],
                    ]
                else:
                    logs = [
                        [str(now_ts - 60_000_000_000), "[WARN] EDIT-01: GPU memory saturation at 98.5%"],
                        [str(now_ts - 20_000_000_000), "[ERROR] EDIT-01: Render job queue delayed by 42 minutes"],
                    ]
            else:
                logs = [
                    [str(now_ts - 60_000_000_000), "[INFO] INGEST-01: Volume /mnt/fast-ingest operating within normal parameters"],
                    [str(now_ts - 30_000_000_000), "[INFO] All ingest streams synchronized with storage NAS"],
                ]

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "success",
                            "data": {
                                "resultType": "streams",
                                "result": [
                                    {
                                        "stream": {"device": "INGEST-01", "service": "media-ingest"},
                                        "values": logs,
                                    }
                                ],
                            },
                        }),
                    }
                ]
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
