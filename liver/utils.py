import cv2
import numpy as np


def sortPoints(cnt):
    new_cnt = []
    start = cnt[0]
    del cnt[0]
    new_cnt.append(start)

    while len(cnt)!=1:
        dist = [np.linalg.norm(start - i) for i in cnt]
        x = dist.index(min(dist))
        start = cnt[x]
        del cnt[x]
        new_cnt.append(start)
    new_cnt.append(cnt[0])
    return new_cnt

def greenandred(img, config=None):
    if config is None:
        config = {}
    green_lower = tuple(config.get("hsv_green_lower", [40, 70, 30]))
    green_upper = tuple(config.get("hsv_green_upper", [255, 255, 255]))
    red1_lower = tuple(config.get("hsv_red1_lower", [0, 70, 50]))
    red1_upper = tuple(config.get("hsv_red1_upper", [10, 255, 255]))
    red2_lower = tuple(config.get("hsv_red2_lower", [170, 70, 50]))
    red2_upper = tuple(config.get("hsv_red2_upper", [180, 255, 255]))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mask_green = cv2.inRange(hsv, green_lower, green_upper)
    mask_red1 = cv2.inRange(hsv, red1_lower, red1_upper)
    mask_red2 = cv2.inRange(hsv, red2_lower, red2_upper)

    ## slice the red
    imask_red1 = mask_red1>0
    red = np.zeros_like(img, np.uint8)
    red[imask_red1] = img[imask_red1]

    ## slice the green
    imask_green = mask_green>0
    green = np.zeros_like(img, np.uint8)
    green[imask_green] = img[imask_green]

    return green,red

def find(img, config=None):
    if config is None:
        config = {}
    kernel_size = config.get("blur_kernel", 3)
    area_min = config.get("contour_area_min", 200)

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    blur_gray = cv2.GaussianBlur(gray,(kernel_size,kernel_size),0)
    (cnt, hierarchy) = cv2.findContours(
        blur_gray.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    new_cnt = []
    for i in cnt:
        area = cv2.contourArea(i)
        if area>area_min:
            new_cnt.append(i)
    return new_cnt

def inorout(cnt,cnt_mean,mask):
    new_cnt=[]
    new_cnt_mean=[]
    gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    for idx in range(len(cnt_mean)):
        x = cnt_mean[idx][0][0]
        y = cnt_mean[idx][0][1]
        if gray[y][x]==255:
            new_cnt_mean.append(cnt_mean[idx])
            new_cnt.append(cnt[idx])
    return new_cnt,new_cnt_mean
