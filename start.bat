@echo off
title Zebrafish Liver Analysis Tool
cd /d "%~dp0"

rem Keep everything the app downloads inside this folder (not on C:).
rem Same drive as .venv, so uv can hardlink instead of copy (no warning).
set "UV_CACHE_DIR=%~dp0.uv-cache"
set "UV_PYTHON_INSTALL_DIR=%~dp0.python"
set "UV_PYTHON_PREFERENCE=only-managed"
set "CELLPOSE_LOCAL_MODELS_PATH=%~dp0models"
set "HF_HOME=%~dp0.hf"

echo Starting Zebrafish Liver Analysis Tool...
echo.
uv run python app.py
pause
