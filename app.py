import json
import logging
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

from config import get_config, merge_overrides, profile_config
from i18n import LANGUAGES, localize_columns, t
from profiles import DEFAULT_PROFILE, PROFILES
from profiles.base import BOOL, HSV, ModelUnavailable

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


TABS = [
    {"label": "tab_count", "button": "btn_count", "analyses": ["count"], "prefix": "counting", "columns": 2,
     "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
    {"label": "tab_boundary", "button": "btn_boundary", "analyses": ["boundary"], "prefix": "boundary", "columns": 2,
     "outputs": ["warnings", "gallery", "zip"]},
    {"label": "tab_cell", "button": "btn_cell", "analyses": ["cell"], "prefix": "cell_ratio", "columns": 2,
     "outputs": ["warnings", "gallery", "crops", "summary", "details", "csv", "zip"]},
    {"label": "tab_combined", "button": "btn_combined", "analyses": ["boundary", "count"], "prefix": "combined",
     "columns": 3, "outputs": ["warnings", "gallery", "summary", "details", "csv", "zip"]},
]


def make_handler(tab):
    def run(lang, profile, files, *values, progress=gr.Progress()):
        # Settings inputs cover every profile (see build_tab); keep only the selected profile's
        values = iter(values)
        cfgs = {name: {a: parse_settings(p.ANALYSES[a].settings, profile_config(name, a), values)
                       for a in tab["analyses"]}
                for name, p in PROFILES.items()}[profile]
        batch = Batch(lang, profile, cfgs)
        analyses = PROFILES[profile].ANALYSES
        for f in progress.tqdm(files or [], desc=batch.t("progress")):
            batch.begin(f)
            img = read_uploaded_image(f)
            if img is None:
                batch.warn("warn_read_failed")
                continue
            try:
                for a in tab["analyses"]:
                    batch.add(analyses[a].run(img, cfgs[a]))
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


def build_tab(tr, lang, profile, tab):
    """Returns this tab's settings panels: {profile name: column shown only for that profile}."""
    with tr(gr.Tab, tab["label"]):
        with gr.Row():
            with gr.Column(scale=4):
                files = tr(gr.File, "upload", file_count="multiple", file_types=IMAGE_TYPES)
                preview = tr(gr.Gallery, "preview", columns=4, height=150, interactive=False)
            button = tr(gr.Button, tab["button"], prop="value", variant="primary", scale=0)
        files.change(preview_uploads, inputs=[files], outputs=[preview])

        panels, settings = {}, []
        with tr(gr.Accordion, "advanced", open=False):
            for name, p in PROFILES.items():
                with gr.Column(visible=name == DEFAULT_PROFILE) as panels[name]:
                    for a in tab["analyses"]:
                        if len(tab["analyses"]) > 1:
                            tr(gr.Markdown, f"section_{a}", prop="value")
                        settings += build_settings(tr, p.ANALYSES[a].settings, profile_config(name, a))

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

        button.click(make_handler(tab), inputs=[lang, profile, files] + settings,
                     outputs=[outputs[k] for k in tab["outputs"]])
    return panels


def build_app():
    default_lang = APP_CFG["default_language"]
    tr = Translatable(default_lang)
    profile_choices = lambda lang: [(t(f"profile_{name}", lang), name) for name in PROFILES]
    describe = lambda lang, profile: t(f"profile_desc_{profile}", lang)

    with gr.Blocks(title="Zebrafish Liver Analysis Tool", delete_cache=(RETENTION_S, RETENTION_S)) as app:
        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=320):  # wraps the selectors below the title on phones
                tr(gr.Markdown, "title", prop="value")
            profile = tr.add(gr.Dropdown, lambda lang: {"label": t("profile", lang), "choices": profile_choices(lang)},
                             value=DEFAULT_PROFILE, scale=0, min_width=260)
            lang = gr.Radio(LANGUAGES, value=default_lang, show_label=False, container=False, scale=0, min_width=200)
        description = gr.Markdown(describe(default_lang, DEFAULT_PROFILE))

        panels = [build_tab(tr, lang, profile, tab) for tab in TABS]
        panel_list = [panel for tab_panels in panels for panel in tab_panels.values()]

        lang.change(tr.relabel, inputs=[lang], outputs=tr.components)
        lang.change(describe, inputs=[lang, profile], outputs=[description])
        profile.change(describe, inputs=[lang, profile], outputs=[description])
        profile.change(lambda selected: [gr.update(visible=name == selected) for p in panels for name in p],
                       inputs=[profile], outputs=panel_list)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_app().launch(server_name=APP_CFG["server_name"], server_port=APP_CFG["server_port"])
