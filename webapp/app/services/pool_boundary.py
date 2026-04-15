import cv2
import numpy as np
from typing import List, Tuple, Optional

Point = Tuple[int, int]


def sanitize_polygon(points: List[Point]) -> Optional[List[Point]]:
    """
    Turn an arbitrary point list into a valid simple polygon using convex hull.
    """
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
    Stricter prototype pool detector.

    Important behavior:
    - returns None if confidence is low
    - does NOT guess using a bounding rectangle fallback
    """
    img = frame.copy()
    h, w = img.shape[:2]

    # Latest frame from Picamera2 is RGB
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    # Tune this later if needed
    lower_blue = np.array([80, 40, 40])
    upper_blue = np.array([140, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    # Require a reasonably large region
    min_area = 0.08 * (w * h)
    if area < min_area:
        return None

    x, y, bw, bh = cv2.boundingRect(largest)

    # Reject tiny or skinny regions
    if bw < 0.2 * w or bh < 0.15 * h:
        return None

    # Reject regions too high in the frame
    # Pools in your setup should usually be lower / centered, not near the very top
    if y < 0.10 * h:
        return None

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    # Require a decent polygon, not a random blob
    if len(approx) < 4 or len(approx) > 12:
        return None

    raw_polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
    polygon = sanitize_polygon(raw_polygon)

    if polygon is None or len(polygon) < 4:
        return None

    return polygon


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