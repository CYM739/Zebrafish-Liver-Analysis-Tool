"""Neutrophil / macrophage counting inside the hand-drawn liver outline.

Differences from dhcl8881 (liver/main.py):
- the scale-bar exclusion compares x with the width and y with the height (dhcl8881 swaps them,
  which keeps the scale bar in the outline of non-square images)
- red uses both hue ranges (0-10 and 170-179); green is limited to green hues
- cells much larger than the image's median are flagged as possibly merged (not split)
"""
import statistics

import cv2
import numpy as np

from annotate import contour_records, draw_contours
from liver.utils import find, sortPoints
from profiles.base import result

CELL_TYPES = (  # (cell type, ID prefix, result image, HSV ranges in config, caption)
    ("macrophage", "M", "macrophages", ("hsv_red1", "hsv_red2"), "cap_macrophages_flagged"),
    ("neutrophil", "N", "neutrophils", ("hsv_green",), "cap_neutrophils_flagged"),
)


def liver_mask(img, cfg):
    """Liver region enclosed by the white dashed outline, or None if there is no outline."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bright = cv2.threshold(gray, cfg["mask_threshold"], cfg["mask_threshold_max"], cv2.THRESH_BINARY)
    k = cfg["mask_blur_kernel"]
    dashes, _ = cv2.findContours(cv2.GaussianBlur(bright, (k, k), 0), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    h, w = img.shape[:2]
    corner = cfg["scalebar_corner"]
    points = [np.mean(d, axis=0).astype(np.int32)[0] for d in dashes]
    points = [p for p in points if p[0] < w * corner or p[1] < h * corner]
    if len(points) < 3:
        return None
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [np.array(sortPoints(points), np.int32)], 255)
    return mask


def _cells_of_color(img, hsv, liver, cfg, range_keys):
    """Contours of one stain whose centre lies inside the liver."""
    color = np.zeros(hsv.shape[:2], np.uint8)
    for key in range_keys:
        color |= cv2.inRange(hsv, tuple(cfg[f"{key}_lower"]), tuple(cfg[f"{key}_upper"]))
    stain = np.zeros_like(img)
    stain[color > 0] = img[color > 0]
    contours = find(stain, cfg)
    return [c for c in contours if liver[tuple(np.mean(c, axis=0).astype(np.int32)[0][::-1])]]


def _flag_merged(cells, cfg):
    """Mark cells whose area is at least merged_area_factor x the median of their type and image."""
    limit = (cfg["merged_area_factor"] * statistics.median(c["area_px"] for c in cells)
             if len(cells) >= cfg["merged_min_cells"] else float("inf"))
    for c in cells:
        c["possibly_merged"] = c["area_px"] >= limit
    return {i for i, c in enumerate(cells) if c["possibly_merged"]}


def count(img, cfg):
    liver = liver_mask(img, cfg)
    if liver is None:
        return result(images=[(image, caption, img.copy(), {"n": 0, "flagged": 0}) for _, _, image, _, caption in CELL_TYPES],
                      summary={f"{t}_count": 0 for t, *_ in CELL_TYPES}, warning="warn_no_liver_outline")
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    images, cells, summary = [], [], {}
    for cell_type, prefix, image, range_keys, caption in CELL_TYPES:
        contours = _cells_of_color(img, hsv, liver, cfg, range_keys)
        records = contour_records(contours, prefix)
        flagged = _flag_merged(records, cfg)
        images.append((image, caption, draw_contours(img, contours, records, flagged),
                       {"n": len(records), "flagged": len(flagged)}))
        cells += [{"image": image, "cell_type": cell_type, **r} for r in records]
        summary[f"{cell_type}_count"] = len(records)
        summary[f"{cell_type}_possibly_merged"] = len(flagged)
    return result(images=images, cells=cells, summary=summary)
