#!/usr/bin/env python3
# Copyright 2026 OhhO Robotics
# SPDX-License-Identifier: Apache-2.0
"""Render maps/apartment.pgm with the start pose and named waypoints as a PNG.

    python3 render_map_overlay.py [OUT.png]

Needs numpy only (no ROS, no PIL). Markers: start = yellow, kitchen = red,
desk = blue, door = green; a short line shows each heading.
"""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import yaml

from waypoint_loader import load_initial_pose, load_waypoints

PACKAGE = Path(__file__).resolve().parents[1]
SCALE = 8
COLORS = {
    "start": (230, 190, 0),
    "kitchen": (220, 30, 30),
    "desk": (30, 70, 220),
    "door": (20, 150, 50),
}


def read_pgm(path: Path) -> np.ndarray:
    data = path.read_bytes()
    magic, size, _maxval, pixels = data.split(b"\n", 3)
    assert magic == b"P5"
    width, height = (int(v) for v in size.split())
    return np.frombuffer(pixels, dtype=np.uint8).reshape(height, width)


def write_png(path: Path, rgb: np.ndarray) -> None:
    raw = b"".join(b"\x00" + rgb[r].tobytes() for r in range(rgb.shape[0]))

    def chunk(tag: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(tag + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", rgb.shape[1], rgb.shape[0], 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main(argv) -> int:
    out = Path(argv[0]) if argv else PACKAGE / "docs" / "apartment_map_waypoints.png"
    meta = yaml.safe_load((PACKAGE / "maps" / "apartment.yaml").read_text())
    grid = read_pgm(PACKAGE / "maps" / meta["image"])
    res = float(meta["resolution"])
    ox, oy = float(meta["origin"][0]), float(meta["origin"][1])
    height = grid.shape[0]
    big = np.kron(grid, np.ones((SCALE, SCALE), dtype=np.uint8))
    rgb = np.stack([big, big, big], axis=-1)

    def px(x, y):
        return (
            int((x - ox) / res * SCALE),
            int((height - (y - oy) / res) * SCALE),
        )

    def dot(x, y, yaw, color):
        cx, cy = px(x, y)
        for dy in range(-7, 8):
            for dx in range(-7, 8):
                if dx * dx + dy * dy <= 49:
                    rgb[cy + dy, cx + dx] = color
        for step in range(8, 30):
            hx = cx + int(step * math.cos(yaw))
            hy = cy - int(step * math.sin(yaw))
            rgb[hy - 1 : hy + 2, hx - 1 : hx + 2] = color

    sx, sy, syaw = load_initial_pose()
    dot(sx, sy, syaw, COLORS["start"])
    for name, w in load_waypoints().items():
        dot(w.x, w.y, w.yaw, COLORS[name])
    write_png(out, rgb)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main(sys.argv[1:]))
