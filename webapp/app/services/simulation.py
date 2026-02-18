from datetime import datetime
from app.services.state import STATE
from app.services.event_bus import BUS

async def set_pool_boundary():
    STATE.pool_boundary_set = True
    STATE.last_event = "Pool boundary set"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "boundary_set", "state": STATE.__dict__})

async def object_entered(kind: str = "person"):
    STATE.object_in_pool = True
    STATE.alive_status = "unknown"
    STATE.alert_level = "warning"
    STATE.last_event = f"{kind} entered pool"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "entered", "kind": kind, "state": STATE.__dict__})

async def alive_update(status: str):
    # status: "alive" or "distress"
    STATE.alive_status = status
    STATE.alert_level = "info" if status == "alive" else "critical"
    STATE.last_event = f"Alive status updated: {status}"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "alive_update", "status": status, "state": STATE.__dict__})

async def object_exited():
    STATE.object_in_pool = False
    STATE.alive_status = "unknown"
    STATE.alert_level = "none"
    STATE.last_event = "Object exited pool"
    STATE.last_event_time = datetime.utcnow()
    await BUS.broadcast({"type": "exited", "state": STATE.__dict__})
