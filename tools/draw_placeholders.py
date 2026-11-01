#!/usr/bin/env python3
"""
Draws the two built-in placeholder characters (Droplet, Sprout) as PNGs into
characters-src/, and generates the app icons into src-tauri/icons/.
Replace the PNGs with your own art any time; then run tools/make_character.py.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "characters-src"
ICONS = ROOT / "src-tauri" / "icons"
S = 4  # supersample factor for smooth edges


def canvas(size=256):
    return Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))


def down(img, size=256):
    return img.resize((size, size), Image.LANCZOS)


def face(d, cx, cy, mood, body, eye_dx=38, eye_dy=0, scale=1.0):
    """Eyes + mouth centred on (cx, cy) in supersampled px."""
    r = int(13 * S * scale)
    for sx in (-1, 1):
        ex, ey = cx + sx * eye_dx * S, cy + eye_dy * S
        if mood == "happy":
            # closed happy eyes: arcs
            d.arc([ex - r, ey - r, ex + r, ey + r], 200, 340, fill=(30, 40, 60, 255), width=5 * S)
        else:
            d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(30, 40, 60, 255))
            hr = int(4 * S * scale)
            d.ellipse([ex - r + 3 * S, ey - r + 3 * S, ex - r + 3 * S + 2 * hr, ey - r + 3 * S + 2 * hr], fill="white")
            if mood == "sad":
                # droopy lid
                d.rectangle([ex - r, ey - r, ex + r, ey - r + 9 * S], fill=body)
    mw, mh = 26 * S, 16 * S
    my = cy + 34 * S
    if mood == "sad":
        d.arc([cx - mw, my, cx + mw, my + mh], 200, 340, fill=(30, 40, 60, 255), width=5 * S)
    elif mood == "happy":
        d.chord([cx - mw, my - mh, cx + mw, my + mh], 10, 170, fill=(30, 40, 60, 255))
        d.chord([cx - mw + 6 * S, my - 2 * S, cx + mw - 6 * S, my + mh - 2 * S], 10, 170, fill=(235, 90, 110, 255))
    else:
        d.arc([cx - mw, my - mh, cx + mw, my + mh], 15, 165, fill=(30, 40, 60, 255), width=5 * S)
    # cheeks
    for sx in (-1, 1):
        d.ellipse([cx + sx * 58 * S - 12 * S, cy + 22 * S - 7 * S, cx + sx * 58 * S + 12 * S, cy + 22 * S + 7 * S],
                  fill=(255, 150, 160, 110))


def droplet(mood):
    im = canvas()
    d = ImageDraw.Draw(im)
    cx, cy = 128 * S, 150 * S
    body = (62, 167, 255, 255)
    # teardrop: circle + triangle top
    d.ellipse([cx - 86 * S, cy - 70 * S, cx + 86 * S, cy + 102 * S], fill=body)
    d.polygon([(cx, 16 * S), (cx - 74 * S, cy - 20 * S), (cx + 74 * S, cy - 20 * S)], fill=body)
    # shine
    d.ellipse([cx - 60 * S, cy - 40 * S, cx - 30 * S, cy + 10 * S], fill=(200, 230, 255, 170))
    face(d, cx, cy + 8 * S, mood, body)
    if mood == "wave":
        d.ellipse([cx + 86 * S, cy - 40 * S, cx + 120 * S, cy - 6 * S], fill=body)  # raised hand
    elif mood == "happy":
        for sx in (-1, 1):
            d.ellipse([cx + sx * 104 * S - 16 * S, cy - 60 * S - 16 * S, cx + sx * 104 * S + 16 * S, cy - 60 * S + 16 * S], fill=body)
    else:
        for sx in (-1, 1):
            d.ellipse([cx + sx * 96 * S - 16 * S, cy + 40 * S - 16 * S, cx + sx * 96 * S + 16 * S, cy + 40 * S + 16 * S], fill=body)
    return down(im)


def sprout(mood):
    im = canvas()
    d = ImageDraw.Draw(im)
    cx, cy = 128 * S, 158 * S
    body = (92, 196, 120, 255)
    leaf = (56, 160, 90, 255)
    d.rounded_rectangle([cx - 90 * S, cy - 70 * S, cx + 90 * S, cy + 96 * S], radius=70 * S, fill=body)
    # stem + leaves
    d.line([(cx, cy - 70 * S), (cx, cy - 110 * S)], fill=leaf, width=8 * S)
    d.ellipse([cx - 44 * S, cy - 132 * S, cx - 2 * S, cy - 104 * S], fill=leaf)
    d.ellipse([cx + 2 * S, cy - 132 * S, cx + 44 * S, cy - 104 * S], fill=leaf)
    d.ellipse([cx - 64 * S, cy - 44 * S, cx - 34 * S, cy + 2 * S], fill=(200, 240, 210, 150))
    face(d, cx, cy + 4 * S, mood, body)
    if mood == "wave":
        d.ellipse([cx + 86 * S, cy - 44 * S, cx + 120 * S, cy - 10 * S], fill=body)
    elif mood == "happy":
        for sx in (-1, 1):
            d.ellipse([cx + sx * 106 * S - 16 * S, cy - 64 * S - 16 * S, cx + sx * 106 * S + 16 * S, cy - 64 * S + 16 * S], fill=body)
    else:
        for sx in (-1, 1):
            d.ellipse([cx + sx * 98 * S - 16 * S, cy + 36 * S - 16 * S, cx + sx * 98 * S + 16 * S, cy + 36 * S + 16 * S], fill=body)
    return down(im)


def write_character(cid, fn, meta):
    d = SRC / cid
    d.mkdir(parents=True, exist_ok=True)
    for mood in ("idle", "wave", "happy", "sad"):
        fn(mood).save(d / f"{mood}.png")
    (d / "manifest.json").write_text(__import__("json").dumps(meta, indent=2), encoding="utf-8")
    print(f"characters-src/{cid}: idle/wave/happy/sad.png + manifest.json")


def icons():
    ICONS.mkdir(parents=True, exist_ok=True)
    base = Image.new("RGBA", (256 * S, 256 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([0, 0, 256 * S, 256 * S], radius=56 * S, fill=(47, 124, 246, 255))
    drop = droplet("idle").resize((200 * S, 200 * S), Image.LANCZOS)
    base.paste(drop, (28 * S, 30 * S), drop)
    big = base.resize((512, 512), Image.LANCZOS)
    big.save(ICONS / "icon.png")
    big.resize((256, 256), Image.LANCZOS).save(ICONS / "128x128@2x.png")
    big.resize((128, 128), Image.LANCZOS).save(ICONS / "128x128.png")
    big.resize((32, 32), Image.LANCZOS).save(ICONS / "32x32.png")
    big.save(ICONS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("src-tauri/icons: icon.png, icon.ico, 32x32.png, 128x128.png, 128x128@2x.png")


if __name__ == "__main__":
    write_character("droplet", droplet, {"name": "Droplet", "tagline": "The cheerful buddy",
                                         "greeting": "Hey {name}! 💧 Time for a water break?"})
    write_character("sprout", sprout, {"name": "Sprout", "tagline": "The calm buddy",
                                       "greeting": "Hi {name} 🌱 A quick sip of water?"})
    icons()
