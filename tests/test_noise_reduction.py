"""
Unit tests for Real-time Noise Reduction and Audio Suppression.
"""

import unittest
import numpy as np
from src.core.noise_reducer import RealtimeNoiseReducer
from src.config.settings_manager import settings


class TestNoiseReduction(unittest.TestCase):

    def test_bypass_when_zero(self):
        reducer = RealtimeNoiseReducer(strength=0.0)
        chunk = np.random.randn(1024, 1).astype(np.float32) * 0.05
        processed = reducer.process(chunk)
        np.testing.assert_array_equal(processed, chunk)

    def test_noise_suppression_attenuation(self):
        reducer = RealtimeNoiseReducer(sample_rate=44100, strength=0.7)
        noise = (np.random.randn(1024) * 0.01).astype(np.float32)

        # Feed several chunks to establish noise floor and gate
        for _ in range(30):
            cleaned = reducer.process(noise)

        in_rms = float(np.sqrt(np.mean(noise**2)))
        out_rms = float(np.sqrt(np.mean(cleaned**2)))
        reduction_db = 20 * np.log10(out_rms / in_rms)

        self.assertLess(out_rms, in_rms)
        self.assertLess(reduction_db, -6.0, f"Expected at least 6 dB reduction, got {reduction_db:.1f} dB")

    def test_voice_preservation(self):
        reducer = RealtimeNoiseReducer(sample_rate=44100, strength=0.6)
        noise = (np.random.randn(1024) * 0.005).astype(np.float32)
        # Settle noise floor
        for _ in range(20):
            reducer.process(noise)

        t = np.linspace(0, 1024 / 44100, 1024, endpoint=False)
        voice = (0.2 * np.sin(2 * np.pi * 500 * t) + noise).astype(np.float32)
        cleaned_voice = reducer.process(voice)

        voice_rms = float(np.sqrt(np.mean(voice**2)))
        cleaned_rms = float(np.sqrt(np.mean(cleaned_voice**2)))

        # Cleaned voice should retain significant energy (>50% RMS)
        self.assertGreater(cleaned_rms, voice_rms * 0.5)

    def test_slider_settings_persistence(self):
        settings.set("noise_reduction", 55)
        self.assertEqual(settings.get("noise_reduction"), 55)
        settings.set("noise_reduction", 0)
        self.assertEqual(settings.get("noise_reduction"), 0)


if __name__ == "__main__":
    unittest.main()
