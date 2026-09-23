"""
Generate high-resolution application icon (.ico and .png) for CNAT Screen Recorder.
Creates multi-size icon bundle: 256x256, 128x128, 64x64, 48x48, 32x32, 16x16.
"""

from pathlib import Path
from PIL import Image, ImageDraw

def create_app_icon():
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Outer rounded container with gradient-like luxury look
    # Background squircle
    margin = 24
    corner_radius = 110
    
    # Outer dark glow/rim
    draw.rounded_rectangle(
        [(margin - 4, margin - 4), (size - margin + 4, size - margin + 4)],
        radius=corner_radius + 4,
        fill=(13, 14, 18, 255)
    )
    
    # Primary accent body (Indigo #6366F1 -> #4338CA)
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=corner_radius,
        fill=(99, 102, 241, 255)
    )

    # Inner subtle rim
    draw.rounded_rectangle(
        [(margin + 12, margin + 12), (size - margin - 12, size - margin - 12)],
        radius=corner_radius - 10,
        outline=(165, 180, 252, 120),
        width=4
    )

    # 2. Camera lens / Aperture outer circle (Dark Glass)
    cx, cy = size // 2, size // 2
    r_outer = 150
    draw.ellipse(
        [(cx - r_outer, cy - r_outer), (cx + r_outer, cy + r_outer)],
        fill=(22, 24, 32, 240),
        outline=(255, 255, 255, 200),
        width=8
    )

    # 3. Inner Lens Ring
    r_mid = 110
    draw.ellipse(
        [(cx - r_mid, cy - r_mid), (cx + r_mid, cy + r_mid)],
        fill=(32, 35, 46, 255),
        outline=(99, 102, 241, 180),
        width=6
    )

    # 4. Vibrant Recording Core (Red #EF4444)
    r_core = 60
    draw.ellipse(
        [(cx - r_core, cy - r_core), (cx + r_core, cy + r_core)],
        fill=(239, 68, 68, 255),
        outline=(254, 202, 202, 220),
        width=6
    )

    # 5. Lens reflection highlight (subtle crescent)
    hl_box = [(cx - 90, cy - 90), (cx + 20, cy + 20)]
    draw.arc(hl_box, start=190, end=290, fill=(255, 255, 255, 180), width=8)

    # Save high-res PNG
    png_path = assets_dir / "app_icon.png"
    img.save(png_path, format="PNG")
    print(f"Generated {png_path}")

    # Generate multi-size ICO
    ico_path = assets_dir / "app_icon.ico"
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Generated {ico_path}")

if __name__ == "__main__":
    create_app_icon()
