#!/usr/bin/env python3
"""VELMARA — a travel poster for a place that does not exist.

A program that paints one 1024x1024 travel poster and writes it to
/output/entry.png (or ./output/entry.png when /output does not exist).

Pure Python 3.13 standard library only: no Pillow, no network, no random
numbers. The PNG encoder is written by hand (zlib + struct) and every
shape is drawn into an RGB buffer with small scanline helpers.

The place: VELMARA, a terracotta-cliff city above a violet sea, under two
suns — one large and golden, one small and rose-red. A small fleet of
sailboats crosses the calm teal water, guided down to the harbour by the
lighthouse beam falling onto the waves. The only text in the picture is
the name of the place itself.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
INDIGO = (27, 42, 94)
ROSE = (232, 106, 122)
GOLD = (245, 185, 66)
GOLD_DEEP = (230, 150, 50)
CREAM = (245, 239, 224)
TEXT_CREAM = (255, 246, 224)
TEXT_SHADOW = (22, 30, 66)
TEAL_DEEP = (16, 70, 100)
TEAL = (30, 122, 140)
CLIFF = (192, 138, 78)
CLIFF_SHADE = (169, 113, 63)
TERRA = (198, 102, 60)
WINDOW = (255, 196, 90)
DARK = (40, 50, 80)

HORIZON = 700  # y where the sea begins

# ------------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def put(x, y, color):
    """Set one pixel, clipped to the canvas."""
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def blend(x, y, color, alpha):
    """Blend a colour over the pixel at (x, y); alpha 0..1."""
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        buf[i] = int(buf[i] * (1.0 - alpha) + color[0] * alpha)
        buf[i + 1] = int(buf[i + 1] * (1.0 - alpha) + color[1] * alpha)
        buf[i + 2] = int(buf[i + 2] * (1.0 - alpha) + color[2] * alpha)


def hline(y, x0, x1, color):
    """Fill a horizontal span on row y, clipped."""
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    i = _idx(x0, y)
    n = x1 - x0 + 1
    buf[i:i + n * 3] = bytes(color) * n


def fill_rect(x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1 + 1)):
        hline(y, x0, x1, color)


def lerp(a, b, t):
    return int(round(a + (b - a) * t))


def lerp_color(c0, c1, t):
    return (lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t))


def quant(color, step=3):
    """Snap channels to a coarse grid so long gradients stay compressible."""
    return tuple(max(0, min(255, (c // step) * step)) for c in color)


# ------------------------------------------------------------------ sky/sea
# Sky gradient stops (y, colour): indigo -> rose -> gold at the horizon.
SKY_STOPS = [(0, INDIGO), (300, (110, 66, 132)), (500, ROSE),
             (620, (244, 158, 84)), (HORIZON, GOLD)]


def sky_color(y):
    for i in range(len(SKY_STOPS) - 1):
        y0, c0 = SKY_STOPS[i]
        y1, c1 = SKY_STOPS[i + 1]
        if y <= y1:
            t = (y - y0) / max(1, y1 - y0)
            return quant(lerp_color(c0, c1, t))
    return quant(GOLD)


def sea_color(y):
    t = (y - HORIZON) / max(1, H - 1 - HORIZON)
    return quant(lerp_color(TEAL, TEAL_DEEP, t))


def paint_sky_and_sea():
    for y in range(HORIZON):
        c = sky_color(y)
        i = y * W * 3
        buf[i:i + W * 3] = bytes(c) * W
    for y in range(HORIZON, H):
        c = sea_color(y)
        i = y * W * 3
        buf[i:i + W * 3] = bytes(c) * W


# ------------------------------------------------------------------- shapes
def fill_circle(cx, cy, r, color, y_lo=None, y_hi=None):
    """Filled circle; optionally clipped to a y range (for domes)."""
    y_lo = -r if y_lo is None else max(-r, y_lo - cy)
    y_hi = r if y_hi is None else min(r, y_hi - cy)
    for dy in range(y_lo, y_hi + 1):
        half = int(math.sqrt(max(0, r * r - dy * dy)))
        hline(cy + dy, cx - half, cx + half, color)


def fill_circle_alpha(cx, cy, r, color, alpha):
    for dy in range(-r, r + 1):
        half = int(math.sqrt(max(0, r * r - dy * dy)))
        for x in range(cx - half, cx + half + 1):
            blend(x, cy + dy, color, alpha)


def fill_polygon(points, color):
    """Scanline fill for a simple polygon."""
    ys = [p[1] for p in points]
    y_min, y_max = max(0, min(ys)), min(H - 1, max(ys))
    n = len(points)
    for y in range(y_min, y_max + 1):
        xs = []
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(y, int(math.ceil(xs[k])), int(math.floor(xs[k + 1])), color)


def fill_polygon_alpha(points, color, alpha):
    ys = [p[1] for p in points]
    y_min, y_max = max(0, min(ys)), min(H - 1, max(ys))
    n = len(points)
    for y in range(y_min, y_max + 1):
        xs = []
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(math.ceil(xs[k])), int(math.floor(xs[k + 1])) + 1):
                blend(x, y, color, alpha)


def draw_line(x0, y0, x1, y1, color):
    """Bresenham line, 1px."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        put(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_bird(x, y, s, color):
    """A tiny distant bird: two short strokes forming a shallow V."""
    draw_line(x - s, y - s // 2, x, y, color)
    draw_line(x, y, x + s, y - s // 2, color)


# -------------------------------------------------------------------- suns
def paint_suns():
    # Large golden sun, low on the right.
    cx, cy, r = 830, 470, 62
    for glow_r, alpha in ((r + 58, 0.08), (r + 40, 0.11), (r + 22, 0.16)):
        fill_circle_alpha(cx, cy, glow_r, (255, 214, 130), alpha)
    fill_circle(cx, cy, r, (255, 206, 96))
    fill_circle(cx, cy, int(r * 0.72), (255, 222, 140))
    # Small rose-red sun beside it: one soft halo, no visible rings.
    cx2, cy2, r2 = 908, 548, 34
    fill_circle_alpha(cx2, cy2, r2 + 20, (255, 140, 130), 0.12)
    fill_circle(cx2, cy2, r2, (240, 108, 122))
    fill_circle(cx2, cy2, int(r2 * 0.7), (250, 142, 138))
    # Warm haze bands hugging the horizon.
    for y in range(648, HORIZON, 4):
        for x in range(430, W, 2):
            blend(x, y, (255, 220, 150), 0.10)


def paint_birds():
    for (x, y, s) in ((196, 176, 12), (258, 148, 10), (330, 198, 11),
                      (520, 138, 10), (604, 186, 12), (428, 226, 9)):
        draw_bird(x, y, s, (38, 44, 84))


# ------------------------------------------------------------- cliff + city
def cliff_top(x):
    """The top edge of the headland as a function of x."""
    if x < 100:
        return 500 - int(x * 38 / 100)
    if x < 200:
        return 462 + int((x - 100) * 16 / 100)
    return 478 + int((x - 200) * 12 / 12)


CLIFF_POLY = [(0, 500), (100, 462), (200, 478), (212, 540),
              (200, 660), (170, 782), (90, 792), (0, 742)]


def paint_cliff():
    fill_polygon(CLIFF_POLY, CLIFF)
    # Warm strata: a few faint darker bands across the rock face.
    for y in range(560, 780, 44):
        xs = []
        n = len(CLIFF_POLY)
        for i in range(n):
            x0, y0 = CLIFF_POLY[i]
            x1, y1 = CLIFF_POLY[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        if len(xs) >= 2:
            xs.sort()
            for x in range(int(xs[0]) + 8, int(xs[-1]) - 8):
                blend(x, y, CLIFF_SHADE, 0.30)


def paint_building(x, w, h, roof, color=CREAM):
    top = cliff_top(x + w // 2) + 4
    base = top + h
    fill_rect(x, top, x + w - 1, base, color)
    if roof == "dome":
        fill_circle(x + w // 2, top, w // 2, color, y_lo=top - w // 2, y_hi=top)
        fill_rect(x + w // 2 - 2, top - w // 2 - 8, x + w // 2 + 2,
                  top - w // 2, GOLD_DEEP)
    elif roof == "terra":
        fill_polygon([(x - 2, top), (x + w + 2, top), (x + w - 6, top - 16),
                      (x + 6, top - 16)], TERRA)
    else:  # flat roof with a thin gold trim
        hline(top, x, x + w - 1, GOLD_DEEP)
    # Warm lit windows, in a deterministic pattern.
    for row in range(2):
        wy = top + 14 + row * 20
        if wy > base - 10:
            break
        for col in range(w // 16):
            wx = x + 8 + col * 16
            if (row * 5 + col * 3 + x) % 4 != 0:
                fill_rect(wx, wy, wx + 5, wy + 7, WINDOW)
    return top


def paint_city():
    specs = [
        (8, 38, 62, "dome"), (50, 34, 88, "flat"), (88, 40, 56, "terra"),
        (132, 36, 92, "dome"), (168, 24, 48, "flat"),
    ]
    for (x, w, h, roof) in specs:
        paint_building(x, w, h, roof)
    paint_lighthouse()


def paint_lighthouse():
    # The lighthouse stands at the tip of the headland, taller than the
    # town, its lamp above the rooftops.
    x, w = 182, 22
    top = 392
    base = cliff_top(x + w // 2) + 62
    # Tapered white tower with two terracotta bands.
    fill_polygon([(x, base), (x + w, base), (x + w - 3, top + 18),
                  (x + 3, top + 18)], CREAM)
    fill_rect(x + 1, top + 52, x + w - 2, top + 64, TERRA)
    fill_rect(x + 1, top + 88, x + w - 2, top + 100, TERRA)
    # Lamp room and cap.
    fill_rect(x + 2, top + 2, x + w - 3, top + 18, DARK)
    fill_rect(x + 6, top + 6, x + w - 7, top + 14, WINDOW)
    fill_polygon([(x - 1, top + 2), (x + w + 1, top + 2),
                  (x + w // 2, top - 12)], TERRA)
    # The beam is painted separately (paint_beam), after the fleet, so it
    # falls down onto the water and the ships instead of sweeping
    # sideways across the sky.


def paint_beam():
    """A cone of light falling DOWN from the lamp onto the water, so the
    ships crossing below the cliff can see the rocks and keep clear of
    each other. The cone stays left of the poster's name."""
    lx, ly = 193, 402
    # Wide outer cone, then a narrower brighter core, both aimed at the
    # water just left of the cliff's foot.
    fill_polygon_alpha([(lx, ly), (24, 858), (216, 888)],
                       (255, 232, 170), 0.22)
    fill_polygon_alpha([(lx, ly), (64, 854), (196, 880)],
                       (255, 240, 190), 0.32)
    # Bright pool where the light lands on the water, smoothed over
    # several steps so no hard rings show.
    for glow_r, alpha in ((70, 0.06), (56, 0.08), (42, 0.10), (28, 0.14),
                          (14, 0.20)):
        fill_circle_alpha(128, 862, glow_r, (255, 222, 150), alpha)
    for dx in range(-60, 61, 4):
        blend(128 + dx, 862, (255, 232, 170), 0.12)


# -------------------------------------------------------------------- sea
def _hash(x, y):
    """Deterministic pseudo-random 0..999 from a coordinate pair."""
    return ((x * 73856093) ^ (y * 19349663) ^ 0x5DEECE66D) % 1000


def paint_sea_glitter():
    # Golden sparkle path under the suns, densest near their x.
    for y in range(HORIZON + 8, H - 8, 6):
        spread = 70 + (y - HORIZON) // 3
        for x in range(720 - spread, 940 + spread, 5):
            if x < 0 or x >= W:
                continue
            v = _hash(x, y)
            if v < 12:
                put(x, y, (255, 214, 120))
                if v < 4:
                    put(x + 1, y, (255, 226, 150))
                    put(x, y + 1, (255, 214, 120))
    # Faint horizontal swell lines.
    for y in range(HORIZON + 26, H - 20, 46):
        for x in range(0, W, 3):
            if _hash(x, y) < 70:
                blend(x, y, (120, 190, 200), 0.15)


def paint_sailboat(bx, by, s=1.0):
    """One sailboat at (bx, by), scaled by s (1.0 = hero boat)."""
    # Hull.
    fill_polygon([(bx - int(34 * s), by), (bx + int(34 * s), by),
                  (bx + int(22 * s), by + int(16 * s)),
                  (bx - int(22 * s), by + int(16 * s))], (52, 44, 66))
    # Mast and two white sails.
    draw_line(bx, by - 2, bx, by - int(66 * s), (52, 44, 66))
    fill_polygon([(bx + int(3 * s), by - int(64 * s)),
                  (bx + int(3 * s), by - int(4 * s)),
                  (bx + int(40 * s), by - int(4 * s))], (250, 246, 236))
    fill_polygon([(bx - int(3 * s), by - int(56 * s)),
                  (bx - int(3 * s), by - int(4 * s)),
                  (bx - int(30 * s), by - int(4 * s))], (238, 230, 214))
    # Soft reflection on the water.
    for dy in range(1, int(26 * s) + 1):
        alpha = 0.16 * (1.0 - dy / (26.0 * s))
        half = int(30 * s * (1.0 - dy / (30.0 * s)))
        for x in range(bx - half, bx + half + 1):
            blend(x, by + int(18 * s) + dy, (250, 246, 236), alpha)


def paint_fleet():
    """A small fleet crossing the sea: the hero boat plus six more at
    varied distances, all clear of the poster's name above the horizon."""
    for (bx, by, s) in ((640, 836, 1.0), (300, 900, 0.8), (860, 760, 0.55),
                        (480, 745, 0.42), (950, 920, 0.7), (230, 880, 0.65),
                        (760, 950, 0.9)):
        paint_sailboat(bx, by, s)


# -------------------------------------------------------------------- type
# 5x7 bitmap font (rows top to bottom, '#' = on). Only the letters we need.
FONT = {
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
}

SCALE = 14
ADVANCE = 6 * SCALE  # 5 modules + 1 module of space


def text_width(text):
    return len(text) * 5 * SCALE + (len(text) - 1) * SCALE


def draw_text(text, x0, y0, color):
    x = x0
    for ch in text:
        glyph = FONT[ch]
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "#":
                    fill_rect(x + col * SCALE, y0 + row * SCALE,
                              x + col * SCALE + SCALE - 2,
                              y0 + row * SCALE + SCALE - 2, color)
        x += ADVANCE


def paint_name():
    name = "VELMARA"
    w = text_width(name)
    x0 = (W - w) // 2
    y0 = 540
    # Dark shadow first so the cream letters read against the gold sky.
    draw_text(name, x0 + 7, y0 + 7, TEXT_SHADOW)
    draw_text(name, x0, y0, TEXT_CREAM)
    # Thin gold rule under the name, with a small diamond at its centre.
    ry = y0 + 7 * SCALE + 20
    for dy in range(3):
        hline(ry + dy, x0 + 30, x0 + w - 30, GOLD)
    cx = W // 2
    fill_polygon([(cx - 9, ry - 8), (cx, ry - 17), (cx + 9, ry - 8),
                  (cx, ry + 3)], GOLD)


# ------------------------------------------------------------------- frame
def paint_frame():
    fill_rect(0, 0, W - 1, 15, CREAM)
    fill_rect(0, H - 16, W - 1, H - 1, CREAM)
    fill_rect(0, 0, 15, H - 1, CREAM)
    fill_rect(W - 16, 0, W - 1, H - 1, CREAM)
    for x in range(20, W - 20):
        put(x, 20, GOLD_DEEP)
        put(x, H - 21, GOLD_DEEP)
    for y in range(20, H - 20):
        put(20, y, GOLD_DEEP)
        put(W - 21, y, GOLD_DEEP)


# -------------------------------------------------------------- PNG writer
def png_chunk(ctype, data):
    chunk = struct.pack(">I", len(data)) + ctype + data
    chunk += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return chunk


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: None
        raw += buf[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += png_chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    paint_sky_and_sea()
    paint_suns()
    paint_birds()
    paint_cliff()
    paint_city()
    paint_sea_glitter()
    paint_fleet()
    paint_beam()
    paint_name()
    paint_frame()
    if os.path.isdir("/output"):
        out = "/output/entry.png"
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "output", "entry.png")
    size = write_png(out)
    print("wrote %s (%d bytes)" % (out, size))


if __name__ == "__main__":
    main()
