# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for CNAT Screen Recorder.
Builds a standalone, single-file executable with all dark glassmorphic QSS styles,
icons, QtAwesome fonts, and bundled FFmpeg engine included.
"""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJECT_ROOT = Path.cwd()

# Core data files to embed
datas = [
    (str(PROJECT_ROOT / "src" / "ui" / "styles.qss"), "src/ui"),
]

# Assets directory (icons, branding)
assets_dir = PROJECT_ROOT / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "assets"))

binaries = []
hiddenimports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "sounddevice",
    "dxcam",
    "mss",
    "pynput",
    "pynput.keyboard",
    "pynput.mouse",
    "keyboard",
    "av",
    "cv2",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "psutil",
    "pygetwindow",
    "win32gui",
    "win32con",
    "win32process",
    "pywintypes",
]

# Collect specialized package assets (QtAwesome webfonts, imageio bundled FFmpeg binaries)
for pkg in ("qtawesome", "imageio_ffmpeg"):
    try:
        p_datas, p_binaries, p_hidden = collect_all(pkg)
        datas.extend(p_datas)
        binaries.extend(p_binaries)
        hiddenimports.extend(p_hidden)
    except Exception:
        pass

# Deduplicate hidden imports
hiddenimports = sorted(list(set(hiddenimports)))

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = str(PROJECT_ROOT / "assets" / "app_icon.ico")
if not os.path.exists(icon_path):
    icon_path = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CNAT_Screen_Recorder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
