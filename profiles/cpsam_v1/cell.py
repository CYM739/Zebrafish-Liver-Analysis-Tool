"""Nuclear-to-cytoplasmic ratio from Cellpose-SAM cell and nucleus segmentation.

Unlike dhcl8881 (cell/main.py), both areas come from segmented shapes instead of a fitted circle.
The N/C denominator follows config `nc_denominator` (see profiles.base.nc_ratio).
"""
import functools
import statistics
from collections import defaultdict

import cv2
import numpy as np
import torch
from scipy import ndimage

from annotate import draw_labels
from profiles.base import ModelUnavailable, means, nc_ratio, result

_CHANNELS = {"blue": 0, "green": 1, "red": 2}  # BGR index of each stain
_EXCLUDED_COLOR = (128, 128, 128)
_CELL_COLOR = (0, 255, 0)
_NUCLEUS_COLOR = (0, 255, 255)
_CROP_MARGIN = 15
_MEASUREMENTS = ("cell_area_um2", "nuclear_area_um2", "cytoplasmic_area_um2", "nc_ratio")


@functools.cache
def _model(name):
    from cellpose import models  # heavy import, only when this profile is used
    try:
        return models.CellposeModel(gpu=torch.cuda.is_available(), pretrained_model=name)
    except Exception as e:  # weights are downloaded on first use
        raise ModelUnavailable("warn_model_download_failed") from e


def _segment(model, bgr, cfg):
    masks, *_ = model.eval(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), channel_axis=2, diameter=cfg["diameter"] or None,
                           flow_threshold=cfg["flow_threshold"], cellprob_threshold=cfg["cellprob_threshold"])
    return masks


def _nuclei_per_cell(cells, nuclei, overlap_min):
    """cell label -> [(nucleus label, nucleus pixels inside the cell)], each nucleus going to the cell
    that holds most of it, provided that is at least overlap_min of the nucleus."""
    both = (cells > 0) & (nuclei > 0)
    base = int(nuclei.max()) + 1
    keys, overlap = np.unique(cells[both].astype(np.int64) * base + nuclei[both], return_counts=True)
    nucleus_area = np.bincount(nuclei.ravel())
    best = {}
    for key, px in zip(keys, overlap):
        cell, nucleus = divmod(int(key), base)
        if px > best.get(nucleus, (0, 0))[1]:
            best[nucleus] = (cell, int(px))
    owned = defaultdict(list)
    for nucleus, (cell, px) in best.items():
        if px >= overlap_min * nucleus_area[nucleus]:
            owned[cell].append((nucleus, px))
    return owned


def _outline(img, labels, keep, color):
    edge = cv2.morphologyEx(np.where(np.isin(labels, keep), labels, 0).astype(np.uint16),
                            cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[edge] = color


def cell(img, cfg):
    model = _model(cfg["model"])
    cells = _segment(model, img, cfg)
    stain = np.zeros_like(img)
    channel = _CHANNELS[cfg["nucleus_channel"]]
    stain[..., channel] = img[..., channel]
    nuclei = _segment(model, stain, cfg)

    labels = np.unique(cells)[1:]
    if not len(labels):
        return result(images=[("segmentation", "cap_cells_nuclei", img.copy(), {"n": 0})],
                      summary={"n_segmented": 0, "n_cells": 0}, warning="warn_no_cells_found")

    border = set(np.unique(np.concatenate([cells[0], cells[-1], cells[:, 0], cells[:, -1]]))) if cfg["exclude_border"] else set()
    owned = _nuclei_per_cell(cells, nuclei, cfg["nucleus_overlap_min"])
    cell_px = np.bincount(cells.ravel())
    centres = ndimage.center_of_mass(np.ones_like(cells), cells, labels)
    boxes = ndimage.find_objects(cells)
    um2 = cfg["um_conversion"] ** 2

    records, kept, kept_nuclei = [], [], []
    excluded = dict.fromkeys(("n_excluded_edge", "n_excluded_dim", "n_excluded_nucleus", "n_excluded_nucleus_only"), 0)
    # Mean cell-stain brightness per cell; dim (out-of-focus) cells have unreliable outlines
    brightness = np.asarray(ndimage.mean(img[..., _CHANNELS[cfg["cell_channel"]]], cells, labels))
    min_brightness = cfg["min_relative_brightness"] * np.median(brightness)
    for label, (cy, cx), bright in zip(labels, centres, brightness):
        if label in border:
            excluded["n_excluded_edge"] += 1
            continue
        if bright < min_brightness:
            excluded["n_excluded_dim"] += 1
            continue
        if len(owned[label]) != 1:
            excluded["n_excluded_nucleus"] += 1
            continue
        nucleus, nuclear_px = owned[label][0]
        if nuclear_px > cfg["max_nucleus_fraction"] * cell_px[label]:  # outline drawn around the nucleus only
            excluded["n_excluded_nucleus_only"] += 1
            continue
        kept.append(label)
        kept_nuclei.append(nucleus)
        records.append({"image": "segmentation", "cell_id": len(records) + 1, "x": int(cx), "y": int(cy),
                        "cell_area_um2": cell_px[label] * um2, "nuclear_area_um2": nuclear_px * um2,
                        "cytoplasmic_area_um2": (cell_px[label] - nuclear_px) * um2,
                        "nc_ratio": nc_ratio(nuclear_px, cell_px[label], cfg["nc_denominator"])})

    vis = img.copy()
    _outline(vis, cells, [l for l in labels if l not in kept], _EXCLUDED_COLOR)
    _outline(vis, cells, kept, _CELL_COLOR)
    _outline(vis, nuclei, kept_nuclei, _NUCLEUS_COLOR)
    h, w = img.shape[:2]
    crops = []
    for label in kept:
        ys, xs = boxes[label - 1]
        crops.append(vis[max(ys.start - _CROP_MARGIN, 0):min(ys.stop + _CROP_MARGIN, h),
                         max(xs.start - _CROP_MARGIN, 0):min(xs.stop + _CROP_MARGIN, w)].copy())
    draw_labels(vis, [(r["cell_id"], (r["x"], r["y"])) for r in records])

    return result(
        images=[("segmentation", "cap_cells_nuclei", vis, {"n": len(records)})],
        cells=records, crops=crops,
        summary={"n_segmented": len(labels), "n_cells": len(records), **excluded, **means(records, _MEASUREMENTS),
                 "median_nc_ratio": statistics.median(r["nc_ratio"] for r in records) if records else None},
        warning=None if records else "warn_no_cells_passed_qc", n=len(labels))
