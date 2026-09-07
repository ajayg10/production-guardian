"""Telemetry and Grafana integration status routes."""
from fastapi import APIRouter
from pydantic import BaseModel

from integrations.grafana_mcp.client import get_grafana_mcp_client
from simulator.engine import get_simulator
from simulator.generator import MetricGenerator

router = APIRouter()


class TelemetryStatusResponse(BaseModel):
    """Current telemetry snapshot for the UI."""
    simulator_state: str
    scenario: str | None
    incident_active: bool
    metrics: dict
    health_scores: dict
    data_source: str = "Grafana Cloud (Remote Write)"
    explore_url: str = ""


class GrafanaStatusResponse(BaseModel):
    """Grafana integration status."""
    mcp_available: bool
    grafana_url: str
    mcp_url: str
    message: str | None = None
    tools_available: list[str] = []
    remote_write_active: bool = True
    explore_url: str = ""
    datasource_uid: str = "grafanacloud-prom"


@router.get("/telemetry/status", response_model=TelemetryStatusResponse)
async def get_telemetry_status() -> TelemetryStatusResponse:
    """
    Get current telemetry snapshot.

    Returns current metric values from the simulator.
    These are the same values being pushed to Grafana Cloud.
    """
    sim = get_simulator()
    metrics = sim.get_current_metrics()

    gen = MetricGenerator()
    health_scores = gen.calculate_system_health(metrics)

    from config import get_settings
    cfg = get_settings()
    explore_url = f"{cfg.grafana_url}/explore" if cfg.grafana_url else ""

    return TelemetryStatusResponse(
        simulator_state=sim.state.value,
        scenario=sim.active_scenario_name,
        incident_active=sim.is_incident_active,
        metrics=metrics,
        health_scores=health_scores,
        data_source="Grafana Cloud (Prometheus Remote Write)",
        explore_url=explore_url,
    )


@router.get("/telemetry/history")
async def get_telemetry_history(
    metric: str = "storage_utilization",
    points: int = 30,
) -> dict:
    """
    Get simulated time-series history for a metric.

    Generates realistic historical data that matches the current simulator state.
    In production, this would query Grafana Prometheus.
    """
    import time
    import random

    sim = get_simulator()
    metrics = sim.get_current_metrics()
    current_val = metrics.get(metric, 0)

    from simulator.generator import BASELINE_METRICS
    baseline = BASELINE_METRICS.get(metric, {}).get("value", current_val)
    noise = BASELINE_METRICS.get(metric, {}).get("noise", current_val * 0.02)

    history = []
    now = time.time()

    for i in range(points):
        t = now - (points - i) * 60  # One point per minute going back

        # Progress from baseline to current value
        progress = i / max(points - 1, 1)
        if sim.is_incident_active:
            val = baseline + (current_val - baseline) * min(progress * 1.5, 1.0)
        else:
            val = current_val

        val += random.gauss(0, noise * 0.3)
        history.append({
            "timestamp": t,
            "value": round(max(0, val), 3),
        })

    return {
        "metric": metric,
        "data_source": "DEMO_SIMULATOR",
        "history": history,
        "current_value": current_val,
    }


@router.get("/integrations/grafana/status", response_model=GrafanaStatusResponse)
async def get_grafana_status() -> GrafanaStatusResponse:
    """
    Check Grafana MCP integration status.

    Makes an actual health check to the Grafana MCP server.
    Returns connection status and available tools.
    """
    from config import get_settings
    settings = get_settings()

    client = get_grafana_mcp_client()
    health = await client.check_health()

    # If available, list tools
    tools = []
    if health.get("available"):
        try:
            tool_list = await client.list_tools()
            tools = [t.get("name", "") for t in tool_list if t.get("name")]
        except Exception:
            pass

    sim = get_simulator()
    metric_name = "production_guardian_storage_utilization"
    if sim.is_incident_active and sim.active_scenario_name:
        scenario_map = {
            "STORAGE_SATURATION": "production_guardian_storage_utilization",
            "NETWORK_DEGRADATION": "production_guardian_packet_loss_pct",
            "CAMERA_FAILURE": "production_guardian_camera_temperature_c",
            "RENDER_BOTTLENECK": "production_guardian_gpu_usage_pct",
        }
        metric_name = scenario_map.get(sim.active_scenario_name, "production_guardian_storage_utilization")

    active_mcp_url = "http://localhost:8000/mcp"

    explore_url = (
        f"{settings.grafana_url}/explore?schemaVersion=1&panes=%7B%22v0b%22:%7B%22datasource%22:%22grafanacloud-prom%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22expr%22:%22{metric_name}%22%7D%5D%7D%7D"
        if settings.grafana_url
        else ""
    )

    return GrafanaStatusResponse(
        mcp_available=health.get("available", False),
        grafana_url=settings.grafana_url or "not configured",
        mcp_url=active_mcp_url,
        message=health.get("message"),
        tools_available=tools,
        remote_write_active=bool(settings.grafana_prometheus_remote_write_url),
        explore_url=explore_url,
        datasource_uid="grafanacloud-prom",
    )
