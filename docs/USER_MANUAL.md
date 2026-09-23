# CNAT Screen Recorder — Official User Manual & Operating Guide

<p align="center">
  <b>Version 1.0.0 (Production Release)</b><br>
  <i>Developed and Maintained by <b>Coder & AccoTax (CNAT)</b></i>
</p>

---

## 🏢 Organization & Developer Credentials

| Attribute | Details |
| :--- | :--- |
| **Software Name** | **CNAT Screen Recorder** |
| **Version** | `1.0.0` (Production Master) |
| **Organization** | **Coder & AccoTax (CNAT)** |
| **Lead Developer** | **Sukanta Hui** |
| **Official Website** | [www.codernaccotax.co.in](https://www.codernaccotax.co.in) |
| **Contact / WhatsApp** | `+91 7003756860` / `7003756860` |
| **Official Repository** | [https://github.com/sukantahui/pythonscreenrecorder.git](https://github.com/sukantahui/pythonscreenrecorder.git) |
| **Copyright** | © 2026 Coder & AccoTax (CNAT). All rights reserved. |

---

## 📋 Table of Contents

1. [Introduction & System Overview](#1-introduction--system-overview)
2. [System Requirements & Hardware Acceleration](#2-system-requirements--hardware-acceleration)
3. [Default Profile & Quick Start](#3-default-profile--quick-start)
4. [Screen Capture Modes & Aspect Ratio Presets](#4-screen-capture-modes--aspect-ratio-presets)
5. [Audio Capture Engine & Multi-Source Mixing](#5-audio-capture-engine--multi-source-mixing)
6. [Real-Time AI Noise Suppression](#6-real-time-ai-noise-suppression)
7. [Webcam Studio & Presenter Modes](#7-webcam-studio--presenter-modes)
8. [Live On-Screen Annotation Canvas](#8-live-on-screen-annotation-canvas)
9. [Floating Capsule Toolbar & Global Hotkeys](#9-floating-capsule-toolbar--global-hotkeys)
10. [Video Quality Profiles, 4K Master & Encoders](#10-video-quality-profiles-4k-master--encoders)
11. [Post-Recording Player, Trimmer & Format Exporter](#11-post-recording-player-trimmer--format-exporter)
12. [Diagnostics, Troubleshooting & FAQs](#12-diagnostics-troubleshooting--faqs)
13. [Contact, Technical Support & License](#13-contact-technical-support--license)

---

## 1. Introduction & System Overview

**CNAT Screen Recorder** is a studio-grade desktop recording and live streaming capture software engineered specifically for creators, educators, software developers, and corporate professionals. 

Built with **Python 3.10+** and **PyQt6**, the software integrates a high-performance multithreaded capture architecture capable of fluid **4K Ultra HD (3840×2160) @ 60/120 FPS** screen recording with ultra-low latency, real-time hardware GPU acceleration, multi-track audio mixing (system loopback, external studio microphone, and webcam audio), dynamic floating webcam picture-in-picture (PiP) bubbles with studio shapes and filters, on-screen live drawing annotations, and comprehensive post-processing utilities.

---

## 2. System Requirements & Hardware Acceleration

### Minimum Requirements:
- **Operating System**: Windows 10 (64-bit) Build 19041+ or Windows 11.
- **Processor**: Intel Core i3 (7th Gen+) or AMD Ryzen 3 (3000 Series+).
- **RAM**: 4 GB RAM.
- **Display**: 1280×720 minimum display resolution.
- **Storage**: 200 MB free space for application; additional space for recording files.

### Recommended (for 4K Ultra HD @ 60 FPS):
- **Processor**: Intel Core i7 / i9 (10th Gen+) or AMD Ryzen 7 / 9.
- **RAM**: 16 GB DDR4/DDR5 RAM.
- **Graphics Card (Hardware GPU Acceleration)**:
  - **NVIDIA**: GeForce GTX 1060 or RTX series (`NVENC` hardware encoder).
  - **Intel**: Intel Iris Xe / UHD 630+ (`QuickSync / QSV`).
  - **AMD**: Radeon RX 5000 / 6000 / 7000 series (`AMF`).
- **Microphone**: Dedicated USB Studio Microphone (e.g., **JBL Commercial CSUM10**).
- **Webcam**: High-definition webcam or smartphone camera via **Iriun Webcam**.

---

## 3. Default Profile & Quick Start

When you launch **CNAT Screen Recorder**, it initializes automatically with the optimized creator profile:

1. **🔊 System Audio**: Unchecked (`Off`) by default to prevent unwanted desktop notifications from interrupting your narration.
2. **🎙️ Microphone**: Checked (`On`) by default, automatically binding to your primary dedicated microphone (**JBL Commercial CSUM10** via WASAPI).
3. **🔇 Real-Time Noise Reduction**: Set to `0%` (`Off`) by default; adjust the slider to eliminate room hiss and fan noise.
4. **📷 Webcam PiP**: Checked (`On`) by default, automatically selecting **Iriun Webcam** with the **⭕ Circle Bubble** framing shape.
5. **🎙️ Webcam Audio**: Unchecked (`Off`) by default, preventing unwanted room echo.
6. **🎯 Resolution & Quality**: Set to **`4K Ultra HD (3840x2160)`** & **`4K Ultra Master (60 Mbps)`**.
7. **📐 Window Sizing**: Fixed **`860 × 840 px`** dashboard with memory geometry.

### Quick Start in 3 Steps:
1. Open the application.
2. Select **🖥️ Full Screen** or choose a locked aspect ratio preset (e.g., **📱 9:16 Reel** for YouTube Shorts/Reels or **🎬 16:9** for YouTube).
3. Press **`F9`** (or click **● START RECORDING**) to begin recording after a 3-second visual countdown. Press **`F9`** again to finish.

---

## 4. Screen Capture Modes & Aspect Ratio Presets

### 1. Full Screen Mode (`🖥️ Full Screen`)
Captures the entire primary display at native or 4K scaled resolution with zero frame drops.

### 2. Custom Region Mode (`🔲 Custom Region`)
Allows you to click and drag a custom capture box anywhere on your screen. The interactive selector features live dimension badges, drag handles, and position coordinates.

### 3. Social Media Locked Aspect Ratio Presets:
| Preset | Aspect Ratio | Standard Resolutions | Target Platform |
| :--- | :---: | :---: | :--- |
| **📱 9:16 Reel** | `9:16` | 1080×1920, 720×1280 | Instagram Reels, YouTube Shorts, TikTok |
| **🎬 16:9 YouTube** | `16:9` | 3840×2160 (4K), 1920×1080 | YouTube, Twitch, Facebook Landscape |
| **📷 1:1 Square** | `1:1` | 1080×1080, 720×720 | Instagram Square Posts, Twitter Feeds |
| **🖼️ 4:5 Portrait** | `4:5` | 1080×1350, 864×1080 | Instagram Portrait Posts |
| **📺 4:3 Classic** | `4:3` | 1440×1080, 1024×768 | Presentations, iPad Displays, Legacy Media |
| **🎞️ 21:9 Cinema** | `21:9` | 2560×1080, 3440×1440 | Ultrawide Cinematic Gameplays & Demos |
| **🔓 Freeform** | Arbitrary | Unlocked Width & Height | Flexible application/window capture |

---

## 5. Audio Capture Engine & Multi-Source Mixing

CNAT Screen Recorder incorporates a low-latency, multithreaded audio capture and mixing subsystem:

- **System Audio (WASAPI Loopback)**: Captures internal PC sounds, music, meetings, and game audio directly from the sound card without needing virtual audio cables.
- **Dedicated Microphone**: Captures vocal narration with support for mono/stereo multi-channel endpoints. Automatically prioritizes dedicated USB microphones (**JBL Commercial CSUM10**).
- **Webcam Audio**: Optionally captures audio from the camera's built-in microphone array.
- **Independent Volume & VU Meters**: Real-time progress bars provide live audio level feedback for immediate gain monitoring.

---

## 6. Real-Time AI Noise Suppression

The built-in **Real-Time Noise Reducer** runs directly in pure NumPy with zero CPU overhead:
- **0% (Off)**: Studio clean bypass.
- **1% – 35% (Subtle / Low)**: Eliminates subtle AC hum and PC fan whir while preserving full vocal dynamics.
- **36% – 70% (Balanced / Medium)**: Filters ambient room echo, distant traffic, and continuous background noise.
- **71% – 100% (High / Aggressive)**: Maximum spectral subtraction and downward audio gating for noisy office or classroom environments.

---

## 7. Webcam Studio & Presenter Modes

### 1. Floating Picture-in-Picture (PiP) Overlay
- **Draggable Anywhere**: Click and drag the webcam bubble anywhere across multi-monitor setups.
- **Dynamic Resizing**: Scroll the mouse wheel over the bubble to resize from **100 px** up to **600 px**.
- **Hover Pill Action Bar**: Hover near the top of the webcam bubble to reveal quick action pills:
  - 🔄 **Flip**: Horizontally mirror camera view.
  - 📐 **Shape**: Cycle through studio framing shapes.
  - 🎨 **Filter**: Cycle real-time color and beauty filters.
  - 📌 **Dock**: Instantly snap webcam to 4 screen corners (Bottom-Right, Bottom-Left, Top-Right, Top-Left).
  - ⛶ **Full**: Switch into Fullscreen Presenter Cam mode.
  - ❌ **Hide**: Close camera PiP.

### 2. Studio Framing Shapes:
- **⭕ Circle Bubble**: Classic circular floating presenter bubble.
- **🎬 16:9 Widescreen**: Cinematic widescreen framing.
- **🔲 Rounded Card**: Modern rounded presentation card.
- **📱 9:16 Vertical Reel**: Mobile-ready vertical framing.
- **⬛ Classic Square**: 1:1 square camera framing.

### 3. Studio Filters:
- 🌿 **Natural / Original**: Unfiltered raw camera output.
- ☀️ **Studio Warm**: Flattering golden skin-tone enhancement.
- ❄️ **Crisp Cool**: High-contrast modern tech presentation tone.
- 💡 **Brightness Boost**: Enhanced exposure for dim environments.
- 🎞️ **Monochrome (B&W)**: Cinematic black and white.
- ✨ **Soft Skin Smooth**: Bilateral skin-smoothing beauty filter.

### 4. ⛶ Fullscreen & Region Presenter Cam Mode (`F4`)
Transform the entire recording canvas into a full camera view. Ideal for podcast intros, video conclusions, or direct instructor talks before switching back to screen capture. Press **`F4`** or **`Esc`** at any time to toggle back to the floating bubble!

---

## 8. Live On-Screen Annotation Canvas

Press **`F8`** during any recording to freeze screen interactions and open the transparent annotation overlay:

- ✏️ **Freehand Pen**: Smooth fluid ink for circling and handwriting.
- 🖍️ **Neon Highlighter**: Semi-transparent fluorescent highlighter for marking code or text.
- ➡️ **Smart Arrows**: Auto-aligning directional indicator arrows.
- 🔲 **Rectangles & Circles**: Geometry bounding boxes for highlighting UI elements.
- 🔢 **Numbered Step Badges**: Sequential circle badges `(1)`, `(2)`, `(3)` for instructional tutorials.
- 🔤 **Text Labels**: Crisp typography notes with dark backdrop.
- 🎨 **Color Palette**: Red, Emerald Green, Electric Blue, Amber Yellow, Purple, Pure White, Neon Cyan.
- ↩️ **Undo / Redo / Clear**: Full history stack for effortless corrections.

---

## 9. Floating Capsule Toolbar & Global Hotkeys

During recording, the main dashboard minimizes to the system tray, and a sleek **Floating Capsule Bar** appears at the top-center of your screen:

- ⏱️ **Live Elapsed Timer**: Real-time `MM:SS` duration counter.
- ⏸️ **Pause / Resume**: Temporarily halt recording without creating multiple video files.
- ⏹️ **Stop & Save**: Finish recording and open the instant player.
- ✏️ **Draw (`F8`)**: Open live annotation canvas.
- 📷 **PiP (`F7`)**: Toggle webcam visibility.
- ⛶ **Presenter Cam (`F4`)**: Toggle Fullscreen Presenter Mode.
- 📸 **Screenshot (`F11`)**: Take an instant high-resolution PNG snapshot.

### Global Hotkey Cheat Sheet:
| Shortcut | Action | Description |
| :---: | :--- | :--- |
| **`F9`** | **Start / Stop Recording** | Primary global capture toggle |
| **`F10`** | **Pause / Resume** | Freeze and resume recording |
| **`F8`** | **Annotation Canvas** | Toggle drawing and whiteboard tools |
| **`F7`** | **Toggle Webcam PiP** | Show or hide floating camera bubble |
| **`F4`** | **Fullscreen Presenter Cam** | Toggle full camera presenter mode |
| **`F6`** | **Mute / Unmute Mic** | Instant microphone mute toggle |
| **`F11`** | **Take Screenshot** | Capture full-resolution PNG image |
| **`Esc`** | **Exit Overlay / Restore** | Restore floating bubble or cancel region |

---

## 10. Video Quality Profiles, 4K Master & Encoders

| Quality Profile | Bitrate | CRF / CQ | Recommended Use Case |
| :--- | :---: | :---: | :--- |
| **4K Ultra Master (60 Mbps)** | `60 Mbps` | `14` | Ultra-crisp text, 4K UHD YouTube tutorials, Master archives |
| **High Quality (20 Mbps)** | `20 Mbps` | `18` | 1080p / 1440p standard recordings, high motion video |
| **Medium Quality (8 Mbps)** | `8 Mbps` | `23` | General meetings, long presentations, space saving |
| **Low Size / Draft (3 Mbps)** | `3 Mbps` | `28` | Quick preview drafts, low bandwidth sharing |

---

## 11. Post-Recording Player, Trimmer & Format Exporter

When recording finishes, the **Recording Complete Preview Dialog** opens automatically:
- 🎬 **Instant Playback**: Synchronized audio and video playback with scrubbing slider and volume control.
- ✂️ **Lossless Trimmer**: Set `Start Time` and `End Time` spinboxes and export trimmed clips in seconds without re-encoding quality loss.
- 🎞️ **Convert to Animated GIF**: Export lightweight high-frame-rate GIFs for documentation and GitHub pull requests.
- 🎵 **Extract MP3 Audio**: Convert voice narration and interviews into standalone MP3 audio files.
- 📋 **Copy to Clipboard & Explorer**: Copy video file directly or open containing folder with one click.

---

## 12. Diagnostics, Troubleshooting & FAQs

### Q1: Where are my recordings saved?
**A:** By default, all recordings are saved to:
```
C:\Users\<YourUsername>\Videos\CNATRecordings\
```
You can change the output directory anytime via the **Settings (⚙️)** panel.

### Q2: How do I connect Iriun Webcam on my smartphone?
1. Install **Iriun 4K Webcam** on your Android / iPhone and on your PC.
2. Connect both phone and PC to the same Wi-Fi network (or connect via USB Cable with USB debugging enabled).
3. Open CNAT Screen Recorder. Iriun Webcam is automatically discovered and selected!

### Q3: My audio is silent during playback.
- Check the **Microphone** card on the main dashboard to verify your device is selected.
- If recording PC audio, check the **System Audio** checkbox.
- Ensure microphone permissions are allowed in Windows Settings (*Settings > Privacy & Security > Microphone*).

---

## 13. Contact, Technical Support & License

**CNAT Screen Recorder** is an official software release by **Coder & AccoTax (CNAT)**.

- **Organization**: Coder & AccoTax (CNAT)
- **Lead Developer**: Sukanta Hui
- **Official Website**: [https://www.codernaccotax.co.in](https://www.codernaccotax.co.in)
- **Helpline / WhatsApp**: `+91 7003756860` / `7003756860`
- **GitHub Repository**: [https://github.com/sukantahui/pythonscreenrecorder](https://github.com/sukantahui/pythonscreenrecorder)
- **License**: **Coder & AccoTax (CNAT) Software License**. Copyright © 2026 Coder & AccoTax (CNAT). All rights reserved.

*(Generated and verified on September 24, 2026)*
