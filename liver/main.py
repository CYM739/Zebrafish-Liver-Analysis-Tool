import cv2
import numpy as np
from liver.utils import sortPoints, greenandred, find, inorout


def count_cells(img, config=None):
    """Count neutrophils (green) and macrophages (red) within the liver region.

    Args:
        img: BGR numpy array
        config: dict with liver config values

    Returns:
        dict with red_img, green_img, mac_count, neu_count
    """
    if config is None:
        config = {}

    mask_threshold = config.get("mask_threshold", 249)
    mask_threshold_max = config.get("mask_threshold_max", 250)
    mask_blur_kernel = config.get("mask_blur_kernel", 13)

    img1 = img.copy()
    img_green = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, th1 = cv2.threshold(gray, mask_threshold, mask_threshold_max, cv2.THRESH_BINARY)

    blur_gray = cv2.GaussianBlur(th1, (mask_blur_kernel, mask_blur_kernel), 0)
    (cnt, hierarchy) = cv2.findContours(
        blur_gray.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    new_cnt = []
    for i in cnt:
        mean = np.mean(i, axis=0).astype(np.int32)
        if (mean[0][0] < img.shape[0] * 0.95 or mean[0][1] < img.shape[1] * 0.95):
            new_cnt.append(mean[0])
    if len(new_cnt) < 3:
        return {
            "red_img": img.copy(),
            "green_img": img.copy(),
            "mac_count": 0,
            "neu_count": 0,
            "warning": "No liver region detected — not enough bright border points to form a mask. Is this a channel-mix image with a bright border?",
        }

    new_cnt = sortPoints(new_cnt)
    new_cnt = np.array(new_cnt).astype(np.int32)

    mask = np.zeros_like(img, dtype=np.uint8)
    cv2.fillPoly(mask, [new_cnt], (255, 255, 255))

    green, red = greenandred(img, config)

    green_cnt = find(green, config)
    green_mean = [np.mean(i, axis=0).astype(np.int32) for i in green_cnt]
    new_green_cnt, new_green_cnt_mean = inorout(green_cnt, green_mean, mask)

    red_cnt = find(red, config)
    red_mean = [np.mean(i, axis=0).astype(np.int32) for i in red_cnt]
    new_red_cnt, new_red_cnt_mean = inorout(red_cnt, red_mean, mask)

    cv2.drawContours(img1, new_red_cnt, -1, (255, 255, 255), 5)
    cv2.drawContours(img_green, new_green_cnt, -1, (255, 255, 255), 5)

    return {
        "red_img": img1,
        "green_img": img_green,
        "mac_count": len(new_red_cnt_mean),
        "neu_count": len(new_green_cnt_mean),
        "warning": None,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mix_dir')
    args = parser.parse_args()

    img = cv2.imread(args.mix_dir)
    result = count_cells(img)

    cv2.imwrite("result/red.jpg", result["red_img"])
    cv2.imwrite("result/green.jpg", result["green_img"])
    with open('./result/output.txt', 'w') as f:
        f.write('macrophage count:' + str(result["mac_count"]) + '\n')
        f.write('neutrophil count:' + str(result["neu_count"]))
