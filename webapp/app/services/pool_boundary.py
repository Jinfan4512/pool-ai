import cv2
import numpy as np
from typing import List, Tuple, Optional

Point = Tuple[int, int]


def detect_pool_polygon(frame) -> Optional[List[Point]]:
    """
    Simple prototype pool detector.
    This uses color/edge/contour logic to guess the pool boundary.

    For now, it returns the largest 4-point contour approximation.
    You can improve this later.
    """
    img = frame.copy()
    h, w = img.shape[:2]

    # Convert to HSV to try to isolate blue-ish water region
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Broad blue range; tune later for your pool
    lower_blue = np.array([80, 30, 30])
    upper_blue = np.array([140, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Clean mask
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)

    # Ignore tiny detections
    if cv2.contourArea(largest) < 0.05 * (w * h):
        return None

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)

    # If approx has too few points, fallback to bounding rect
    if len(approx) < 4:
        x, y, bw, bh = cv2.boundingRect(largest)
        return [(x, y), (x + bw, y), (x + bw, y + bh), (x, y + bh)]

    polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]

    return polygon


def create_pool_mask(frame_shape, polygon_points: List[Point]):
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