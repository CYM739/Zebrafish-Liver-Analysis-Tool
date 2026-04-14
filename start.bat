@echo off
title Zebrafish Liver Analysis Tool
cd /d "%~dp0"
echo Starting Zebrafish Liver Analysis Tool...
echo.
uv run python app.py
pause
