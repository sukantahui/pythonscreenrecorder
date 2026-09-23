"""
Audio capture worker using SoundDevice for WASAPI Loopback (System Audio),
Microphone, and Webcam Audio input.
"""

import threading
import time
import queue
from typing import Optional, List, Dict, Any, Callable
import numpy as np
import sounddevice as sd
from src.config.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_SIZE


class AudioCaptureWorker:
    """Captures and mixes system loopback audio, microphone audio, and webcam audio."""

    def __init__(
        self,
        audio_queue: queue.Queue,
        record_system_audio: bool = True,
        record_mic: bool = False,
        mic_device_id: Optional[int] = None,
        record_webcam_audio: bool = False,
        webcam_audio_device_id: Optional[int] = None,
        system_volume: float = 1.0,
        mic_volume: float = 1.0,
        webcam_volume: float = 1.0,
        level_callback: Optional[Callable[[float, float], None]] = None,
    ):
        self.audio_queue = audio_queue
        self.record_system_audio = record_system_audio
        self.record_mic = record_mic
        self.mic_device_id = mic_device_id
        self.record_webcam_audio = record_webcam_audio
        self.webcam_audio_device_id = webcam_audio_device_id
        self.system_volume = system_volume
        self.mic_volume = mic_volume
        self.webcam_volume = webcam_volume
        self.level_callback = level_callback

        self._running = False
        self._paused = False

        self._system_stream: Optional[sd.InputStream] = None
        self._mic_stream: Optional[sd.InputStream] = None
        self._webcam_stream: Optional[sd.InputStream] = None

        self._latest_system_level = 0.0
        self._latest_mic_level = 0.0
        self._latest_webcam_level = 0.0

        # Sub-queues for audio blending
        self._sys_chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._mic_chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._cam_chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._mixer_thread: Optional[threading.Thread] = None

    @staticmethod
    def is_webcam_audio_device(name: str) -> bool:
        """Check if an audio device name corresponds to a webcam or virtual camera."""
        keywords = ("webcam", "camera", "cam", "iriun", "droidcam", "c920", "c922", "brio", "streamcam", "logitech hd")
        lower = name.lower()
        return any(k in lower for k in keywords)

    @classmethod
    def get_audio_devices(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Discover available playback (loopback), microphone, and webcam recording devices."""
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()

        loopback_devices = []
        input_devices = []
        webcam_devices = []

        for idx, dev in enumerate(devices):
            api_name = hostapis[dev["hostapi"]]["name"]
            is_cam = cls.is_webcam_audio_device(dev["name"])
            dev_info = {
                "id": idx,
                "name": f"{dev['name']} ({api_name})",
                "raw_name": dev["name"],
                "api": api_name,
                "is_webcam": is_cam,
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
                if is_cam:
                    webcam_devices.append(dev_info)

        return {
            "loopback": loopback_devices,
            "microphones": input_devices,
            "webcam_microphones": webcam_devices,
        }

    @classmethod
    def match_webcam_audio(cls, camera_name: str = "") -> Optional[int]:
        """Find the best matching audio input device ID for a given webcam name."""
        devices = cls.get_audio_devices().get("microphones", [])
        if not devices:
            return None

        clean_cam = camera_name.lower().replace("camera", "").replace("webcam", "").strip()

        # 1. Match with active camera name or webcam keyword
        candidates = []
        for dev in devices:
            raw_name = dev.get("raw_name", dev["name"]).lower()
            if clean_cam and clean_cam in raw_name:
                candidates.append(dev)
            elif cls.is_webcam_audio_device(raw_name):
                candidates.append(dev)

        # Prioritize Iriun candidates if present
        iriun_candidates = [c for c in candidates if any(k in c["name"].lower() for k in ("iriun", "irium"))]
        target_list = iriun_candidates if iriun_candidates else candidates

        # Prefer WASAPI
        for c in target_list:
            if "wasapi" in c.get("api", "").lower():
                return c["id"]

        return target_list[0]["id"]

    @classmethod
    def get_preferred_mic_device(cls, prefer_iriun: bool = True) -> Optional[int]:
        """Find the preferred default microphone device, prioritizing Iriun Webcam."""
        devices = cls.get_audio_devices().get("microphones", [])
        if not devices:
            return None

        if prefer_iriun:
            # 1. Search for Iriun on WASAPI
            for dev in devices:
                name = dev["name"].lower()
                if any(k in name for k in ("iriun", "irium")) and "wasapi" in dev.get("api", "").lower():
                    return dev["id"]
            # 2. Search for Iriun on any host API
            for dev in devices:
                name = dev["name"].lower()
                if any(k in name for k in ("iriun", "irium")):
                    return dev["id"]

        # Fallback to system default input
        try:
            default_in = sd.default.device[0]
            if default_in is not None and default_in >= 0:
                return default_in
        except Exception:
            pass

        return devices[0]["id"] if devices else None

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
        rms = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0.0
        self._latest_system_level = min(float(rms * 3.0), 1.0)

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

    def _webcam_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        rms = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0.0
        self._latest_webcam_level = min(float(rms * 4.0), 1.0)

        scaled = indata * self.webcam_volume
        try:
            self._cam_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            pass

    def _mixer_loop(self):
        """Pulls audio chunks, mixes system + mic + webcam, and enqueues to main audio queue."""
        def _to_stereo(chunk):
            if chunk is None:
                return None
            if chunk.ndim == 1:
                return np.column_stack((chunk, chunk))
            elif chunk.shape[1] == 1:
                return np.repeat(chunk, 2, axis=1)
            elif chunk.shape[1] > 2:
                return chunk[:, :2]
            return chunk

        while self._running:
            if self._paused:
                time.sleep(0.02)
                continue

            sys_chunk = None
            mic_chunk = None
            cam_chunk = None

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

            if self.record_webcam_audio:
                try:
                    cam_chunk = self._cam_chunk_queue.get(timeout=0.04)
                except queue.Empty:
                    pass

            # Gather active non-empty stereo chunks
            active_chunks = []
            for c in (sys_chunk, mic_chunk, cam_chunk):
                stereo = _to_stereo(c)
                if stereo is not None and len(stereo) > 0:
                    active_chunks.append(stereo)

            if not active_chunks:
                time.sleep(0.01)
                continue

            target_len = min(len(c) for c in active_chunks)
            if target_len == 0:
                continue

            mixed = np.zeros((target_len, AUDIO_CHANNELS), dtype=np.float32)
            for c in active_chunks:
                mixed += c[:target_len]

            mixed = np.clip(mixed, -1.0, 1.0)
            pcm_bytes = (mixed * 32767).astype(np.int16).tobytes()

            try:
                self.audio_queue.put_nowait(pcm_bytes)
            except queue.Full:
                pass

            if self.level_callback:
                try:
                    combined_mic = max(self._latest_mic_level, self._latest_webcam_level)
                    self.level_callback(self._latest_system_level, combined_mic)
                except Exception:
                    pass

    def start(self):
        """Start audio streams and mixer thread."""
        self._running = True
        self._paused = False

        if self.record_system_audio:
            loopback_dev = self.get_default_loopback_device()
            try:
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
                channels = 1
                if self.mic_device_id is not None:
                    try:
                        dev_info = sd.query_devices(self.mic_device_id)
                        channels = min(max(int(dev_info.get("max_input_channels", 1)), 1), 2)
                    except Exception:
                        pass

                self._mic_stream = sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=channels,
                    blocksize=AUDIO_CHUNK_SIZE,
                    dtype="float32",
                    device=self.mic_device_id,
                    callback=self._mic_audio_callback,
                )
                self._mic_stream.start()
            except Exception as e:
                print(f"[AudioCaptureWorker] Microphone stream error: {e}")

        if self.record_webcam_audio and self.webcam_audio_device_id is not None:
            try:
                channels = 1
                try:
                    dev_info = sd.query_devices(self.webcam_audio_device_id)
                    channels = min(max(int(dev_info.get("max_input_channels", 1)), 1), 2)
                except Exception:
                    pass

                self._webcam_stream = sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=channels,
                    blocksize=AUDIO_CHUNK_SIZE,
                    dtype="float32",
                    device=self.webcam_audio_device_id,
                    callback=self._webcam_audio_callback,
                )
                self._webcam_stream.start()
            except Exception as e:
                print(f"[AudioCaptureWorker] Webcam audio stream error: {e}")

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

        if self._webcam_stream:
            try:
                self._webcam_stream.stop()
                self._webcam_stream.close()
            except Exception:
                pass
            self._webcam_stream = None
