# Master Agent Blueprint: GUI Python Screen Recorder

> **Purpose**: This document serves as the primary execution blueprint for an AI coding agent or software engineer to autonomously construct a production-ready, high-performance **GUI-based Python Screen Recorder**.

---

## 1. Executive Summary & Architecture Overview

The application is a desktop screen recording suite built with **Python 3.10+**, **PyQt6**, **DXCam/MSS**, **SoundDevice (WASAPI Loopback)**, and **FFmpeg**. It delivers smooth 60-120 FPS recording, synchronized dual-track audio (System + Mic), live screen annotations, webcam picture-in-picture, and hardware-accelerated video encoding (NVENC / QuickSync / AMF / CPU).

### Project Architecture & Reference Specifications
Before writing code, study the modular technical specifications in the `docs/` folder:
- [01_system_architecture.md](file:///e:/python%20screen%20recorder/docs/01_system_architecture.md): Multi-threading model, frame queues, monotonic A/V sync algorithm.
- [02_feature_specifications.md](file:///e:/python%20screen%20recorder/docs/02_feature_specifications.md): Capture modes, live drawing canvas, webcam PiP, hotkeys, audio mixer.
- [03_tech_stack_and_engine.md](file:///e:/python%20screen%20recorder/docs/03_tech_stack_and_engine.md): Capture backends, WASAPI audio loopback, FFmpeg stdin streaming pipelines.
- [04_ui_ux_design.md](file:///e:/python%20screen%20recorder/docs/04_ui_ux_design.md): Dark Glassmorphic UI design tokens, floating recording widget, QSS styling.
- [05_testing_and_verification.md](file:///e:/python%20screen%20recorder/docs/05_testing_and_verification.md): Testing matrix, audio diagnostics, benchmark scripts, edge-case handlers.

---

## 2. Target File & Folder Structure

Structure the implementation as follows:

```
python-screen-recorder/
├── main.py                         # Application entrypoint & Qt Application lifecycle
├── requirements.txt                # Project dependencies
├── resources/                      # Icons, fonts, and assets
│   └── icons/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── constants.py            # Resolution presets, default hotkeys, color tokens
│   │   └── settings_manager.py     # JSON/QSettings persistence for user preferences
│   ├── core/
│   │   ├── __init__.py
│   │   ├── controller.py           # Recording state machine & orchestrator
│   │   ├── video_capture.py        # DXCam / MSS screen capture worker thread
│   │   ├── audio_capture.py        # WASAPI Loopback system sound + Mic worker
│   │   ├── ffmpeg_writer.py        # Real-time FFmpeg pipe streaming & muxer
│   │   └── hardware_detect.py      # Automated NVENC / QSV / AMF GPU probe
│   ├── overlays/
│   │   ├── __init__.py
│   │   ├── region_selector.py      # Interactive transparent bounding-box picker
│   │   ├── annotation_canvas.py    # Screen drawing tools (Pen, Arrow, Text, Blur)
│   │   ├── webcam_pip.py           # Draggable circular/rounded webcam overlay
│   │   ├── cursor_highlighter.py   # Halo, click ripple effects, mouse tracking
│   │   └── keystroke_hud.py        # Live shortcut keystroke display overlay
│   ├── services/
│   │   ├── __init__.py
│   │   ├── hotkey_service.py       # Global keyboard listener (pynput)
│   │   ├── tray_service.py         # System tray icon & context menu
│   │   └── post_processor.py       # Video trimming & GIF converter
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py          # Primary modern dashboard
│       ├── floating_bar.py         # Minimal capsule recording toolbar
│       ├── settings_dialog.py      # Device selector, codec & hotkey config modal
│       ├── preview_dialog.py       # Post-recording playback & trim modal
│       └── styles.qss              # Master stylesheet
└── docs/                           # Architecture & spec documentation
```

---

## 3. Step-by-Step Phased Implementation Plan

Follow these sequential phases. **Do not skip phases.**

### Phase 1: Environment & Core Engine Foundation
1. Install and verify dependencies from [requirements.txt](file:///e:/python%20screen%20recorder/requirements.txt).
2. Implement `src/core/hardware_detect.py` to detect available GPU encoders (`h264_nvenc`, `h264_qsv`, `h264_amf`, or software `libx264`).
3. Implement `src/core/video_capture.py` supporting both full-screen and arbitrary bounding boxes with automatic even-pixel normalization (`width & ~1`, `height & ~1`).
4. Implement `src/core/audio_capture.py` capturing WASAPI system audio and microphone with volume gain scaling.
5. Implement `src/core/ffmpeg_writer.py` to feed raw video/audio frames through FFmpeg subprocess pipes with zero intermediate disk lag.

### Phase 2: State Controller & Synchronization
1. Implement `src/core/controller.py` managing state transitions (`IDLE` -> `COUNTDOWN` -> `RECORDING` -> `PAUSED` -> `FINALIZING`).
2. Integrate monotonic timestamps (`time.perf_counter`) to prevent A/V drift during frame rate drops or system lag.
3. Add crash-safe faststart handling (`-movflags +faststart` or temp MKV recording) so recordings are never corrupted if closed unexpectedly.

### Phase 3: PyQt6 Modern UI & Interactive Overlays
1. Create `src/ui/styles.qss` implementing the dark glassmorphic design system.
2. Build `src/ui/main_window.py` with display mode cards, audio level meters, quality presets, and the primary record button.
3. Build `src/overlays/region_selector.py` with 8-handle resizing, aspect ratio locks, and real-time dimension HUD.
4. Build `src/ui/floating_bar.py` (frameless draggable pill widget) displaying elapsed time, pause/resume, stop, and annotation toggles.

### Phase 4: Creative Tools & Overlays
1. Build `src/overlays/annotation_canvas.py`: Transparent top-level canvas with smooth freehand pen, highlighters, arrows, numbered step badges, and blur brush.
2. Build `src/overlays/webcam_pip.py`: Draggable, circular or rounded camera feed embedded or composited into the video.
3. Build `src/overlays/cursor_highlighter.py` & `keystroke_hud.py` using `pynput`.

### Phase 5: System Integration & Post-Recording Preview
1. Implement `src/services/hotkey_service.py` (`F9` Record/Stop, `F10` Pause, `F8` Annotate, `F11` Screenshot).
2. Implement `src/services/tray_service.py` with dynamic pulsing recording icon.
3. Implement `src/ui/preview_dialog.py` for post-recording instant video playback, trimming, and GIF export.
4. Wire everything together in `main.py` with DPI awareness and graceful signal handling (`SIGINT`, `SIGTERM`, `closeEvent`).

---

## 4. Non-Negotiable Engineering Standards

1. **Thread Safety**: Never interact with PyQt6 UI widgets directly from background capture or audio threads. Always emit `pyqtSignal`.
2. **Zero Memory Leaks**: Enforce bounded ring-buffers / queues for video and audio frames to prevent unbounded memory growth if disk writing is momentarily blocked.
3. **No Corrupt Video Outputs**: When stopping a recording, always cleanly close stdin pipes and wait for the FFmpeg process to terminate and write the file footer before notifying the UI.
4. **Clean Code & Robust Logging**: Use Python standard `logging` with structured formatting (`%(asctime)s [%(levelname)s] %(name)s: %(message)s`).
5. **High-DPI Scaling**: Enable `Qt.ApplicationAttribute.AA_EnableHighDpiScaling` and `SetProcessDpiAwareness(2)` on Windows so coordinates never mismatch display pixels.
