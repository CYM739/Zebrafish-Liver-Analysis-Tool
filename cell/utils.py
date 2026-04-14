import os
import pandas as pd
from torchvision.io import read_image
import PIL.Image as Image
import torch
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import torchvision
from torchvision import transforms
from torchvision.transforms import functional as TF
import cv2
from torchvision.transforms import ToTensor
import numpy as np
from torch import Tensor


class CellDataset(Dataset):
    def __init__(self, annotations_file, img_dir, transform=None, target_transform=None):
        self.img_labels = pd.read_csv(annotations_file)
        self.img_dir = img_dir
        self.transform = transform
        self.target_transform = target_transform

    def __len__(self):
        return len(self.img_labels)

    def __getitem__(self, idx):
        img_path = self.img_dir+'/'+str(idx)+'.tif'
        image = Image.open(img_path)
        tranform = transforms.Compose([transforms.Pad(12, fill=(0,0,0), padding_mode='constant'),ToTensor()])
        image = tranform(image)
        label = self.img_labels['0'][idx]
        return image, label

class MaskDataset(Dataset):
    def __init__(self, label_dir, img_dir, transform=None, target_transform=None):
        self.leng = os.listdir(label_dir)
        self.label_dir = label_dir
        self.img_dir = img_dir
        self.transform = transform
        self.target_transform = target_transform

    def __len__(self):
        return len(self.leng)

    def __getitem__(self, idx):
        img_path = self.img_dir+'/'+str(idx)+'.jpg'
        label_path = self.label_dir+'/'+str(idx)+'.jpg'
        image = Image.open(img_path)
        label = Image.open(label_path)
        transform = transforms.Compose([transforms.Pad(12, fill=(0,0,0), padding_mode='constant'),ToTensor()])
        transform_label = transforms.Compose([transforms.Pad(12, fill=(0), padding_mode='constant'),ToTensor()])
        image = transform(image)
        label = transform_label(label)
        return image, label


def mix_circle(img, config=None):
    """Detect circles in a channel-mix image using HoughCircles.

    Args:
        img: BGR numpy array (NOT a file path)
        config: dict with cell config values
    Returns:
        numpy array of circles (x, y, radius) or None
    """
    if config is None:
        config = {}
    value = config.get("padding", 100)
    lab_lower = np.array(config.get("lab_lower", [70, 70, 70]))
    lab_upper = np.array(config.get("lab_upper", [190, 255, 255]))
    blur_kernel = config.get("blur_kernel", 5)
    median_blur_kernel = config.get("median_blur_kernel", 7)
    hough_dp = config.get("hough_dp", 1)
    hough_min_dist_divisor = config.get("hough_min_dist_divisor", 64)
    hough_param1 = config.get("hough_param1", 50)
    hough_param2 = config.get("hough_param2", 0.8)
    hough_min_radius = config.get("hough_min_radius", 1)
    hough_max_radius = config.get("hough_max_radius", 60)

    captured_frame = cv2.copyMakeBorder(img, value, value, value, value,
                                        cv2.BORDER_CONSTANT, value=(0, 0, 0))

    captured_frame_bgr = cv2.cvtColor(captured_frame, cv2.COLOR_BGRA2BGR)
    captured_frame_bgr = cv2.medianBlur(captured_frame_bgr, median_blur_kernel)
    captured_frame_lab = cv2.cvtColor(captured_frame_bgr, cv2.COLOR_BGR2Lab)

    captured_frame_lab_red = cv2.inRange(captured_frame_lab, lab_lower, lab_upper)
    captured_frame_lab_red = cv2.GaussianBlur(captured_frame_lab_red,
                                              (blur_kernel, blur_kernel), 2, 2)

    circles = cv2.HoughCircles(captured_frame_lab_red, cv2.HOUGH_GRADIENT_ALT,
                               hough_dp,
                               captured_frame_lab_red.shape[0] / hough_min_dist_divisor,
                               param1=hough_param1, param2=hough_param2,
                               minRadius=hough_min_radius, maxRadius=hough_max_radius)
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
    return circles


def cut(img_padded, circle, config=None):
    """Extract a square crop around a detected circle.

    Args:
        img_padded: BGR numpy array, already padded
        circle: array-like [x, y, radius]
        config: dict with cell config values
    Returns:
        cropped BGR numpy array
    """
    if config is None:
        config = {}
    value = config.get("padding", 100)

    circle = list(circle)  # make mutable copy
    h, w = img_padded.shape[:2]

    cv2.circle(img_padded, center=(circle[0], circle[1]), radius=circle[2],
               color=(0, 255, 0), thickness=2)

    if circle[0] > w - value:
        circle[0] = w - value
    if circle[1] > h - value:
        circle[1] = h - value
    if circle[0] < value:
        circle[0] = value
    if circle[1] < value:
        circle[1] = value

    new_image = img_padded[circle[1]-value:circle[1]+value,
                           circle[0]-value:circle[0]+value, :]
    return new_image


def dice_coeff(input: Tensor, target: Tensor, reduce_batch_first: bool = False, epsilon: float = 1e-6):
    assert input.size() == target.size()
    assert input.dim() == 3 or not reduce_batch_first

    sum_dim = (-1, -2) if input.dim() == 2 or not reduce_batch_first else (-1, -2, -3)

    inter = 2 * (input * target).sum(dim=sum_dim)
    sets_sum = input.sum(dim=sum_dim) + target.sum(dim=sum_dim)
    sets_sum = torch.where(sets_sum == 0, inter, sets_sum)

    dice = (inter + epsilon) / (sets_sum + epsilon)
    return dice.mean()


def multiclass_dice_coeff(input: Tensor, target: Tensor, reduce_batch_first: bool = False, epsilon: float = 1e-6):
    return dice_coeff(input.flatten(0, 1), target.flatten(0, 1), reduce_batch_first, epsilon)


def dice_loss(input: Tensor, target: Tensor, multiclass: bool = False):
    fn = multiclass_dice_coeff if multiclass else dice_coeff
    return 1 - fn(input, target, reduce_batch_first=True)
