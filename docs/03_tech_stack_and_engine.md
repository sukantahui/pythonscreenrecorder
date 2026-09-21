# 03. Tech Stack, Capture Engine & FFmpeg Integration

This document specifies the concrete libraries, hardware acceleration backends, and low-level FFmpeg streaming pipelines for the Python Screen Recorder.

---

## 1. Technology Stack Breakdown

| Layer | Primary Library | Secondary / Fallback | Rationale |
| :--- | :--- | :--- | :--- |
| **GUI Framework** | `PyQt6` | `PySide6` | Industry standard for cross-platform desktop GUIs, hardware-accelerated OpenGL widgets, native Windows styling, and rock-solid `QThread` event loops. |
| **Windows Capture** | `dxcam` | `mss` | `dxcam` uses the DirectX Desktop Duplication API (DirectX 11) for zero-copy 60-120 FPS capture. `mss` provides a robust, zero-dependency cross-platform fallback. |
| **Audio Engine** | `sounddevice` | `pyaudio` | Seamless WASAPI loopback support on Windows to record pristine system audio alongside microphone input with precise buffer callbacks. |
| **Encoding Pipeline**| Direct `FFmpeg` Process | `PyAV` | Streaming raw video and audio frames directly into an FFmpeg subprocess `stdin` yields minimal latency, zero memory leaks, and native hardware encoder support. |
| **Hardware Encoders**| `NVENC` (Nvidia) / `QSV` (Intel) / `AMF` (AMD) | `libx264` (CPU) | Offloads video compression to GPU silicon, preventing frame drops and game lag during recording. |
| **Input Hooking** | `pynput` | `keyboard` / `mouse` | Low-level event listeners for global key combinations and mouse clicks. |

---

## 2. High-Performance Video Capture Engine

### 2.1 DXCam (Primary for Windows)
```python
import dxcam

# Initialize DXCam instance targeting primary or selected display output
camera = dxcam.create(device_idx=0, output_idx=0, output_color="BGR")

# Start background capture targeting exact target FPS
camera.start(target_fps=60, video_mode=True)

# Inside worker loop:
frame = camera.get_latest_frame()  # Returns numpy ndarray (H, W, 3) in BGR format
```

### 2.2 MSS (Fallback / Region Capture)
```python
import mss
import numpy as np

with mss.mss() as sct:
    monitor = {"top": top, "left": left, "width": width, "height": height}
    sct_img = sct.grab(monitor)
    # Convert raw BGRA bytes to numpy array
    frame = np.array(sct_img)[:, :, :3]  # Strip alpha -> BGR
```

> [!IMPORTANT]
> **Even Dimension Constraint**: H.264 / H.265 codecs require frame width and height to be divisible by 2.
> If the user selects a region of `1023 x 751`, the capture engine must automatically pad or crop the bounding box to `1024 x 752` before sending bytes to FFmpeg:
> `width = width + (width % 2)`
> `height = height + (height % 2)`

---

## 3. Audio Capture & WASAPI Loopback Engine

### 3.1 Device Discovery (System Audio + Microphone)
```python
import sounddevice as sd

# Find default WASAPI loopback device for system sound
devices = sd.query_devices()
hostapis = sd.query_hostapis()
wasapi_api_idx = next(i for i, api in enumerate(hostapis) if "WASAPI" in api["name"])

system_loopback_device = None
for idx, dev in enumerate(devices):
    if dev["hostapi"] == wasapi_api_idx and dev["max_input_channels"] > 0:
        # Check if device is a loopback endpoint
        if "loopback" in dev["name"].lower() or dev.get("is_loopback", False):
            system_loopback_device = idx
            break
```

### 3.2 Concurrent Audio Streaming & Mixing
```python
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 48000
CHANNELS = 2

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio Buffer Warning: {status}")
    # Normalize and convert to 16-bit PCM
    pcm_data = (indata * 32767).astype(np.int16).tobytes()
    audio_queue.put(pcm_data)

# Open audio input stream
stream = sd.RawInputStream(
    samplerate=SAMPLE_RATE,
    blocksize=1024,
    device=system_loopback_device,
    channels=CHANNELS,
    dtype='float32',
    callback=audio_callback
)
```

---

## 4. Hardware-Accelerated FFmpeg Subprocess Pipeline

### 4.1 Automated GPU Hardware Acceleration Detection
The application probes available FFmpeg encoders on startup by running `ffmpeg -encoders` and selects the best available engine:

1. **NVIDIA GPU**: `h264_nvenc` (Options: `-preset p4 -rc vbr -cq 23 -b:v 5M`)
2. **Intel QuickSync**: `h264_qsv` (Options: `-preset medium -global_quality 23`)
3. **AMD Radeon**: `h264_amf` (Options: `-quality balanced -rc cbr`)
4. **Software CPU**: `libx264` (Options: `-preset ultrafast -crf 23 -tune zerolatency`)

### 4.2 FFmpeg Subprocess Pipe Command Structure

To achieve real-time synchronized recording without temporary intermediate files, we spawn an FFmpeg subprocess with **two stdin pipes** (or a named pipe / socket / multi-input):

```python
import subprocess

ffmpeg_cmd = [
    "ffmpeg",
    "-y",  # Overwrite output file
    # Video input stream (Pipe 0 / stdin)
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{width}x{height}",
    "-r", str(fps),
    "-i", "-",  # Video frames from stdin
    # Audio input stream (named pipe or separate input)
    "-f", "s16le",
    "-ar", "48000",
    "-ac", "2",
    "-i", audio_pipe_path,  # Audio from local FIFO / named pipe or combined muxer
    # Video Encoding settings
    "-c:v", selected_video_codec,
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",  # Web-optimized MP4 header
    output_filepath
]

process = subprocess.Popen(
    ffmpeg_cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE
)
```

---

## 5. GIF and Secondary Formats Conversion

For lightweight animated GIF exports from recorded MP4s, generate an optimized palette using the two-pass FFmpeg palettegen filter to avoid banding:

```bash
ffmpeg -i input.mp4 -vf "fps=15,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
```
