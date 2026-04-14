from fastapi import APIRouter
from app.services.state import STATE

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status")
def get_status():
    return {
        "boundary_set": STATE.pool_boundary_set,
        "in_pool": STATE.object_in_pool,
        "alive": STATE.alive_status,
        "stream_on": STATE.streaming_enabled,
        "alert_level": STATE.alert_level,
        "last_event": STATE.last_event,
        "last_event_time": (
            STATE.last_event_time.isoformat() if STATE.last_event_time else None
        ),
    }