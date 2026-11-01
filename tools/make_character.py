#!/usr/bin/env python3
"""
Build animated character GIFs for Reminder Buddy from static PNGs.

Folder layout (source):
    characters-src/<id>/
        manifest.json      optional: {"name": "...", "tagline": "...", "greeting": "Hey {name}! ..."}
        idle.png           required (transparent background recommended, roughly square)
        wave.png           optional – shown when the reminder appears
        happy.png          optional – shown after "Yes"
        sad.png            optional – shown after "Later"
      -- or, for true frame-by-frame animation --
        idle_01.png idle_02.png ...   (any mood followed by _NN)

Output (what the app ships):
    public/characters/<id>/{idle,wave,happy,sad}.gif
    public/characters/index.json

Usage:
    python tools/make_character.py                 # build every character in characters-src/
    python tools/make_character.py myhero          # build just characters-src/myhero
    python tools/make_character.py --rebuild-index # only regenerate index.json

A single static PNG is animated procedurally per mood: idle = gentle bob,
wave = bob + rock, happy = jump + squash, sad = slow droop.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "characters-src"
OUT = ROOT / "public" / "characters"

MOODS = ["idle", "wave", "happy", "sad"]
SIZE = 192          # output canvas (px)
PAD = 24            # headroom so jumps/rotation never clip
FRAME_MS = 60


# ---------------------------------------------------------------------------
# procedural motion recipes: return (dx, dy, angle_deg, scale_x, scale_y) per t in [0,1)
# ---------------------------------------------------------------------------

def motion(mood: str, t: float):
    tau = 2 * math.pi
    if mood == "idle":
        s = math.sin(t * tau)
        return 0, -4 * s, 0, 1 + 0.015 * s, 1 - 0.02 * s
    if mood == "wave":
        s = math.sin(t * tau)
        rock = math.sin(t * tau * 2)
        return 2 * rock, -5 * abs(s), 7 * rock, 1 + 0.02 * abs(s), 1 - 0.03 * abs(s)
    if mood == "happy":
        # squash, jump, land
        if t < 0.15:
            k = t / 0.15
            return 0, 4 * k, 0, 1 + 0.12 * k, 1 - 0.14 * k
        if t < 0.65:
            k = (t - 0.15) / 0.5
            y = -26 * math.sin(k * math.pi)
            return 0, y, 0, 1 - 0.06 * math.sin(k * math.pi), 1 + 0.08 * math.sin(k * math.pi)
        k = (t - 0.65) / 0.35
        s = math.sin(k * math.pi)
        return 0, 3 * s, 0, 1 + 0.08 * s, 1 - 0.08 * s
    if mood == "sad":
        k = 0.5 - 0.5 * math.cos(t * tau)  # ease in-out, 0→1→0
        return -3 * k, 7 * k, -5 * k, 1, 1 - 0.03 * k
    return 0, 0, 0, 1, 1


def fit(img: Image.Image, box: int) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((box, box), Image.LANCZOS)
    canvas = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    canvas.paste(img, ((box - img.width) // 2, box - img.height), img)  # bottom-aligned
    return canvas


def render_frame(sprite: Image.Image, dx: float, dy: float, ang: float, sx: float, sy: float) -> Image.Image:
    w, h = sprite.size
    scaled = sprite.resize((max(1, int(w * sx)), max(1, int(h * sy))), Image.LANCZOS)
    rotated = scaled.rotate(ang, resample=Image.BICUBIC, expand=True)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # anchor: bottom-centre of the sprite box sits at the bottom-centre of the canvas minus padding
    x = (SIZE - rotated.width) // 2 + int(dx)
    y = SIZE - PAD - rotated.height + int(dy) + (rotated.height - scaled.height) // 2
    canvas.paste(rotated, (x, y), rotated)
    return canvas


def to_gif_frame(frame: Image.Image) -> Image.Image:
    alpha = frame.getchannel("A")
    pal = frame.convert("RGB").quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    mask = alpha.point(lambda a: 255 if a < 96 else 0)
    pal.paste(255, mask)
    return pal


def save_gif(frames: list[Image.Image], path: Path, ms: int = FRAME_MS):
    gif_frames = [to_gif_frame(f) for f in frames]
    gif_frames[0].save(
        path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=ms,
        loop=0,
        transparency=255,
        disposal=2,
        optimize=False,
    )


# ---------------------------------------------------------------------------

def build_mood(src_dir: Path, out_dir: Path, mood: str, fallback: Path | None) -> bool:
    # frame-by-frame sequence?
    seq = sorted(src_dir.glob(f"{mood}_[0-9]*.png"), key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    if seq:
        frames = [render_frame(fit(Image.open(p), SIZE - 2 * PAD), 0, 0, 0, 1, 1) for p in seq]
        save_gif(frames, out_dir / f"{mood}.gif", ms=90)
        return True

    single = src_dir / f"{mood}.png"
    if not single.exists():
        single = fallback
    if single is None or not single.exists():
        return False

    sprite = fit(Image.open(single), SIZE - 2 * PAD)
    n = 28 if mood in ("idle", "sad") else 24
    frames = [render_frame(sprite, *motion(mood, i / n)) for i in range(n)]
    save_gif(frames, out_dir / f"{mood}.gif")
    return True


def build_character(cid: str) -> dict | None:
    src_dir = SRC / cid
    if not src_dir.is_dir():
        print(f"  !! characters-src/{cid} not found", file=sys.stderr)
        return None
    idle = src_dir / "idle.png"
    if not idle.exists() and not list(src_dir.glob("idle_[0-9]*.png")):
        print(f"  !! {cid}: idle.png (or idle_01.png…) is required", file=sys.stderr)
        return None

    out_dir = OUT / cid
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {"name": cid.replace("-", " ").title()}
    mf = src_dir / "manifest.json"
    if mf.exists():
        meta.update(json.loads(mf.read_text(encoding="utf-8")))

    moods = []
    fallback = idle if idle.exists() else None
    for mood in MOODS:
        has_own = (src_dir / f"{mood}.png").exists() or bool(list(src_dir.glob(f"{mood}_[0-9]*.png")))
        if build_mood(src_dir, out_dir, mood, fallback):
            moods.append(mood)
            print(f"  {cid}/{mood}.gif  {'(own art)' if has_own else '(derived from idle.png)'}")

    entry = {"id": cid, **{k: v for k, v in meta.items() if k in ("name", "tagline", "greeting")}, "moods": moods}
    (out_dir / "manifest.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


def rebuild_index():
    entries = []
    for d in sorted(OUT.iterdir()):
        mf = d / "manifest.json"
        if d.is_dir() and mf.exists() and (d / "idle.gif").exists():
            entries.append(json.loads(mf.read_text(encoding="utf-8")))
    (OUT / "index.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"index.json: {len(entries)} character(s) -> {', '.join(e['id'] for e in entries)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="character ids to build (default: all in characters-src/)")
    ap.add_argument("--rebuild-index", action="store_true", help="only regenerate public/characters/index.json")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if not args.rebuild_index:
        ids = args.ids or [p.name for p in sorted(SRC.iterdir()) if p.is_dir()] if SRC.exists() else []
        if not ids:
            print("Nothing to build: put PNGs in characters-src/<id>/ first.")
        for cid in ids:
            print(f"Building {cid}…")
            build_character(cid)
    rebuild_index()


if __name__ == "__main__":
    main()
