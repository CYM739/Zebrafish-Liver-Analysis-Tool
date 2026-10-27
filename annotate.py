import cv2
import numpy as np
from config import get_config

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_labels(img, labels, above=False):
    """Draw outlined ID labels on a BGR image, in place.

    Args:
        img: BGR numpy array
        labels: iterable of (text, (x, y))
        above: False centres each label on its point; True places it just above the point
    """
    cfg = get_config()["annotation"]
    scale = max(img.shape[:2]) / 1000 * cfg["font_scale_per_1000px"]
    thickness = max(1, round(scale * 2))
    for text, (x, y) in labels:
        text = str(text)
        (w, h), _ = cv2.getTextSize(text, _FONT, scale, thickness)
        org = (int(x - w / 2), int(y - h / 2) if above else int(y + h / 2))
        cv2.putText(img, text, org, _FONT, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
        cv2.putText(img, text, org, _FONT, scale, tuple(cfg["label_color"]), thickness, cv2.LINE_AA)
    return img


def contour_records(contours, prefix):
    """One record per contour, located at its mean contour point; IDs are prefix + 1-based index."""
    records = []
    for n, c in enumerate(contours, start=1):
        x, y = np.mean(c, axis=0).astype(np.int32)[0]
        records.append({"cell_id": f"{prefix}{n}", "x": int(x), "y": int(y), "area_px": float(cv2.contourArea(c))})
    return records


def draw_contours(img, contours, records, flagged=()):
    """Copy of img with each contour outlined and labelled with its cell_id.

    Contours whose index is in flagged are outlined in the configured flag colour instead of white.
    """
    flag_color = tuple(get_config()["annotation"]["flag_color"])
    out = img.copy()
    labels = []
    for i, (c, record) in enumerate(zip(contours, records)):
        cv2.drawContours(out, [c], -1, flag_color if i in flagged else (255, 255, 255), 5)
        bx, by, bw, _ = cv2.boundingRect(c)
        labels.append((record["cell_id"], (bx + bw / 2, by)))
    return draw_labels(out, labels, above=True)
