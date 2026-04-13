from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.services.pool_state import POOL_STATE
from app.services.pool_boundary import detect_pool_polygon
from app.services.frame_store import get_latest_frame
from app.services.state import STATE
from app.services.event_bus import BUS

router = APIRouter(prefix="/api/pool", tags=["pool"])


@router.post("/detect")
async def detect_pool_boundary():
    """
    Detect the pool boundary from the latest frame already captured
    by the live video stream.
    """
    frame = get_latest_frame()

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail="No camera frame available. Start the live stream first."
        )

    polygon = detect_pool_polygon(frame)

    if polygon is None:
        raise HTTPException(
            status_code=404,
            detail="Could not detect pool boundary from current frame"
        )

    POOL_STATE.detected_polygon = polygon

    STATE.last_event = "Pool boundary detected by AI"
    STATE.last_event_time = datetime.utcnow()

    await BUS.broadcast({
        "type": "pool_detected",
        "state": STATE.__dict__,
        "detected_polygon": polygon
    })

    return {
        "ok": True,
        "detected_polygon": polygon
    }


@router.post("/confirm")
async def confirm_pool_boundary():
    """
    Confirm the most recently detected pool boundary for this server session.
    """
    if not POOL_STATE.detected_polygon:
        raise HTTPException(
            status_code=400,
            detail="No detected pool boundary available"
        )

    POOL_STATE.confirmed_polygon = POOL_STATE.detected_polygon
    POOL_STATE.boundary_set = True

    STATE.pool_boundary_set = True
    STATE.last_event = "Pool boundary confirmed by user"
    STATE.last_event_time = datetime.utcnow()

    await BUS.broadcast({
        "type": "pool_confirmed",
        "state": STATE.__dict__,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    })

    return {
        "ok": True,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.get("/status")
async def pool_status():
    """
    Return current pool boundary state.
    """
    return {
        "boundary_set": POOL_STATE.boundary_set,
        "detected_polygon": POOL_STATE.detected_polygon,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.post("/clear")
async def clear_pool_boundary():
    """
    Clear detected and confirmed pool boundaries for this session.
    """
    POOL_STATE.detected_polygon = None
    POOL_STATE.confirmed_polygon = None
    POOL_STATE.boundary_set = False

    STATE.pool_boundary_set = False
    STATE.last_event = "Pool boundary cleared"
    STATE.last_event_time = datetime.utcnow()

    await BUS.broadcast({
        "type": "pool_cleared",
        "state": STATE.__dict__,
    })

    return {"ok": True}