"""
Database seed script for Production Guardian.

Seeds:
- NIGHTFALL production
- Scenes 40-45 with realistic film production data
- Scene 42 as the critical demo scene

Run from the apps/api directory:
  python ../../database/seed/seed.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Add apps/api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, delete

from datetime import datetime, timezone, timedelta

from models.database import (
    Production,
    Scene,
    ScenePriority,
    SceneStatus,
    ProductionStatus,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    RemediationAction,
    RemediationStatus,
    AgentRun,
    AgentRunStatus,
)
from core.database import Base


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://guardian:guardian@localhost:5432/production_guardian",
)


async def seed(db: AsyncSession) -> None:
    """Seed all production data."""
    print("🎬 Seeding Production Guardian database...")

    # Import child models to delete in foreign key dependency order
    from models.database import Incident, RemediationAction, AgentRun

    # Clear existing data
    await db.execute(delete(RemediationAction))
    await db.execute(delete(AgentRun))
    await db.execute(delete(Incident))
    await db.execute(delete(Scene))
    await db.execute(delete(Production))
    await db.commit()
    print("  ✓ Cleared existing data")

    # Create NIGHTFALL production
    production = Production(
        id=str(uuid.uuid4()),
        name="nightfall",
        display_name="NIGHTFALL",
        genre="Sci-Fi Thriller",
        production_day=47,
        status=ProductionStatus.ACTIVE,
        shoot_window_start="08:00",
        shoot_window_end="18:00",
        current_scene_number=42,
        primary_location="Stage 7 — Silverline Studios",
    )
    db.add(production)
    await db.flush()
    print(f"  ✓ Created production: NIGHTFALL (id: {production.id[:8]}...)")

    # Scene data
    scenes_data = [
        {
            "scene_number": 40,
            "title": "The Signal",
            "description": "Commander Reyes discovers the anomalous signal from deep space. INT. COMMAND DECK.",
            "location": "Stage 5 — Command Deck",
            "priority": ScenePriority.MEDIUM,
            "status": SceneStatus.COMPLETED,
            "estimated_footage_gb": 420.0,
            "editorial_deadline": "18:00",
            "dependent_scene_numbers": [41],
            "estimated_duration_hours": 6.0,
        },
        {
            "scene_number": 41,
            "title": "The Briefing",
            "description": "Senior crew reviews anomaly data. INT. BRIEFING ROOM. Night.",
            "location": "Stage 5 — Briefing Room",
            "priority": ScenePriority.MEDIUM,
            "status": SceneStatus.COMPLETED,
            "estimated_footage_gb": 310.0,
            "editorial_deadline": "18:00",
            "dependent_scene_numbers": [42],
            "estimated_duration_hours": 4.5,
        },
        {
            "scene_number": 42,
            "title": "Point of No Return",
            "description": (
                "Crew enters the anomaly zone. Critical action sequence. "
                "EXT. SPACE / INT. SHIP. High-intensity visual effects work."
            ),
            "location": "Stage 7 — Main Stage",
            "priority": ScenePriority.CRITICAL,
            "status": SceneStatus.IN_PROGRESS,
            "estimated_footage_gb": 680.0,
            "editorial_deadline": "22:00",
            "dependent_scene_numbers": [43, 44],
            "estimated_duration_hours": 10.0,
        },
        {
            "scene_number": 43,
            "title": "Inside the Anomaly",
            "description": "The crew's first encounter with the anomaly interior. VFX-heavy sequence.",
            "location": "Stage 7 — VFX Stage",
            "priority": ScenePriority.HIGH,
            "status": SceneStatus.SCHEDULED,
            "estimated_footage_gb": 540.0,
            "editorial_deadline": "23:00",
            "dependent_scene_numbers": [44],
            "estimated_duration_hours": 8.0,
        },
        {
            "scene_number": 44,
            "title": "Contact",
            "description": "First contact sequence. Emotionally pivotal scene. INT. ANOMALY CORE.",
            "location": "Stage 7 — VFX Stage",
            "priority": ScenePriority.HIGH,
            "status": SceneStatus.SCHEDULED,
            "estimated_footage_gb": 380.0,
            "editorial_deadline": "23:59",
            "dependent_scene_numbers": [45],
            "estimated_duration_hours": 6.0,
        },
        {
            "scene_number": 45,
            "title": "The Return",
            "description": "Resolution sequence. Crew emerges changed. EXT. SPACE.",
            "location": "Stage 3 — Exterior",
            "priority": ScenePriority.MEDIUM,
            "status": SceneStatus.SCHEDULED,
            "estimated_footage_gb": 290.0,
            "editorial_deadline": None,
            "dependent_scene_numbers": [],
            "estimated_duration_hours": 4.5,
        },
    ]

    for scene_data in scenes_data:
        scene = Scene(
            id=str(uuid.uuid4()),
            production_id=production.id,
            **scene_data,
        )
        db.add(scene)

    print(f"  ✓ Created {len(scenes_data)} scenes (40-45)")
    print("  ✓ Scene 42 'Point of No Return' marked as CRITICAL, IN_PROGRESS")

    # -------------------------------------------------------------------------
    # Seed Realistic Production Incidents
    # -------------------------------------------------------------------------
    now = datetime.now(timezone.utc)

    # 1. Active critical incident on critical Scene 42
    inc_active = Incident(
        id=str(uuid.uuid4()),
        production_id=production.id,
        title="Storage Saturation on INGEST-01",
        description="High disk utilization on primary ingest volume /mnt/fast-ingest causing write contention and throttling incoming Scene 42 raw camera packages.",
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.ACTIVE,
        scenario_type="STORAGE_SATURATION",
        root_cause="Storage saturation on INGEST-01. Disk utilization approaching 94% capacity threshold.",
        confidence=0.94,
        affected_systems=["INGEST-01", "NAS-01"],
        affected_scene_numbers=[42, 43],
        production_impact={
            "current_ingest_rate_gbps": 0.68,
            "required_ingest_rate_gbps": 1.85,
            "projected_delay_minutes": 47.0,
            "deadline_at_risk": True,
            "downstream_risk": ["Scene 43 assembly blocked", "Daily delivery package at risk"],
        },
        estimated_delay_minutes=47.0,
        deadline_at_risk=True,
        started_at=now - timedelta(minutes=14),
    )
    db.add(inc_active)
    await db.flush()

    action_active = RemediationAction(
        id=str(uuid.uuid4()),
        incident_id=inc_active.id,
        action="Free 180 GB from completed proxy files on INGEST-01",
        action_type="SIMULATED",
        risk_level="LOW",
        expected_benefit="HIGH",
        expected_recovery_minutes=15,
        confidence=0.92,
        status=RemediationStatus.PENDING,
        details={"volume": "/mnt/fast-ingest", "target_gb": 180, "action": "purge_cache"},
    )
    db.add(action_active)

    # 2. Resolved incident from earlier today (Network Degradation)
    inc_network = Incident(
        id=str(uuid.uuid4()),
        production_id=production.id,
        title="Network Degradation on NET-EDGE-07",
        description="Packet loss and latency spike on edge 10GbE network link between Stage 7 DIT cart and central storage.",
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.RESOLVED,
        scenario_type="NETWORK_DEGRADATION",
        root_cause="Dirty fiber optic transceiver connector on NET-EDGE-07 causing 8.5% packet drop.",
        confidence=0.96,
        affected_systems=["NET-EDGE-07", "NET-CORE-01"],
        affected_scene_numbers=[41],
        production_impact={
            "current_ingest_rate_gbps": 1.40,
            "required_ingest_rate_gbps": 1.85,
            "projected_delay_minutes": 15.0,
            "deadline_at_risk": False,
        },
        estimated_delay_minutes=15.0,
        deadline_at_risk=False,
        started_at=now - timedelta(hours=3, minutes=25),
        investigated_at=now - timedelta(hours=3, minutes=20),
        resolved_at=now - timedelta(hours=3, minutes=5),
    )
    db.add(inc_network)
    await db.flush()

    action_network = RemediationAction(
        id=str(uuid.uuid4()),
        incident_id=inc_network.id,
        action="Reroute upload traffic to redundant Stage 7 secondary fiber link",
        action_type="SIMULATED",
        risk_level="LOW",
        expected_benefit="HIGH",
        expected_recovery_minutes=10,
        confidence=0.95,
        status=RemediationStatus.COMPLETED,
        details={"interface": "eth1_backup", "status": "active"},
    )
    db.add(action_network)

    # 3. Resolved incident from yesterday (Camera Thermal Alert)
    inc_camera = Incident(
        id=str(uuid.uuid4()),
        production_id=production.id,
        title="Camera Overheat on CAM-03",
        description="VFX soundstage heat lamps caused enclosure temperature on CAM-03 to reach 78°C, dropping recording frames.",
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.RESOLVED,
        scenario_type="CAMERA_FAILURE",
        root_cause="Cooling fan exhaust blocked by heavy matte box accessory on CAM-03 rig.",
        confidence=0.91,
        affected_systems=["CAM-03"],
        affected_scene_numbers=[40],
        estimated_delay_minutes=12.0,
        deadline_at_risk=False,
        started_at=now - timedelta(days=1, hours=2),
        investigated_at=now - timedelta(days=1, hours=1, minutes=50),
        resolved_at=now - timedelta(days=1, hours=1, minutes=30),
    )
    db.add(inc_camera)
    await db.flush()

    action_camera = RemediationAction(
        id=str(uuid.uuid4()),
        incident_id=inc_camera.id,
        action="Reposition auxiliary soundstage cooling fan toward CAM-03 cage",
        action_type="SIMULATED",
        risk_level="LOW",
        expected_benefit="HIGH",
        expected_recovery_minutes=8,
        confidence=0.90,
        status=RemediationStatus.COMPLETED,
        details={"camera": "CAM-03", "temp_before": 78.0, "temp_after": 42.0},
    )
    db.add(action_camera)

    # 4. Closed incident from Day 45 (Render Queue Contention)
    inc_render = Incident(
        id=str(uuid.uuid4()),
        production_id=production.id,
        title="Render Bottleneck on EDIT-01",
        description="Concurrent 8K ProRes timeline export jobs saturated all 4 GPUs on EDIT-01 workstation.",
        severity=IncidentSeverity.MEDIUM,
        status=IncidentStatus.CLOSED,
        scenario_type="RENDER_BOTTLENECK",
        root_cause="GPU VRAM exhaustion from unbatched ProRes timeline rendering jobs.",
        confidence=0.88,
        affected_systems=["EDIT-01"],
        affected_scene_numbers=[40],
        estimated_delay_minutes=0.0,
        deadline_at_risk=False,
        started_at=now - timedelta(days=2, hours=4),
        investigated_at=now - timedelta(days=2, hours=3, minutes=55),
        resolved_at=now - timedelta(days=2, hours=3, minutes=20),
    )
    db.add(inc_render)

    await db.commit()
    print("  ✓ Created 4 production incidents (1 Active, 2 Resolved, 1 Closed)")
    print("  ✓ Attached remediation history and production impact models")
    print("\n✅ Seed complete!")
    print("\nProduction context:")
    print(f"  Production: NIGHTFALL (Day {production.production_day})")
    print(f"  Location: {production.primary_location}")
    print(f"  Current Scene: {production.current_scene_number}")
    print(f"  Shoot Window: {production.shoot_window_start}–{production.shoot_window_end}")


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ Tables created/verified")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
