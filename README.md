# CNAT Screen Recorder

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/GUI-PyQt6-green?logo=qt&logoColor=white" alt="PyQt6">
  <img src="https://img.shields.io/badge/Resolution-4K%20UHD%20(3840x2160)-orange" alt="4K UHD">
  <img src="https://img.shields.io/badge/Framerate-60%2F120%20FPS-red" alt="Framerate">
  <img src="https://img.shields.io/badge/Audio-WASAPI%20Loopback%20%2B%20Mic-purple" alt="Audio">
  <img src="https://img.shields.io/badge/Hardware%20Accel-NVENC%20%7C%20QSV%20%7C%20AMF-yellow" alt="Hardware Accel">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white" alt="Platform Windows">
  <img src="https://img.shields.io/badge/Developer-Sukanta%20Hui%20(CNAT)-blueviolet" alt="Developer Sukanta Hui">
</p>

---

## 📌 Overview

**CNAT Screen Recorder** is a professional-grade, high-performance desktop screen recording, live annotation, and streaming capture suite developed by **Coder & AccoTax (CNAT)**. Built with **Python 3.10+** and **PyQt6**, it delivers fluid **4K Ultra HD @ 60/120 FPS** screen recording with ultra-low CPU/GPU overhead, real-time webcam picture-in-picture (PiP) overlays, dual-channel audio mixing (system loopback + microphone), and global hotkeys.

---

## 📖 Official User Manual & Operating Guide

Comprehensive, publication-quality documentation is available for all users:

- 📘 **[Official Markdown User Manual (docs/USER_MANUAL.md)](docs/USER_MANUAL.md)**: Full operating guide with 4K recording profiles, audio configuration, studio PiP shapes, and hotkey cheat sheet.
- 🌐 **[Styled Standalone HTML User Manual (docs/USER_MANUAL.html)](docs/USER_MANUAL.html)**: Interactive, responsive guide with dark mode styling and direct **"Print to PDF"** support (`Ctrl + P`).
- 📄 **[Quick User Guide (USER_GUIDE.md)](USER_GUIDE.md)**: Repository quick reference.

*(💡 You can also access, read, and export the manual directly inside the application by clicking the **📖 Manual** button in the top header or **📖 User Manual** in the footer!)*

---

## ✨ Key Features

