#!/usr/bin/env python3
"""Build penny-desktop-kit Build 1 pack assets from generated art.

Run once (or re-run after regenerating art) from the repo root:

    python tools/build_assets.py

What it does per theme pack in packs/:
  - renames the generated wallpaper to wallpaper.png (and drops the
    media-generation-*.json sidecars -- never manifest.json)
  - converts the generated folder art (webp) to folder.ico (multi-size)
  - draws arrow + hand cursor art in the theme colour and writes real
    .cur files (CUR = ICO container, type 2, with hotspot) via
    penny_desktop_kit.cursors
  - copies the kawaii folder art to penny_desktop_kit/app.ico (app icon)

Everything is eager: the built assets ship in the repo, nothing is
downloaded at install or first run.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

from penny_desktop_kit.cursors import build_cur

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = os.path.join(ROOT, "packs")

# theme dir -> (display name, cursor outline colour)
THEMES = {
    "kawaii-pink": ("Kawaii Pink", (214, 51, 132)),
    "cozy-winter": ("Cozy Winter", (74, 111, 165)),
    "cyberpunk-neon": ("Cyberpunk Neon", (255, 46, 166)),
}

ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def _find_generated(d, marker, suffix):
    hits = [n for n in sorted(os.listdir(d)) if marker in n and n.endswith(suffix)]
    return os.path.join(d, hits[0]) if hits else None


def _draw_arrow(outline):
    """Classic pointer arrow, 32x32, white fill, theme-coloured outline."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    pts = [(1, 1), (1, 23), (6, 18), (9, 25), (12, 23), (9, 16), (15, 16)]
    draw.polygon(pts, fill=(255, 255, 255, 255))
    draw.line(pts + [pts[0]], fill=outline + (255,), width=2, joint="curve")
    return im


def _draw_hand(outline):
    """Stylised pointing hand (link select), 32x32, fingertip at top."""
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    # index finger pointing up
    draw.rounded_rectangle([13, 2, 18, 16], radius=2, fill=(255, 255, 255, 255),
                           outline=outline + (255,), width=2)
    # palm
    draw.rounded_rectangle([8, 14, 24, 28], radius=3, fill=(255, 255, 255, 255),
                           outline=outline + (255,), width=2)
    # thumb blob on the left
    draw.ellipse([5, 15, 12, 23], fill=(255, 255, 255, 255),
                 outline=outline + (255,), width=2)
    # knuckle bump for a folded finger
    draw.rounded_rectangle([19, 12, 22, 16], radius=1, fill=(255, 255, 255, 255),
                           outline=outline + (255,), width=2)
    return im


def build_theme(theme_dir, outline):
    d = os.path.join(PACKS, theme_dir)
    # wallpaper -> wallpaper.png
    src = _find_generated(d, "wallpaper", ".png")
    if src is None:
        raise SystemExit("no wallpaper found in %s" % d)
    dst = os.path.join(d, "wallpaper.png")
    if os.path.abspath(src) != os.path.abspath(dst):
        os.replace(src, dst)
    # folder art -> folder.ico (multi-size)
    art = _find_generated(d, "folder", ".webp")
    if art is None:
        raise SystemExit("no folder art found in %s" % d)
    im = Image.open(art).convert("RGBA")
    im.save(os.path.join(d, "folder.ico"), format="ICO", sizes=ICO_SIZES)
    # cursors
    curdir = os.path.join(d, "cursors")
    os.makedirs(curdir, exist_ok=True)
    build_cur(_draw_arrow(outline), (0, 0), os.path.join(curdir, "arrow.cur"))
    build_cur(_draw_hand(outline), (15, 2), os.path.join(curdir, "link.cur"))
    # drop media-generation json sidecars ONLY -- manifest.json stays.
    for name in list(os.listdir(d)):
        if name.startswith("media-generation-") and name.endswith(".json"):
            os.remove(os.path.join(d, name))
    print("built %s: wallpaper.png, folder.ico, cursors/arrow.cur, cursors/link.cur" % theme_dir)


def main():
    for theme_dir, (_name, outline) in THEMES.items():
        build_theme(theme_dir, outline)
    # app icon: reuse the kawaii folder icon
    shutil.copyfile(os.path.join(PACKS, "kawaii-pink", "folder.ico"),
                    os.path.join(ROOT, "penny_desktop_kit", "app.ico"))
    print("built penny_desktop_kit/app.ico")


if __name__ == "__main__":
    main()
