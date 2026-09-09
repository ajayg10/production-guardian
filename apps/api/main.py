"""
Production Guardian — FastAPI Backend

AI-powered autonomous operations system for film production monitoring.
"""
import os
import sys

# Ensure root directory and apps/api directory are on sys.path
_api_dir = os.path.dirname(os.path.abspath(__file__))   # d:/production-guardian/apps/api
_apps_dir = os.path.dirname(_api_dir)                    # d:/production-guardian/apps
_root_dir = os.path.dirname(_apps_dir)                   # d:/production-guardian  ← project root
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from api.routes import agent, health, incidents, mcp, production, remediation, telemetry
from config import get_settings
from core.database import init_db
from core.logging import configure_logging

# Configure structured logging before anything else
configure_logging()
logger = structlog.get_logger(__name__)

settings = get_settings()


async def _telemetry_push_worker():
    """Background loop ensuring continuous metric push to Grafana Cloud."""
    from simulator.engine import get_simulator
    from simulator.pusher import push_metrics_to_grafana
    logger.info("telemetry_worker.started", interval=15)
    while True:
        try:
            sim = get_simulator()
            metrics = sim.get_current_metrics()
            push_metrics_to_grafana(metrics)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("telemetry_worker.error", error=str(e))
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    logger.info(
        "production_guardian.startup",
        app_env=settings.app_env,
        gemini_model=settings.gemini_model,
        grafana_url=settings.grafana_url,
    )

    # Validate critical configuration
    _validate_configuration()

    # Initialize database connection pool
    await init_db()
    logger.info("production_guardian.database_ready")

    # Start continuous background push worker to Grafana Cloud
    push_task = asyncio.create_task(_telemetry_push_worker())

    yield

    push_task.cancel()
    try:
        await push_task
    except asyncio.CancelledError:
        pass

    logger.info("production_guardian.shutdown")


def _validate_configuration() -> None:
    """Validate required configuration on startup. Warns but does not crash."""
    warnings = []

    if not settings.google_api_key:
        warnings.append("GOOGLE_API_KEY is not configured — Gemini agent will be unavailable")

    if not settings.grafana_url:
        warnings.append("GRAFANA_URL is not configured — Grafana integration will be unavailable")

    if not settings.grafana_service_account_token:
        warnings.append(
            "GRAFANA_SERVICE_ACCOUNT_TOKEN is not configured — Grafana queries will fail"
        )

    if not settings.grafana_mcp_url:
        warnings.append("GRAFANA_MCP_URL is not configured — MCP integration will be unavailable")

    if not settings.grafana_prometheus_remote_write_url:
        warnings.append(
            "GRAFANA_PROMETHEUS_REMOTE_WRITE_URL is not configured — "
            "Telemetry will not reach Grafana"
        )

    for warning in warnings:
        logger.warning("production_guardian.config_warning", message=warning)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Production Guardian API",
        description=(
            "AI-powered autonomous operations system for film and media production. "
            "Monitors infrastructure telemetry, investigates incidents via Grafana MCP, "
            "and predicts production impact using Google Gemini."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow frontend in local, Vercel, and custom domains
    allowed_origins = [
        "https://production-guardian.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    if settings.frontend_url and settings.frontend_url not in allowed_origins:
        allowed_origins.append(settings.frontend_url.rstrip("/"))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root endpoint with interactive landing page
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Production Guardian API</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; justify-content: center; }
    .container { max-width: 720px; width: 100%; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
    h1 { margin-top: 0; color: #38bdf8; font-size: 28px; display: flex; align-items: center; gap: 10px; }
    p { color: #94a3b8; line-height: 1.6; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; background: #065f46; color: #34d399; margin-bottom: 20px; }
    .links { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 24px; }
    .card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; text-decoration: none; color: inherit; transition: all 0.2s; }
    .card:hover { border-color: #38bdf8; transform: translateY(-2px); }
    .card h3 { margin: 0 0 6px 0; color: #f1f5f9; font-size: 16px; }
    .card p { margin: 0; font-size: 13px; color: #64748b; }
    .status-row { display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding: 10px 0; font-size: 14px; }
    .status-val { color: #34d399; font-weight: 500; }
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">&#9679; ONLINE &amp; OPERATIONAL</div>
    <h1>&#127916; Production Guardian API</h1>
    <p>Autonomous AI operations &amp; incident management system for film production infrastructure.</p>
    
    <div style="margin: 24px 0;">
      <div class="status-row"><span>FastAPI Backend</span><span class="status-val">Port 8000 (Running)</span></div>
      <div class="status-row"><span>Grafana MCP Protocol</span><span class="status-val">/mcp (Active)</span></div>
      <div class="status-row"><span>Grafana Cloud Connection</span><span class="status-val">Live (mightyblackberry600)</span></div>
      <div class="status-row"><span>Database</span><span class="status-val">PostgreSQL 16 (Connected)</span></div>
    </div>

    <div class="links">
      <a href="http://localhost:3000" class="card">
        <h3>Web Application &rarr;</h3>
        <p>Open the Next.js production dashboard at :3000</p>
      </a>
      <a href="/api/docs" class="card">
        <h3>Interactive API Docs &rarr;</h3>
        <p>Explore Swagger UI OpenAPI specification</p>
      </a>
      <a href="/api/health" class="card">
        <h3>Health Check &rarr;</h3>
        <p>Inspect backend &amp; database health</p>
      </a>
      <a href="https://mightyblackberry600.grafana.net" target="_blank" class="card">
        <h3>Grafana Cloud &rarr;</h3>
        <p>Open Grafana Cloud telemetry stack</p>
      </a>
    </div>
  </div>
</body>
</html>"""

    @app.get("/docs", include_in_schema=False)
    async def docs_redirect():
        return RedirectResponse(url="/api/docs")

    @app.get("/redoc", include_in_schema=False)
    async def redoc_redirect():
        return RedirectResponse(url="/api/redoc")

    # Register routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(production.router, prefix="/api", tags=["production"])
    app.include_router(incidents.router, prefix="/api", tags=["incidents"])
    app.include_router(agent.router, prefix="/api", tags=["agent"])
    app.include_router(remediation.router, prefix="/api", tags=["remediation"])
    app.include_router(telemetry.router, prefix="/api", tags=["telemetry"])
    app.include_router(mcp.router, tags=["mcp"])

    return app


app = create_app()
