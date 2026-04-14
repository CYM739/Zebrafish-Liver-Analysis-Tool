import cv2
import numpy as np
import math


def detect_boundary(img, config=None):
    """Detect the liver region boundary from a fluorescence image.

    Args:
        img: BGR numpy array
        config: dict with liver1 config values

    Returns:
        dict with output_img, boundary_contours
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
        return {"output_img": img.copy(), "boundary_contours": [],
                "warning": "No liver boundary detected — no green regions found. Check HSV range or image type."}

    allcon = np.vstack(new_contours)
    allcon1 = sorted(allcon, key=lambda k: [k[0][0], k[0][1]])

    x = 0
    y1 = 0
    y2 = 0
    n_list = []
    for i in allcon1:
        if x == 0 and y1 == 0:
            x = i[0][0]
            y1 = i[0][1]
            y2 = i[0][1]
        if x == i[0][0] and y2 < i[0][1]:
            y2 = i[0][1]
        elif x == i[0][0] and y1 > i[0][1]:
            y1 = i[0][1]
        elif x != i[0][0] and y1 != y2:
            n_list.append([[int(x), int(y1)]])
            n_list.append([[int(x), int(y2)]])
            x = i[0][0]
            y1 = i[0][1]
            y2 = i[0][1]
        elif x != i[0][0] and y1 == y2:
            n_list.append([[int(x), int(y1)]])
            x = i[0][0]
            y1 = i[0][1]
            y2 = i[0][1]

    def euclidean_distance(p1, p2):
        return math.sqrt((p1[0][0] - p2[0][0]) ** 2 + (p1[0][1] - p2[0][1]) ** 2)

    nn_list = []
    nn_list.append(n_list[0])
    while len(n_list) != 0:
        reference_point = nn_list[-1]
        n_list.remove(reference_point)
        sorted_points = sorted(n_list, key=lambda p: euclidean_distance(p, reference_point))
        if sorted_points != []:
            nn_list.append(sorted_points[0])

    output = cv2.drawContours(output, [allcon], -1, [0, 255, 0], thickness=1)

    contour_dims = []
    for contour in contours:
        x_r, y_r, w, h = cv2.boundingRect(contour)
        contour_dims.append({"width": w, "height": h})

    return {
        "output_img": output,
        "boundary_contours": contour_dims,
        "warning": None,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mix_dir')
    args = parser.parse_args()

    img = cv2.imread(args.mix_dir)
    result = detect_boundary(img)
    cv2.imwrite('output.jpg', result["output_img"])
