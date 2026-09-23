@echo off
title CNAT Screen Recorder
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Running setup first...
    call setup.bat
)

echo Starting CNAT Screen Recorder...
start "" ".\.venv\Scripts\pythonw.exe" "main.py"
