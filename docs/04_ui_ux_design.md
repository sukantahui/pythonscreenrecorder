# 04. UI / UX Design & Styling Specification

This document defines the visual design system, PyQt6 layouts, widget hierarchies, and QSS stylesheets for a sleek, modern desktop screen recorder.

---

## 1. Design System & Theme Tokens

The interface follows a **Modern Dark Glassmorphism** aesthetic inspired by top-tier modern productivity apps (e.g., CleanShot X, OBS Studio, Loom, CapCut).

| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--bg-base` | `#0D0E12` | Deep canvas background |
| `--bg-surface` | `#161820` | Cards, panels, and container widgets |
| `--bg-elevated` | `#20232E` | Hover states, dialogs, dropdowns |
| `--border-subtle` | `#2D313F` | Widget borders and dividers |
| `--accent-primary` | `#6366F1` | Brand Indigo (buttons, active tabs, focus rings) |
| `--accent-hover` | `#4F46E5` | Hover state for primary buttons |
| `--danger-record` | `#EF4444` | Recording active, Record button, Stop button |
| `--success-ready` | `#10B981` | Ready status, active audio indicators |
| `--text-primary` | `#F9FAFB` | Main headings, primary labels, timer |
| `--text-secondary`| `#9CA3AF` | Subtitles, helper text, inactive options |

---

## 2. Key Screen Mockups & Widget Layouts

### 2.1 Main Dashboard Window Layout
```
+-------------------------------------------------------------------------------+
|  🔴 REC STUDIO v1.0                    [📁 Videos]  [⚙️ Settings]  [─  ◻  ✕]  |
+-------------------------------------------------------------------------------+
|                                                                               |
|   [ 🖥️ Full Screen ]    [ 🔲 Custom Region ]    [ 🪟 App Window ]             |
|                                                                               |
|   +-------------------+  +-------------------+  +-------------------+         |
|   | 🔊 System Audio   |  | 🎙️ Microphone     |  | 📷 Webcam Overlay  |         |
|   | Realtek Speakers  |  | Blue Yeti         |  | Logitech C920     |         |
|   | [========] (100%) |  | [======  ] (75%)  |  | [ Circular (BR) ]  |         |
|   +-------------------+  +-------------------+  +-------------------+         |
|                                                                               |
|   Quality: [ 1080p 60fps (High) ▼ ]      Format: [ MP4 (H.264) ▼ ]            |
|                                                                               |
|                        +---------------------------+                          |
|                        |   ● START RECORDING (F9)  |                          |
|                        +---------------------------+                          |
|                                                                               |
|   Recent Recordings                                                           |
|   +-----------------------------------------------------------------------+   |
|   | 🎬 rec_2026-09-21_14-30.mp4    03:12    48.2 MB    [ ▶ Play ] [ 📂 ]  |   |
|   | 🎬 rec_2026-09-21_11-15.mp4    00:45    12.1 MB    [ ▶ Play ] [ 📂 ]  |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### 2.2 Floating Minimal Recording Bar (Capsule Widget)
When recording starts, the main window minimizes, and a sleek floating pill stays pinned to the top or bottom of the screen:
```
+------------------------------------------------------------------+
|  ⠿  🔴 00:04:22  |  60 FPS  |  [ ⏸ Pause ]  [ ⏹ Stop ]  [ ✏️ Draw ]  |
+------------------------------------------------------------------+
```
- **Attributes**: `Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow`
- **Draggable**: Drag handle (`⠿`) allows placing the bar anywhere on screen without being captured (if region recording is active outside of it).

### 2.3 Interactive Region Selection Overlay
- Covers entire desktop with `Qt.WindowType.FullScreen`.
- Semi-transparent dark background (`rgba(0, 0, 0, 0.5)`).
- Rubber-band draggable selection rectangle with glowing border and 8 corner/edge handles.
- **HUD Box**: Pinned above/below selection displaying:
  `[ 1920 × 1080 ] [ 16:9 ] [ Fullscreen ] [ 720p ] [ 1080p ] [ ✕ Cancel ] [ ✔ Confirm ]`

---

## 3. Production PyQt6 QSS Stylesheet Template

```css
/* Master Stylesheet */
QWidget {
    background-color: #0D0E12;
    color: #F9FAFB;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #6366F1;
}

/* Card Containers */
QFrame.Card {
    background-color: #161820;
    border: 1px solid #2D313F;
    border-radius: 12px;
    padding: 16px;
}

QFrame.Card:hover {
    border-color: #4F46E5;
}

/* Big Red Start Record Button */
QPushButton#BtnRecord {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF4444, stop:1 #DC2626);
    color: #FFFFFF;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-radius: 24px;
    padding: 12px 32px;
    min-height: 48px;
}

QPushButton#BtnRecord:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F87171, stop:1 #EF4444);
}

QPushButton#BtnRecord:pressed {
    background-color: #B91C1C;
}

/* Secondary Action Buttons */
QPushButton {
    background-color: #20232E;
    color: #F3F4F6;
    border: 1px solid #2D313F;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2B2F3D;
    border-color: #6366F1;
}

/* Floating Toolbar */
QFrame#FloatingToolbar {
    background-color: rgba(22, 24, 32, 0.92);
    border: 1px solid #3F4458;
    border-radius: 20px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #2D313F;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #6366F1;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #6366F1;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

/* Dropdown ComboBoxes */
QComboBox {
    background-color: #161820;
    border: 1px solid #2D313F;
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 120px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #1C1E24;
    border: 1px solid #2D313F;
    selection-background-color: #6366F1;
    border-radius: 6px;
}
```
