import cv2
import math
import statistics
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as T
from torchvision import transforms
from torchvision.transforms import ToTensor
import pandas as pd
import numpy as np

from cell.utils import cut, mix_circle
from cell.model import Net, Unet

_MODULE_DIR = Path(__file__).parent


def load_models(config=None, device=None):
    """Load classifier and segmenter models once.

    Returns:
        tuple of (classifier, segmenter, device)
    """
    if config is None:
        config = {}
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    classifier_path = config.get("model_classifier_path", _MODULE_DIR / "save1.pt")
    segmenter_path = config.get("model_segmenter_path", _MODULE_DIR / "save_mask.pt")

    if not Path(classifier_path).is_absolute():
        classifier_path = _MODULE_DIR / classifier_path
    if not Path(segmenter_path).is_absolute():
        segmenter_path = _MODULE_DIR / segmenter_path

    m = Net().to(device).eval()
    m1 = Unet().to(device).eval()
    m.load_state_dict(torch.load(str(classifier_path), map_location=device, weights_only=True))
    m1.load_state_dict(torch.load(str(segmenter_path), map_location=device, weights_only=True))

    return (m, m1, device)


def analyze_cells(img, models, config=None):
    """Analyze cell nuclear-to-cytoplasmic ratio.

    Args:
        img: BGR numpy array (original, unpadded)
        models: tuple of (classifier, segmenter, device) from load_models()
        config: dict with cell config values

    Returns:
        dict with annotated_img, all_circles_img, dataframe, cell_gallery
    """
    if config is None:
        config = {}

    value = config.get("padding", 100)
    um = config.get("um_conversion", 0.181)
    confidence_thresh = config.get("confidence_threshold", 0.75)
    seg_thresh = config.get("segmentation_threshold", 0.9)

    m, m1, device = models
    tranform = transforms.Compose([
        transforms.Pad(12, fill=(0, 0, 0), padding_mode='constant'),
        ToTensor()
    ])

    circles = mix_circle(img, config)
    if circles is None:
        return {
            "annotated_img": img.copy(),
            "all_circles_img": img.copy(),
            "dataframe": pd.DataFrame(),
            "cell_gallery": [],
            "warning": "No cells detected — HoughCircles found nothing. Check LAB range or image type.",
        }

    # Padded copies for drawing
    captured_frame1 = cv2.copyMakeBorder(img, value, value, value, value,
                                         cv2.BORDER_CONSTANT, value=(0, 0, 0))
    captured_frame2 = cv2.copyMakeBorder(img, value, value, value, value,
                                         cv2.BORDER_CONSTANT, value=(0, 0, 0))
    # Padded copy for cutting (won't be drawn on)
    img_padded = cv2.copyMakeBorder(img, value, value, value, value,
                                    cv2.BORDER_CONSTANT, value=(0, 0, 0))

    new_circle = []
    cell_gallery = []
    idx = 0

    with torch.no_grad():
        for i in range(len(circles)):
            a = cut(img_padded.copy(), circles[i], config)
            image = Image.fromarray(cv2.cvtColor(a, cv2.COLOR_BGR2RGB))
            cv2.circle(captured_frame1, center=(circles[i, 0], circles[i, 1]),
                       radius=circles[i, 2], color=(0, 255, 0), thickness=2)
            image_t = tranform(image).to(device).unsqueeze(0)
            output = m(image_t)
            if output > confidence_thresh:
                new_circle.append(circles[i])
                output1 = m1(image_t)
                x = torch.sigmoid(output1.squeeze(1))
                res = x >= seg_thresh
                y = torchvision.utils.draw_segmentation_masks(
                    image_t.squeeze(0), res, 0.5, (0, 255, 0))
                y_pil = T.ToPILImage()(y)
                cell_gallery.append(y_pil)
                idx += 1

    if not new_circle:
        all_circles_img = captured_frame1[value:-value, value:-value]
        return {
            "annotated_img": img.copy(),
            "all_circles_img": all_circles_img,
            "dataframe": pd.DataFrame(),
            "cell_gallery": [],
            "warning": f"No valid cells found — {len(circles)} circles detected but none passed the confidence threshold ({confidence_thresh}).",
        }

    # Build ratio table and overlay segmentation
    raius = []
    field = []
    mask_field = []
    ratio = []
    y = T.ToTensor()(Image.fromarray(cv2.cvtColor(captured_frame2, cv2.COLOR_BGR2RGB)))
    padded_h, padded_w = captured_frame2.shape[:2]

    with torch.no_grad():
        for i in range(len(new_circle)):
            cv2.circle(captured_frame2, center=(new_circle[i][0], new_circle[i][1]),
                       radius=new_circle[i][2], color=(0, 255, 0), thickness=2)
            a = cut(img_padded.copy(), new_circle[i], config)
            image = Image.fromarray(cv2.cvtColor(a, cv2.COLOR_BGR2RGB))
            image_t = tranform(image).to(device).unsqueeze(0)
            output1 = m1(image_t)
            x = torch.sigmoid(output1.squeeze(1))

            pad_left = new_circle[i][0] - 112
            pad_right = padded_w - 112 - new_circle[i][0]
            pad_top = new_circle[i][1] - 112
            pad_bottom = padded_h - 112 - new_circle[i][1]
            pad = nn.ZeroPad2d((pad_left, pad_right, pad_top, pad_bottom))
            x = pad(x)
            res = x >= seg_thresh
            y = torchvision.utils.draw_segmentation_masks(y, res, 0.45, (0, 255, 0))
            positive_pixel_count = res.sum()

            raius.append(int(new_circle[i][2]))
            field.append(math.pi * new_circle[i][2] * new_circle[i][2] * um * um)
            mask_field.append(int(positive_pixel_count.cpu()) * um * um)
            ratio.append((math.pi * new_circle[i][2] * new_circle[i][2]) /
                         max(int(positive_pixel_count.cpu()), 1))

    if raius:
        raius.append(round(statistics.mean(raius), 2))
        field.append(round(statistics.mean(field), 4))
        mask_field.append(round(statistics.mean(mask_field), 4))
        ratio.append(round(statistics.mean(ratio), 4))

    data = {
        "radius": raius,
        "nuclear_area": field,
        "cytoplasmic_area": mask_field,
        "ratio": ratio,
    }
    df = pd.DataFrame(data)

    # Convert overlay tensor to BGR numpy for output
    annotated_pil = T.ToPILImage()(y[:, value:-value, value:-value])
    annotated_img = cv2.cvtColor(np.array(annotated_pil), cv2.COLOR_RGB2BGR)

    # Crop padding from all-circles image
    all_circles_img = captured_frame1[value:-value, value:-value]

    return {
        "annotated_img": annotated_img,
        "all_circles_img": all_circles_img,
        "dataframe": df,
        "cell_gallery": cell_gallery,
        "warning": None,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mix_dir')
    parser.add_argument('--all_sample_dir', default='./sample/')
    parser.add_argument('--test_dir', default='./test/')
    args = parser.parse_args()

    img = cv2.imread(args.mix_dir)
    models = load_models()
    result = analyze_cells(img, models)

    for i, cell_img in enumerate(result["cell_gallery"]):
        cell_img.save(args.all_sample_dir + str(i) + '.jpg')

    result["dataframe"].to_csv(args.test_dir + 'test.csv')
    annotated = Image.fromarray(cv2.cvtColor(result["annotated_img"], cv2.COLOR_BGR2RGB))
    annotated.save(args.test_dir + 'test.jpg')
