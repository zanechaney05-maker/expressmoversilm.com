#!/usr/bin/env python3
"""Rebuild src/img from the original photos. Needs Pillow (pip install pillow).

    python3 tools/make_images.py "/path/to/Express Movers Photos"

Each entry below maps a site name to an original file. To add a photo, add a line,
run this script, then use pic("name", "alt text", sizes) in build.py.
"""
import json, os, sys
from PIL import Image, ImageOps

SRC = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "img")
os.makedirs(OUT, exist_ok=True)

PORTRAIT = {
    "uncw-boxes": "IMG_9256.jpeg", "two-movers-boxes": "IMG_8965.jpeg", "ramp-uncw": "IMG_9258.jpeg",
    "hand-truck-load": "IMG_9465.jpeg", "hand-truck-boxes": "IMG_8930.jpeg", "crew-ramp": "IMG_9295.jpeg",
    "crew-straps": "IMG_8817-58c45375.jpeg", "crew-three": "IMG_9222.jpeg", "crew-two": "IMG_8774.jpeg",
    "totes": "IMG_8816.jpeg", "boxes-thumbs": "IMG_8797.jpeg", "boxes-wrapped": "IMG_8432.jpg",
    "load-two": "IMG_8515.jpg", "load-pair": "IMG_8929.jpeg", "container": "IMG_9635.jpeg",
    "hoodies": "IMG_9444.jpeg", "mattress": "IMG_8392.jpg", "thumbs-ladder": "IMG_8824.jpeg",
    "dresser": "IMG_8899.jpeg", "boxes-yellow": "IMG_8810.jpeg", "loaded-thumbs": "IMG_8399-47ca0bae.jpg",
    "tailgate-tall": "IMG_9286.jpeg",
}
man = {}


def load(name):
    return ImageOps.exif_transpose(Image.open(os.path.join(SRC, name))).convert("RGB")


def emit(name, im, widths):
    ws = [w for w in widths if w <= im.width] or [im.width]
    for w in ws:
        im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(
            os.path.join(OUT, "%s-%d.webp" % (name, w)), "WEBP", quality=76, method=6)
    man[name] = {"w": max(ws), "h": round(im.height * max(ws) / im.width), "widths": ws}


hero = load("IMG_9286.jpeg").crop((0, 770, 1920, 2050))          # the five-person tailgate photo, cropped wide
emit("crew-tailgate", hero, [800, 1280, 1920])
hero.resize((1200, 800), Image.LANCZOS).save(os.path.join(OUT, "crew-tailgate.jpg"), quality=82, optimize=True)
emit("crew-storage", load("IMG_8634.jpeg"), [800, 1280, 1920])
for name, original in PORTRAIT.items():
    emit(name, load(original), [280, 400, 800, 1200])
# Three small originals. Replace these if larger copies turn up.
emit("pool-table", load("2024-07-02.png"), [382])
emit("ramp-hand-truck", load("2024-02-27 (1).jpg"), [382])
emit("piano", load("2024-02-27-63e11d04-f14a874d.png").rotate(90, expand=True), [366])

# Jared's portrait lives in this repo, next to this script.
portrait = os.path.join(os.path.dirname(os.path.abspath(__file__)), "originals", "jared.jpg")
if os.path.exists(portrait):
    emit("jared", ImageOps.exif_transpose(Image.open(portrait)).convert("RGB"), [280, 400, 800])

logo = Image.open(os.path.join(SRC, "EXPRESS-MOVER-LLC-LOGO.png")).convert("RGBA")
logo = logo.crop(logo.getbbox())
logo.resize((200, round(logo.height * 200 / logo.width)), Image.LANCZOS).save(os.path.join(OUT, "logo-200.webp"), "WEBP", quality=90, method=6)
man["logo"] = {"w": 200, "h": round(logo.height * 200 / logo.width), "widths": [200]}
bar = Image.new("RGBA", (logo.width + 120, logo.height + 120), (29, 31, 28, 255))
bar.alpha_composite(logo, (60, 60))
bar.convert("RGB").resize((600, round(bar.height * 600 / bar.width)), Image.LANCZOS).save(os.path.join(OUT, "logo.png"), optimize=True)

json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print("%d photos written to %s" % (len(man), OUT))
