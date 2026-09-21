"""
Audio capture worker using SoundDevice for WASAPI Loopback (System Audio) and Microphone.
"""

import threading
import time
import queue
from typing import Optional, List, Dict, Any, Callable
import numpy as np
import sounddevice as sd
from src.config.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE


class AudioCaptureWorker:
    """Captures and mixes system loopback audio and microphone audio."""

    def __init__(
        self,
        audio_queue: queue.Queue,
        record_system_audio: bool = True,
        record_mic: bool = False,
        mic_device_id: Optional[int] = None,
        system_volume: float = 1.0,
        mic_volume: float = 1.0,
        level_callback: Optional[Callable[[float, float], None]] = None,
    ):
        self.audio_queue = audio_queue
        self.record_system_audio = record_system_audio
        self.record_mic = record_mic
        self.mic_device_id = mic_device_id
        self.system_volume = system_volume
        self.mic_volume = mic_volume
        self.level_callback = level_callback

        self._running = False
        self._paused = False

        self._system_stream: Optional[sd.InputStream] = None
        self._mic_stream: Optional[sd.InputStream] = None

        self._latest_system_level = 0.0
        self._latest_mic_level = 0.0

        # Sub-queues for audio blending
        self._sys_chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._mic_chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._mixer_thread: Optional[threading.Thread] = None

    @staticmethod
    def get_audio_devices() -> Dict[str, List[Dict[str, Any]]]:
        """Discover available playback (loopback) and recording devices."""
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        loopback_devices = []
        input_devices = []

        for idx, dev in enumerate(devices):
            api_name = hostapis[dev["hostapi"]]["name"]
            dev_info = {
                "id": idx,
                "name": f"{dev['name']} ({api_name})",
                "raw_name": dev["name"],
                "api": api_name,
                "max_inputs": dev["max_input_channels"],
                "max_outputs": dev["max_output_channels"],
                "default_samplerate": dev["default_samplerate"],
            }

            # Loopback candidate on Windows WASAPI
            if "WASAPI" in api_name:
                if dev.get("is_loopback", False) or "loopback" in dev["name"].lower() or dev["max_output_channels"] > 0:
                    loopback_devices.append(dev_info)

            # Microphone candidate
            if dev["max_input_channels"] > 0:
                input_devices.append(dev_info)

        return {"loopback": loopback_devices, "microphones": input_devices}

    @staticmethod
    def get_default_loopback_device() -> Optional[int]:
        """Find default WASAPI loopback device ID."""
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        wasapi_id = None
        for i, api in enumerate(hostapis):
            if "WASAPI" in api["name"]:
                wasapi_id = i
                break

        if wasapi_id is None:
            return None

        for idx, dev in enumerate(devices):
            if dev["hostapi"] == wasapi_id and (dev.get("is_loopback", False) or "loopback" in dev["name"].lower()):
                return idx

        # Fallback to default output on WASAPI
        try:
            default_out = sd.default.device[1]
            if default_out is not None and default_out >= 0:
                return default_out
        except Exception:
            pass

        return None

    def _system_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        # Calculate level for VU meter
        rms = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0.0
        self._latest_system_level = min(float(rms * 3.0), 1.0)

        # Scale volume
        scaled = indata * self.system_volume
        try:
            self._sys_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            pass

    def _mic_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        rms = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0.0
        self._latest_mic_level = min(float(rms * 4.0), 1.0)

        scaled = indata * self.mic_volume
        try:
            self._mic_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            pass

    def _mixer_loop(self):
        """Pulls audio chunks, mixes system + mic, and enqueues to main audio queue."""
        silence_chunk = np.zeros((AUDIO_CHUNK_SIZE, AUDIO_CHANNELS), dtype=np.float32)

        while self._running:
            if self._paused:
                time.sleep(0.02)
                continue

            sys_chunk = None
            mic_chunk = None

            if self.record_system_audio:
                try:
                    sys_chunk = self._sys_chunk_queue.get(timeout=0.04)
                except queue.Empty:
                    pass

            if self.record_mic:
                try:
                    mic_chunk = self._mic_chunk_queue.get(timeout=0.04)
                except queue.Empty:
                    pass

            # If neither has data, sleep briefly
            if sys_chunk is None and mic_chunk is None:
                time.sleep(0.01)
                continue

            # Ensure proper channel shape (Stereo)
            if sys_chunk is not None:
                if sys_chunk.ndim == 1:
                    sys_chunk = np.column_stack((sys_chunk, sys_chunk))
                elif sys_chunk.shape[1] == 1:
                    sys_chunk = np.repeat(sys_chunk, 2, axis=1)
            else:
                sys_chunk = np.zeros_like(silence_chunk)

            if mic_chunk is not None:
                if mic_chunk.ndim == 1:
                    mic_chunk = np.column_stack((mic_chunk, mic_chunk))
                elif mic_chunk.shape[1] == 1:
                    mic_chunk = np.repeat(mic_chunk, 2, axis=1)
            else:
                mic_chunk = np.zeros_like(silence_chunk)

            # Match lengths
            min_len = min(len(sys_chunk), len(mic_chunk)) if (len(sys_chunk) > 0 and len(mic_chunk) > 0) else max(len(sys_chunk), len(mic_chunk))
            if min_len == 0:
                continue

            sys_chunk = sys_chunk[:min_len]
            mic_chunk = mic_chunk[:min_len]

            # Blend signals and clip
            mixed = np.clip(sys_chunk + mic_chunk, -1.0, 1.0)
            pcm_bytes = (mixed * 32767).astype(np.int16).tobytes()

            try:
                self.audio_queue.put_nowait(pcm_bytes)
            except queue.Full:
                pass

            if self.level_callback:
                try:
                    self.level_callback(self._latest_system_level, self._latest_mic_level)
                except Exception:
                    pass

    def start(self):
        """Start audio streams and mixer thread."""
        self._running = True
        self._paused = False

        if self.record_system_audio:
            loopback_dev = self.get_default_loopback_device()
            try:
                # On Windows, extra_settings can request loopback
                self._system_stream = sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=AUDIO_CHANNELS,
                    blocksize=AUDIO_CHUNK_SIZE,
                    dtype="float32",
                    device=loopback_dev,
                    callback=self._system_audio_callback,
                )
                self._system_stream.start()
            except Exception as e:
                print(f"[AudioCaptureWorker] System loopback stream error: {e}")

        if self.record_mic:
            try:
                self._mic_stream = sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=1,  # Most mics are mono, will be upmixed to stereo
                    blocksize=AUDIO_CHUNK_SIZE,
                    dtype="float32",
                    device=self.mic_device_id,
                    callback=self._mic_audio_callback,
                )
                self._mic_stream.start()
            except Exception as e:
                print(f"[AudioCaptureWorker] Microphone stream error: {e}")

        self._mixer_thread = threading.Thread(target=self._mixer_loop, daemon=True, name="AudioMixerThread")
        self._mixer_thread.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        """Stop all streams."""
        self._running = False
        if self._system_stream:
            try:
                self._system_stream.stop()
                self._system_stream.close()
            except Exception:
                pass
            self._system_stream = None

        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None
