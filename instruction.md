# Master Agent Instructions: GUI-Based Python Screen Recorder

> [!NOTE]
> This is the primary instruction file for the AI Agent. For the full master blueprint and modular documentation breakdown, refer to [INSTRUCTIONS.md](file:///e:/python%20screen%20recorder/INSTRUCTIONS.md) and the `docs/` folder.

---

## 📌 Executive Instructions for the Coding Agent

You are tasked with building a high-performance, industry-standard **GUI-based Python Screen Recorder**. 

### 📚 Modular Documentation Suite
The project specifications have been divided into specialized modules as per industry best practices:

1. **[INSTRUCTIONS.md](file:///e:/python%20screen%20recorder/INSTRUCTIONS.md)**: Master Blueprint, Project Structure, and Phased Implementation Plan (Phases 1 through 5).
2. **[docs/01_system_architecture.md](file:///e:/python%20screen%20recorder/docs/01_system_architecture.md)**: Threading model, Audio/Video synchronization strategy, Monotonic timestamping, and Ring buffer management.
3. **[docs/02_feature_specifications.md](file:///e:/python%20screen%20recorder/docs/02_feature_specifications.md)**: Detailed feature breakdown (Fullscreen, Region picker, Window capture, System sound + Mic WASAPI mixer, Webcam PiP, Live annotation canvas, Mouse effects, Keystroke HUD, Global hotkeys, System tray).
4. **[docs/03_tech_stack_and_engine.md](file:///e:/python%20screen%20recorder/docs/03_tech_stack_and_engine.md)**: Concrete technology choices (`PyQt6`, `dxcam`/`mss`, `sounddevice`, hardware-accelerated `FFmpeg` pipe streaming for NVENC/QSV/AMF/CPU).
5. **[docs/04_ui_ux_design.md](file:///e:/python%20screen%20recorder/docs/04_ui_ux_design.md)**: Modern dark glassmorphic design system tokens, layout wireframes, floating minimal recording bar, and production QSS stylesheet.
6. **[docs/05_testing_and_verification.md](file:///e:/python%20screen%20recorder/docs/05_testing_and_verification.md)**: Quality assurance testing matrix, audio diagnostic scripts, and capture benchmark utilities.
7. **[requirements.txt](file:///e:/python%20screen%20recorder/requirements.txt)**: Exact versioned dependencies.

---

## 🚀 Execution Strategy

When building the application, adhere to the 5 development phases in [INSTRUCTIONS.md](file:///e:/python%20screen%20recorder/INSTRUCTIONS.md):
- **Phase 1**: Core Engine (Video/Audio capture workers + FFmpeg pipe streamer).
- **Phase 2**: State Controller & Monotonic Timestamp A/V sync.
- **Phase 3**: Modern PyQt6 UI, Floating Capsule Bar, and Interactive Region Selector.
- **Phase 4**: Creative Overlays (Live annotation canvas, Webcam PiP, Cursor ripples, Keystroke HUD).
- **Phase 5**: Global Hotkeys, System Tray, Post-Recording Trim & GIF exporter.
