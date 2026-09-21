"""
Global hotkey listener service using pynput.
"""

from typing import Callable, Dict
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard


class HotkeyService(QObject):
    """Listens for global shortcuts in background."""

    record_stop_triggered = pyqtSignal()
    pause_resume_triggered = pyqtSignal()
    annotate_triggered = pyqtSignal()
    screenshot_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._listener: keyboard.GlobalHotKeys = None

    def start(self, hotkeys_map: Dict[str, str] = None):
        """Register and start hotkey listeners."""
        self.stop()

        if hotkeys_map is None:
            hotkeys_map = {
                "record_stop": "F9",
                "pause_resume": "F10",
                "annotate": "F8",
                "screenshot": "F11",
            }

        def to_pynput_str(key: str) -> str:
            k = key.strip().lower()
            if k.startswith("f") and k[1:].isdigit():
                return f"<{k}>"
            if "+" in k:
                parts = [f"<{p.strip()}>" if len(p.strip()) > 1 else p.strip() for p in k.split("+")]
                return "+".join(parts)
            return f"<{k}>" if len(k) > 1 else k

        bindings = {}
        if "record_stop" in hotkeys_map:
            bindings[to_pynput_str(hotkeys_map["record_stop"])] = self.record_stop_triggered.emit
        if "pause_resume" in hotkeys_map:
            bindings[to_pynput_str(hotkeys_map["pause_resume"])] = self.pause_resume_triggered.emit
        if "annotate" in hotkeys_map:
            bindings[to_pynput_str(hotkeys_map["annotate"])] = self.annotate_triggered.emit
        if "screenshot" in hotkeys_map:
            bindings[to_pynput_str(hotkeys_map["screenshot"])] = self.screenshot_triggered.emit

        try:
            self._listener = keyboard.GlobalHotKeys(bindings)
            self._listener.start()
        except Exception as e:
            print(f"[HotkeyService] Error registering hotkeys: {e}")

    def stop(self):
        """Stop hotkey listener thread."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


hotkey_service = HotkeyService()
