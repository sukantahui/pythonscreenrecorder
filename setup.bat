@echo off
title CNAT Screen Recorder - Setup
echo ===================================================
echo     CNAT Screen Recorder - Automatic Setup
echo     Developed by Coder ^& AccoTax (Sukanta Hui)
echo ===================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment (.venv)...
if not exist ".venv" (
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

echo.
echo [2/3] Activating virtual environment and upgrading pip...
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo.
echo [3/3] Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ===================================================
echo  Setup Completed Successfully!
echo  You can now run the app using: run.bat or python main.py
echo ===================================================
pause
