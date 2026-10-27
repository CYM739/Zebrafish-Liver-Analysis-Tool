# Zebrafish Liver Analysis Tool

Gradio web UI for zebrafish liver microscopy image analysis. Forked from [dhcl8881/nhri](https://github.com/dhcl8881/nhri).

## Setup

```bash
uv sync
```

### Model Weights

Download and place in `cell/`:
- `save1.pt` (ResNet18 classifier, ~47MB)
- `save_mask.pt` (U-Net segmenter, ~168MB)

These are available from the [original author's Google Drive](https://github.com/dhcl8881/nhri) (see original repo for link).

### Run

```bash
uv run python app.py
```
Or double-click `start.bat` on Windows.

Opens at http://localhost:7860. Server address, port, default UI language (中文 / English) and how long results are kept are set in the `app` section of `config.yaml`.

## Tabs

1. **Neutrophil / Macrophage Count** — counts green (neutrophil) and red (macrophage) cells in liver region
2. **Liver Boundary Detection** — detects liver outline from green fluorescence
3. **Cell N/C Ratio** — nuclear-to-cytoplasmic area ratio using ResNet18 + U-Net
4. **Combined** — boundary detection + cell counting in one pass

## Output files

Every detected cell is numbered on the result image, and the same number appears in the CSV:

| Tab | `*_summary.csv` (one row per image) | `*_cells.csv` (one row per cell) |
|---|---|---|
| Count / Combined | `macrophage_count`, `neutrophil_count` | `result_image`, `cell_type`, `cell_id` (`M1`… / `N1`…), `x`, `y`, `area_px` |
| Cell N/C Ratio | `n_candidates`, `n_cells`, mean of each measurement | `result_image`, `cell_id`, `x`, `y`, `radius_px`, `nuclear_area_um2`, `cytoplasmic_area_um2`, `nc_ratio`, `classifier_score`, `crop_image` |

`x`, `y` are pixel coordinates in the original image. `result_image` / `crop_image` are file names inside the downloaded `.zip`.

## Command line

Run from the repository root, e.g. `uv run python -m liver.main --mix_dir liver/1/1_channel_mix.tif` (also `liver1.main`, `cell.main`).

---

# 斑馬魚肝臟細胞程式 (Original)
1. cell資料夾內為肝臟細胞核值比計算
1. liver資料夾內為neutrophils和macrophage數量計算
1. liver1資料夾內為肝臟細胞範圍偵測

