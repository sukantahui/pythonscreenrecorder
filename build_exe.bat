@echo off
setlocal enabledelayedexpansion
title CNAT Screen Recorder - Single-File EXE Builder
color 0B

echo =====================================================================
echo       CNAT Screen Recorder - Single-File EXE Packaging
echo       Developed by Coder ^& AccoTax (Sukanta Hui)
echo =====================================================================
echo.

REM 1. Detect Python Interpreter (.venv preferred, fallback to system)
set "PYTHON_EXE="
set "PIP_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    set "PIP_EXE=.venv\Scripts\pip.exe"
    echo [INFO] Using Virtual Environment: .venv
    goto :check_dependencies
)

REM Check if system python has PyQt6 installed
python -c "import PyQt6" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    set "PIP_EXE=pip"
    echo [INFO] Using System Python installation
    goto :check_dependencies
)

echo [INFO] Virtual environment not found and PyQt6 not in system Python.
echo [INFO] Running setup.bat to configure environment and dependencies...
call setup.bat

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    set "PIP_EXE=.venv\Scripts\pip.exe"
    goto :check_dependencies
)

echo [ERROR] Setup could not be completed.
pause
exit /b 1

:check_dependencies
echo.
echo [1/4] Checking dependencies and packaging tools...
"%PYTHON_EXE%" -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Dependencies not detected in environment.
    echo [INFO] Installing required packages from requirements.txt...
    "%PIP_EXE%" install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies from requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo [OK] Core dependencies verified.
)

"%PYTHON_EXE%" -m PyInstaller --version >nul 2>&1
if not errorlevel 1 goto :pyinstaller_ready

echo [INFO] PyInstaller not detected. Installing PyInstaller...
"%PIP_EXE%" install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller. Please check your internet connection.
    pause
    exit /b 1
)

:pyinstaller_ready
echo [OK] PyInstaller is ready.

echo.
echo [2/4] Verifying application icons and assets...
if exist "assets\app_icon.ico" goto :icon_ready

echo [INFO] Generating high-resolution application icons...
"%PYTHON_EXE%" "scripts\generate_icon.py"

:icon_ready
echo [OK] Application icon verified: assets\app_icon.ico

echo.
echo [3/4] Cleaning previous build artifacts...
taskkill /F /IM "CNAT_Screen_Recorder.exe" >nul 2>&1
timeout /t 1 /nobreak >nul 2>&1
if exist "build" rmdir /s /q "build"
if exist "dist\CNAT_Screen_Recorder.exe" del /f /q "dist\CNAT_Screen_Recorder.exe"
echo [OK] Cleaned build directory.

echo.
echo [4/4] Bundling single-file executable with PyInstaller...
echo [INFO] Packing all code, Qt styles, QtAwesome fonts, and FFmpeg engine...
echo [INFO] This typically takes 1 to 2 minutes. Please wait...
echo.

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean CNAT_Screen_Recorder.spec
if errorlevel 1 (
    echo.
    echo =====================================================================
    echo [ERROR] PyInstaller encountered an error during the build process!
    echo Please review the logs above for missing packages or compiler errors.
    echo =====================================================================
    pause
    exit /b 1
)

if not exist "dist\CNAT_Screen_Recorder.exe" (
    echo.
    echo [ERROR] Build finished, but dist\CNAT_Screen_Recorder.exe was not found.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo  BUILD SUCCEEDED!
echo  Single-file executable created at:
echo  --^> dist\CNAT_Screen_Recorder.exe
echo =====================================================================
for %%F in ("dist\CNAT_Screen_Recorder.exe") do (
    set /a size_mb=%%~zF / 1048576
    echo  File Size: ~!size_mb! MB - %%~zF bytes
)
echo =====================================================================
echo.

if "%1"=="--no-interaction" exit /b 0
if "%1"=="-y" exit /b 0

echo What would you like to do next?
echo  [1] Open 'dist' folder in Windows Explorer
echo  [2] Run CNAT Screen Recorder now
echo  [3] Exit
echo.
choice /c 123 /t 30 /d 1 /m "Enter choice [1-3] (Default is 1 in 30s): "

if errorlevel 3 exit /b 0
if errorlevel 2 (
    echo Launching CNAT Screen Recorder...
    start "" "dist\CNAT_Screen_Recorder.exe"
    exit /b 0
)
if errorlevel 1 (
    explorer.exe /select,"dist\CNAT_Screen_Recorder.exe"
    exit /b 0
)
