"""Green-region boundary. Unlike dhcl8881 (liver1/main.py), each region is outlined on its own,
instead of joining all regions' points into one polyline (which draws lines across the image)."""
import cv2
import numpy as np

from profiles.base import result


def boundary(img, cfg):
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV),
                       np.array(cfg["hsv_green_lower"], np.uint8), np.array(cfg["hsv_green_upper"], np.uint8))
    output = cv2.bitwise_and(img, img, mask=mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = [c for c in contours if cv2.contourArea(c) > cfg["contour_area_min"]]
    if not regions:
        return result(images=[("boundary", "cap_boundary", img.copy(), {})], warning="warn_no_green_region")
    cv2.drawContours(output, regions, -1, (0, 255, 0), 1)
    return result(images=[("boundary", "cap_boundary", output, {})])
