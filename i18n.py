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
    "section_liver1": {"en": "### Boundary Detection", "zh": "### 範圍偵測"},
    "section_liver": {"en": "### Cell Counting", "zh": "### 細胞計數"},
    "hsv_neutrophil": {"en": "**Green (neutrophil) color range (HSV)**", "zh": "**綠色（嗜中性球）顏色範圍 (HSV)**"},
    "hsv_macrophage": {"en": "**Red (macrophage) color range (HSV)**", "zh": "**紅色（巨噬細胞）顏色範圍 (HSV)**"},
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

    # Result captions
    "cap_macrophages": {"en": "Macrophages ({n}) · {name}", "zh": "巨噬細胞（{n}）· {name}"},
    "cap_neutrophils": {"en": "Neutrophils ({n}) · {name}", "zh": "嗜中性球（{n}）· {name}"},
    "cap_boundary": {"en": "Liver boundary · {name}", "zh": "肝臟範圍 · {name}"},
    "cap_segmentation": {"en": "Cytoplasm segmentation ({n} cells) · {name}", "zh": "細胞質分割（{n} 個細胞）· {name}"},
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

    # Table columns (CSV files keep the English column keys)
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
    "col_classifier_score": {"en": "Detection score", "zh": "判定分數"},
    "col_crop_image": {"en": "Cell image", "zh": "單一細胞圖"},
    "col_macrophage_count": {"en": "Macrophages", "zh": "巨噬細胞數"},
    "col_neutrophil_count": {"en": "Neutrophils", "zh": "嗜中性球數"},
    "col_n_candidates": {"en": "Nuclei found", "zh": "偵測到的細胞核數"},
    "col_n_cells": {"en": "Cells analyzed", "zh": "有效細胞數"},
    "col_mean_radius_px": {"en": "Mean nucleus radius (px)", "zh": "平均細胞核半徑（像素）"},
    "col_mean_nuclear_area_um2": {"en": "Mean nuclear area (µm²)", "zh": "平均細胞核面積 (µm²)"},
    "col_mean_cytoplasmic_area_um2": {"en": "Mean cytoplasmic area (µm²)", "zh": "平均細胞質面積 (µm²)"},
    "col_mean_nc_ratio": {"en": "Mean N/C ratio", "zh": "平均核質比"},
}


def t(key, lang, **kwargs):
    return STRINGS[key][lang].format(**kwargs)


def localize_columns(df, lang):
    """Rename a results table's columns for display."""
    return df.rename(columns=lambda c: t(f"col_{c}", lang))
