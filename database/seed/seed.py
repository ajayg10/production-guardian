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


async def seed(db: AsyncSession, count: int = 10) -> None:
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

    INCIDENT_CATALOG = [
        {
            "title": "Storage Saturation on INGEST-01",
            "description": "High disk utilization on primary ingest volume /mnt/fast-ingest causing write contention and throttling incoming Scene 42 raw camera packages.",
            "severity": IncidentSeverity.CRITICAL,
            "status": IncidentStatus.ACTIVE,
            "scenario_type": "STORAGE_SATURATION",
            "root_cause": "Storage saturation on INGEST-01. Disk utilization approaching 94% capacity threshold.",
            "confidence": 0.94,
            "affected_systems": ["INGEST-01", "NAS-01"],
            "affected_scene_numbers": [42, 43],
            "production_impact": {
                "current_ingest_rate_gbps": 0.68,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 47.0,
                "deadline_at_risk": True,
                "downstream_risk": ["Scene 43 assembly blocked", "Daily delivery package at risk"],
            },
            "estimated_delay_minutes": 47.0,
            "deadline_at_risk": True,
            "offset_start": timedelta(minutes=14),
            "offset_resolved": None,
            "action": "Free 180 GB from completed proxy files on INGEST-01",
            "action_status": RemediationStatus.PENDING,
            "action_details": {"volume": "/mnt/fast-ingest", "target_gb": 180, "action": "purge_cache"},
        },
        {
            "title": "Network Degradation on NET-EDGE-07",
            "description": "Packet loss and latency spike on edge 10GbE network link between Stage 7 DIT cart and central storage.",
            "severity": IncidentSeverity.HIGH,
            "status": IncidentStatus.INVESTIGATING,
            "scenario_type": "NETWORK_DEGRADATION",
            "root_cause": "Dirty fiber optic transceiver connector on NET-EDGE-07 causing 8.5% packet drop.",
            "confidence": 0.96,
            "affected_systems": ["NET-EDGE-07", "NET-CORE-01"],
            "affected_scene_numbers": [42],
            "production_impact": {
                "current_ingest_rate_gbps": 1.25,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 22.0,
                "deadline_at_risk": True,
            },
            "estimated_delay_minutes": 22.0,
            "deadline_at_risk": True,
            "offset_start": timedelta(minutes=45),
            "offset_resolved": None,
            "action": "Failover to redundant 10GbE fiber link on NET-CORE-01",
            "action_status": RemediationStatus.APPROVED,
            "action_details": {"interface": "eth1_backup", "status": "switching"},
        },
        {
            "title": "Camera Overheat on CAM-03",
            "description": "VFX soundstage heat lamps caused enclosure temperature on CAM-03 to reach 78°C, dropping recording frames.",
            "severity": IncidentSeverity.HIGH,
            "status": IncidentStatus.RESOLVED,
            "scenario_type": "CAMERA_FAILURE",
            "root_cause": "Cooling fan exhaust blocked by heavy matte box accessory on CAM-03 rig.",
            "confidence": 0.91,
            "affected_systems": ["CAM-03"],
            "affected_scene_numbers": [41],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 12.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 12.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(hours=3, minutes=15),
            "offset_resolved": timedelta(hours=2, minutes=45),
            "action": "Reposition auxiliary soundstage cooling fan toward CAM-03 cage",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"camera": "CAM-03", "temp_before": 78.0, "temp_after": 42.0},
        },
        {
            "title": "Render Queue Bottleneck on EDIT-01",
            "description": "Concurrent 8K ProRes timeline export jobs saturated all 4 GPUs on EDIT-01 workstation.",
            "severity": IncidentSeverity.MEDIUM,
            "status": IncidentStatus.RESOLVED,
            "scenario_type": "RENDER_BOTTLENECK",
            "root_cause": "GPU VRAM exhaustion from unbatched ProRes timeline rendering jobs.",
            "confidence": 0.88,
            "affected_systems": ["EDIT-01"],
            "affected_scene_numbers": [41],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 0.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 0.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(hours=6),
            "offset_resolved": timedelta(hours=5, minutes=18),
            "action": "Reschedule non-critical editorial proxies to off-peak queue",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"workstation": "EDIT-01", "freed_vram_gb": 32},
        },
        {
            "title": "Media Checksum Corruption on NAS-01",
            "description": "High disk I/O caused checksum parity mismatch during automated camera raw verification on NAS volume.",
            "severity": IncidentSeverity.HIGH,
            "status": IncidentStatus.RESOLVED,
            "scenario_type": "MEDIA_INTEGRITY_FAILURE",
            "root_cause": "Faulty PCIe NVMe cache driver on NAS storage head node.",
            "confidence": 0.95,
            "affected_systems": ["NAS-01", "MEDIA-STORE-01"],
            "affected_scene_numbers": [40],
            "production_impact": {
                "current_ingest_rate_gbps": 1.70,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 18.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 18.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=1, hours=2),
            "offset_resolved": timedelta(days=1, hours=1, minutes=20),
            "action": "Re-verify checksums from secondary on-set shuttle drive backup",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"verified_files": 412, "errors_fixed": 3},
        },
        {
            "title": "DIT Cart Wireless Link Latency Spike on NET-EDGE-04",
            "description": "Wireless video telemetry dropped packets during remote vehicle chase sequence on Stage 3.",
            "severity": IncidentSeverity.MEDIUM,
            "status": IncidentStatus.RESOLVED,
            "scenario_type": "NETWORK_DEGRADATION",
            "root_cause": "RF interference from soundstage high-power lighting ballast on channel 36.",
            "confidence": 0.89,
            "affected_systems": ["NET-EDGE-04"],
            "affected_scene_numbers": [40],
            "production_impact": {
                "current_ingest_rate_gbps": 1.80,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 5.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 5.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=1, hours=5),
            "offset_resolved": timedelta(days=1, hours=4, minutes=45),
            "action": "Switch wireless transmission frequency to clean DFS band 120",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"new_frequency_ghz": 5.6, "packet_loss_after": "0.01%"},
        },
        {
            "title": "Ingest Card Reader CRC Error on INGEST-02",
            "description": "CFexpress Type B card reader generated bus errors during 8K RAW offload.",
            "severity": IncidentSeverity.LOW,
            "status": IncidentStatus.RESOLVED,
            "scenario_type": "STORAGE_SATURATION",
            "root_cause": "Thermal throttling on USB-C thunderbolt hub causing bus resets.",
            "confidence": 0.93,
            "affected_systems": ["INGEST-02"],
            "affected_scene_numbers": [40],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 8.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 8.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=2, hours=1),
            "offset_resolved": timedelta(days=2, minutes=40),
            "action": "Swap CFexpress card reader to dedicated PCIe direct interface",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"interface": "PCIe_Direct", "offload_speed_gbps": 1.95},
        },
        {
            "title": "GPU Out-of-Memory during Daily Assembly on EDIT-02",
            "description": "Exceeded 48GB VRAM limit when loading unrendered multi-camera Scene 39 timeline.",
            "severity": IncidentSeverity.MEDIUM,
            "status": IncidentStatus.CLOSED,
            "scenario_type": "RENDER_BOTTLENECK",
            "root_cause": "Full-resolution 8K timeline playback active without proxy switching.",
            "confidence": 0.97,
            "affected_systems": ["EDIT-02"],
            "affected_scene_numbers": [39],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 0.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 0.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=2, hours=8),
            "offset_resolved": timedelta(days=2, hours=7, minutes=30),
            "action": "Enable 1/4 resolution playback proxies for multi-cam timeline",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"playback_mode": "1/4_proxy", "fps": 24.0},
        },
        {
            "title": "SDI Genlock Frame Sync Loss on CAM-01",
            "description": "External tri-level sync signal drifted during multi-camera motion capture setup.",
            "severity": IncidentSeverity.LOW,
            "status": IncidentStatus.CLOSED,
            "scenario_type": "CAMERA_FAILURE",
            "root_cause": "Impedance mismatch on 75-ohm BNC cable termination from master clock.",
            "confidence": 0.90,
            "affected_systems": ["CAM-01"],
            "affected_scene_numbers": [38],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 0.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 0.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=3, hours=3),
            "offset_resolved": timedelta(days=3, hours=2, minutes=45),
            "action": "Replace 75-ohm terminator on master sync distributor output",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"jitter_ns": 0.8, "genlock_status": "locked"},
        },
        {
            "title": "Storage High-Watermark Alert on MEDIA-STORE-01",
            "description": "Archive volume reached 88% capacity after Day 43 wrap ingestion.",
            "severity": IncidentSeverity.LOW,
            "status": IncidentStatus.CLOSED,
            "scenario_type": "STORAGE_SATURATION",
            "root_cause": "Completed Day 40-42 raw takes not yet offloaded to cold LTO-8 tape backup.",
            "confidence": 0.94,
            "affected_systems": ["MEDIA-STORE-01"],
            "affected_scene_numbers": [37],
            "production_impact": {
                "current_ingest_rate_gbps": 1.85,
                "required_ingest_rate_gbps": 1.85,
                "projected_delay_minutes": 0.0,
                "deadline_at_risk": False,
            },
            "estimated_delay_minutes": 0.0,
            "deadline_at_risk": False,
            "offset_start": timedelta(days=4, hours=6),
            "offset_resolved": timedelta(days=4, hours=4),
            "action": "Trigger automated cold LTO-8 tape backup and archive purge",
            "action_status": RemediationStatus.COMPLETED,
            "action_details": {"archived_gb": 1250, "freed_capacity": "32%"},
        },
    ]

    target_count = max(1, count)
    created_count = 0

    for i in range(target_count):
        base_tmpl = INCIDENT_CATALOG[i % len(INCIDENT_CATALOG)]
        multiplier = i // len(INCIDENT_CATALOG)

        # Apply multiplier offset if count exceeds base catalog
        time_shift = timedelta(days=multiplier * 5)
        start_time = now - (base_tmpl["offset_start"] + time_shift)
        resolved_time = None
        if base_tmpl["offset_resolved"]:
            resolved_time = now - (base_tmpl["offset_resolved"] + time_shift)

        title = base_tmpl["title"]
        if multiplier > 0:
            title = f"{title} (Repeat #{multiplier + 1})"

        inc = Incident(
            id=str(uuid.uuid4()),
            production_id=production.id,
            title=title,
            description=base_tmpl["description"],
            severity=base_tmpl["severity"],
            status=base_tmpl["status"],
            scenario_type=base_tmpl["scenario_type"],
            root_cause=base_tmpl["root_cause"],
            confidence=base_tmpl["confidence"],
            affected_systems=base_tmpl["affected_systems"],
            affected_scene_numbers=base_tmpl["affected_scene_numbers"],
            production_impact=base_tmpl["production_impact"],
            estimated_delay_minutes=base_tmpl["estimated_delay_minutes"],
            deadline_at_risk=base_tmpl["deadline_at_risk"],
            started_at=start_time,
            resolved_at=resolved_time,
        )
        db.add(inc)
        await db.flush()

        if base_tmpl.get("action"):
            act = RemediationAction(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                action=base_tmpl["action"],
                action_type="SIMULATED",
                risk_level="LOW",
                expected_benefit="HIGH",
                expected_recovery_minutes=15,
                confidence=base_tmpl["confidence"],
                status=base_tmpl["action_status"],
                details=base_tmpl.get("action_details", {}),
            )
            db.add(act)

        created_count += 1

    await db.commit()
    print(f"  ✓ Created {created_count} production incidents across full shoot history")
    print("  ✓ Attached remediation history and production impact models")
    print("\n✅ Seed complete!")
    print("\nProduction context:")
    print(f"  Production: NIGHTFALL (Day {production.production_day})")
    print(f"  Location: {production.primary_location}")
    print(f"  Current Scene: {production.current_scene_number}")
    print(f"  Shoot Window: {production.shoot_window_start}–{production.shoot_window_end}")


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Seed Production Guardian database")
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=10,
        help="Number of incidents to seed (default: 10, can be any number)",
    )
    args = parser.parse_args()

    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ Tables created/verified")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed(session, count=args.count)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
