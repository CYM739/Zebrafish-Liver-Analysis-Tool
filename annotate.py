import cv2
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
