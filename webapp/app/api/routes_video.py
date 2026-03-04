import time
from typing import Generator, Optional

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.state import STATE
from app.services.stream_session import SESSION

router = APIRouter(prefix="/video", tags=["video"])

# Use laptop webcam for now. Try 0 first; if camera doesn't open, try 1.
CAMERA_INDEX = 0

def mjpeg_generator() -> Generator[bytes, None, None]:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(
            "Could not open camera. Try changing CAMERA_INDEX to 1, "
            "or allow camera permission for your terminal/VS Code."
        )

    boundary = b"--frame"

    try:
        while True:
            # Stop if user turned stream off
            if not STATE.streaming_enabled:
                break

            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            ok, jpg = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            data = jpg.tobytes()

            yield boundary + b"\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
            yield data + b"\r\n"

            time.sleep(0.03)  # ~30 fps
    finally:
        cap.release()

@router.get("/mjpeg")
def video_mjpeg(key: Optional[str] = None):
    # Require user has enabled streaming + valid key
    if not STATE.streaming_enabled:
        raise HTTPException(status_code=403, detail="Stream is off")
    if not SESSION.is_valid(key):
        raise HTTPException(status_code=401, detail="Invalid stream key")

    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )