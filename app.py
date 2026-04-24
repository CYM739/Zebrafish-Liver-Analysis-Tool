import gradio as gr
import cv2
import numpy as np
import pandas as pd
import tempfile
import os
import zipfile
from pathlib import Path
from PIL import Image
from config import get_config, merge_overrides
from liver.main import count_cells
from liver1.main import detect_boundary
from cell.main import load_models, analyze_cells

# Load config once
CONFIG = get_config()

# Load cell models once at startup
print("Loading cell analysis models...")
CELL_MODELS = load_models(CONFIG.get("cell", {}))
print("Models loaded.")

_TMPDIR = tempfile.mkdtemp(prefix="nhri_")


def read_uploaded_image(filepath):
    """Read an image from a Gradio upload path, handling Unicode."""
    data = np.fromfile(filepath, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


def save_result_image(img_bgr, name):
    """Save a BGR image to temp dir, return the path."""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb)
    path = os.path.join(_TMPDIR, f"{name}.png")
    pil.save(path)
    return path


def make_zip(file_paths, csv_path, zip_name):
    """Bundle result images and CSV into a zip file."""
    zip_path = os.path.join(_TMPDIR, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in file_paths:
            zf.write(p, os.path.basename(p))
        if csv_path and os.path.exists(csv_path):
            zf.write(csv_path, os.path.basename(csv_path))
    return zip_path


def format_warnings(warnings):
    """Format warning list into markdown."""
    msgs = [w for w in warnings if w]
    if not msgs:
        return ""
    lines = "\n".join(f"- {m}" for m in msgs)
    return f"### ⚠ Warnings\n{lines}"


def preview_uploads(files):
    """Convert uploaded files (including .tif) to previewable images."""
    if not files:
        return []
    previews = []
    for f in files:
        img = read_uploaded_image(f)
        if img is not None:
            path = save_result_image(img, f"preview_{Path(f).stem}")
            previews.append((path, Path(f).name))
    return previews


# ---------------------------------------------------------------------------
# Tab 1: Neutrophil / Macrophage Counting
# ---------------------------------------------------------------------------
def run_counting(files,
                 green_h_low, green_s_low, green_v_low,
                 green_h_up, green_s_up, green_v_up,
                 red1_h_low, red1_s_low, red1_v_low,
                 red1_h_up, red1_s_up, red1_v_up,
                 contour_area_min, blur_kernel, mask_threshold,
                 progress=gr.Progress()):
    if not files:
        return [], pd.DataFrame(), None, None, ""

    overrides = {
        "hsv_green_lower": [int(green_h_low), int(green_s_low), int(green_v_low)],
        "hsv_green_upper": [int(green_h_up), int(green_s_up), int(green_v_up)],
        "hsv_red1_lower": [int(red1_h_low), int(red1_s_low), int(red1_v_low)],
        "hsv_red1_upper": [int(red1_h_up), int(red1_s_up), int(red1_v_up)],
        "contour_area_min": int(contour_area_min),
        "blur_kernel": int(blur_kernel) | 1,
        "mask_threshold": int(mask_threshold),
    }
    cfg = merge_overrides("liver", overrides)

    gallery = []
    rows = []
    warnings = []
    result_files = []

    for i, f in enumerate(progress.tqdm(files, desc="Counting cells")):
        fname = Path(f).stem
        progress(i / len(files), desc=f"Processing {Path(f).name} — detecting liver region...")
        img = read_uploaded_image(f)
        if img is None:
            warnings.append(f"**{Path(f).name}**: Failed to read image file.")
            continue

        progress(i / len(files), desc=f"Processing {Path(f).name} — counting neutrophils & macrophages...")
        result = count_cells(img, cfg)

        if result.get("warning"):
            warnings.append(f"**{Path(f).name}**: {result['warning']}")

        red_path = save_result_image(result["red_img"], f"{fname}_macrophages_{i}")
        green_path = save_result_image(result["green_img"], f"{fname}_neutrophils_{i}")
        gallery.append((red_path, f"{fname} - Macrophages ({result['mac_count']})"))
        gallery.append((green_path, f"{fname} - Neutrophils ({result['neu_count']})"))
        result_files.extend([red_path, green_path])
        rows.append({
            "filename": Path(f).name,
            "macrophage_count": result["mac_count"],
            "neutrophil_count": result["neu_count"],
        })

    df = pd.DataFrame(rows)
    csv_path = None
    if not df.empty:
        csv_path = os.path.join(_TMPDIR, "counting_results.csv")
        df.to_csv(csv_path, index=False)

    zip_path = make_zip(result_files, csv_path, "counting_results.zip") if result_files else None

    return gallery, df, csv_path, zip_path, format_warnings(warnings)


# ---------------------------------------------------------------------------
# Tab 2: Liver Boundary Detection
# ---------------------------------------------------------------------------
def run_boundary(files,
                 green_h_low, green_s_low, green_v_low,
                 green_h_up, green_s_up, green_v_up,
                 contour_area_min,
                 progress=gr.Progress()):
    if not files:
        return [], None, ""

    overrides = {
        "hsv_green_lower": [int(green_h_low), int(green_s_low), int(green_v_low)],
        "hsv_green_upper": [int(green_h_up), int(green_s_up), int(green_v_up)],
        "contour_area_min": int(contour_area_min),
    }
    cfg = merge_overrides("liver1", overrides)

    gallery = []
    warnings = []
    result_files = []

    for i, f in enumerate(progress.tqdm(files, desc="Detecting boundaries")):
        fname = Path(f).stem
        progress(i / len(files), desc=f"Processing {Path(f).name} — detecting liver boundary...")
        img = read_uploaded_image(f)
        if img is None:
            warnings.append(f"**{Path(f).name}**: Failed to read image file.")
            continue

        result = detect_boundary(img, cfg)

        if result.get("warning"):
            warnings.append(f"**{Path(f).name}**: {result['warning']}")

        path = save_result_image(result["output_img"], f"{fname}_boundary_{i}")
        gallery.append((path, fname))
        result_files.append(path)

    zip_path = make_zip(result_files, None, "boundary_results.zip") if result_files else None

    return gallery, zip_path, format_warnings(warnings)


# ---------------------------------------------------------------------------
# Tab 3: Cell N/C Ratio
# ---------------------------------------------------------------------------
def run_cell_ratio(files,
                   confidence, seg_threshold, um_conversion,
                   hough_param1, hough_param2,
                   hough_min_radius, hough_max_radius,
                   progress=gr.Progress()):
    if not files:
        return [], [], pd.DataFrame(), None, None, ""

    overrides = {
        "confidence_threshold": float(confidence),
        "segmentation_threshold": float(seg_threshold),
        "um_conversion": float(um_conversion),
        "hough_param1": int(hough_param1),
        "hough_param2": float(hough_param2),
        "hough_min_radius": int(hough_min_radius),
        "hough_max_radius": int(hough_max_radius),
    }
    cfg = merge_overrides("cell", overrides)

    annotated_gallery = []
    cell_gallery = []
    all_dfs = []
    warnings = []
    result_files = []

    for i, f in enumerate(progress.tqdm(files, desc="Analyzing cells")):
        fname = Path(f).stem
        progress(i / len(files), desc=f"Processing {Path(f).name} — detecting circles...")
        img = read_uploaded_image(f)
        if img is None:
            warnings.append(f"**{Path(f).name}**: Failed to read image file.")
            continue

        progress(i / len(files), desc=f"Processing {Path(f).name} — running model inference...")
        result = analyze_cells(img, CELL_MODELS, cfg)

        if result.get("warning"):
            warnings.append(f"**{Path(f).name}**: {result['warning']}")

        seg_path = save_result_image(result["annotated_img"], f"{fname}_seg_{i}")
        circ_path = save_result_image(result["all_circles_img"], f"{fname}_circles_{i}")
        annotated_gallery.append((seg_path, f"{fname} - Segmentation"))
        annotated_gallery.append((circ_path, f"{fname} - Detected Circles"))
        result_files.extend([seg_path, circ_path])

        for j, cell_img in enumerate(result["cell_gallery"]):
            cell_path = os.path.join(_TMPDIR, f"{fname}_cell_{i}_{j}.png")
            cell_img.save(cell_path)
            cell_gallery.append((cell_path, f"Cell {j}"))
            result_files.append(cell_path)

        if not result["dataframe"].empty:
            df_copy = result["dataframe"].copy()
            df_copy.insert(0, "filename", Path(f).name)
            all_dfs.append(df_copy)

    df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    csv_path = None
    if not df.empty:
        csv_path = os.path.join(_TMPDIR, "cell_ratio_results.csv")
        df.to_csv(csv_path, index=False)

    zip_path = make_zip(result_files, csv_path, "cell_ratio_results.zip") if result_files else None

    return annotated_gallery, cell_gallery, df, csv_path, zip_path, format_warnings(warnings)


# ---------------------------------------------------------------------------
# Tab 4: Combined (Boundary + Counting)
# ---------------------------------------------------------------------------
def run_combined(files,
                 b_green_h_low, b_green_s_low, b_green_v_low,
                 b_green_h_up, b_green_s_up, b_green_v_up,
                 b_contour_area_min,
                 c_green_h_low, c_green_s_low, c_green_v_low,
                 c_green_h_up, c_green_s_up, c_green_v_up,
                 c_red1_h_low, c_red1_s_low, c_red1_v_low,
                 c_red1_h_up, c_red1_s_up, c_red1_v_up,
                 c_contour_area_min, c_blur_kernel, c_mask_threshold,
                 progress=gr.Progress()):
    if not files:
        return [], pd.DataFrame(), None, None, ""

    boundary_cfg = merge_overrides("liver1", {
        "hsv_green_lower": [int(b_green_h_low), int(b_green_s_low), int(b_green_v_low)],
        "hsv_green_upper": [int(b_green_h_up), int(b_green_s_up), int(b_green_v_up)],
        "contour_area_min": int(b_contour_area_min),
    })
    counting_cfg = merge_overrides("liver", {
        "hsv_green_lower": [int(c_green_h_low), int(c_green_s_low), int(c_green_v_low)],
        "hsv_green_upper": [int(c_green_h_up), int(c_green_s_up), int(c_green_v_up)],
        "hsv_red1_lower": [int(c_red1_h_low), int(c_red1_s_low), int(c_red1_v_low)],
        "hsv_red1_upper": [int(c_red1_h_up), int(c_red1_s_up), int(c_red1_v_up)],
        "contour_area_min": int(c_contour_area_min),
        "blur_kernel": int(c_blur_kernel) | 1,
        "mask_threshold": int(c_mask_threshold),
    })

    gallery = []
    rows = []
    warnings = []
    result_files = []

    for i, f in enumerate(progress.tqdm(files, desc="Combined analysis")):
        fname = Path(f).stem
        img = read_uploaded_image(f)
        if img is None:
            warnings.append(f"**{Path(f).name}**: Failed to read image file.")
            continue

        progress(i / len(files), desc=f"Processing {Path(f).name} — detecting boundary...")
        b_result = detect_boundary(img, boundary_cfg)
        if b_result.get("warning"):
            warnings.append(f"**{Path(f).name}** (boundary): {b_result['warning']}")

        progress(i / len(files), desc=f"Processing {Path(f).name} — counting cells...")
        c_result = count_cells(img, counting_cfg)
        if c_result.get("warning"):
            warnings.append(f"**{Path(f).name}** (counting): {c_result['warning']}")

        bp = save_result_image(b_result["output_img"], f"{fname}_boundary_{i}")
        rp = save_result_image(c_result["red_img"], f"{fname}_macrophages_{i}")
        gp = save_result_image(c_result["green_img"], f"{fname}_neutrophils_{i}")
        gallery.append((bp, f"{fname} - Boundary"))
        gallery.append((rp, f"{fname} - Macrophages ({c_result['mac_count']})"))
        gallery.append((gp, f"{fname} - Neutrophils ({c_result['neu_count']})"))
        result_files.extend([bp, rp, gp])
        rows.append({
            "filename": Path(f).name,
            "macrophage_count": c_result["mac_count"],
            "neutrophil_count": c_result["neu_count"],
        })

    df = pd.DataFrame(rows)
    csv_path = None
    if not df.empty:
        csv_path = os.path.join(_TMPDIR, "combined_results.csv")
        df.to_csv(csv_path, index=False)

    zip_path = make_zip(result_files, csv_path, "combined_results.zip") if result_files else None

    return gallery, df, csv_path, zip_path, format_warnings(warnings)


# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------
def build_app():
    lc = CONFIG["liver"]
    l1c = CONFIG["liver1"]
    cc = CONFIG["cell"]

    with gr.Blocks(title="Zebrafish Liver Analysis Tool") as app:
        gr.Markdown("# Zebrafish Liver Analysis Tool")

        # ---- Tab 1: Counting ----
        with gr.Tab("Neutrophil / Macrophage Count"):
            with gr.Row():
                with gr.Column(scale=4):
                    count_files = gr.File(file_count="multiple", label="Upload Images",
                                          file_types=[".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"])
                    count_preview = gr.Gallery(label="Image Preview", columns=4, height=150,
                                               interactive=False)
                count_btn = gr.Button("Run Counting", variant="primary", scale=0)
            count_files.change(preview_uploads, inputs=[count_files], outputs=[count_preview])

            with gr.Accordion("Advanced Settings", open=False):
                gr.Markdown("**Green (Neutrophil) HSV Range**")
                with gr.Row():
                    c_gh_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][0], step=1, label="H Lower")
                    c_gs_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][1], step=1, label="S Lower")
                    c_gv_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    c_gh_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][0], step=1, label="H Upper")
                    c_gs_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][1], step=1, label="S Upper")
                    c_gv_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][2], step=1, label="V Upper")
                gr.Markdown("**Red (Macrophage) HSV Range**")
                with gr.Row():
                    c_rh_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][0], step=1, label="H Lower")
                    c_rs_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][1], step=1, label="S Lower")
                    c_rv_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    c_rh_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][0], step=1, label="H Upper")
                    c_rs_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][1], step=1, label="S Upper")
                    c_rv_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][2], step=1, label="V Upper")
                with gr.Row():
                    c_area = gr.Slider(10, 2000, value=lc["contour_area_min"], step=10, label="Min Contour Area")
                    c_blur = gr.Slider(1, 31, value=lc["blur_kernel"], step=2, label="Blur Kernel")
                    c_thresh = gr.Slider(200, 255, value=lc["mask_threshold"], step=1, label="Mask Threshold")

            count_warnings = gr.Markdown("")
            count_gallery = gr.Gallery(label="Results", columns=2, interactive=False)
            count_table = gr.Dataframe(label="Cell Counts")
            with gr.Row():
                count_csv = gr.File(label="Download CSV")
                count_zip = gr.File(label="Download All Results (.zip)")

            count_btn.click(
                run_counting,
                inputs=[count_files,
                        c_gh_l, c_gs_l, c_gv_l, c_gh_u, c_gs_u, c_gv_u,
                        c_rh_l, c_rs_l, c_rv_l, c_rh_u, c_rs_u, c_rv_u,
                        c_area, c_blur, c_thresh],
                outputs=[count_gallery, count_table, count_csv, count_zip, count_warnings],
            )

        # ---- Tab 2: Boundary ----
        with gr.Tab("Liver Boundary Detection"):
            with gr.Row():
                with gr.Column(scale=4):
                    bound_files = gr.File(file_count="multiple", label="Upload Images",
                                          file_types=[".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"])
                    bound_preview = gr.Gallery(label="Image Preview", columns=4, height=150,
                                               interactive=False)
                bound_btn = gr.Button("Detect Boundary", variant="primary", scale=0)
            bound_files.change(preview_uploads, inputs=[bound_files], outputs=[bound_preview])

            with gr.Accordion("Advanced Settings", open=False):
                gr.Markdown("**Green HSV Range**")
                with gr.Row():
                    b_gh_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][0], step=1, label="H Lower")
                    b_gs_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][1], step=1, label="S Lower")
                    b_gv_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    b_gh_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][0], step=1, label="H Upper")
                    b_gs_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][1], step=1, label="S Upper")
                    b_gv_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][2], step=1, label="V Upper")
                b_area = gr.Slider(1, 500, value=l1c["contour_area_min"], step=1, label="Min Contour Area")

            bound_warnings = gr.Markdown("")
            bound_gallery = gr.Gallery(label="Results", columns=2, interactive=False)
            bound_zip = gr.File(label="Download All Results (.zip)")

            bound_btn.click(
                run_boundary,
                inputs=[bound_files,
                        b_gh_l, b_gs_l, b_gv_l, b_gh_u, b_gs_u, b_gv_u,
                        b_area],
                outputs=[bound_gallery, bound_zip, bound_warnings],
            )

        # ---- Tab 3: Cell Ratio ----
        with gr.Tab("Cell N/C Ratio"):
            with gr.Row():
                with gr.Column(scale=4):
                    cell_files = gr.File(file_count="multiple", label="Upload Images",
                                         file_types=[".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"])
                    cell_preview = gr.Gallery(label="Image Preview", columns=4, height=150,
                                              interactive=False)
                cell_btn = gr.Button("Analyze Cells", variant="primary", scale=0)
            cell_files.change(preview_uploads, inputs=[cell_files], outputs=[cell_preview])

            with gr.Accordion("Advanced Settings", open=False):
                with gr.Row():
                    cell_conf = gr.Slider(0.1, 1.0, value=cc["confidence_threshold"],
                                          step=0.05, label="Confidence Threshold")
                    cell_seg = gr.Slider(0.1, 1.0, value=cc["segmentation_threshold"],
                                         step=0.05, label="Segmentation Threshold")
                    cell_um = gr.Number(value=cc["um_conversion"], label="um/pixel")
                with gr.Row():
                    cell_hp1 = gr.Slider(10, 300, value=cc["hough_param1"],
                                         step=1, label="Hough Param1")
                    cell_hp2 = gr.Slider(0.1, 2.0, value=cc["hough_param2"],
                                         step=0.1, label="Hough Param2")
                with gr.Row():
                    cell_rmin = gr.Slider(1, 30, value=cc["hough_min_radius"],
                                          step=1, label="Min Radius")
                    cell_rmax = gr.Slider(10, 200, value=cc["hough_max_radius"],
                                          step=1, label="Max Radius")

            cell_warnings = gr.Markdown("")
            cell_ann_gallery = gr.Gallery(label="Annotated Results", columns=2, interactive=False)
            cell_crop_gallery = gr.Gallery(label="Individual Cells", columns=6, interactive=False)
            cell_table = gr.Dataframe(label="Cell Measurements")
            with gr.Row():
                cell_csv = gr.File(label="Download CSV")
                cell_zip = gr.File(label="Download All Results (.zip)")

            cell_btn.click(
                run_cell_ratio,
                inputs=[cell_files,
                        cell_conf, cell_seg, cell_um,
                        cell_hp1, cell_hp2, cell_rmin, cell_rmax],
                outputs=[cell_ann_gallery, cell_crop_gallery, cell_table, cell_csv, cell_zip, cell_warnings],
            )

        # ---- Tab 4: Combined ----
        with gr.Tab("Combined (Boundary + Counting)"):
            with gr.Row():
                with gr.Column(scale=4):
                    combo_files = gr.File(file_count="multiple", label="Upload Images",
                                          file_types=[".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"])
                    combo_preview = gr.Gallery(label="Image Preview", columns=4, height=150,
                                               interactive=False)
                combo_btn = gr.Button("Run Combined Analysis", variant="primary", scale=0)
            combo_files.change(preview_uploads, inputs=[combo_files], outputs=[combo_preview])

            with gr.Accordion("Advanced Settings", open=False):
                gr.Markdown("### Boundary Detection Settings")
                gr.Markdown("**Green HSV Range**")
                with gr.Row():
                    cb_gh_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][0], step=1, label="H Lower")
                    cb_gs_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][1], step=1, label="S Lower")
                    cb_gv_l = gr.Slider(0, 255, value=l1c["hsv_green_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    cb_gh_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][0], step=1, label="H Upper")
                    cb_gs_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][1], step=1, label="S Upper")
                    cb_gv_u = gr.Slider(0, 255, value=l1c["hsv_green_upper"][2], step=1, label="V Upper")
                cb_area = gr.Slider(1, 500, value=l1c["contour_area_min"], step=1, label="Min Contour Area")

                gr.Markdown("### Cell Counting Settings")
                gr.Markdown("**Green (Neutrophil) HSV Range**")
                with gr.Row():
                    cc_gh_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][0], step=1, label="H Lower")
                    cc_gs_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][1], step=1, label="S Lower")
                    cc_gv_l = gr.Slider(0, 255, value=lc["hsv_green_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    cc_gh_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][0], step=1, label="H Upper")
                    cc_gs_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][1], step=1, label="S Upper")
                    cc_gv_u = gr.Slider(0, 255, value=lc["hsv_green_upper"][2], step=1, label="V Upper")
                gr.Markdown("**Red (Macrophage) HSV Range**")
                with gr.Row():
                    cc_rh_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][0], step=1, label="H Lower")
                    cc_rs_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][1], step=1, label="S Lower")
                    cc_rv_l = gr.Slider(0, 255, value=lc["hsv_red1_lower"][2], step=1, label="V Lower")
                with gr.Row():
                    cc_rh_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][0], step=1, label="H Upper")
                    cc_rs_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][1], step=1, label="S Upper")
                    cc_rv_u = gr.Slider(0, 255, value=lc["hsv_red1_upper"][2], step=1, label="V Upper")
                with gr.Row():
                    cc_c_area = gr.Slider(10, 2000, value=lc["contour_area_min"], step=10, label="Min Contour Area")
                    cc_c_blur = gr.Slider(1, 31, value=lc["blur_kernel"], step=2, label="Blur Kernel")
                    cc_c_thresh = gr.Slider(200, 255, value=lc["mask_threshold"], step=1, label="Mask Threshold")

            combo_warnings = gr.Markdown("")
            combo_gallery = gr.Gallery(label="Results", columns=3, interactive=False)
            combo_table = gr.Dataframe(label="Cell Counts")
            with gr.Row():
                combo_csv = gr.File(label="Download CSV")
                combo_zip = gr.File(label="Download All Results (.zip)")

            combo_btn.click(
                run_combined,
                inputs=[combo_files,
                        cb_gh_l, cb_gs_l, cb_gv_l, cb_gh_u, cb_gs_u, cb_gv_u,
                        cb_area,
                        cc_gh_l, cc_gs_l, cc_gv_l, cc_gh_u, cc_gs_u, cc_gv_u,
                        cc_rh_l, cc_rs_l, cc_rv_l, cc_rh_u, cc_rs_u, cc_rv_u,
                        cc_c_area, cc_c_blur, cc_c_thresh],
                outputs=[combo_gallery, combo_table, combo_csv, combo_zip, combo_warnings],
            )

    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
