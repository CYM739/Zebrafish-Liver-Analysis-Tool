"""First improved profile: fixes the confirmed issues of dhcl8881 and measures the N/C ratio with Cellpose-SAM."""
from profiles.base import BOOL, HSV, Analysis
from profiles.cpsam_v1.boundary import boundary
from profiles.cpsam_v1.cell import cell
from profiles.cpsam_v1.count import count

NAME = "cpsam-v1"

ANALYSES = {
    "count": Analysis(count, (
        ("hsv_green", "hsv_neutrophil", HSV),
        ("hsv_red1", "hsv_macrophage", HSV),
        ("hsv_red2", "hsv_macrophage_2", HSV),
        ("contour_area_min", "contour_area_min", (10, 2000, 10)),
        ("blur_kernel", "blur_kernel", (1, 31, 2)),
        ("mask_threshold", "mask_threshold", (200, 255, 1)),
        ("merged_area_factor", "merged_area_factor", (1.5, 10.0, 0.5)),
    )),
    "boundary": Analysis(boundary, (
        ("hsv_green", "hsv_liver", HSV),
        ("contour_area_min", "contour_area_min", (1, 500, 1)),
    )),
    "cell": Analysis(cell, (
        ("um_conversion", "um_conversion", None),
        ("diameter", "cp_diameter", (0, 150, 1)),
        ("cellprob_threshold", "cp_cellprob_threshold", (-6.0, 6.0, 0.5)),
        ("flow_threshold", "cp_flow_threshold", (0.1, 3.0, 0.1)),
        ("max_nucleus_fraction", "cp_max_nucleus_fraction", (0.5, 1.0, 0.05)),
        ("min_relative_brightness", "cp_min_relative_brightness", (0.0, 1.0, 0.05)),
        ("exclude_border", "cp_exclude_border", BOOL),
    )),
}
