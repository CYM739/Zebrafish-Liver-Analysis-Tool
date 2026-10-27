import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import cv2
import gradio as gr
import numpy as np
import pandas as pd
from PIL import Image

from config import get_config, merge_overrides
from i18n import LANGUAGES, localize_columns, t
from liver.main import count_cells
from liver1.main import detect_boundary
from cell.main import load_models, analyze_cells, summarize_cells

CONFIG = get_config()
APP_CFG = CONFIG["app"]
RETENTION_S = APP_CFG["result_retention_minutes"] * 60
IMAGE_TYPES = [".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"]

# Load cell models once at startup
print("Loading cell analysis models...")
CELL_MODELS = load_models(CONFIG["cell"])
print("Models loaded.")

_TMPDIR = Path(tempfile.mkdtemp(prefix="nhri_"))

# Tunable settings shown under "Advanced Settings"; defaults come from config.yaml.
# Entry: (config key, i18n key, (min, max, step) | HSV | None). HSV is a <key>_lower/<key>_upper
# pair of [H, S, V] lists; None is a free number input.
HSV = "hsv"
HSV_MAX = (179, 255, 255)  # 8-bit OpenCV hue only spans 0-179
SETTINGS = {
    "liver": [
        ("hsv_green", "hsv_neutrophil", HSV),
        ("hsv_red1", "hsv_macrophage", HSV),
        ("contour_area_min", "contour_area_min", (10, 2000, 10)),
        ("blur_kernel", "blur_kernel", (1, 31, 2)),
        ("mask_threshold", "mask_threshold", (200, 255, 1)),
    ],
    "liver1": [
        ("hsv_green", "hsv_liver", HSV),
        ("contour_area_min", "contour_area_min", (1, 500, 1)),
    ],
    "cell": [
        ("confidence_threshold", "confidence_threshold", (0.1, 1.0, 0.05)),
        ("segmentation_threshold", "segmentation_threshold", (0.1, 1.0, 0.05)),
        ("um_conversion", "um_conversion", None),
        ("hough_param1", "hough_param1", (10, 300, 1)),
        ("hough_param2", "hough_param2", (0.1, 1.0, 0.05)),
        ("hough_min_radius", "hough_min_radius", (1, 30, 1)),
        ("hough_max_radius", "hough_max_radius", (10, 200, 1)),
    ],
}


def new_run_dir():
    """Private output folder per request, so concurrent users never overwrite each other.
    Folders older than the retention period are removed."""
    now = time.time()
    for d in _TMPDIR.iterdir():
        if now - d.stat().st_mtime > RETENTION_S:
            shutil.rmtree(d, ignore_errors=True)
    return Path(tempfile.mkdtemp(dir=_TMPDIR))


def read_uploaded_image(filepath):
    """Read an image from a Gradio upload path, handling Unicode."""
    return cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)


def save_image(img, path):
    """Save a BGR array or PIL image as PNG."""
    if not isinstance(img, Image.Image):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    img.save(path)
    return str(path)


def preview_uploads(files):
    """Convert uploaded files (including .tif) to previewable images."""
    if not files:
        return []
    run_dir = new_run_dir()
    previews = []
    for i, f in enumerate(files):
        img = read_uploaded_image(f)
        if img is not None:
            previews.append((save_image(img, run_dir / f"preview_{i}.png"), Path(f).name))
    return previews


def parse_settings(section, values):
    """Inverse of build_settings: consume UI values from an iterator into a config dict."""
    defaults = CONFIG[section]
    overrides = {}
    for key, _, rng in SETTINGS[section]:
        if rng == HSV:
            for bound in ("lower", "upper"):
                overrides[f"{key}_{bound}"] = [int(next(values)) for _ in range(3)]
        else:
            value = next(values)  # None (cleared number box) falls back to the config default
            overrides[key] = None if value is None else type(defaults[key])(value)
    return merge_overrides(section, overrides)


