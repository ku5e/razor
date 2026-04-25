"""Generate razor.ico for PyInstaller builds."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

SIZE = 256
BG   = (26, 26, 46)       # C["bg"]
FG   = (224, 92, 92)      # C["work"] red

img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded square background
margin = 20
draw.rounded_rectangle([margin, margin, SIZE - margin, SIZE - margin],
                       radius=40, fill=BG)

# "R" glyph centered
try:
    font = ImageFont.truetype("arialbd.ttf", 160)
except OSError:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "R", font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (SIZE - tw) // 2 - bbox[0]
y = (SIZE - th) // 2 - bbox[1] - 8
draw.text((x, y), "R", font=font, fill=FG)

# Save multi-size ICO (Windows needs several sizes)
out = Path(__file__).parent / "razor.ico"
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
images = [img.resize(s, Image.LANCZOS) for s in sizes]
images[0].save(out, format="ICO", sizes=[(s[0], s[1]) for s in sizes],
               append_images=images[1:])
print(f"Saved: {out}")
