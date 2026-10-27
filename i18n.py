"""User-facing text for the web UI in every supported language."""

LANGUAGES = [("中文", "zh"), ("English", "en")]

STRINGS = {
    # Page and tabs
    "title": {"en": "# Zebrafish Liver Analysis Tool", "zh": "# 斑馬魚肝臟分析工具"},
    "tab_count": {"en": "Neutrophil / Macrophage Count", "zh": "嗜中性球 / 巨噬細胞計數"},
    "tab_boundary": {"en": "Liver Boundary Detection", "zh": "肝臟範圍偵測"},
    "tab_cell": {"en": "Cell N/C Ratio", "zh": "肝細胞核質比"},
    "tab_combined": {"en": "Combined (Boundary + Counting)", "zh": "綜合分析（範圍 + 計數）"},
    "btn_count": {"en": "Run Counting", "zh": "開始計數"},
    "btn_boundary": {"en": "Detect Boundary", "zh": "偵測範圍"},
    "btn_cell": {"en": "Analyze Cells", "zh": "分析細胞"},
    "btn_combined": {"en": "Run Combined Analysis", "zh": "執行綜合分析"},

    # Analysis profiles
    "profile": {"en": "Analysis method", "zh": "分析方法"},
    "profile_dhcl8881": {"en": "Original (dhcl8881)", "zh": "原作者版本（dhcl8881）"},
    "profile_cpsam-v1": {"en": "Improved v1 (Cellpose-SAM)", "zh": "改良版 v1（Cellpose-SAM）"},
    "profile_desc_dhcl8881": {
        "en": "The original author's methods and models, unchanged. Results match earlier versions of this tool.",
        "zh": "原作者的分析方法與模型，未做任何修改，結果與本工具先前版本相同。"},
    "profile_desc_cpsam-v1": {
        "en": "Outlines each cell and its nucleus with Cellpose-SAM and skips cells that cannot be measured reliably "
              "(cut off by the image edge, out of focus, or without exactly one nucleus). "
              "The first analysis downloads a 1.2 GB model; without a GPU each image takes 1–2 minutes.",
        "zh": "以 Cellpose-SAM 描出每個細胞與細胞核的輪廓，並略過無法可靠測量的細胞（被影像邊緣切到、失焦、或不是剛好一個細胞核）。"
              "第一次分析需下載約 1.2 GB 模型；沒有 GPU 時每張影像約需 1–2 分鐘。"},

    # Shared components
    "upload": {"en": "Upload Images", "zh": "上傳影像"},
    "preview": {"en": "Image Preview", "zh": "影像預覽"},
    "advanced": {"en": "Advanced Settings", "zh": "進階設定"},
    "results": {"en": "Results", "zh": "分析結果"},
    "crops": {"en": "Individual Cells", "zh": "單一細胞"},
    "summary_table": {"en": "Summary per Image", "zh": "每張影像摘要"},
    "details_table": {"en": "Per-Cell Details (IDs match the numbers on the result images)",
                      "zh": "每個細胞明細（編號對應結果圖上標示的數字）"},
    "csv": {"en": "Download CSV", "zh": "下載 CSV"},
    "zip": {"en": "Download All Results (.zip)", "zh": "下載全部結果 (.zip)"},
    "progress": {"en": "Analyzing images", "zh": "影像分析中"},

    # Settings
    "section_boundary": {"en": "### Boundary Detection", "zh": "### 範圍偵測"},
    "section_count": {"en": "### Cell Counting", "zh": "### 細胞計數"},
    "hsv_neutrophil": {"en": "**Green (neutrophil) color range (HSV)**", "zh": "**綠色（嗜中性球）顏色範圍 (HSV)**"},
    "hsv_macrophage": {"en": "**Red (macrophage) color range (HSV)**", "zh": "**紅色（巨噬細胞）顏色範圍 (HSV)**"},
    "hsv_macrophage_2": {"en": "**Red (macrophage) color range 2 (HSV, hues near 179)**",
                         "zh": "**紅色（巨噬細胞）顏色範圍 2（HSV，色相接近 179 的紅色）**"},
    "hsv_liver": {"en": "**Green (liver) color range (HSV)**", "zh": "**綠色（肝臟）顏色範圍 (HSV)**"},
    "hsv_lower": {"en": "{ch} lower", "zh": "{ch} 下限"},
    "hsv_upper": {"en": "{ch} upper", "zh": "{ch} 上限"},
    "contour_area_min": {"en": "Minimum area (px)", "zh": "最小面積（像素）"},
    "blur_kernel": {"en": "Smoothing size", "zh": "平滑程度"},
    "mask_threshold": {"en": "Liver outline brightness", "zh": "肝臟外框亮度門檻"},
    "confidence_threshold": {"en": "Cell detection threshold", "zh": "細胞判定門檻"},
    "segmentation_threshold": {"en": "Cytoplasm segmentation threshold", "zh": "細胞質分割門檻"},
    "um_conversion": {"en": "Microns per pixel (µm/px)", "zh": "每像素微米數 (µm/px)"},
    "hough_param1": {"en": "Nucleus edge sensitivity", "zh": "細胞核邊緣門檻"},
    "hough_param2": {"en": "Nucleus roundness", "zh": "細胞核圓度要求"},
    "hough_min_radius": {"en": "Minimum nucleus radius (px)", "zh": "最小細胞核半徑（像素）"},
    "hough_max_radius": {"en": "Maximum nucleus radius (px)", "zh": "最大細胞核半徑（像素）"},
    "merged_area_factor": {"en": "Flag as possibly merged at (× median area)", "zh": "面積達中位數幾倍時標示為可能黏連"},
    "cp_diameter": {"en": "Typical cell diameter (px, 0 = automatic)", "zh": "細胞直徑（像素，0 = 自動）"},
    "cp_cellprob_threshold": {"en": "Cell detection threshold (lower finds more cells)", "zh": "細胞判定門檻（越低找到越多細胞）"},
    "cp_flow_threshold": {"en": "Cell shape tolerance (higher accepts more shapes)", "zh": "細胞形狀容許度（越高接受越多形狀）"},
    "cp_exclude_border": {"en": "Exclude cells cut off by the image edge", "zh": "排除被影像邊緣切到的細胞"},
    "cp_min_relative_brightness": {"en": "Exclude cells dimmer than (fraction of the median cell)",
                                   "zh": "亮度低於中位數細胞此比例時排除（失焦）"},
    "cp_max_nucleus_fraction": {"en": "Exclude cells whose nucleus fills more than (fraction of cell)",
                                "zh": "細胞核佔細胞面積超過此比例時排除"},

    # Result captions
    "cap_macrophages": {"en": "Macrophages ({n}) · {name}", "zh": "巨噬細胞（{n}）· {name}"},
    "cap_neutrophils": {"en": "Neutrophils ({n}) · {name}", "zh": "嗜中性球（{n}）· {name}"},
    "cap_macrophages_flagged": {"en": "Macrophages ({n}, {flagged} flagged) · {name}", "zh": "巨噬細胞（{n}，{flagged} 個待檢查）· {name}"},
    "cap_neutrophils_flagged": {"en": "Neutrophils ({n}, {flagged} flagged) · {name}", "zh": "嗜中性球（{n}，{flagged} 個待檢查）· {name}"},
    "cap_boundary": {"en": "Liver boundary · {name}", "zh": "肝臟範圍 · {name}"},
    "cap_segmentation": {"en": "Cytoplasm segmentation ({n} cells) · {name}", "zh": "細胞質分割（{n} 個細胞）· {name}"},
    "cap_cells_nuclei": {"en": "Cells and nuclei ({n} cells) · {name}", "zh": "細胞與細胞核分割（{n} 個細胞）· {name}"},
    "cap_all_nuclei": {"en": "All detected nuclei ({n}) · {name}", "zh": "所有偵測到的細胞核（{n}）· {name}"},
    "cap_cell": {"en": "#{id} · {name}", "zh": "#{id} · {name}"},

    # Warnings
    "warnings": {"en": "### ⚠ Warnings", "zh": "### ⚠ 注意"},
    "warn_read_failed": {"en": "This file could not be opened as an image.", "zh": "無法開啟此影像檔。"},
    "warn_no_liver_outline": {
        "en": "No liver outline found. Make sure the white dashed liver outline is drawn on the image.",
        "zh": "找不到肝臟外框。請確認影像上已畫上白色虛線的肝臟範圍。"},
    "warn_no_green_region": {
        "en": "No green fluorescence found. Check the image, or adjust the green color range in Advanced Settings.",
        "zh": "找不到綠色螢光區域。請確認影像，或在進階設定中調整綠色顏色範圍。"},
    "warn_no_circles": {
        "en": "No nuclei found. Check the image, or adjust the nucleus settings in Advanced Settings.",
        "zh": "找不到細胞核。請確認影像，或在進階設定中調整細胞核相關設定。"},
    "warn_no_cells_passed": {
        "en": "{n} nuclei were found, but none passed the cell detection threshold ({threshold}).",
        "zh": "找到 {n} 個細胞核，但沒有任何一個達到細胞判定門檻（{threshold}）。"},
    "warn_no_cells_found": {
        "en": "No cells found. Check the image, or lower the cell detection threshold in Advanced Settings.",
        "zh": "找不到細胞。請確認影像，或在進階設定中調低細胞判定門檻。"},
    "warn_no_cells_passed_qc": {
        "en": "{n} cells were found, but none passed the quality filters (fully inside the image, in focus, exactly one nucleus, visible cytoplasm).",
        "zh": "找到 {n} 個細胞，但沒有任何一個通過品質篩選（完整位於影像內、未失焦、恰好一個細胞核、可見細胞質）。"},
    "warn_model_missing": {
        "en": "The analysis model files are not installed. Please ask the administrator to install them (see the README).",
        "zh": "尚未安裝分析模型檔。請聯絡管理員依說明文件安裝。"},
    "warn_model_download_failed": {
        "en": "The Cellpose-SAM model could not be downloaded. Check the internet connection, or ask the administrator to install it.",
        "zh": "無法下載 Cellpose-SAM 模型。請確認網路連線，或聯絡管理員安裝。"},
    "warn_unexpected_error": {
        "en": "This image could not be analyzed because of an unexpected error.",
        "zh": "分析此影像時發生未預期的錯誤。"},

    # Table columns (CSV files keep the English column keys)
    "col_profile": {"en": "Method", "zh": "分析方法"},
    "col_filename": {"en": "File", "zh": "檔名"},
    "col_result_image": {"en": "Result image", "zh": "結果圖"},
    "col_cell_type": {"en": "Cell type", "zh": "細胞類型"},
    "col_cell_id": {"en": "ID", "zh": "編號"},
    "col_x": {"en": "X (px)", "zh": "X（像素）"},
    "col_y": {"en": "Y (px)", "zh": "Y（像素）"},
    "col_area_px": {"en": "Area (px)", "zh": "面積（像素）"},
    "col_radius_px": {"en": "Nucleus radius (px)", "zh": "細胞核半徑（像素）"},
    "col_nuclear_area_um2": {"en": "Nuclear area (µm²)", "zh": "細胞核面積 (µm²)"},
    "col_cytoplasmic_area_um2": {"en": "Cytoplasmic area (µm²)", "zh": "細胞質面積 (µm²)"},
    "col_nc_ratio": {"en": "N/C ratio", "zh": "核質比"},
    "col_cell_area_um2": {"en": "Cell area (µm²)", "zh": "細胞面積 (µm²)"},
    "col_possibly_merged": {"en": "Possibly merged", "zh": "可能黏連"},
    "col_classifier_score": {"en": "Detection score", "zh": "判定分數"},
    "col_crop_image": {"en": "Cell image", "zh": "單一細胞圖"},
    "col_macrophage_count": {"en": "Macrophages", "zh": "巨噬細胞數"},
    "col_neutrophil_count": {"en": "Neutrophils", "zh": "嗜中性球數"},
    "col_macrophage_possibly_merged": {"en": "Macrophages flagged", "zh": "待檢查巨噬細胞數"},
    "col_neutrophil_possibly_merged": {"en": "Neutrophils flagged", "zh": "待檢查嗜中性球數"},
    "col_n_segmented": {"en": "Cells found", "zh": "分割出的細胞數"},
    "col_n_excluded_edge": {"en": "Excluded: at image edge", "zh": "排除：位於影像邊緣"},
    "col_n_excluded_dim": {"en": "Excluded: out of focus", "zh": "排除：失焦過暗"},
    "col_n_excluded_nucleus": {"en": "Excluded: not exactly one nucleus", "zh": "排除：細胞核數不為 1"},
    "col_n_excluded_nucleus_only": {"en": "Excluded: outline around nucleus only", "zh": "排除：外框只圈到細胞核"},
    "col_median_nc_ratio": {"en": "Median N/C ratio", "zh": "核質比中位數"},
    "col_n_candidates": {"en": "Nuclei found", "zh": "偵測到的細胞核數"},
    "col_n_cells": {"en": "Cells analyzed", "zh": "有效細胞數"},
    "col_mean_radius_px": {"en": "Mean nucleus radius (px)", "zh": "平均細胞核半徑（像素）"},
    "col_mean_nuclear_area_um2": {"en": "Mean nuclear area (µm²)", "zh": "平均細胞核面積 (µm²)"},
    "col_mean_cytoplasmic_area_um2": {"en": "Mean cytoplasmic area (µm²)", "zh": "平均細胞質面積 (µm²)"},
    "col_mean_cell_area_um2": {"en": "Mean cell area (µm²)", "zh": "平均細胞面積 (µm²)"},
    "col_mean_nc_ratio": {"en": "Mean N/C ratio", "zh": "平均核質比"},
}


def t(key, lang, **kwargs):
    return STRINGS[key][lang].format(**kwargs)


def localize_columns(df, lang):
    """Rename a results table's columns for display."""
    return df.rename(columns=lambda c: t(f"col_{c}", lang))
