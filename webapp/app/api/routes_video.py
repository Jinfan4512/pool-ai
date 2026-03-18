import time
from typing import Generator, Optional

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from picamera2 import Picamera2

from app.services.state import STATE
from app.services.stream_session import SESSION

router = APIRouter(prefix="/video", tags=["video"])

def mjpeg_generator() -> Generator[bytes, None, None]:
    picam2 = Picamera2()

    # 1280x720 is a good starting point for live streaming
    config = picam2.create_video_configuration(
        main={"size": (1280, 720)}
    )
    picam2.configure(config)
    picam2.start()

    boundary = b"--frame"

    try:
        while True:
            if not STATE.streaming_enabled:
                break

            # Picamera2 returns RGB array
            frame = picam2.capture_array()

            # Convert RGB to BGR for OpenCV encoding
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            ok, jpg = cv2.imencode(".jpg", frame_bgr)
            if not ok:
                continue

            data = jpg.tobytes()

            yield boundary + b"\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
            yield data + b"\r\n"

            time.sleep(0.03)
    finally:
        picam2.stop()

@router.get("/mjpeg")
def video_mjpeg(key: Optional[str] = None):
    if not STATE.streaming_enabled:
        raise HTTPException(status_code=403, detail="Stream is off")
    if not SESSION.is_valid(key):
        raise HTTPException(status_code=401, detail="Invalid stream key")

    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
