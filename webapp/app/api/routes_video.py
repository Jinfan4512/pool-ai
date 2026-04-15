import time
from datetime import datetime
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
from app.services.pool_boundary import (
    create_pool_mask,
    compute_box_pool_overlap,
    box_center_in_polygon,
)
from app.services.frame_store import set_latest_frame

router = APIRouter(prefix="/video", tags=["video"])

W = 1280
H = 720
RES = (W, H)

OVERLAP_THRESHOLD = 0.10

model = YOLO("/home/poolai/YOLO/pool-ai/yolo11-improved2_ncnn_model", task="detect")

# Custom model class IDs
CAT_CLASS_ID = 0
DOG_CLASS_ID = 1
PERSON_CLASS_ID = 2
POOL_CLASS_ID = 3


def mjpeg_generator() -> Generator[bytes, None, None]:
    picam2 = None
    pool_mask = None
    last_confirmed_polygon = None
    prev_in_pool = False

    try:
        picam2 = Picamera2()
        picam2.preview_configuration.main.size = RES
        picam2.preview_configuration.main.format = "RGB888"
        picam2.preview_configuration.controls.FrameRate = 60
        picam2.preview_configuration.align()
        picam2.configure("preview")
        picam2.start()

        time.sleep(0.2)

        boundary = b"--frame"
        fps = 0.0
        t_start = time.time()

        while True:
            if not STATE.streaming_enabled:
                break

            frame = picam2.capture_array()
            if frame is None:
                time.sleep(0.02)
                continue

            frame_for_model = frame.copy()
            set_latest_frame(frame_for_model)

            if POOL_STATE.confirmed_polygon != last_confirmed_polygon:
                if POOL_STATE.confirmed_polygon:
                    pool_mask = create_pool_mask(
                        frame_for_model.shape,
                        POOL_STATE.confirmed_polygon
                    )
                else:
                    pool_mask = None

                last_confirmed_polygon = POOL_STATE.confirmed_polygon

            results = model(frame_for_model, conf=0.25, verbose=False)
            result = results[0]
            annotated_frame = result.plot()

            # Draw detected pool boundary (yellow) if not confirmed
            if POOL_STATE.detected_polygon and not POOL_STATE.boundary_set:
                pts = np.array(POOL_STATE.detected_polygon, dtype=np.int32)
                cv2.polylines(
                    annotated_frame,
                    [pts],
                    isClosed=True,
                    color=(0, 255, 255),
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
                    color=(255, 0, 0),
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

            # -----------------------------
            # Person / animal in-pool detection
            # -----------------------------
            max_overlap = 0.0
            in_pool_now = False

            if result.boxes is not None and POOL_STATE.confirmed_polygon is not None:
                for box in result.boxes:
                    cls_id = int(box.cls[0].item())

                    # Only track cat, dog, person for alerts
                    if cls_id not in [CAT_CLASS_ID, DOG_CLASS_ID, PERSON_CLASS_ID]:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    overlap = 0.0
                    if pool_mask is not None:
                        overlap = compute_box_pool_overlap(pool_mask, (x1, y1, x2, y2))

                    center_inside = box_center_in_polygon(
                        POOL_STATE.confirmed_polygon,
                        (x1, y1, x2, y2)
                    )

                    if overlap > max_overlap:
                        max_overlap = overlap

                    cv2.putText(
                        annotated_frame,
                        f"Overlap {overlap:.2f}",
                        (int(x1), min(H - 20, int(y2) + 25)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )

                    if center_inside:
                        cv2.putText(
                            annotated_frame,
                            "CENTER INSIDE",
                            (int(x1), max(20, int(y1) - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2
                        )

                    if center_inside or overlap >= OVERLAP_THRESHOLD:
                        in_pool_now = True

            print(
                f"DEBUG overlap={max_overlap:.2f}, "
                f"threshold={OVERLAP_THRESHOLD:.2f}, "
                f"in_pool_now={in_pool_now}"
            )

            STATE.pool_boundary_set = POOL_STATE.boundary_set
            STATE.object_in_pool = in_pool_now
            STATE.alive_status = "alive" if in_pool_now else "unknown"
            STATE.alert_level = "warning" if in_pool_now else "none"

            if in_pool_now and not prev_in_pool:
                STATE.last_event = "Human or animal detected in pool"
                STATE.last_event_time = datetime.utcnow()

            if not in_pool_now and prev_in_pool:
                STATE.last_event = "Object exited pool"
                STATE.last_event_time = datetime.utcnow()

            prev_in_pool = in_pool_now

            if in_pool_now:
                cv2.putText(
                    annotated_frame,
                    "WARNING: HUMAN/ANIMAL OVERLAP WITH POOL",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    3
                )

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