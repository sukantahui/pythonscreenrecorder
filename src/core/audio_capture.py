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
from src.core.noise_reducer import RealtimeNoiseReducer


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
        noise_reduction: float = 0.0,
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
        self.noise_reduction = noise_reduction
        self.level_callback = level_callback

        self._mic_noise_reducer = RealtimeNoiseReducer(sample_rate=AUDIO_SAMPLE_RATE, strength=self.noise_reduction)
        self._cam_noise_reducer = RealtimeNoiseReducer(sample_rate=AUDIO_SAMPLE_RATE, strength=self.noise_reduction)

        self._running = False
        self._paused = False
        self._recording_active = False

        self._system_stream: Optional[sd.InputStream] = None
        self._mic_stream: Optional[sd.InputStream] = None
        self._webcam_stream: Optional[sd.InputStream] = None
        self._wasapi_loopback_active = False
        self._wasapi_thread: Optional[threading.Thread] = None

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

            # Exclude raw Windows WDM-KS devices which don't support PortAudio InputStream blocking API
            if "WDM-KS" in api_name:
                continue

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

    def _wasapi_loopback_loop(self):
        """Dedicated WASAPI loopback capture thread using PyAudioWPatch on Windows."""
        p = None
        stream = None
        try:
            import pyaudiowpatch as pyaudio
            p = pyaudio.PyAudio()
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                if not default_speakers.get("isLoopbackDevice", False):
                    for loopback in p.get_loopback_device_info_generator():
                        if default_speakers["name"] in loopback["name"]:
                            default_speakers = loopback
                            break

                channels = min(2, max(1, int(default_speakers.get("maxInputChannels", 2))))
                dev_rate = int(default_speakers.get("defaultSampleRate", AUDIO_SAMPLE_RATE))

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=dev_rate,
                    input=True,
                    input_device_index=default_speakers["index"],
                    frames_per_buffer=AUDIO_CHUNK_SIZE,
                )
                self._wasapi_loopback_active = True
                print(f"[AudioCaptureWorker] System WASAPI loopback started on: {default_speakers.get('name')} ({dev_rate} Hz, ch={channels})")

                while self._running:
                    if self._paused:
                        time.sleep(0.02)
                        continue

                    try:
                        data = stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                    except Exception:
                        time.sleep(0.005)
                        continue

                    if not data:
                        time.sleep(0.005)
                        continue

                    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    if channels == 1:
                        chunk = np.column_stack((samples, samples))
                    else:
                        chunk = samples.reshape(-1, channels)
                        if channels > 2:
                            chunk = chunk[:, :2]

                    if dev_rate != AUDIO_SAMPLE_RATE and len(chunk) > 0:
                        new_len = int(len(chunk) * AUDIO_SAMPLE_RATE / dev_rate)
                        chunk = np.interp(
                            np.linspace(0, len(chunk), new_len, endpoint=False),
                            np.arange(len(chunk)),
                            chunk,
                        )

                    rms = np.sqrt(np.mean(chunk**2)) if len(chunk) > 0 else 0.0
                    self._latest_system_level = min(float(rms * 3.0), 1.0)

                    scaled = chunk * self.system_volume
                    try:
                        self._sys_chunk_queue.put_nowait(scaled)
                    except queue.Full:
                        try:
                            self._sys_chunk_queue.get_nowait()
                            self._sys_chunk_queue.put_nowait(scaled)
                        except Exception:
                            pass

            finally:
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
                if p:
                    try:
                        p.terminate()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[AudioCaptureWorker] System loopback stream error: {e}")
        finally:
            self._wasapi_loopback_active = False

    def _system_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        rms = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0.0
        self._latest_system_level = min(float(rms * 3.0), 1.0)

        scaled = indata * self.system_volume
        try:
            self._sys_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            try:
                self._sys_chunk_queue.get_nowait()
                self._sys_chunk_queue.put_nowait(scaled.copy())
            except Exception:
                pass

    def start_recording(self, start_time: Optional[float] = None):
        """Begin actively pushing audio chunks into recording queue."""
        self._recording_active = True

    def stop_recording(self):
        """Stop pushing audio chunks into recording queue."""
        self._recording_active = False

    def set_noise_reduction(self, strength: float):
        """Update noise reduction strength in real-time (0.0 to 1.0)."""
        self.noise_reduction = float(strength)
        self._mic_noise_reducer.set_strength(self.noise_reduction)
        self._cam_noise_reducer.set_strength(self.noise_reduction)

    def _mic_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        processed = self._mic_noise_reducer.process(indata)
        rms = np.sqrt(np.mean(processed**2)) if len(processed) > 0 else 0.0
        self._latest_mic_level = min(float(rms * 4.0), 1.0)

        scaled = processed * self.mic_volume
        try:
            self._mic_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            try:
                self._mic_chunk_queue.get_nowait()
                self._mic_chunk_queue.put_nowait(scaled.copy())
            except Exception:
                pass

    def _webcam_audio_callback(self, indata, frames, time_info, status):
        if self._paused:
            return
        processed = self._cam_noise_reducer.process(indata)
        rms = np.sqrt(np.mean(processed**2)) if len(processed) > 0 else 0.0
        self._latest_webcam_level = min(float(rms * 4.0), 1.0)

        scaled = processed * self.webcam_volume
        try:
            self._cam_chunk_queue.put_nowait(scaled.copy())
        except queue.Full:
            try:
                self._cam_chunk_queue.get_nowait()
                self._cam_chunk_queue.put_nowait(scaled.copy())
            except Exception:
                pass

    def _mixer_loop(self):
        """Pulls audio chunks, mixes active sources without latency accumulation, and feeds audio queue."""
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

            sys_active = self.record_system_audio and (
                getattr(self, "_wasapi_loopback_active", False) or (self._system_stream is not None)
            )
            mic_active = self.record_mic and (self._mic_stream is not None)
            cam_active = self.record_webcam_audio and (self._webcam_stream is not None)

            # If no audio sources are running, avoid busy-waiting
            if not (sys_active or mic_active or cam_active):
                time.sleep(0.02)
                continue

            sys_chunk = None
            mic_chunk = None
            cam_chunk = None

            # 1. Non-blocking retrieval from active sources
            if sys_active:
                try:
                    sys_chunk = self._sys_chunk_queue.get_nowait()
                except queue.Empty:
                    pass

            if mic_active:
                try:
                    mic_chunk = self._mic_chunk_queue.get_nowait()
                except queue.Empty:
                    pass

            if cam_active:
                try:
                    cam_chunk = self._cam_chunk_queue.get_nowait()
                except queue.Empty:
                    pass

            # 2. Time-alignment: if both system and mic are active but one is temporarily behind,
            # wait a short window (up to 12ms) for the other source before mixing
            if sys_active and mic_active:
                if sys_chunk is not None and mic_chunk is None:
                    try:
                        mic_chunk = self._mic_chunk_queue.get(timeout=0.012)
                    except queue.Empty:
                        pass
                elif mic_chunk is not None and sys_chunk is None:
                    try:
                        sys_chunk = self._sys_chunk_queue.get(timeout=0.012)
                    except queue.Empty:
                        pass

            # If no active chunk is ready yet, yield CPU briefly
            if sys_chunk is None and mic_chunk is None and cam_chunk is None:
                time.sleep(0.004)
                continue

            # 3. Gather active stereo chunks
            active_chunks = []
            for c in (sys_chunk, mic_chunk, cam_chunk):
                stereo = _to_stereo(c)
                if stereo is not None and len(stereo) > 0:
                    active_chunks.append(stereo)

            if not active_chunks:
                continue

            target_len = min(len(c) for c in active_chunks)
            if target_len == 0:
                continue

            mixed = np.zeros((target_len, AUDIO_CHANNELS), dtype=np.float32)
            for c in active_chunks:
                mixed += c[:target_len]

            mixed = np.clip(mixed, -1.0, 1.0)
            pcm_bytes = (mixed * 32767).astype(np.int16).tobytes()

            if self._recording_active:
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

        # 1. System audio capture
        if self.record_system_audio:
            # First try PyAudioWPatch for native Windows WASAPI loopback
            try:
                self._wasapi_thread = threading.Thread(
                    target=self._wasapi_loopback_loop, daemon=True, name="WASAPILoopbackThread"
                )
                self._wasapi_thread.start()
                # Give WASAPI loopback thread a moment to initialize
                time.sleep(0.05)
            except Exception as e:
                print(f"[AudioCaptureWorker] Could not start WASAPI thread: {e}")

            # Fallback to sounddevice loopback if WASAPI loopback didn't activate
            if not getattr(self, "_wasapi_loopback_active", False):
                loopback_dev = self.get_default_loopback_device()
                if loopback_dev is not None:
                    try:
                        d_info = sd.query_devices(loopback_dev)
                        out_ch = int(d_info.get("max_output_channels", 0))
                        in_ch = int(d_info.get("max_input_channels", 0))
                        cand = out_ch if out_ch > 0 else in_ch
                        sys_channels = cand if cand > 0 else AUDIO_CHANNELS
                        for ch in [sys_channels, 2, 1]:
                            try:
                                self._system_stream = sd.InputStream(
                                    samplerate=AUDIO_SAMPLE_RATE,
                                    channels=ch,
                                    blocksize=AUDIO_CHUNK_SIZE,
                                    dtype="float32",
                                    device=loopback_dev,
                                    callback=self._system_audio_callback,
                                )
                                self._system_stream.start()
                                print(f"[AudioCaptureWorker] Fallback sounddevice loopback started on device {loopback_dev}")
                                break
                            except Exception:
                                pass
                    except Exception as e2:
                        print(f"[AudioCaptureWorker] Sounddevice loopback fallback error: {e2}")

        # 2. Microphone capture with device validation and automatic default fallback
        if self.record_mic:
            mic_id = self.mic_device_id
            # Validate device has real input channels
            if mic_id is not None:
                try:
                    dev_info = sd.query_devices(mic_id)
                    if int(dev_info.get("max_input_channels", 0)) <= 0:
                        print(f"[AudioCaptureWorker] Device {mic_id} ({dev_info.get('name')}) is output-only. Falling back to default input.")
                        mic_id = None
                except Exception as e:
                    print(f"[AudioCaptureWorker] Error querying mic {mic_id}: {e}. Falling back to default.")
                    mic_id = None

            device_candidates = [mic_id] if mic_id is not None else [None]
            if mic_id is not None:
                device_candidates.append(None)  # Add default fallback if specific device fails

            opened = False
            for target_dev in device_candidates:
                cand_channels = [1, 2]
                if target_dev is not None:
                    try:
                        d_info = sd.query_devices(target_dev)
                        max_in = int(d_info.get("max_input_channels", 1))
                        cand_channels = [max_in, 1, 2]
                    except Exception:
                        cand_channels = [1, 2]

                channel_list = []
                for ch in cand_channels:
                    if ch not in channel_list and ch > 0:
                        channel_list.append(ch)

                for ch in channel_list:
                    try:
                        self._mic_stream = sd.InputStream(
                            samplerate=AUDIO_SAMPLE_RATE,
                            channels=ch,
                            blocksize=AUDIO_CHUNK_SIZE,
                            dtype="float32",
                            device=target_dev,
                            callback=self._mic_audio_callback,
                        )
                        self._mic_stream.start()
                        opened = True
                        print(f"[AudioCaptureWorker] Microphone started on device {target_dev} (channels={ch})")
                        break
                    except Exception:
                        pass
                if opened:
                    break

            if not opened:
                print(f"[AudioCaptureWorker] Warning: Could not open any microphone stream.")

        # 3. Webcam audio capture with validation
        if self.record_webcam_audio and self.webcam_audio_device_id is not None:
            cam_dev_id = self.webcam_audio_device_id
            try:
                dev_info = sd.query_devices(cam_dev_id)
                if int(dev_info.get("max_input_channels", 0)) <= 0:
                    cam_dev_id = None
            except Exception:
                cam_dev_id = None

            if cam_dev_id is not None:
                cand_channels = [1, 2]
                try:
                    d_info = sd.query_devices(cam_dev_id)
                    max_in = int(d_info.get("max_input_channels", 1))
                    cand_channels = [max_in, 1, 2]
                except Exception:
                    pass

                channel_list = []
                for ch in cand_channels:
                    if ch not in channel_list and ch > 0:
                        channel_list.append(ch)

                opened = False
                for ch in channel_list:
                    try:
                        self._webcam_stream = sd.InputStream(
                            samplerate=AUDIO_SAMPLE_RATE,
                            channels=ch,
                            blocksize=AUDIO_CHUNK_SIZE,
                            dtype="float32",
                            device=cam_dev_id,
                            callback=self._webcam_audio_callback,
                        )
                        self._webcam_stream.start()
                        opened = True
                        print(f"[AudioCaptureWorker] Webcam audio started on device {cam_dev_id} (channels={ch})")
                        break
                    except Exception:
                        pass

                if not opened:
                    print(f"[AudioCaptureWorker] Warning: Could not open webcam audio on device {cam_dev_id}.")

        # 4. Launch mixer thread
        self._mixer_thread = threading.Thread(target=self._mixer_loop, daemon=True, name="AudioMixerThread")
        self._mixer_thread.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        """Stop all streams and mixer thread."""
        self._running = False

        if self._wasapi_thread and self._wasapi_thread.is_alive():
            try:
                self._wasapi_thread.join(timeout=1.0)
            except Exception:
                pass
            self._wasapi_thread = None

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

        if self._mixer_thread and self._mixer_thread.is_alive():
            try:
                self._mixer_thread.join(timeout=1.0)
            except Exception:
                pass
            self._mixer_thread = None

