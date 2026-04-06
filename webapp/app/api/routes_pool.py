import time
import cv2
from fastapi import APIRouter, HTTPException
from picamera2 import Picamera2

from app.services.pool_state import POOL_STATE
from app.services.pool_boundary import detect_pool_polygon

router = APIRouter(prefix="/api/pool", tags=["pool"])

W = 1280
H = 720
RES = (W, H)


def capture_single_frame():
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = RES
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.controls.FrameRate = 30
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    time.sleep(0.2)

    try:
        frame = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame_bgr
    finally:
        picam2.stop()
        try:
            picam2.close()
        except Exception:
            pass


@router.post("/detect")
def detect_pool_boundary():
    frame = capture_single_frame()
    polygon = detect_pool_polygon(frame)

    if polygon is None:
        raise HTTPException(status_code=404, detail="Could not detect pool boundary")

    POOL_STATE.detected_polygon = polygon
    return {
        "ok": True,
        "detected_polygon": polygon
    }


@router.post("/confirm")
def confirm_pool_boundary():
    if not POOL_STATE.detected_polygon:
        raise HTTPException(status_code=400, detail="No detected pool boundary available")

    POOL_STATE.confirmed_polygon = POOL_STATE.detected_polygon
    POOL_STATE.boundary_set = True

    return {
        "ok": True,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.get("/status")
def pool_status():
    return {
        "boundary_set": POOL_STATE.boundary_set,
        "detected_polygon": POOL_STATE.detected_polygon,
        "confirmed_polygon": POOL_STATE.confirmed_polygon
    }


@router.post("/clear")
def clear_pool_boundary():
    POOL_STATE.detected_polygon = None
    POOL_STATE.confirmed_polygon = None
    POOL_STATE.boundary_set = False
    return {"ok": True}