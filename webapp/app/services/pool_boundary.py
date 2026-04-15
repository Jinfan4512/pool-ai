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
    Detect pool boundary from the latest RGB frame.
    """
    img = frame.copy()
    h, w = img.shape[:2]

    # FIX: latest frame is RGB, not BGR
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    lower_blue = np.array([80, 30, 30])
    upper_blue = np.array([140, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)

    if cv2.contourArea(largest) < 0.05 * (w * h):
        return None

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    if len(approx) < 4:
        x, y, bw, bh = cv2.boundingRect(largest)
        raw_polygon = [(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)]
    else:
        raw_polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]

    return sanitize_polygon(raw_polygon)


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
    """
    overlap_ratio = pool pixels inside box / box area
    """
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
    """
    Return True if the center of the box is inside the polygon.
    """
    polygon_points = sanitize_polygon(polygon_points)
    if polygon_points is None:
        return False

    x1, y1, x2, y2 = box
    cx = (float(x1) + float(x2)) / 2.0
    cy = (float(y1) + float(y2)) / 2.0

    pts = np.array(polygon_points, dtype=np.int32)
    result = cv2.pointPolygonTest(pts, (cx, cy), False)

    return result >= 0