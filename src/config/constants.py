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

# Locked Aspect Ratio Presets for Social Media & Streaming
ASPECT_RATIO_PRESETS = {
    "freeform": {
        "name": "Freeform (Unlocked)",
        "label": "Freeform",
        "icon": "🔓",
        "ratio": None,
        "desc": "Arbitrary selection",
        "default_size": None,
        "sizes": [],
    },
    "9:16": {
        "name": "Reel / Shorts (9:16)",
        "label": "9:16 Reel",
        "icon": "📱",
        "ratio": (9, 16),
        "desc": "Instagram Reels, YouTube Shorts, TikTok, Stories",
        "default_size": (1080, 1920),
        "sizes": [(1080, 1920), (720, 1280), (540, 960)],
    },
    "16:9": {
        "name": "YouTube / Landscape (16:9)",
        "label": "16:9 YouTube",
        "icon": "🎬",
        "ratio": (16, 9),
        "desc": "YouTube, Facebook Landscape, Twitch",
        "default_size": (1920, 1080),
        "sizes": [(1920, 1080), (1280, 720), (2560, 1440), (3840, 2160)],
    },
    "1:1": {
        "name": "Instagram Post (1:1)",
        "label": "1:1 Square",
        "icon": "📷",
        "ratio": (1, 1),
        "desc": "Instagram Square Post, Facebook Feed",
        "default_size": (1080, 1080),
        "sizes": [(1080, 1080), (720, 720), (600, 600)],
    },
    "4:5": {
        "name": "Instagram Portrait (4:5)",
        "label": "4:5 Portrait",
        "icon": "🖼️",
        "ratio": (4, 5),
        "desc": "Instagram Portrait Feed Post",
        "default_size": (1080, 1350),
        "sizes": [(1080, 1350), (864, 1080), (720, 900)],
    },
    "4:3": {
        "name": "Facebook / Classic (4:3)",
        "label": "4:3 Classic",
        "icon": "📺",
        "ratio": (4, 3),
        "desc": "Classic TV, iPad / Tablets, FB Posts",
        "default_size": (1440, 1080),
        "sizes": [(1440, 1080), (1024, 768), (800, 600)],
    },
    "21:9": {
        "name": "Ultrawide / Cinema (21:9)",
        "label": "21:9 Cinema",
        "icon": "🎞️",
        "ratio": (21, 9),
        "desc": "Ultrawide monitors, Cinematic widescreen",
        "default_size": (2560, 1080),
        "sizes": [(2560, 1080), (3440, 1440)],
    },
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
HOTKEY_WEBCAM_FULLSCREEN = "F4"
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

# Webcam Studio Configuration Presets
WEBCAM_SHAPES = {
    "circle": {"name": "Circle Bubble", "icon": "⭕", "ratio": (1, 1), "desc": "Classic circular floating presenter bubble"},
    "wide": {"name": "16:9 Widescreen", "icon": "🎬", "ratio": (16, 9), "desc": "Standard 16:9 widescreen presenter framing"},
    "rounded": {"name": "Rounded Card", "icon": "🔲", "ratio": (1, 1), "desc": "Modern rounded square presentation card"},
    "portrait": {"name": "9:16 Vertical Reel", "icon": "📱", "ratio": (9, 16), "desc": "Mobile-ready vertical portrait framing"},
    "square": {"name": "Classic Square", "icon": "⬛", "ratio": (1, 1), "desc": "1:1 square framing"},
}

WEBCAM_FILTERS = {
    "normal": {"name": "Natural / Original", "icon": "🌿", "desc": "Pristine camera output without filters"},
    "warm": {"name": "Studio Warm", "icon": "☀️", "desc": "Flattering golden amber skin-tone enhancement"},
    "cool": {"name": "Crisp Cool", "icon": "❄️", "desc": "High-clarity modern tech presentation tone"},
    "bright": {"name": "Brightness Boost", "icon": "💡", "desc": "Enhanced illumination and contrast for dim rooms"},
    "bw": {"name": "Monochrome (B&W)", "icon": "🎞️", "desc": "Classic cinematic black and white"},
    "beauty": {"name": "Soft Skin Smooth", "icon": "✨", "desc": "Subtle bilateral skin smoothing filter"},
}

WEBCAM_BORDER_THEMES = {
    "indigo": {"name": "Cyber Indigo", "color": "#6366F1", "glow": "#818CF8"},
    "cyan": {"name": "Neon Cyan", "color": "#00ADB5", "glow": "#00FFF5"},
    "emerald": {"name": "Studio Emerald", "color": "#10B981", "glow": "#34D399"},
    "sunset": {"name": "Sunset Orange", "color": "#F97316", "glow": "#FB923C"},
    "none": {"name": "Borderless / Clean", "color": "transparent", "glow": "transparent"},
}

