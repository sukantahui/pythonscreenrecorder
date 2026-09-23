"""
Persistent configuration manager using JSON.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from src.config.constants import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION,
    DEFAULT_QUALITY,
    FORMAT_MP4,
    HOTKEY_RECORD,
    HOTKEY_PAUSE,
    HOTKEY_ANNOTATE,
    HOTKEY_WEBCAM,
    HOTKEY_WEBCAM_FULLSCREEN,
    HOTKEY_MIC_MUTE,
    HOTKEY_SCREENSHOT,
)


class SettingsManager:
    """Manages application settings persistence."""

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "output_dir": DEFAULT_OUTPUT_DIR,
        "fps": DEFAULT_FPS,
        "format": FORMAT_MP4,
        "resolution": DEFAULT_RESOLUTION,
        "quality_profile": DEFAULT_QUALITY,
        "encoder": "auto",
        "record_system_audio": True,
        "system_audio_volume": 100,
        "record_microphone": False,
        "mic_device_id": None,
        "mic_volume": 100,
        "record_webcam_audio": False,
        "webcam_audio_device_id": None,
        "webcam_audio_volume": 100,
        "noise_reduction": 0,
        "webcam_enabled": False,
        "webcam_device_id": 0,
        "webcam_device_name": "",
        "webcam_shape": "circle",  # circle, rounded, rect
        "webcam_size": 220,
        "webcam_mirrored": True,
        "show_cursor": True,
        "highlight_clicks": True,
        "show_keystrokes": False,
        "countdown_seconds": 3,
        "minimize_to_tray_on_record": True,
        "hotkeys": {
            "record_stop": HOTKEY_RECORD,
            "pause_resume": HOTKEY_PAUSE,
            "annotate": HOTKEY_ANNOTATE,
            "toggle_webcam": HOTKEY_WEBCAM,
            "toggle_webcam_fullscreen": HOTKEY_WEBCAM_FULLSCREEN,
            "mute_mic": HOTKEY_MIC_MUTE,
            "screenshot": HOTKEY_SCREENSHOT,
        },
    }

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_dir = Path.home() / ".cnat_screen_recorder"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "settings.json"
        else:
            self.config_file = Path(config_path)

        self.settings: Dict[str, Any] = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        """Load settings from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[SettingsManager] Error loading settings: {e}")

    def save(self) -> None:
        """Persist settings to JSON file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[SettingsManager] Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Update a setting value and save."""
        self.settings[key] = value
        self.save()


# Singleton instance
settings = SettingsManager()
