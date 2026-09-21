# 02. Feature Specifications & Requirements

This document details all functional requirements, user interactions, and technical parameters required for the GUI Python Screen Recorder.

---

## 1. Capture Modes & Target Selection

### 1.1 Full Screen & Multi-Monitor Support
- Automatically detect all connected monitors (e.g., Primary 1920x1080 @ 100% DPI, Secondary 2560x1440 @ 125% DPI).
- Allow user to pick individual monitors or record the entire virtual desktop span.
- Proper handling of Windows High-DPI scaling (`SetProcessDpiAwareness` / `Qt.ApplicationAttribute.AA_EnableHighDpiScaling`).

### 1.2 Custom Region Selection (Interactive Box)
- Semi-transparent overlay allows click-and-drag bounding box selection.
- 8-point resize handles (corners and edges) for precise pixel adjustment.
- **HUD Indicator**: Displays real-time `(X, Y, Width, Height)` and aspect ratio.
- **Preset Buttons**: Quick-select `1920x1080 (16:9)`, `1280x720 (16:9)`, `1080x1920 (9:16 Vertical/Shorts)`, `1080x1080 (1:1)`.
- Option to lock aspect ratio during resize.

### 1.3 Specific Window Capture
- Dropdown listing all active, non-minimized desktop windows with their app icons.
- Ability to track window coordinates if the user moves the target window during recording.
- Auto-crop capture coordinates to window rect (using `GetWindowRect` / `pywin32`).

---

## 2. Audio Capture & Mixer Subsystem

| Channel | Source Backend | Description | Features |
| :--- | :--- | :--- | :--- |
| **System Sound** | WASAPI Loopback (`sounddevice`) | Captures audio emitted by games, videos, browsers, and OS. | Volume slider (0-200%), Mute button, Real-time VU meter. |
| **Microphone** | Direct Sound / WASAPI Input | Captures voice from external or built-in microphone. | Device selector, Gain boost, Noise gate, Real-time VU meter. |

- **Audio Track Options**:
  - **Single Mixed Track**: Audio channels blended into a standard Stereo track.
  - **Multi-Track Export**: Video container includes Track 1 (System Audio) and Track 2 (Microphone Audio) for post-production editing in Premiere/DaVinci.

---

## 3. Webcam Picture-in-Picture (PiP) Overlay

- **Camera Discovery**: Query available video capture devices via OpenCV (`cv2.VideoCapture`).
- **Shapes & Framing**:
  - Circle mask with customizable border color and thickness.
  - Rounded rectangle mask.
  - Classic rectangular window.
- **Positioning**:
  - Draggable anywhere on the capture region in real time.
  - Corner snap presets: Top-Left, Top-Right, Bottom-Left, Bottom-Right.
- **Customization**:
  - Scale slider (10% to 50% of screen width).
  - Horizontal Mirror / Flip toggle.

---

## 4. Live Annotation & Screen Drawing Tools

A transparent, click-through capable top-level canvas (`Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint`) activated during recording:

```
[✏️ Pen] [🖌️ Highlighter] [➡️ Arrow] [⬜ Rectangle] [⭕ Circle] [🔢 Step Badge] [🔤 Text] [⬛ Blur/Pixelate] [↩️ Undo] [🗑️ Clear]
```

1. **Pen / Brush**: Freehand smooth drawing with customizable color palette and stroke thickness (2px to 20px).
2. **Highlighter**: 50% opacity translucent stroke for highlighting documents/code without obscuring text.
3. **Geometry Tools**: Clean lines, auto-aligning arrows, bounding rectangles, and ellipses.
4. **Step Counter / Badges**: Clicking drops incrementing numbered circles `①`, `②`, `③` for tutorials.
5. **Text Tool**: Click anywhere to type text annotations with customizable font size.
6. **Blur / Obfuscation Tool**: Drag a rectangle to pixelate or blur passwords, API keys, or personal information on screen.
7. **Auto-Fade Mode**: Annotations disappear automatically after 3 seconds (ideal for live presentations).

---

## 5. Mouse Cursor Effects & Keystroke HUD

### 5.1 Cursor Enhancements
- **Highlight Halo**: Translucent colored circle surrounding the cursor (e.g., bright yellow/cyan).
- **Click Ripples**:
  - Left-click: Expanding red ring animation.
  - Right-click: Expanding blue ring animation.
  - Middle-click: Expanding green ring animation.
- **Hide Cursor Toggle**: Option to completely omit the mouse pointer from the recording.

### 5.2 Keystroke HUD (Keycast)
- Floating customizable overlay in the bottom corner of the screen.
- Displays keyboard shortcuts pressed by the user (e.g., `Ctrl + Shift + P`, `Alt + Tab`, `Cmd + S`).
- Automatically fades out after 1.5 seconds of inactivity.

---

## 6. Global Hotkeys & System Tray Integration

### 6.1 Default Global Keybindings (Configurable)
- `F9` or `Ctrl + Shift + R`: Start / Stop Recording
- `F10` or `Ctrl + Shift + P`: Pause / Resume Recording
- `F8` or `Ctrl + Shift + A`: Toggle Annotation Canvas
- `F11` or `Ctrl + Shift + S`: Instant Screenshot (Save to folder & copy to clipboard)

### 6.2 System Tray & Minimization
- Minimize to System Tray when recording starts (leaves desktop clutter-free).
- Tray icon pulses red when recording is active.
- Context menu: Quick Stop, Pause, Open Output Folder, Exit.
- Native desktop notifications on recording start, stop, and screenshot capture.

---

## 7. Recording Controls & Floating Widget

When recording begins, the main window can either hide or transform into an ultra-compact, semi-transparent **Floating Control Bar**:
- Elapsed Time counter (`00:02:45`).
- Current FPS & dropped frames counter.
- **Pause / Resume** button.
- **Stop & Save** button.
- **Draw / Annotate** toggle.
- **Screenshot** button.
- Drag-handle to reposition the toolbar anywhere on screen.

---

## 8. Post-Recording Manager & Quick Editor

Upon stopping a recording, an instant preview modal appears:
1. **Video Preview Player**: Play/pause, seek bar, timecode, and playback speed (0.5x, 1x, 1.5x, 2x).
2. **Trim / Cut**: Draggable start and end markers to trim unwanted footage before saving.
3. **Export Presets**:
   - **High Quality MP4 (H.264/AAC)**: Best for YouTube/Vimeo.
   - **Ultra-Small MP4 (H.265/HEVC)**: Best for Discord/Slack/Email.
   - **Animated GIF**: For short clips, bug reports, and READMEs (with customizable FPS & loop count).
   - **Audio Only (MP3/WAV)**: Extract meeting/lecture audio.
4. **Quick Actions**: "Open in Explorer", "Copy File", "Share", "Delete".
