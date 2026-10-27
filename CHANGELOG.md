# Changelog

All changes relative to the [original repository](https://github.com/dhcl8881/nhri) by dhcl8881.

## [Unreleased] - 2026-10-24 (profiles)

### Added

- **Analysis profiles** (`profiles/`): each is a complete set of algorithms and models. Settings per profile live under `profiles:` in `config.yaml`; `offered_in_app` limits which analyses a profile can be picked for, and tabs with more than one offered profile show a method selector. Every CSV row records the profile, and the `.zip` includes `*_settings.json` with the exact settings used.
  - `dhcl8881` (default): the original author's code (`liver/`, `liver1/`, `cell/`), unchanged. Verified to reproduce the original's counts and every per-cell measurement on all sample images.
  - `cpsam-v1`: the first improved profile (`profiles/cpsam_v1/`), offered in the app for the N/C ratio only:
    - **N/C ratio** by Cellpose-SAM (`cpsam_v2`) cell and nucleus segmentation. N/C denominator set by `nc_denominator` (dev-side, not in the app): `cell` (default) = nucleus ÷ whole cell, `cytoplasm` = nucleus ÷ (cell − nucleus). Quality filters, all adjustable: exclude cells cut off by the image edge, out-of-focus cells, cells without exactly one nucleus, and outlines drawn around the nucleus only. The summary adds the median N/C.
    - **Counting** (dev-only until validated): scale-bar exclusion compares x with the width and y with the height; red uses both hue ranges (0–10, 170–179); green is limited to hues 40–90. Possibly merged cells (≥ 3× the image's median area) are outlined in orange and flagged in the CSV; they are not split.
    - **Boundary** (dev-only until validated): each green region is outlined separately (no lines across the image).
- `cellpose==4.2.1.1` and `scipy` dependencies.

### Changed

- `opencv-python` → `opencv-python-headless` (required by cellpose; both install `cv2`, so they cannot coexist).
- Models load on first use instead of at startup. If the dhcl8881 weights or the Cellpose model are missing, the app still starts and shows a message on the affected analysis.
- `app.py` handles all profiles through one result format (`profiles/base.py`), so adding a profile needs no app changes.
- Shared contour labelling helpers moved from `liver/main.py` to `annotate.py`.

## 2026-10-22 (cell IDs, 中/英)

### Added

- **Every detection is numbered and traceable to the CSV.** Result images now carry an ID next to each detected cell (`M1…` macrophages, `N1…` neutrophils, `1…` hepatocytes), and each tab writes two CSVs:
  - `*_summary.csv`: one row per image (counts, or the N/C-ratio means)
  - `*_cells.csv`: one row per detected cell with `cell_id`, `x`, `y`, `result_image` (the highlighted image it appears on), and, for the N/C ratio, `classifier_score` and `crop_image`
- **中文 / English toggle** for the whole UI (`i18n.py`); the default language is set in `config.yaml` → `app.default_language`
- `annotate.py`: a shared ID-label drawing helper; label colour and size are set in `config.yaml` → `annotation`
- `config.yaml` → `app`: server address/port, default language, and result retention time

### Changed

- **`app.py`** rewritten around a single tab builder and a shared run loop. The four tabs are declared in `TABS`/`SETTINGS` instead of ~300 lines of copy-pasted sliders and handlers. The combined tab reuses the boundary and counting steps.
- The N/C ratio CSV no longer mixes an unlabelled average row in with the cells; averages moved to `*_summary.csv`. The CLI writes `test_summary.csv` alongside `test.csv`.
- `cell/main.py`: classification and segmentation now happen in one pass; the U-Net previously ran twice per accepted cell. Results are identical, verified against the previous code on all sample images.
- Analysis modules return warning keys instead of English sentences, so the UI can translate them. Warnings are reworded for end users.
- The HSV hue slider max is 179 (the OpenCV 8-bit hue range; equivalent to the old 255). The "Nucleus roundness" (`hough_param2`) slider max is 1.0, because OpenCV's `HOUGH_GRADIENT_ALT` finds nothing above 1.
- Gallery captions put the result type / cell number first, so they stay readable when truncated on phones.
- CSV files are written as UTF-8 with BOM, so Excel shows non-ASCII file names correctly.
- CLIs run from the repository root (`python -m liver.main ...`). The `liver` CLI always writes to `liver/result/`.

### Fixed

- Concurrent users overwrote each other's result files and CSVs, because every request wrote to the same fixed file names. Each run now gets its own folder, and old folders are removed after `result_retention_minutes`.
- Temporary results and uploads grew without limit; both are now cleaned up after the retention period.
- Startup downloaded ImageNet ResNet18 weights that were immediately overwritten by `save1.pt`, which broke startup on offline machines. `Net(pretrained=False)` is now used for inference.
- On a CUDA machine, the full-image segmentation overlay mixed CPU and GPU tensors; masks are now moved to CPU before drawing.
- `liver1`: removed unused point-sorting code that raised `IndexError` on some inputs, and an unused `boundary_contours` output.
- An even blur kernel value no longer crashes `cv2.GaussianBlur`.
- Removed tracked `__pycache__` files and the unused root `main.py`.

## 2026-04-14

### Added

- **Gradio Web UI** (`app.py`)
  - 4-tab interface: Neutrophil/Macrophage Count, Liver Boundary Detection, Cell N/C Ratio, Combined Mode
  - Single or batch image upload with .tif preview support
  - Interactive results gallery, data tables, and per-image captions with counts
  - Advanced Settings accordion per tab with override sliders for all tunable parameters
  - Download CSV and Download All Results (.zip) buttons on every tab
  - Warning messages when analysis detects nothing (wrong image type, no cells found, etc.)
  - Progress status text showing current processing step per image

- **Configuration system**
  - `config.yaml` — all hardcoded thresholds extracted into a single config file (HSV ranges, contour area minimums, blur kernels, HoughCircles params, model confidence thresholds, um/pixel conversion, etc.)
  - `config.py` — config loader with `get_config()` and `merge_overrides()` for runtime slider overrides without mutating defaults

- **Project packaging** (`pyproject.toml`)
  - uv-managed project with portable Python 3.10
  - Pinned dependency versions (torch 2.11.0+cu126, torchvision 0.26.0+cu126, gradio 6.12.0, etc.)
  - PyTorch CUDA index pinned via `[tool.uv.sources]` — prevents accidental CPU-only torch installation
  - `uv sync` reproduces the exact environment

- **Package init files** — `liver/__init__.py`, `liver1/__init__.py`, `cell/__init__.py` for proper module imports

### Changed

- **`liver/main.py`** — extracted logic into `count_cells(img, config)` function that accepts a BGR array and config dict, returns results dict instead of writing files. Argparse moved inside `__main__` guard. Added early return with warning when liver mask can't be formed (< 3 contour points).

- **`liver/utils.py`** — `greenandred()` and `find()` now accept optional `config` dict for HSV ranges, blur kernel, and contour area threshold instead of hardcoded values. Defaults preserved when config is None.

- **`liver1/main.py`** — extracted logic into `detect_boundary(img, config)` function. Argparse moved inside `__main__` guard. Added early return with warning when no green contours found.

- **`cell/main.py`** — extracted into `load_models(config)` (one-time model loading) and `analyze_cells(img, models, config)`. Models load once at startup, not per request. Argparse moved inside `__main__` guard. Added warnings for "no circles detected" and "no cells passed confidence threshold".

- **`cell/utils.py`** — `mix_circle()` now accepts a BGR numpy array instead of a file path, with all HoughCircles parameters configurable via config dict. `cut()` accepts a pre-padded image array instead of re-reading from disk per circle, and computes boundary limits dynamically from image shape instead of hardcoded 1224.

- **`cell/model.py`**
  - Removed bare `net = Net()` on line 21 that ran at import time (unnecessary model instantiation)
  - Updated `models.resnet18(pretrained=True)` to `models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)` (deprecated parameter fix)
  - Fixed `from resnet import resnet50` to `from cell.resnet import resnet50` (proper package import)

### Not changed

- All analysis algorithms remain identical to the original — same HSV ranges, same contour detection logic, same HoughCircles parameters, same ResNet18 classifier + U-Net segmenter pipeline. No model retraining or algorithmic modifications.
- `cell/resnet.py` — untouched (custom ResNet50 backbone)
- Original CLI usage still works via `if __name__ == '__main__'` blocks
- Model weight files (`save1.pt`, `save_mask.pt`) — unchanged, not included in repo due to GitHub size limits. Place them in `cell/` before running. See README for download link.
- Sample/test images and results — unchanged
