import time
from typing import Generator, Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from picamera2 import Picamera2
from ultralytics import YOLO

from app.services.state import STATE
from app.services.stream_session import SESSION
from app.services.pool_state import POOL_STATE
from app.services.pool_boundary import create_pool_mask, compute_box_pool_overlap

router = APIRouter(prefix="/video", tags=["video"])

# Camera settings
W = 640
H = 480
RES = (W, H)

# Overlap threshold:
# if overlap between person/pet box and pool mask is above this,
# the system considers the object to be in the pool
OVERLAP_THRESHOLD = 0.20

# Load YOLO model once
model = YOLO("/home/poolai/YOLO/pool-ai/yolo11-pool_ncnn_model", task="detect")


def mjpeg_generator() -> Generator[bytes, None, None]:
    picam2 = None
    pool_mask = None
    last_confirmed_polygon = None

    try:
        # Start Pi camera
        picam2 = Picamera2()
        picam2.preview_configuration.main.size = RES
        picam2.preview_configuration.main.format = "RGB888"
        picam2.preview_configuration.controls.FrameRate = 60
        picam2.preview_configuration.align()
        picam2.configure("preview")
        picam2.start()

        # Small warm-up delay
        time.sleep(0.2)

        boundary = b"--frame"
        fps = 0.0
        t_start = time.time()

        while True:
            # Stop streaming quickly if user disconnects
            if not STATE.streaming_enabled:
                break

            # Capture one frame from Pi camera
            frame = picam2.capture_array()
            if frame is None:
                time.sleep(0.02)
                continue

            # Convert RGB -> BGR for OpenCV / YOLO plotting
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Rebuild mask only if confirmed polygon changed
            if POOL_STATE.confirmed_polygon != last_confirmed_polygon:
                if POOL_STATE.confirmed_polygon:
                    pool_mask = create_pool_mask(
                        frame_bgr.shape,
                        POOL_STATE.confirmed_polygon
                    )
                else:
                    pool_mask = None

                last_confirmed_polygon = POOL_STATE.confirmed_polygon

            # Run YOLO detection
            results = model(frame_bgr, conf=0.25, verbose=False)
            result = results[0]

            # Draw YOLO boxes first
            annotated_frame = result.plot()

            # Draw detected pool boundary (yellow) if available but not confirmed
            if POOL_STATE.detected_polygon and not POOL_STATE.boundary_set:
                pts = np.array(POOL_STATE.detected_polygon, dtype=np.int32)
                cv2.polylines(
                    annotated_frame,
                    [pts],
                    isClosed=True,
                    color=(0, 255, 255),   # yellow
                    thickness=2
                )
                cv2.putText(
                    annotated_frame,
                    "Detected Pool Boundary (Not Confirmed)",
                    (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )

            # Draw confirmed pool boundary (blue)
            if POOL_STATE.confirmed_polygon and POOL_STATE.boundary_set:
                pts = np.array(POOL_STATE.confirmed_polygon, dtype=np.int32)
                cv2.polylines(
                    annotated_frame,
                    [pts],
                    isClosed=True,
                    color=(255, 0, 0),   # blue
                    thickness=3
                )
                cv2.putText(
                    annotated_frame,
                    "Confirmed Pool Boundary",
                    (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 0, 0),
                    2
                )

            # Overlap detection
            person_or_pet_in_pool = False

            if result.boxes is not None and pool_mask is not None:
                for box in result.boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())

                    # COCO classes:
                    # 0 = person
                    # 15 = cat
                    # 16 = dog
                    if cls_id not in [0, 15, 16]:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    overlap = compute_box_pool_overlap(pool_mask, (x1, y1, x2, y2))

                    if overlap >= OVERLAP_THRESHOLD:
                        person_or_pet_in_pool = True

                        label_text = f"In Pool ({overlap:.2f})"
                        cv2.putText(
                            annotated_frame,
                            label_text,
                            (int(x1), max(20, int(y1) - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2
                        )

            # Warning message
            if person_or_pet_in_pool:
                cv2.putText(
                    annotated_frame,
                    "WARNING: HUMAN/ANIMAL OVERLAP WITH POOL",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    3
                )

            # FPS calculation
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
                2
            )

            # Check again before streaming frame out
            if not STATE.streaming_enabled:
                break

            # Encode frame as JPEG
            ok, jpg = cv2.imencode(".jpg", annotated_frame)
            if not ok:
                continue

            data = jpg.tobytes()

            # Send MJPEG frame to browser
            yield boundary + b"\r\n"
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8")
            yield data + b"\r\n"

            # Small delay to keep stream responsive
            time.sleep(0.01)

    except GeneratorExit:
        # Browser closed connection
        pass
    except Exception as e:
        print(f"Video stream error: {e}")
    finally:
        if picam2 is not None:
            try:
                picam2.stop()
            except Exception:
                pass
            try:
                picam2.close()
            except Exception:
                pass


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