class Batch:
    """Collects the outputs of one analysis run."""

    def __init__(self, lang):
        self.lang = lang
        self.dir = new_run_dir()
        self.gallery, self.crops, self.summary, self.details, self.warnings = [], [], [], [], []
        self._stems = set()

    def t(self, key, **kwargs):
        return t(key, self.lang, **kwargs)

    def begin(self, src):
        """Start a new input file; result file names are derived from its (de-duplicated) stem."""
        self.filename = Path(src).name
        stem = Path(src).stem
        self.stem = f"{stem}_{len(self._stems)}" if stem in self._stems else stem
        self._stems.add(self.stem)

    def save(self, img, suffix, caption, gallery=None):
        """Save a result image, show it in a gallery and return its file name for the CSV."""
        path = save_image(img, self.dir / f"{self.stem}_{suffix}.png")
        (self.gallery if gallery is None else gallery).append((path, caption))
        return Path(path).name

    def warn(self, key, **kwargs):
        if key:
            self.warnings.append(f"**{self.filename}**: {self.t(key, **kwargs)}")

    def outputs(self, prefix):
        """Write CSVs and the zip; return everything a tab can display."""
        tables = {"summary": pd.DataFrame(self.summary).round(4),
                  "cells": pd.DataFrame(self.details).round(4)}
        csvs = []
        for name, df in tables.items():
            if not df.empty:
                path = self.dir / f"{prefix}_{name}.csv"
                df.to_csv(path, index=False, encoding="utf-8-sig")  # BOM so Excel reads non-ASCII names
                csvs.append(str(path))
        files = [p for p, _ in self.gallery + self.crops] + csvs
        zip_path = None
        if files:
            zip_path = str(self.dir / f"{prefix}_results.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in files:
                    zf.write(p, Path(p).name)
        return {
            "warnings": "\n".join([self.t("warnings")] + [f"- {w}" for w in self.warnings]) if self.warnings else "",
            "gallery": self.gallery,
            "crops": self.crops,
            "summary": localize_columns(tables["summary"], self.lang),
            "details": localize_columns(tables["cells"], self.lang),
            "csv": csvs or None,
            "zip": zip_path,
        }


# ---------------------------------------------------------------------------
# Per-image analyses
# ---------------------------------------------------------------------------
def process_count(batch, img, cfgs):
    r = count_cells(img, cfgs["liver"])
    batch.warn(r["warning"])
    for cell_type, image_key, cells_key, caption in (
            ("macrophage", "red_img", "macrophages", "cap_macrophages"),
            ("neutrophil", "green_img", "neutrophils", "cap_neutrophils")):
        cells = r[cells_key]
        result_image = batch.save(r[image_key], cells_key, batch.t(caption, name=batch.stem, n=len(cells)))
        batch.details += [{"filename": batch.filename, "result_image": result_image, "cell_type": cell_type, **c}
                          for c in cells]
    batch.summary.append({"filename": batch.filename,
                          "macrophage_count": len(r["macrophages"]),
                          "neutrophil_count": len(r["neutrophils"])})


def process_boundary(batch, img, cfgs):
    r = detect_boundary(img, cfgs["liver1"])
    batch.warn(r["warning"])
    batch.save(r["output_img"], "boundary", batch.t("cap_boundary", name=batch.stem))


def process_combined(batch, img, cfgs):
    process_boundary(batch, img, cfgs)
    process_count(batch, img, cfgs)


def process_cell(batch, img, cfgs):
    cfg = cfgs["cell"]
    r = analyze_cells(img, CELL_MODELS, cfg)
    batch.warn(r["warning"], n=r["n_candidates"], threshold=cfg["confidence_threshold"])
    cells = r["cells"]
    result_image = batch.save(r["annotated_img"], "segmentation",
                              batch.t("cap_segmentation", name=batch.stem, n=len(cells)))
    batch.save(r["all_circles_img"], "all_nuclei", batch.t("cap_all_nuclei", name=batch.stem, n=r["n_candidates"]))
    for cell, crop in zip(cells, r["cell_gallery"]):
        crop_image = batch.save(crop, f"cell_{cell['cell_id']}",
                                batch.t("cap_cell", name=batch.stem, id=cell["cell_id"]), gallery=batch.crops)
        batch.details.append({"filename": batch.filename, "result_image": result_image, **cell,
                              "crop_image": crop_image})
    batch.summary.append({"filename": batch.filename, "n_candidates": r["n_candidates"], **summarize_cells(cells)})


TABS = [
    {"label": "tab_count", "button": "btn_count", "sections": ["liver"], "process": process_count,
     "prefix": "counting", "columns": 2, "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
    {"label": "tab_boundary", "button": "btn_boundary", "sections": ["liver1"], "process": process_boundary,
     "prefix": "boundary", "columns": 2, "outputs": ["warnings", "gallery", "zip"]},
    {"label": "tab_cell", "button": "btn_cell", "sections": ["cell"], "process": process_cell,
     "prefix": "cell_ratio", "columns": 2,
     "outputs": ["warnings", "gallery", "crops", "summary", "details", "csv", "zip"]},
    {"label": "tab_combined", "button": "btn_combined", "sections": ["liver1", "liver"], "process": process_combined,
     "prefix": "combined", "columns": 3, "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
]


def make_handler(tab):
    def run(lang, files, *values, progress=gr.Progress()):
        batch = Batch(lang)
        if files:
            values = iter(values)
            cfgs = {section: parse_settings(section, values) for section in tab["sections"]}
            for f in progress.tqdm(files, desc=batch.t("progress")):
                batch.begin(f)
                img = read_uploaded_image(f)
                if img is None:
                    batch.warn("warn_read_failed")
                    continue
                tab["process"](batch, img, cfgs)
        out = batch.outputs(tab["prefix"])
        return [out[k] for k in tab["outputs"]]
    return run


# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------
class Translatable:
    """Creates components with text in the current language and remembers them for relabelling."""

    def __init__(self, lang):
        self.lang = lang
        self.entries = []

    def __call__(self, cls, key, prop="label", fmt=None, **kwargs):
        fmt = fmt or {}
        component = cls(**{prop: t(key, self.lang, **fmt)}, **kwargs)
        self.entries.append((component, prop, key, fmt))
        return component

    @property
    def components(self):
        return [c for c, *_ in self.entries]

    def relabel(self, lang):
        return [gr.update(**{prop: t(key, lang, **fmt)}) for _, prop, key, fmt in self.entries]


def build_settings(tr, section):
    """Advanced-settings inputs for one config section, in the order parse_settings reads them."""
    defaults = CONFIG[section]
    inputs, scalars = [], []
    for key, label, rng in SETTINGS[section]:
        if rng == HSV:
            tr(gr.Markdown, label, prop="value")
            for bound in ("lower", "upper"):
                with gr.Row():
                    for ch, mx, v in zip("HSV", HSV_MAX, defaults[f"{key}_{bound}"]):
                        inputs.append(tr(gr.Slider, f"hsv_{bound}", fmt={"ch": ch},
                                         minimum=0, maximum=mx, value=min(v, mx), step=1))
        else:
            scalars.append((key, label, rng))
    with gr.Row():
        for key, label, rng in scalars:
            if rng is None:
                inputs.append(tr(gr.Number, label, value=defaults[key]))
            else:
                inputs.append(tr(gr.Slider, label, minimum=rng[0], maximum=rng[1], step=rng[2], value=defaults[key]))
    return inputs


def build_tab(tr, lang, tab):
    with tr(gr.Tab, tab["label"]):
        with gr.Row():
            with gr.Column(scale=4):
                files = tr(gr.File, "upload", file_count="multiple", file_types=IMAGE_TYPES)
                preview = tr(gr.Gallery, "preview", columns=4, height=150, interactive=False)
            button = tr(gr.Button, tab["button"], prop="value", variant="primary", scale=0)
        files.change(preview_uploads, inputs=[files], outputs=[preview])

        with tr(gr.Accordion, "advanced", open=False):
            settings = []
            for section in tab["sections"]:
                if len(tab["sections"]) > 1:
                    tr(gr.Markdown, f"section_{section}", prop="value")
                settings += build_settings(tr, section)

        outputs = {
            "warnings": gr.Markdown(""),
            "gallery": tr(gr.Gallery, "results", columns=tab["columns"], interactive=False),
        }
        if "crops" in tab["outputs"]:
            outputs["crops"] = tr(gr.Gallery, "crops", columns=6, interactive=False)
        if "summary" in tab["outputs"]:
            outputs["summary"] = tr(gr.Dataframe, "summary_table")
            outputs["details"] = tr(gr.Dataframe, "details_table")
        with gr.Row():
            if "csv" in tab["outputs"]:
                outputs["csv"] = tr(gr.File, "csv", file_count="multiple")
            outputs["zip"] = tr(gr.File, "zip")

        button.click(make_handler(tab), inputs=[lang, files] + settings,
                     outputs=[outputs[k] for k in tab["outputs"]])


def build_app():
    default_lang = APP_CFG["default_language"]
    tr = Translatable(default_lang)
    with gr.Blocks(title="Zebrafish Liver Analysis Tool", delete_cache=(RETENTION_S, RETENTION_S)) as app:
        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=320):  # wraps the language toggle below the title on phones
                tr(gr.Markdown, "title", prop="value")
            lang = gr.Radio(LANGUAGES, value=default_lang, show_label=False, container=False, scale=0, min_width=200)
        for tab in TABS:
            build_tab(tr, lang, tab)
        lang.change(tr.relabel, inputs=[lang], outputs=tr.components)
    return app


if __name__ == "__main__":
    build_app().launch(server_name=APP_CFG["server_name"], server_port=APP_CFG["server_port"])
