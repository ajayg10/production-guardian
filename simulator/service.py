"""
Simulator background service.

This module provides a background task runner that periodically pushes
telemetry to Grafana Cloud. Can be run as a standalone process or
integrated with the FastAPI backend.
"""
import asyncio
import os
import sys
import time

import structlog

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from dotenv import load_dotenv
load_dotenv()

from config import get_settings
from core.logging import configure_logging
from simulator.engine import get_simulator
from simulator.pusher import TelemetryPusher

configure_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()

PUSH_INTERVAL = settings.simulator_push_interval_seconds


async def run_simulator() -> None:
    """Run the simulator push loop indefinitely."""
    import requests
    pusher = TelemetryPusher()
    sim = get_simulator()
    api_url = os.getenv("API_URL", "http://api:8000").rstrip("/")

    logger.info(
        "simulator.service_started",
        push_interval_seconds=PUSH_INTERVAL,
        grafana_configured=bool(settings.grafana_prometheus_remote_write_url),
        api_url=api_url,
    )

    while True:
        try:
            metrics = None
            source = "local_engine"

            # Attempt to pull active scenario metrics from FastAPI backend
            try:
                resp = requests.get(f"{api_url}/api/telemetry/status", timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    metrics = data.get("metrics")
                    state = data.get("simulator_state", "NORMAL")
                    scenario = data.get("scenario")
                    source = f"api ({state}: {scenario})"
            except Exception:
                pass

            if not metrics:
                metrics = sim.get_current_metrics()

            success = pusher.push(metrics)

            if success:
                logger.info(
                    "simulator.push_success",
                    source=source,
                    metric_count=len(metrics),
                    storage_util=metrics.get("storage_utilization"),
                    throughput=metrics.get("ingest_throughput_gbps"),
                )
            else:
                logger.warning(
                    "simulator.push_failed",
                    reason="Grafana remote write failed or rejected",
                )

        except Exception as e:
            logger.error("simulator.push_error", error=str(e))

        await asyncio.sleep(PUSH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_simulator())
