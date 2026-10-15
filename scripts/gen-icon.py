#!/usr/bin/env python3
"""Generate QR-style "あお" icons for the extension.

Renders the text "あお" with a heavy CJK font onto a coarse module grid,
thresholds it into QR-like black squares, adds the three QR finder patterns
and writes PNGs at every size the manifest uses plus an SVG for the PWA icon.
"""
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "images")
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"

N = 33          # modules per side (QR version 4 size)
QUIET = 1       # quiet-zone modules around the symbol
FINDER = 7      # finder pattern size
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 102, 204)


def text_mask(size_px: int) -> Image.Image:
    """Render あお as a 1-bit mask fitted to the central area of the grid."""
    # Available area: between finders on top, full width on bottom.
    # Use an oversampled canvas then downsample to module resolution.
    scale = 20
    canvas = Image.new("L", (N * scale, N * scale), 0)
    draw = ImageDraw.Draw(canvas)
    # region: rows 1..N-2, cols 1..N-2 (inside quiet zone)
    text = "あお"
    # text band: between the top finders and the bottom-left finder
    band_top = (QUIET + FINDER + 2) * scale
    band_bottom = (N - QUIET - FINDER - 2) * scale
    target_h = band_bottom - band_top
    target_w = (N - 2 * QUIET) * scale
    font_size = int(target_h * 1.1)
    font = ImageFont.truetype(FONT, font_size, index=2)  # index 2 = JP
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ratio = min(target_w / tw, target_h / th)
    font_size = int(font_size * ratio)
    font = ImageFont.truetype(FONT, font_size, index=2)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (N * scale - tw) / 2 - bbox[0]
    y = band_top + (target_h - th) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=255)
    # downsample to module grid with box filter, then threshold
    small = canvas.resize((N, N), Image.BOX)
    return small.point(lambda v: 255 if v > 110 else 0)


def build_modules() -> list[list[int]]:
    mask = text_mask(N)
    grid = [[0] * N for _ in range(N)]
    for r in range(N):
        for c in range(N):
            if mask.getpixel((c, r)):
                grid[r][c] = 1

    # Clear finder zones (with 1-module separator) then draw finders.
    def clear(r0, c0):
        for r in range(r0 - 1, r0 + FINDER + 1):
            for c in range(c0 - 1, c0 + FINDER + 1):
                if 0 <= r < N and 0 <= c < N:
                    grid[r][c] = 0

    def finder(r0, c0):
        for r in range(FINDER):
            for c in range(FINDER):
                on_outer = r in (0, FINDER - 1) or c in (0, FINDER - 1)
                on_inner = 2 <= r <= 4 and 2 <= c <= 4
                grid[r0 + r][c0 + c] = 2 if (on_outer or on_inner) else 0

    for (r0, c0) in [(QUIET, QUIET), (QUIET, N - QUIET - FINDER), (N - QUIET - FINDER, QUIET)]:
        clear(r0, c0)
        finder(r0, c0)

    # timing patterns between finders
    for i in range(QUIET + FINDER + 1, N - QUIET - FINDER - 1):
        if i % 2 == 0:
            if grid[QUIET + 6][i] == 0:
                grid[QUIET + 6][i] = 1
            if grid[i][QUIET + 6] == 0:
                grid[i][QUIET + 6] = 1
    # quiet zone
    for i in range(N):
        for q in range(QUIET):
            grid[q][i] = grid[N - 1 - q][i] = grid[i][q] = grid[i][N - 1 - q] = 0
    return grid


def render_png(grid, size: int, path: str):
    scale = 8
    big = size * scale
    img = Image.new("RGB", (big, big), WHITE)
    d = ImageDraw.Draw(img)
    # rounded white card background
    radius = big * 0.18
    d.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=WHITE)
    m = big / N
    for r in range(N):
        for c in range(N):
            v = grid[r][c]
            if v:
                x0, y0 = c * m, r * m
                d.rectangle([x0, y0, x0 + m - 0.5, y0 + m - 0.5],
                            fill=BLUE if v == 2 else BLACK)
    # transparent corners outside rounded rect
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out = out.resize((size, size), Image.LANCZOS)
    out.save(path)


def render_svg(grid, path: str):
    S = 600
    m = S / N
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">',
        f'<rect width="{S}" height="{S}" rx="{S*0.18:.0f}" fill="#ffffff"/>',
    ]
    for r in range(N):
        for c in range(N):
            v = grid[r][c]
            if v:
                color = "#0066cc" if v == 2 else "#000000"
                parts.append(
                    f'<rect x="{c*m:.2f}" y="{r*m:.2f}" width="{m:.2f}" height="{m:.2f}" fill="{color}"/>'
                )
    parts.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(parts))


if __name__ == "__main__":
    grid = build_modules()
    for row in grid:
        print("".join("█" if v else " " for v in row))
    for size in (16, 19, 38, 48, 128):
        render_png(grid, size, os.path.join(ROOT, f"icon{size}.png"))
    render_svg(grid, os.path.join(ROOT, "icon.svg"))
    
