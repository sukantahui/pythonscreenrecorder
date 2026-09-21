# 05. Testing, Verification & Quality Assurance Protocol

This document provides a rigorous testing matrix and verification procedures that the implementing agent must execute to ensure stability, performance, and cross-hardware reliability.

---

## 1. Quality Assurance Verification Matrix

| Test ID | Test Scenario | Acceptance Criteria | Pass / Fail Check |
| :--- | :--- | :--- | :--- |
| **TEST-01** | **Audio / Video Sync Over Time** | Record 10 minutes of a YouTube video with rapid speech/music. The resulting MP4 must have **< 50ms A/V offset** at minute 1 and minute 10. | [ ] |
| **TEST-02** | **High-DPI Scaling on Windows** | Record on a 125% or 150% scaled display. Bounding box coordinates must match exact on-screen visual pixels without clipping or offset. | [ ] |
| **TEST-03** | **Hardware Acceleration Fallback** | If NVENC is unavailable (or on Intel/AMD systems), the recorder gracefully falls back to QSV/AMF or CPU `libx264` with zero crashes. | [ ] |
| **TEST-04** | **Sudden Process Interruption** | Simulate sudden app closing / `SIGINT` during active recording. Output video must be playable without corrupt header errors (`moov atom not found`). | [ ] |
| **TEST-05** | **Memory Leak Detection** | Continuous 15-minute recording must maintain flat RAM utilization (< 250 MB RSS) with no queue backlog buildup. | [ ] |
| **TEST-06** | **Global Hotkey Interception** | `F9` (Start/Stop) and `F10` (Pause) must trigger instantly even when another full-screen game or application is in active focus. | [ ] |
| **TEST-07** | **Even Dimension Normalization** | Selecting an odd region dimension (e.g., `801 x 603`) is auto-padded to `802 x 604` and encodes cleanly without FFmpeg codec errors. | [ ] |

---

## 2. Automated Diagnostic Scripts

### 2.1 Audio Device & WASAPI Loopback Probe Script
Create `scripts/diagnose_audio.py` to verify loopback device availability on the host:
```python
import sounddevice as sd

print("=== SOUND DEVICE DIAGNOSTIC ===")
devices = sd.query_devices()
for idx, dev in enumerate(devices):
    print(f"[{idx}] {dev['name']} (HostAPI: {dev['hostapi']}, Inputs: {dev['max_input_channels']}, Outputs: {dev['max_output_channels']})")
```

### 2.2 Video Capture FPS & Latency Benchmark Script
Create `scripts/benchmark_capture.py` to test capture throughput:
```python
import time
import mss
import numpy as np

with mss.mss() as sct:
    monitor = sct.monitors[1]
    frames = 0
    start = time.perf_counter()
    
    while frames < 300:
        img = np.array(sct.grab(monitor))
        frames += 1
        
    duration = time.perf_counter() - start
    print(f"Captured {frames} frames in {duration:.2f}s ({frames/duration:.1f} FPS)")
```

---

## 3. Edge Cases & Resilience Protocols

1. **Monitor Disconnect / Resolution Change During Recording**:
   - Catch DirectX / MSS display handle invalidation exceptions.
   - Gracefully pause recording, re-initialize capture handle, and notify user via tray notification.

2. **Microphone Unplugged Mid-Recording**:
   - If the microphone stream drops, continue recording system audio and pad the missing mic channel with silence rather than crashing the video muxer.

3. **Disk Space Low Warning**:
   - Check available disk space on target partition using `psutil.disk_usage()`.
   - If free disk space drops below **500 MB**, automatically stop recording and save the file safely.
