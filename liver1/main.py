import cv2
import numpy as np


def detect_boundary(img, config=None):
    """Detect the liver region boundary from a fluorescence image.

    Args:
        img: BGR numpy array
        config: dict with liver1 config values

    Returns:
        dict with output_img, warning (i18n key or None)
    """
    if config is None:
        config = {}

    green_lower = np.array(config.get("hsv_green_lower", [36, 25, 25]), np.uint8)
    green_upper = np.array(config.get("hsv_green_upper", [100, 255, 255]), np.uint8)
    area_min = config.get("contour_area_min", 20)

    hsvFrame = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsvFrame, green_lower, green_upper)
    output = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    new_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > area_min:
            new_contours.append(contour)

    if not new_contours:
        return {"output_img": img.copy(), "warning": "warn_no_green_region"}

    allcon = np.vstack(new_contours)
    output = cv2.drawContours(output, [allcon], -1, [0, 255, 0], thickness=1)

    return {"output_img": output, "warning": None}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mix_dir')
    args = parser.parse_args()

    img = cv2.imread(args.mix_dir)
    result = detect_boundary(img)
    cv2.imwrite('output.jpg', result["output_img"])
