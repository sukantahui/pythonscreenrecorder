"""
Real-time audio noise reduction processor using pure NumPy.
Applies frequency-domain spectral subtraction, low-frequency rumble filtering,
and smooth downward expansion (noise gating) without external heavy dependencies.
"""

import threading
import numpy as np


class RealtimeNoiseReducer:
    """Real-time voice noise suppressor and background noise gate."""

    def __init__(self, sample_rate: int = 44100, strength: float = 0.0):
        """
        Args:
            sample_rate: Audio sampling frequency in Hz.
            strength: Suppression strength from 0.0 (off/bypass) to 1.0 (maximum).
        """
        self.sample_rate = sample_rate
        self.strength = float(np.clip(strength, 0.0, 1.0))
        self.noise_floor = None
        self.gain_smooth = 1.0
        self._cached_n = 0
        self._hp_gain = None
        self._lock = threading.Lock()

    def set_strength(self, strength: float):
        """Update noise reduction strength (0.0 to 1.0). Thread-safe."""
        with self._lock:
            self.strength = float(np.clip(strength, 0.0, 1.0))
            if self.strength <= 0.01:
                self.noise_floor = None
                self.gain_smooth = 1.0

    def process(self, chunk: np.ndarray) -> np.ndarray:
        """
        Process an incoming audio chunk and return the noise-reduced chunk.
        Supports 1D mono, 2D single-channel, and 2D multi-channel arrays.
        """
        if chunk is None or len(chunk) == 0:
            return chunk

        with self._lock:
            curr_strength = self.strength

        # Bypass when strength is zero
        if curr_strength <= 0.01:
            return chunk

        orig_shape = chunk.shape
        ndim = chunk.ndim

        if ndim == 2 and orig_shape[1] > 1:
            out = np.empty_like(chunk)
            for ch in range(orig_shape[1]):
                out[:, ch] = self._process_mono(chunk[:, ch], curr_strength)
            return out
        elif ndim == 2:
            return self._process_mono(chunk[:, 0], curr_strength)[:, np.newaxis]
        else:
            return self._process_mono(chunk, curr_strength)

    def _process_mono(self, signal: np.ndarray, strength: float) -> np.ndarray:
        n = len(signal)
        if n < 16:
            return signal

        # Prepare cached high-pass filter curve (attenuate sub-80Hz rumble)
        if n != self._cached_n:
            self._cached_n = n
            freqs = np.fft.rfftfreq(n, 1.0 / self.sample_rate)
            self._hp_gain = np.clip((freqs / 80.0) ** 2, 0.0, 1.0).astype(np.float32)

        # 1. Frequency Analysis (RFFT)
        spec = np.fft.rfft(signal)
        mag = np.abs(spec)
        phase = np.angle(spec)

        # Attenuate sub-80Hz low rumble based on filter curve
        if self._hp_gain is not None:
            mag = mag * (1.0 - strength * (1.0 - self._hp_gain))

        # 2. Adaptive Noise Floor Tracking
        if self.noise_floor is None or len(self.noise_floor) != len(mag):
            self.noise_floor = mag.copy()
        else:
            # Fast tracking on dips (quicker fall when silent), slow rise during speech
            self.noise_floor = np.where(
                mag < self.noise_floor,
                0.80 * self.noise_floor + 0.20 * mag,
                0.998 * self.noise_floor + 0.002 * mag,
            )

        # 3. Spectral Subtraction with over-subtraction and musical noise avoidance floor
        sub_factor = 1.0 + strength * 2.5
        floor_margin = max(0.02, 0.15 * (1.0 - strength))
        clean_mag = np.maximum(mag - sub_factor * self.noise_floor, floor_margin * mag)

        # 4. Synthesize Cleaned Waveform (IRFFT)
        clean_spec = clean_mag * np.exp(1j * phase)
        cleaned = np.fft.irfft(clean_spec, n=n).astype(np.float32)

        # 5. Downward Expander (Soft Noise Gate for room silence between words)
        rms = np.sqrt(np.mean(cleaned**2) + 1e-12)
        # Threshold scales from -52 dB (subtle) to -30 dB (aggressive)
        threshold_db = -52.0 + strength * 22.0
        thresh_linear = 10.0 ** (threshold_db / 20.0)

        if rms < thresh_linear:
            ratio = (rms / thresh_linear) ** (1.0 + strength * 2.0)
            target_gain = float(np.clip(ratio, 0.01, 1.0))
        else:
            target_gain = 1.0

        # Fast attack (0.85) to preserve voice consonants, smooth release (0.08) for natural decay
        smooth_rate = 0.85 if target_gain > self.gain_smooth else 0.08
        self.gain_smooth += smooth_rate * (target_gain - self.gain_smooth)

        out_signal = cleaned * self.gain_smooth

        # 6. Dry/Wet Blending based on slider strength
        return (1.0 - strength) * signal + strength * out_signal
