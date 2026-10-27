import cv2
import math
import statistics
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.utils import draw_segmentation_masks
import pandas as pd
import numpy as np

from annotate import draw_labels
from cell.utils import cut, mix_circle
from cell.model import Net, Unet

_MODULE_DIR = Path(__file__).parent
_CROP_HALF = 112  # half of the 224 px model input (200 px crop + 12 px padding per side)
_SUMMARY_FIELDS = ("radius_px", "nuclear_area_um2", "cell_area_um2", "nc_ratio")


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

    m = Net(pretrained=False).to(device).eval()
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
        dict with annotated_img (segmentation overlay with cell IDs), all_circles_img,
        cells (per-cell records), cell_gallery (PIL crops in the same order as cells),
        n_candidates, warning (i18n key or None)
    """
    if config is None:
        config = {}

    value = config.get("padding", 100)
    um2 = config.get("um_conversion", 0.181) ** 2
    confidence_thresh = config.get("confidence_threshold", 0.75)
    seg_thresh = config.get("segmentation_threshold", 0.9)

    m, m1, device = models
    transform = T.Compose([
        T.Pad(12, fill=(0, 0, 0), padding_mode='constant'),
        T.ToTensor()
    ])

    circles = mix_circle(img, config)
    if circles is None:
        return {"annotated_img": img.copy(), "all_circles_img": img.copy(), "cells": [],
                "cell_gallery": [], "n_candidates": 0, "warning": "warn_no_circles"}

    img_padded = cv2.copyMakeBorder(img, value, value, value, value,
                                    cv2.BORDER_CONSTANT, value=(0, 0, 0))
    all_circles = img_padded.copy()
    overlay = T.ToTensor()(Image.fromarray(cv2.cvtColor(img_padded, cv2.COLOR_BGR2RGB)))
    padded_h, padded_w = img_padded.shape[:2]

    cells = []
    cell_gallery = []
    with torch.no_grad():
        for cx, cy, r in circles:
            cv2.circle(all_circles, center=(cx, cy), radius=r, color=(0, 255, 0), thickness=2)
            crop = cut(img_padded.copy(), (cx, cy, r), config)
            image_t = transform(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))).to(device).unsqueeze(0)
            score = m(image_t).item()
            if score <= confidence_thresh:
                continue

            prob = torch.sigmoid(m1(image_t).squeeze(1))
            crop_mask = (prob >= seg_thresh).cpu()
            cell_gallery.append(T.ToPILImage()(draw_segmentation_masks(image_t.squeeze(0).cpu(), crop_mask, 0.5, (0, 255, 0))))

            # Place the crop mask back into full-image coordinates
            pad = nn.ZeroPad2d((cx - _CROP_HALF, padded_w - _CROP_HALF - cx,
                                cy - _CROP_HALF, padded_h - _CROP_HALF - cy))
            full_mask = (pad(prob) >= seg_thresh).cpu()
            overlay = draw_segmentation_masks(overlay, full_mask, 0.45, (0, 255, 0))

            mask_px = int(full_mask.sum())
            nuclear_px = math.pi * r * r
            cells.append({
                "cell_id": len(cells) + 1,
                "x": int(cx - value),
                "y": int(cy - value),
                "radius_px": int(r),
                "nuclear_area_um2": nuclear_px * um2,
                "cell_area_um2": mask_px * um2,  # U-Net mask = whole cell, nucleus included
                "nc_ratio": nuclear_px / max(mask_px, 1),
                "classifier_score": score,
            })

    all_circles_img = all_circles[value:-value, value:-value]
    if not cells:
        return {"annotated_img": img.copy(), "all_circles_img": all_circles_img, "cells": [],
                "cell_gallery": [], "n_candidates": len(circles), "warning": "warn_no_cells_passed"}

    annotated_pil = T.ToPILImage()(overlay[:, value:-value, value:-value])
    annotated_img = cv2.cvtColor(np.array(annotated_pil), cv2.COLOR_RGB2BGR)
    draw_labels(annotated_img, [(c["cell_id"], (c["x"], c["y"])) for c in cells])

    return {
        "annotated_img": annotated_img,
        "all_circles_img": all_circles_img,
        "cells": cells,
        "cell_gallery": cell_gallery,
        "n_candidates": len(circles),
        "warning": None,
    }


def summarize_cells(cells):
    """Per-image summary: number of accepted cells and the mean of each measurement."""
    summary = {"n_cells": len(cells)}
    for field in _SUMMARY_FIELDS:
        summary[f"mean_{field}"] = statistics.mean(c[field] for c in cells) if cells else None
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mix_dir')
    parser.add_argument('--all_sample_dir', default=str(_MODULE_DIR / 'sample') + '/')
    parser.add_argument('--test_dir', default=str(_MODULE_DIR / 'test') + '/')
    args = parser.parse_args()

    img = cv2.imread(args.mix_dir)
    models = load_models()
    result = analyze_cells(img, models)

    for cell, cell_img in zip(result["cells"], result["cell_gallery"]):
        cell_img.save(args.all_sample_dir + str(cell["cell_id"]) + '.jpg')

    pd.DataFrame(result["cells"]).to_csv(args.test_dir + 'test.csv', index=False)
    pd.DataFrame([summarize_cells(result["cells"])]).to_csv(args.test_dir + 'test_summary.csv', index=False)
    annotated = Image.fromarray(cv2.cvtColor(result["annotated_img"], cv2.COLOR_BGR2RGB))
    annotated.save(args.test_dir + 'test.jpg')
