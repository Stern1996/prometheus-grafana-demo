#!/usr/bin/env python3
"""
build_gig_assets.py -- turns the full-resolution screenshots into Fiverr-ready
gig images.

Fiverr's recommended gig image is 1280x769 (they crop to various aspect ratios
for the carousel and the search thumbnail, so getting the aspect right up front
avoids losing content).

Full-resolution originals stay in gallery/ for Upwork, a portfolio site, or any
other use where a bigger image is wanted.

Run:  python build_gig_assets.py
"""

import os
import sys

from PIL import Image

TARGET = (1280, 769)          # Fiverr recommendation
RESAMPLE = Image.LANCZOS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GALLERY = os.path.join(ROOT, "gallery")
OUT = os.path.join(ROOT, "gig-assets")

# source file -> output name, anchor
# anchor decides which edge keeps its content when the aspect needs trimming.
# The dashboard has a time picker at the very top, so it must anchor to the top.
JOBS = [
    ("01-dashboard.png",    "01-dashboard.png",    "Grafana dashboard",   "top"),
    ("02-architecture.png", "02-architecture.png", "Architecture diagram", "center"),
    ("03-alert-rules.png",  "03-alert-rules.png",  "Alert rules",          "center"),
]


def cover_crop(im, target, anchor="center"):
    """Scale so the image covers target, then crop on the chosen axis.

    No letterboxing: the result always fills the frame exactly.
    """
    tw, th = target
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    nw, nh = max(tw, round(sw * scale)), max(th, round(sh * scale))
    im = im.resize((nw, nh), RESAMPLE)

    left = (nw - tw) // 2
    if anchor == "top":
        top = 0                      # keep the header, drop from the bottom
    elif anchor == "bottom":
        top = nh - th
    else:
        top = (nh - th) // 2
    return im.crop((left, top, left + tw, top + th))


def main():
    os.makedirs(OUT, exist_ok=True)
    failures = []

    print(f"target {TARGET[0]}x{TARGET[1]}  (aspect {TARGET[0]/TARGET[1]:.4f})\n")

    for src_name, dst_name, label, anchor in JOBS:
        src = os.path.join(GALLERY, src_name)
        if not os.path.exists(src):
            failures.append(f"{src_name}: missing")
            continue

        im = Image.open(src).convert("RGB")
        before = im.size
        out = cover_crop(im, TARGET, anchor)
        dst = os.path.join(OUT, dst_name)
        out.save(dst, "PNG", optimize=True)

        kb = os.path.getsize(dst) / 1024
        print(f"{label:<20} {before[0]}x{before[1]}  ->  {out.size[0]}x{out.size[1]}"
              f"   {kb:6.0f} KB   anchor={anchor:<6} {dst_name}")

        # Fiverr rejects anything over 5 MB
        if kb > 5000:
            failures.append(f"{dst_name}: {kb/1024:.1f} MB exceeds Fiverr's 5 MB limit")

    print()
    if failures:
        for f in failures:
            print(f"FAIL  {f}", file=sys.stderr)
        return 1

    print(f"OK - {len(JOBS)} images written to gig-assets/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
