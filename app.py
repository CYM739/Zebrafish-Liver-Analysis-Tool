import json
import logging
import shutil
import tempfile
import time
import warnings
import zipfile
from pathlib import Path

import cv2
import gradio as gr
import numpy as np
import pandas as pd
from PIL import Image

from config import get_config, merge_overrides, profile_config
from i18n import LANGUAGES, localize_columns, t
from profiles import DEFAULT_PROFILE, PROFILES, offered
from profiles.base import BOOL, COUNT_STAINS, HSV, ModelUnavailable

CONFIG = get_config()
APP_CFG = CONFIG["app"]
RETENTION_S = APP_CFG["result_retention_minutes"] * 60
IMAGE_TYPES = [".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"]
HSV_MAX = (179, 255, 255)  # 8-bit OpenCV hue only spans 0-179
log = logging.getLogger(__name__)

_TMPDIR = Path(tempfile.mkdtemp(prefix="nhri_"))


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


def stained_cell_type(img):
    """Counting cell type whose stain clearly dominates a single-stain image, else None (config app.stain_*).
    A pixel is clearly stained when its stain channel exceeds both other channels by stain_margin."""
    px = img.astype(np.int16)
    counts = {cell_type: int((px[..., ch] - np.delete(px, ch, axis=2).max(axis=2) > APP_CFG["stain_margin"]).sum())
              for cell_type, ch in COUNT_STAINS.items()}
    (top, n), (_, other) = sorted(counts.items(), key=lambda kv: -kv[1])
    return top if n >= APP_CFG["stain_min_px"] and n >= APP_CFG["stain_dominance"] * other else None


def save_image(img, path):
    """Save a BGR array or PIL image as PNG."""
    if not isinstance(img, Image.Image):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    img.save(path)
    return str(path)


def preview_uploads(*file_lists):
    """Convert the files of every upload box (including .tif) to previewable images."""
    files = [f for files in file_lists for f in files or []]
    if not files:
        return []
    run_dir = new_run_dir()
    previews = []
    for i, f in enumerate(files):
        img = read_uploaded_image(f)
        if img is not None:
            previews.append((save_image(img, run_dir / f"preview_{i}.png"), Path(f).name))
    return previews


def parse_settings(spec, defaults, values):
    """Inverse of build_settings: consume UI values from an iterator into a config dict."""
    overrides = {}
    for key, _, kind in spec:
        if kind == HSV:
            for bound in ("lower", "upper"):
                overrides[f"{key}_{bound}"] = [int(next(values)) for _ in range(3)]
        else:
            value = next(values)  # None (cleared number box) falls back to the config default
            overrides[key] = None if value is None else type(defaults[key])(value)
    return merge_overrides(defaults, overrides)


