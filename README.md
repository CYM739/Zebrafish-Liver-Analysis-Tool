# Zebrafish Liver Analysis Tool

Gradio web UI for zebrafish liver microscopy image analysis. Forked from [dhcl8881/nhri](https://github.com/dhcl8881/nhri).

## Setup

```bash
uv sync
```

### Model Weights

**dhcl8881 profile** — download and place in `cell/`:
- `save1.pt` (ResNet18 classifier, ~47MB)
- `save_mask.pt` (U-Net segmenter, ~168MB)

These are available from the [original author's Google Drive](https://github.com/dhcl8881/nhri) (see original repo for link).

**cpsam-v1 profile** — the Cellpose-SAM model (`cpsam_v2`, ~1.15GB) is downloaded to `~/.cellpose/models` on first use. To install it in advance (e.g. for an offline machine):

```bash
uv run python -c "from cellpose import models; models.CellposeModel(pretrained_model='cpsam_v2')"
```

The Cellpose code is BSD-licensed, but its pretrained models are trained on CC-BY-NC data: fine for academic research, not for commercial use.

### Run

```bash
uv run python app.py
```
Or double-click `start.bat` on Windows.

Opens at http://localhost:7860. Server address, port, default UI language (中文 / English) and how long results are kept are set in the `app` section of `config.yaml`.

## Analysis profiles

A profile is a complete set of algorithms and models. Tabs where more than one profile is offered show a method selector; each result CSV records the profile in its `profile` column, and the `.zip` includes `*_settings.json` with every setting used.

| Profile | What it is |
|---|---|
| `dhcl8881` (default) | The original author's algorithms and models, unchanged (`liver/`, `liver1/`, `cell/`). Reproduces earlier results exactly. |
| `cpsam-v1` | Offered in the app for the N/C ratio only (`offered_in_app`): Cellpose-SAM cell + nucleus segmentation with quality filters. Its N/C values have not yet been validated against manual annotation. Its count and boundary fixes (`profiles/cpsam_v1/`: corrected scale-bar exclusion, both red hue ranges, boundary regions outlined separately, possibly merged cells flagged in orange) stay dev-only until validated. |

Profile settings live under `profiles:` in `config.yaml`; the default profile is `default_profile` and must offer every analysis. `offered_in_app` limits a profile to the listed analyses in the app.

N/C ratio definition (`cpsam-v1`, `cell.nc_denominator`, not shown in the app): `cell` (default) = nucleus ÷ whole cell, `cytoplasm` = nucleus ÷ (cell − nucleus). Both are used in the literature; `cell` counts cytoplasm lying above or below the nucleus. The value used is recorded in `*_settings.json`. To add a profile, add a module under `profiles/` that defines `NAME` and `ANALYSES` (see `profiles/base.py`), register it in `profiles/__init__.py`, and add its section to `config.yaml` and its labels to `i18n.py`.

## Tabs

1. **Neutrophil / Macrophage Count** — counts green (neutrophil) and red (macrophage) cells in liver region
2. **Liver Boundary Detection** — detects liver outline from green fluorescence
3. **Cell N/C Ratio** — nuclear-to-cytoplasmic area ratio (`dhcl8881`: ResNet18 + U-Net; `cpsam-v1`: Cellpose-SAM)
4. **Combined** — boundary detection + cell counting in one pass

## Output files

Every detected cell is numbered on the result image, and the same number appears in the CSV. All rows start with `profile`, `filename`.

| Tab | Profile | `*_summary.csv` (one row per image) | `*_cells.csv` (one row per cell) |
|---|---|---|---|
| Count / Combined | `dhcl8881` | `macrophage_count`, `neutrophil_count` | `result_image`, `cell_type`, `cell_id` (`M1`… / `N1`…), `x`, `y`, `area_px` |
| Cell N/C Ratio | `dhcl8881` | `n_candidates`, `n_cells`, mean of each measurement | `result_image`, `cell_id`, `x`, `y`, `radius_px`, `nuclear_area_um2` (Hough circle πr²), `cell_area_um2`*, `nc_ratio` (nucleus ÷ whole cell), `classifier_score`, `crop_image` |
| Cell N/C Ratio | `cpsam-v1` | `n_segmented`, `n_cells`, `n_excluded_*` per quality filter, means, `median_nc_ratio` | `result_image`, `cell_id`, `x`, `y`, `cell_area_um2`, `nuclear_area_um2`, `cytoplasmic_area_um2` (cell − nucleus), `nc_ratio` (per `nc_denominator`), `crop_image` |

\* The whole U-Net mask, nucleus included. Earlier versions named this column `cytoplasmic_area_um2`; the values are unchanged.

`x`, `y` are pixel coordinates in the original image. `result_image` / `crop_image` are file names inside the downloaded `.zip`.

## Command line

The original (`dhcl8881`) scripts run from the repository root, e.g. `uv run python -m liver.main --mix_dir liver/1/1_channel_mix.tif` (also `liver1.main`, `cell.main`).

---

# 斑馬魚肝臟細胞程式 (Original)
1. cell資料夾內為肝臟細胞核值比計算
1. liver資料夾內為neutrophils和macrophage數量計算
1. liver1資料夾內為肝臟細胞範圍偵測

