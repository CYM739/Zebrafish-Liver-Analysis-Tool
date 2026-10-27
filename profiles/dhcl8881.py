"""The original author's (dhcl8881) algorithms and models, unchanged: liver/, liver1/ and cell/."""
import functools

from cell.main import analyze_cells, load_models, summarize_cells
from liver.main import count_cells
from liver1.main import detect_boundary
from profiles.base import HSV, Analysis, ModelUnavailable, result

NAME = "dhcl8881"


def count(img, cfg):
    r = count_cells(img, cfg)
    cells = [{"image": key, "cell_type": cell_type, **c}
             for key, cell_type in (("macrophages", "macrophage"), ("neutrophils", "neutrophil")) for c in r[key]]
    return result(
        images=[("macrophages", "cap_macrophages", r["red_img"], {"n": len(r["macrophages"])}),
                ("neutrophils", "cap_neutrophils", r["green_img"], {"n": len(r["neutrophils"])})],
        cells=cells,
        summary={"macrophage_count": len(r["macrophages"]), "neutrophil_count": len(r["neutrophils"])},
        warning=r["warning"])


def boundary(img, cfg):
    r = detect_boundary(img, cfg)
    return result(images=[("boundary", "cap_boundary", r["output_img"], {})], warning=r["warning"])


@functools.cache
def _models():
    try:
        return load_models()
    except FileNotFoundError as e:
        raise ModelUnavailable("warn_model_missing") from e


def cell(img, cfg):
    r = analyze_cells(img, _models(), cfg)
    return result(
        images=[("segmentation", "cap_segmentation", r["annotated_img"], {"n": len(r["cells"])}),
                ("all_nuclei", "cap_all_nuclei", r["all_circles_img"], {"n": r["n_candidates"]})],
        cells=[{"image": "segmentation", **c} for c in r["cells"]],
        crops=r["cell_gallery"],
        summary={"n_candidates": r["n_candidates"], **summarize_cells(r["cells"])},
        warning=r["warning"], n=r["n_candidates"], threshold=cfg["confidence_threshold"])


ANALYSES = {
    "count": Analysis(count, (
        ("hsv_green", "hsv_neutrophil", HSV),
        ("hsv_red1", "hsv_macrophage", HSV),
        ("contour_area_min", "contour_area_min", (10, 2000, 10)),
        ("blur_kernel", "blur_kernel", (1, 31, 2)),
        ("mask_threshold", "mask_threshold", (200, 255, 1)),
    )),
    "boundary": Analysis(boundary, (
        ("hsv_green", "hsv_liver", HSV),
        ("contour_area_min", "contour_area_min", (1, 500, 1)),
    )),
    "cell": Analysis(cell, (
        ("confidence_threshold", "confidence_threshold", (0.1, 1.0, 0.05)),
        ("segmentation_threshold", "segmentation_threshold", (0.1, 1.0, 0.05)),
        ("um_conversion", "um_conversion", None),
        ("hough_param1", "hough_param1", (10, 300, 1)),
        ("hough_param2", "hough_param2", (0.1, 1.0, 0.05)),
        ("hough_min_radius", "hough_min_radius", (1, 30, 1)),
        ("hough_max_radius", "hough_max_radius", (10, 200, 1)),
    )),
}