class Batch:
    """Collects the outputs of one analysis run."""

    def __init__(self, lang, profile, settings):
        self.lang = lang
        self.profile = profile
        self.settings = settings
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
        self.row = {}

    def end(self):
        if self.row:
            self.summary.append({"profile": self.profile, "filename": self.filename, **self.row})

    def save(self, img, suffix, caption, gallery=None):
        """Save a result image, show it in a gallery and return its file name for the CSV."""
        path = save_image(img, self.dir / f"{self.stem}_{suffix}.png")
        (self.gallery if gallery is None else gallery).append((path, caption))
        return Path(path).name

    def add(self, r):
        """Record one analysis result (see profiles.base.result) for the current file."""
        names = {suffix: self.save(img, suffix, self.t(caption, name=self.stem, **args))
                 for suffix, caption, img, args in r["images"]}
        crops = r["crops"] or [None] * len(r["cells"])
        for cell, crop in zip(r["cells"], crops):
            row = {"profile": self.profile, "filename": self.filename, "result_image": names[cell["image"]]}
            row.update({k: v for k, v in cell.items() if k != "image"})
            if crop is not None:
                row["crop_image"] = self.save(crop, f"cell_{cell['cell_id']}",
                                              self.t("cap_cell", name=self.stem, id=cell["cell_id"]), gallery=self.crops)
            self.details.append(row)
        self.row.update(r["summary"])
        self.warn(r["warning"], **r["warning_args"])

    def warn(self, key, **kwargs):
        if key:
            self.warnings.append(f"**{self.filename}**: {self.t(key, **kwargs)}")

    def outputs(self, prefix):
        """Write CSVs, the settings used and the zip; return everything a tab can display."""
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
            settings_path = self.dir / f"{prefix}_settings.json"
            settings_path.write_text(json.dumps({"profile": self.profile, "settings": self.settings},
                                                indent=2, ensure_ascii=False), encoding="utf-8")
            zip_path = str(self.dir / f"{prefix}_results.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in files + [str(settings_path)]:
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


# "uploads": (label i18n key, cell type) per upload box. A box with a cell type takes single-stain images
# whose cells are all of that type (passed to "count" as cell_types); None = any image, every analysis.
UPLOAD_ANY = (("upload", None),)
TABS = [
    {"label": "tab_count", "button": "btn_count", "analyses": ["count"], "prefix": "counting", "columns": 2,
     "uploads": (("upload_neutrophil", "neutrophil"), ("upload_macrophage", "macrophage")),
     "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
    {"label": "tab_boundary", "button": "btn_boundary", "analyses": ["boundary"], "prefix": "boundary", "columns": 2,
     "outputs": ["warnings", "gallery", "zip"]},
    {"label": "tab_cell", "button": "btn_cell", "analyses": ["cell"], "prefix": "cell_ratio", "columns": 2,
     "outputs": ["warnings", "gallery", "crops", "summary", "details", "csv", "zip"]},
    {"label": "tab_combined", "button": "btn_combined", "analyses": ["boundary", "count"], "prefix": "combined",
     "columns": 3, "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
]


def make_handler(tab, names):
    uploads = tab.get("uploads", UPLOAD_ANY)

    def run(lang, profile, *inputs, progress=gr.Progress()):
        # Inputs: one file list per upload box, then settings for every offered profile (see build_tab);
        # keep only the selected profile's settings
        jobs = [(f, cell_type) for (_, cell_type), files in zip(uploads, inputs) for f in files or []]
        values = iter(inputs[len(uploads):])
        cfgs = {name: {a: parse_settings(PROFILES[name].ANALYSES[a].settings, profile_config(name, a), values)
                       for a in tab["analyses"]}
                for name in names}[profile]
        batch = Batch(lang, profile, cfgs)
        analyses = PROFILES[profile].ANALYSES
        for f, cell_type in progress.tqdm(jobs, desc=batch.t("progress")):
            batch.begin(f)
            img = read_uploaded_image(f)
            if img is None:
                batch.warn("warn_read_failed")
                continue
            kwargs = {}
            if cell_type:
                detected = stained_cell_type(img)
                if detected and detected != cell_type:  # put in the other box: count what it shows
                    batch.warn(f"warn_upload_is_{detected}")
                    cell_type = detected
                kwargs = {"cell_types": (cell_type,)}
            try:
                for a in tab["analyses"]:
                    batch.add(analyses[a].run(img, cfgs[a], **kwargs))
            except ModelUnavailable as e:
                log.exception("Model unavailable")
                batch.warn(e.args[0])
            except Exception:
                log.exception("Analysis failed for %s", f)
                batch.warn("warn_unexpected_error")
            batch.end()
        out = batch.outputs(tab["prefix"])
        return [out[k] for k in tab["outputs"]]
    return run


# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------
# Gradio draws gallery tiles as squares as wide as a column, so a single wide image overflows a
# short gallery and only its top shows. In .fit-gallery each row is the gallery's full height
# and object_fit="contain" scales the whole image into it. On phones, .stack-on-phone galleries show
# one column-wide square per row instead, since several images side by side would be tiny.
CSS = """
.fit-gallery .grid-container { height: 100%; grid-template-rows: none !important; grid-auto-rows: 100% !important; }
.fit-gallery .thumbnail-item { aspect-ratio: auto !important; }
@media (max-width: 640px) {
  .stack-on-phone .grid-container { height: auto; grid-template-columns: 1fr !important; grid-auto-rows: auto !important; }
  .stack-on-phone .thumbnail-item { aspect-ratio: 1 !important; }
}
"""


class Translatable:
    """Creates components with text in the current language and remembers them for relabelling."""

    def __init__(self, lang):
        self.lang = lang
        self.entries = []  # (component, lang -> update kwargs)

    def __call__(self, cls, key, prop="label", fmt=None, **kwargs):
        fmt = fmt or {}
        return self.add(cls, lambda lang: {prop: t(key, lang, **fmt)}, **kwargs)

    def add(self, cls, text, **kwargs):
        component = cls(**text(self.lang), **kwargs)
        self.entries.append((component, text))
        return component

    @property
    def components(self):
        return [c for c, _ in self.entries]

    def relabel(self, lang):
        return [gr.update(**text(lang)) for _, text in self.entries]


def build_settings(tr, spec, defaults):
    """Advanced-settings inputs for one analysis, in the order parse_settings reads them."""
    inputs, scalars = [], []
    for key, label, kind in spec:
        if kind == HSV:
            tr(gr.Markdown, label, prop="value")
            for bound in ("lower", "upper"):
                with gr.Row():
                    for ch, mx, v in zip("HSV", HSV_MAX, defaults[f"{key}_{bound}"]):
                        inputs.append(tr(gr.Slider, f"hsv_{bound}", fmt={"ch": ch},
                                         minimum=0, maximum=mx, value=min(v, mx), step=1))
        else:
            scalars.append((key, label, kind))
    with gr.Row():
        for key, label, kind in scalars:
            if kind is None:
                inputs.append(tr(gr.Number, label, value=defaults[key]))
            elif kind == BOOL:
                inputs.append(tr(gr.Checkbox, label, value=defaults[key]))
            else:
                inputs.append(tr(gr.Slider, label, minimum=kind[0], maximum=kind[1], step=kind[2], value=defaults[key]))
    return inputs


def describe(lang, profile):
    return t(f"profile_desc_{profile}", lang)


def build_tab(tr, lang, tab):
    names = offered(tab["analyses"])
    with tr(gr.Tab, tab["label"]):
        with gr.Row(visible=len(names) > 1):  # method selector only where there is a choice
            profile = tr.add(gr.Dropdown, lambda lang: {"label": t("profile", lang),
                                                        "choices": [(t(f"profile_{n}", lang), n) for n in names]},
                             value=DEFAULT_PROFILE, scale=0, min_width=260)
            with gr.Column(min_width=320):  # wraps below the selector on phones
                description = gr.Markdown(describe(tr.lang, DEFAULT_PROFILE))
        with gr.Row():
            with gr.Column(scale=4):
                with gr.Row():
                    files = [tr(gr.File, label, file_count="multiple", file_types=IMAGE_TYPES, min_width=240)
                             for label, _ in tab.get("uploads", UPLOAD_ANY)]
                preview = tr(gr.Gallery, "preview", columns=4, height=150, object_fit="contain",
                             elem_classes="fit-gallery", interactive=False)
            button = tr(gr.Button, tab["button"], prop="value", variant="primary", scale=0)
        for box in files:
            box.change(preview_uploads, inputs=files, outputs=[preview])

        panels, settings = {}, []
        with tr(gr.Accordion, "advanced", open=False):
            for name in names:
                with gr.Column(visible=name == DEFAULT_PROFILE) as panels[name]:
                    for a in tab["analyses"]:
                        if len(tab["analyses"]) > 1:
                            tr(gr.Markdown, f"section_{a}", prop="value")
                        settings += build_settings(tr, PROFILES[name].ANALYSES[a].settings, profile_config(name, a))

        outputs = {
            "warnings": gr.Markdown(""),
            "gallery": tr(gr.Gallery, "results", columns=tab["columns"], height=600,
                          object_fit="contain", elem_classes=["fit-gallery", "stack-on-phone"], interactive=False),
        }
        if "crops" in tab["outputs"]:
            outputs["crops"] = tr(gr.Gallery, "crops", columns=6, object_fit="contain", interactive=False)
        if "summary" in tab["outputs"]:
            outputs["summary"] = tr(gr.Dataframe, "summary_table")
            outputs["details"] = tr(gr.Dataframe, "details_table")
        with gr.Row():
            if "csv" in tab["outputs"]:
                outputs["csv"] = tr(gr.File, "csv", file_count="multiple")
            outputs["zip"] = tr(gr.File, "zip")

        button.click(make_handler(tab, names), inputs=[lang, profile, *files] + settings,
                     outputs=[outputs[k] for k in tab["outputs"]])
        lang.change(describe, inputs=[lang, profile], outputs=[description])
        profile.change(describe, inputs=[lang, profile], outputs=[description])
        profile.change(lambda selected: [gr.update(visible=name == selected) for name in panels],
                       inputs=[profile], outputs=list(panels.values()))


def build_app():
    default_lang = APP_CFG["default_language"]
    tr = Translatable(default_lang)
    with gr.Blocks(title="Zebrafish Liver Analysis Tool", delete_cache=(RETENTION_S, RETENTION_S),
                   analytics_enabled=False) as app:  # no usage reports to Gradio / Hugging Face
        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=320):  # wraps the language toggle below the title on phones
                tr(gr.Markdown, "title", prop="value")
            lang = gr.Radio(LANGUAGES, value=default_lang, show_label=False, container=False, scale=0, min_width=200)
        for tab in TABS:
            build_tab(tr, lang, tab)
        lang.change(tr.relabel, inputs=[lang], outputs=tr.components)
    return app


def get_lan_ip():
    """Best-effort detection of this PC's LAN IP (no packets are sent)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Deliberately hidden log noise; keep in sync with CHANGELOG.md ("Suppressed messages").
    # cpsam does not use the optional CPDINO (DINOv3) backbone.
    logging.getLogger("cellpose.vit").addFilter(lambda r: "CPDINO" not in r.getMessage())
    # Cellpose's own sparse tensors are valid; the invariant checks only cost speed.
    warnings.filterwarnings("ignore", message="Sparse invariant checks")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Gradio's internal HTTP requests
    PORT, HOST = APP_CFG["server_port"], APP_CFG["server_name"]
    app = build_app()
    print(f"\nLocal access:   http://localhost:{PORT}")
    # Other PCs can connect only when the server listens beyond this PC (0.0.0.0 = all networks)
    lan_ip = get_lan_ip() if HOST == "0.0.0.0" else None if HOST in ("127.0.0.1", "localhost") else HOST
    if lan_ip:
        print(f"Network access: http://{lan_ip}:{PORT}\n")
    app.launch(server_name=HOST, server_port=PORT, quiet=True, css=CSS)
