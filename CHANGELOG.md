# Changelog

All changes relative to the [original repository](https://github.com/dhcl8881/nhri) by dhcl8881.

## [Unreleased] - 2026-04-14

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
