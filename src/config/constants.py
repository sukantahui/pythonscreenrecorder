"""
Application-wide constants, default configurations, and theme tokens.
"""

from pathlib import Path
import os

# Application & Organization Metadata
APP_NAME = "CNAT Screen Recorder"
APP_VERSION = "1.0.0"
DEVELOPER_NAME = "Sukanta Hui"
COMPANY_NAME = "Coder & AccoTax"
COMPANY_SHORT = "CNAT"
COMPANY_WEBSITE = "https://www.codernaccotax.co.in"
COMPANY_PHONE = "7003756860"
APP_AUTHOR = f"{DEVELOPER_NAME} ({COMPANY_NAME})"
COPYRIGHT_TEXT = f"© 2026 {COMPANY_NAME} ({COMPANY_SHORT}). All rights reserved."

# Directories
DEFAULT_OUTPUT_DIR = str(Path.home() / "Videos" / "CNATRecordings")
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
    "4K Ultra HD (3840x2160)": (3840, 2160),
    "2K QHD (2560x1440)": (2560, 1440),
    "1080p Full HD (1920x1080)": (1920, 1080),
    "720p HD (1280x720)": (1280, 720),
    "Native Display (Original)": None,
    "TikTok / Shorts (9:16)": (1080, 1920),
    "Square (1:1)": (1080, 1080),
}
DEFAULT_RESOLUTION = "4K Ultra HD (3840x2160)"

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

# Quality Presets (Bitrates & CRF)
QUALITY_PROFILES = {
    "4K Ultra Master (60 Mbps)": {"video_bitrate": "60M", "crf": 14, "preset": "fast"},
    "4K High Quality (40 Mbps)": {"video_bitrate": "40M", "crf": 17, "preset": "fast"},
    "2K QHD (25 Mbps)": {"video_bitrate": "25M", "crf": 19, "preset": "medium"},
    "1080p High (15 Mbps)": {"video_bitrate": "15M", "crf": 21, "preset": "medium"},
    "Standard (8 Mbps)": {"video_bitrate": "8M", "crf": 23, "preset": "fast"},
}
DEFAULT_QUALITY = "4K Ultra Master (60 Mbps)"

# Audio Constants
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 2
AUDIO_CHUNK_SIZE = 1024
AUDIO_BITRATE = "192k"

# Default Hotkeys
HOTKEY_RECORD = "F9"
HOTKEY_PAUSE = "F10"
HOTKEY_ANNOTATE = "F8"
HOTKEY_WEBCAM = "F7"
HOTKEY_MIC_MUTE = "F6"
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