- 🎥 **4K Ultra HD & 60/120 FPS Recording**: Capture at 3840×2160, 2560×1440, or 1080p with ultra-fast multithreaded H.264 / HEVC encoding and zero frame-drop.
- 📱 **Seamless Iriun & Phone Webcam Integration**: Automatically discovers wireless/USB smartphone cameras (e.g., [Iriun Webcam](https://iriun.com/)), capture cards, and USB webcams.
- 🪟 **Interactive Resizable PiP Overlay**:
  - Drag corners or edges to resize dynamically (100px – 600px).
  - Mouse scroll wheel scaling.
  - Switch shapes on the fly: **Circle**, **Rounded Rectangle**, or **Square**.
  - Horizontal flip (mirror view) and right-click settings menu.
- 🎙️ **Dual-Channel Audio Mixing**: Record crystal-clear system audio (WASAPI loopback) + microphone commentary simultaneously with live audio level meters and mute controls.
- ✏️ **Live Annotation Canvas**: Draw with pens, neon highlighters, arrows, numbered step badges, rectangles, and text directly over your screen while recording.
- ⚡ **Hardware Acceleration Auto-Detection**: Auto-detects NVIDIA NVENC (`h264_nvenc`), Intel QuickSync (`h264_qsv`), AMD AMF (`h264_amf`), or falls back to optimized multithreaded `libx264`.
- ⌨️ **System-Wide Global Hotkeys**: Start, pause, stop, annotate, and toggle webcam with customizable hotkeys even when the application is minimized.
- 🎨 **Modern Glassmorphic Dark UI**: Custom-styled dark theme tailored for creators, developers, and educators.

---

## 🚀 Quick Start & Installation Guide

Follow these simple steps to clone, set up, and run **CNAT Screen Recorder** on your machine.

### 1. Prerequisites

Ensure you have the following installed on your machine:
- **Operating System**: Windows 10 / Windows 11 (64-bit recommended)
- **Python**: [Python 3.10 or higher](https://www.python.org/downloads/) *(⚠️ Check **"Add python.exe to PATH"** during installation)*
- **Git**: [Git for Windows](https://git-scm.com/downloads)

---

### 2. Clone the Repository

Open your terminal (PowerShell, Command Prompt, or Windows Terminal) and run:

```bash
git clone https://github.com/sukantahui/pythonscreenrecorder.git
cd pythonscreenrecorder
```

---

### 3. Create & Activate a Virtual Environment

It is recommended to use a Python virtual environment to manage dependencies cleanly.

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

> **Note for PowerShell Users:** If you see an execution policy error like `cannot be loaded because running scripts is disabled on this system`, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\activate
> ```

#### On Windows (Command Prompt `cmd`):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 4. Install Dependencies

Upgrade `pip` and install all required packages listed in `requirements.txt`:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. Launch the Application

Run the application with:

```bash
python main.py
```

The **CNAT Screen Recorder** control dashboard will appear immediately!

---

## 📱 Using Iriun Webcam (Turn Your Phone into a 4K Webcam)

You can use your Android phone or iPhone as a high-definition 4K webcam wirelessly via WiFi or via USB cable:

1. **Download the Mobile App**: Install **Iriun Webcam** from Google Play Store or Apple App Store on your smartphone.
2. **Download the PC Driver**: Install the free Iriun Webcam Windows driver from [https://iriun.com/](https://iriun.com/).
3. **Connect**: Open the Iriun app on your phone and ensure your PC and phone are on the same WiFi network (or connected via USB debugging).
4. **Launch Screen Recorder**: In **CNAT Screen Recorder**, click the **Camera** dropdown — `Iriun Webcam` will appear automatically.
5. Click **Preview** or toggle **Webcam PiP (F7)** to activate your webcam overlay on screen!

---

## ⌨️ Global Keyboard Shortcuts

Control your recording from anywhere on your PC without switching windows:

| Action | Default Hotkey | Description |
| :--- | :---: | :--- |
| **Start / Stop Recording** | <kbd>F9</kbd> | Toggle recording on/off |
| **Pause / Resume** | <kbd>F10</kbd> | Temporarily pause or resume active recording |
| **Live Annotation Canvas** | <kbd>F8</kbd> | Toggle transparent drawing overlay |
| **Webcam PiP Overlay** | <kbd>F7</kbd> | Show/hide floating webcam window |
| **Mute / Unmute Mic** | <kbd>F6</kbd> | Instant microphone audio mute toggle |
| **Quick Screenshot** | <kbd>F11</kbd> | Capture screenshot of current screen/region |
| **Clear / Cancel** | <kbd>Esc</kbd> | Clear active drawing strokes or dismiss overlays |

---

## 🖱️ Webcam PiP Controls

- **Move**: Click and drag anywhere inside the webcam window.
- **Resize**: Move your cursor over any corner or edge (look for the resize handle cursor) and drag to scale.
- **Mouse Wheel**: Hover over the webcam window and scroll up/down to zoom in/out.
- **Right-Click Context Menu**:
  - Toggle Shape: **Circle**, **Rounded Rectangle**, or **Square**.
  - **Flip Horizontally (Mirror)**.
  - Change Frame Rate / Quality.
  - Close Webcam.

---

## 📂 Project Architecture

```
pythonscreenrecorder/
├── main.py                     # Application entrypoint & Qt initialization
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation & setup guide
├── src/
│   ├── config/                 # Application constants, defaults, and settings
│   │   ├── constants.py        # 4K profiles, hotkeys, branding constants
│   │   └── settings_manager.py # JSON configuration persistence
│   ├── core/                   # Core capture & media processing engines
│   │   ├── camera_detect.py    # DirectShow / QtMultimedia camera enumeration
│   │   ├── capture_engine.py   # Master frame grabber & orchestrator
│   │   ├── ffmpeg_writer.py    # Multi-threaded FFmpeg encoder & muxer
│   │   ├── audio_recorder.py   # Dual-channel WASAPI & microphone recorder
│   │   └── screen_capture.py   # MSS & DXCAM high-FPS screen grabbers
│   ├── overlays/               # Floating transparent UI components
│   │   ├── webcam_pip.py       # Resizable floating webcam PiP overlay
│   │   ├── drawing_canvas.py   # Real-time drawing & annotation canvas
│   │   └── region_selector.py  # Snapping area selection tool
│   ├── services/               # Background services
│   │   ├── hotkey_service.py   # Global keyboard hook listener (pynput)
│   │   └── notification.py     # Desktop toast notifications
│   └── ui/                     # User interface widgets & dialogs
│       ├── main_window.py      # Main control dashboard
│       ├── about_dialog.py     # Organization & developer credits dialog
│       ├── shortcuts_dialog.py # Interactive keyboard shortcut guide
│       └── styles.qss          # Dark glassmorphic QSS stylesheet
├── scripts/                    # Diagnostic & benchmarking utilities
│   ├── benchmark_capture.py    # Screen capture FPS benchmark
│   └── diagnose_audio.py       # WASAPI loopback device inspector
└── tests/                      # Unit & integration test suite
    ├── test_camera_detect.py   # Camera discovery tests
    └── test_engine.py          # 4K encoding and pipeline integration tests
```

---

## 🧪 Running Diagnostic & Unit Tests

To run the built-in test suite to verify camera discovery, audio devices, and 4K encoder pipeline:

```powershell
# Activate your virtual environment first
.\.venv\Scripts\activate

# Run test suite
python -m unittest discover tests
```

To run diagnostic benchmarks:

```powershell
# Benchmark screen capture FPS
python scripts/benchmark_capture.py

# Inspect audio input & output devices
python scripts/diagnose_audio.py
```

---

## 📦 Building Standalone Single-File Executable (.exe)

You can package **CNAT Screen Recorder** into a portable, standalone single-file Windows executable (`CNAT_Screen_Recorder.exe`) that runs on any modern Windows 10/11 machine without needing Python installed:

Simply double-click or run from command prompt:
```cmd
build_exe.bat
```
*(or run `build.bat`)*

### What the build process does automatically:
1. Detects or configures the virtual environment (`.venv`) and installs any missing packaging dependencies.
2. Generates the high-resolution multi-size application icons (`assets/app_icon.ico`).
3. Uses [PyInstaller](https://pyinstaller.org/) with [CNAT_Screen_Recorder.spec](file:///e:/pythonscreenrecorder/CNAT_Screen_Recorder.spec) to package:
   - All Python modules and background threads.
   - Dark glassmorphic QSS stylesheets (`src/ui/styles.qss`).
   - QtAwesome vector icon font bundles.
   - Bundled high-performance FFmpeg video/audio encoding binaries.
4. Generates a single `.exe` located at `dist\CNAT_Screen_Recorder.exe` and offers to open the folder or launch the app immediately.

---

## 🔧 Troubleshooting & FAQs


<details>
<summary><b>1. PowerShell script execution error when activating .venv</b></summary>
<br>
If PowerShell prevents running scripts, run this command once in your PowerShell terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```
</details>

<details>
<summary><b>2. System audio (loopback) is silent</b></summary>
<br>
Ensure your default audio output device (speakers or headphones) is active. You can run `python scripts/diagnose_audio.py` to list all available loopback-capable WASAPI devices.
</details>

<details>
<summary><b>3. Webcam is not showing in the list</b></summary>
<br>
- For physical webcams: Ensure USB is securely plugged in and camera permissions are enabled in Windows Settings (*Settings > Privacy & Security > Camera*).
- For Iriun Webcam: Ensure the Iriun app is open on your mobile device and connected to the same WiFi network before launching the screen recorder.
</details>

<details>
<summary><b>4. Output video file location</b></summary>
<br>
By default, recordings are saved to:
```
C:\Users\<YourUsername>\Videos\CNATRecordings\
```
You can change the output folder anytime in the **Settings** panel of the application.
</details>

---

## 🏢 About the Developer & Organization

**CNAT Screen Recorder** is engineered and maintained by **Coder & AccoTax (CNAT)**.

- **Organization**: Coder & AccoTax (CNAT)
- **Lead Developer**: Sukanta Hui
- **Website**: [www.codernaccotax.co.in](https://www.codernaccotax.co.in)
- **Phone / WhatsApp**: [+91 7003756860](tel:+917003756860) / `7003756860`
- **Official Repository**: [https://github.com/sukantahui/pythonscreenrecorder.git](https://github.com/sukantahui/pythonscreenrecorder.git)

---

## 📄 License & Terms of Use

This software is developed and published by **Coder & AccoTax (CNAT)**.

- **Copyright**: © 2026 **Coder & AccoTax (CNAT)**. All rights reserved.
- **Lead Developer**: **Sukanta Hui**
- **License Type**: **Coder & AccoTax (CNAT) Proprietary & Commercial Software License**
- **Terms**: Authorized for use, deployment, and distribution according to Coder & AccoTax (CNAT) terms. For inquiries or enterprise licensing, visit [www.codernaccotax.co.in](https://www.codernaccotax.co.in) or call `+91 7003756860`.
