"""
Application-wide constants, default configurations, and theme tokens.
"""

from pathlib import Path
import os

# Application Metadata
APP_NAME = "Apex Screen Recorder"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Antigravity"

# Directories
DEFAULT_OUTPUT_DIR = str(Path.home() / "Videos" / "ApexRecordings")
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

# Capture Modes
MODE_FULLSCREEN = "fullscreen"
MODE_REGION = "region"
MODE_WINDOW = "window"

# FPS Options
FPS_OPTIONS = [30, 60, 120]
DEFAULT_FPS = 60

# Resolution Presets
RESOLUTION_PRESETS = {
    "1080p (Full HD)": (1920, 1080),
    "720p (HD)": (1280, 720),
    "4K (UHD)": (3840, 2160),
    "TikTok / Shorts (9:16)": (1080, 1920),
    "Square (1:1)": (1080, 1080),
}

# Video Codecs & Hardware Acceleration
CODEC_H264_NVENC = "h264_nvenc"
CODEC_H264_QSV = "h264_qsv"
CODEC_H264_AMF = "h264_amf"
CODEC_LIBX264 = "libx264"
CODEC_HEVC_NVENC = "hevc_nvenc"
CODEC_LIBX265 = "libx265"

# Output Formats
FORMAT_MP4 = "mp4"
FORMAT_MKV = "mkv"
FORMAT_WEBM = "webm"
FORMAT_GIF = "gif"

# Quality Presets (Bitrates)
QUALITY_PROFILES = {
    "Ultra (20 Mbps)": {"video_bitrate": "20M", "crf": 18, "preset": "fast"},
    "High (10 Mbps)": {"video_bitrate": "10M", "crf": 21, "preset": "medium"},
    "Standard (5 Mbps)": {"video_bitrate": "5M", "crf": 23, "preset": "fast"},
    "Small File (2.5 Mbps)": {"video_bitrate": "2.5M", "crf": 28, "preset": "veryfast"},
}

# Audio Constants
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 2
AUDIO_CHUNK_SIZE = 1024
AUDIO_BITRATE = "192k"

# Default Hotkeys
HOTKEY_RECORD = "F9"
HOTKEY_PAUSE = "F10"
HOTKEY_ANNOTATE = "F8"
HOTKEY_SCREENSHOT = "F11"

# UI Color Tokens
COLOR_BG_BASE = "#0D0E12"
COLOR_BG_SURFACE = "#161820"
COLOR_BG_ELEVATED = "#20232E"
COLOR_BORDER_SUBTLE = "#2D313F"
COLOR_ACCENT = "#6366F1"
COLOR_ACCENT_HOVER = "#4F46E5"
COLOR_DANGER = "#EF4444"
COLOR_SUCCESS = "#10B981"
COLOR_TEXT_PRIMARY = "#F9FAFB"
COLOR_TEXT_SECONDARY = "#9CA3AF"
