import time
from typing import Generator, Optional

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from picamera2 import Picamera2
from ultralytics import YOLO

from app.services.state import STATE
from app.services.stream_session import SESSION

router = APIRouter(prefix="/video", tags=["video"])

# Camera settings
W = 640
H = 480
RES = (W, H)

# Load YOLO model once when the module is imported
# Change this path if your Raspberry Pi model folder is elsewhere
model = YOLO("/home/poolai/YOLO/pool-ai/yolo11-pool_ncnn_model", task="detect")


def mjpeg_generator() -> Generator[bytes, None, None]:
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = RES
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.controls.FrameRate = 60
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    boundary = b"--frame"

    fps = 0.0
    t_start = time.time()

    try:
        while True:
            if not STATE.streaming_enabled:
                break

            frame = picam2.capture_array()

            results = model(frame, conf=0.25, verbose=False)
            annotated_frame = results[0].plot()

            delta_t = time.time() - t_start
            t_start = time.time()
            if delta_t > 0:
                fps = fps * 0.8 + 0.2 / delta_t

            cv2.putText(
                annotated_frame,
                f"FPS: {round(fps, 1)}",
                (int(W * 0.01), int(H * 0.075)),
                cv2.FONT_HERSHEY_SIMPLEX,
                H * 0.002,
                (0, 0, 255),
                2,
            )

            if not STATE.streaming_enabled:
                break

            ok, jpg = cv2.imencode(".jpg", annotated_frame)
            if not ok:
                continue

            data = jpg.tobytes()

            yield boundary + b"\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
            yield data + b"\r\n"

            time.sleep(0.01)

    except GeneratorExit:
        pass
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