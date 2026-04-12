from fastapi import APIRouter, HTTPException

from app.services.pool_state import POOL_STATE
from app.services.pool_boundary import detect_pool_polygon
from app.services.frame_store import get_latest_frame

router = APIRouter(prefix="/api/pool", tags=["pool"])


@router.post("/detect")
def detect_pool_boundary():
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

    return {
        "ok": True,
        "detected_polygon": polygon
    }


@router.post("/confirm")
def confirm_pool_boundary():
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

    return {
        "ok": True,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.get("/status")
def pool_status():
    """
    Return current pool boundary state.
    """
    return {
        "boundary_set": POOL_STATE.boundary_set,
        "detected_polygon": POOL_STATE.detected_polygon,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.post("/clear")
def clear_pool_boundary():
    """
    Clear detected and confirmed pool boundaries for this session.
    """
    POOL_STATE.detected_polygon = None
    POOL_STATE.confirmed_polygon = None
    POOL_STATE.boundary_set = False

    return {"ok": True}