import cv2
import numpy as np
from typing import List, Tuple, Optional
from ultralytics import YOLO

Point = Tuple[int, int]

# Load model once here for pool-boundary proposal
model = YOLO("/home/poolai/YOLO/pool-ai/yolo11-improved2_ncnn_model", task="detect")

# CHANGE THIS after you print model.names
POOL_CLASS_ID = 3


def sanitize_polygon(points: List[Point]) -> Optional[List[Point]]:
    if not points or len(points) < 3:
        return None

    pts = np.array(points, dtype=np.int32)
    hull = cv2.convexHull(pts)
    hull_points = [(int(p[0][0]), int(p[0][1])) for p in hull]

    if len(hull_points) < 3:
        return None

    return hull_points


def detect_pool_polygon(frame) -> Optional[List[Point]]:
    """
    Detect pool boundary using YOLO pool box, not HSV blue thresholding.
    Returns a rectangle polygon from the best detected pool box.
    """
    results = model(frame, conf=0.25, verbose=False)
    result = results[0]

    if result.boxes is None:
        return None

    best_box = None
    best_conf = -1.0

    for box in result.boxes:
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())

        if cls_id != POOL_CLASS_ID:
            continue

        if conf > best_conf:
            best_conf = conf
            best_box = box

    if best_box is None:
        return None

    x1, y1, x2, y2 = best_box.xyxy[0].tolist()

    polygon = [
        (int(x1), int(y1)),
        (int(x2), int(y1)),
        (int(x2), int(y2)),
        (int(x1), int(y2)),
    ]

    return sanitize_polygon(polygon)


def create_pool_mask(frame_shape, polygon_points: List[Point]):
    polygon_points = sanitize_polygon(polygon_points)
    if polygon_points is None:
        h, w = frame_shape[:2]
        return np.zeros((h, w), dtype=np.uint8)

    h, w = frame_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    pts = np.array(polygon_points, dtype=np.int32)
    cv2.fillPoly(mask, [pts], 255)

    return mask


def compute_box_pool_overlap(mask, box):
    x1, y1, x2, y2 = box

    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = max(0, int(x2))
    y2 = max(0, int(y2))

    if x2 <= x1 or y2 <= y1:
        return 0.0

    roi = mask[y1:y2, x1:x2]
    if roi.size == 0:
        return 0.0

    pool_pixels = cv2.countNonZero(roi)
    box_area = (x2 - x1) * (y2 - y1)

    if box_area == 0:
        return 0.0

    return pool_pixels / box_area


def box_center_in_polygon(polygon_points: List[Point], box) -> bool:
    polygon_points = sanitize_polygon(polygon_points)
    if polygon_points is None:
        return False

    x1, y1, x2, y2 = box
    cx = (float(x1) + float(x2)) / 2.0
    cy = (float(y1) + float(y2)) / 2.0

    pts = np.array(polygon_points, dtype=np.int32)
    result = cv2.pointPolygonTest(pts, (cx, cy), False)

    return result >= 0