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

Opens at http://localhost:7860

## Tabs

1. **Neutrophil / Macrophage Count** — counts green (neutrophil) and red (macrophage) cells in liver region
2. **Liver Boundary Detection** — detects liver outline from green fluorescence
3. **Cell N/C Ratio** — nuclear-to-cytoplasmic area ratio using ResNet18 + U-Net
4. **Combined** — boundary detection + cell counting in one pass

---

# 斑馬魚肝臟細胞程式 (Original)
1. cell資料夾內為肝臟細胞核值比計算
1. liver資料夾內為neutrophils和macrophage數量計算
1. liver1資料夾內為肝臟細胞範圍偵測

