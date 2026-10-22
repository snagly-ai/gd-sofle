"""Draw the two nice!view pictures (68 x 140, 1-bit) in screen-up orientation.

0 = black ink, 1 = white background (matches the nice!view palette).
"""
import math
import random
import sys

from PIL import Image, ImageDraw

W, H = 68, 140
INK, PAPER = 0, 1


def new():
    img = Image.new("1", (W, H), PAPER)
    return img, ImageDraw.Draw(img)


def px(img, x, y, c=INK):
    if 0 <= x < W and 0 <= y < H:
        img.putpixel((x, y), c)


def dither_rect(img, x0, y0, x1, y1, density=2, phase=0):
    """Checker/sparse pattern. density 2 = 50% checker, 3/4 = sparser."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if density == 2:
                on = (x + y + phase) % 2 == 0
            else:
                on = (x % density == (y // 1 + phase) % density) and (y % 2 == 0)
            if on:
                px(img, x, y)


def sun(img, d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, fill=PAPER)
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], outline=None, fill=PAPER)
    for k in range(8):
        a = k * math.pi / 4
        x0, y0 = cx + math.cos(a) * (r + 2), cy + math.sin(a) * (r + 2)
        x1, y1 = cx + math.cos(a) * (r + 4), cy + math.sin(a) * (r + 4)
        d.line([round(x0), round(y0), round(x1), round(y1)], fill=INK)


def bird(img, x, y):
    for dx, dy in ((-2, -1), (-1, 0), (0, 1), (1, 0), (2, -1)):
        px(img, x + dx, y + dy)


def cloud(img, d, cx, cy, w, h):
    """White puffy cloud with black outline (covers what is behind it)."""
    puffs = [(-w // 2 + h // 2, 0, h // 2 + 1), (-w // 6, -h // 3, h // 2 + 2),
             (w // 6, -h // 4, h // 2 + 1), (w // 2 - h // 2, 0, h // 2)]
    mask = Image.new("1", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for ox, oy, r in puffs:
        md.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r], fill=1)
    md.rectangle([cx - w // 2 + h // 2, cy - 1, cx + w // 2 - h // 2, cy + h // 2], fill=1)
    for y in range(H):
        for x in range(W):
            if mask.getpixel((x, y)):
                edge = any(
                    not (0 <= x + a < W and 0 <= y + b < H and mask.getpixel((x + a, y + b)))
                    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                img.putpixel((x, y), INK if edge else PAPER)
    # soft shading along the cloud's underside
    for y in range(H):
        for x in range(W):
            if mask.getpixel((x, y)) and img.getpixel((x, y)) == PAPER:
                if 0 <= y + 2 < H and not mask.getpixel((x, y + 2)) and (x + y) % 2 == 0:
                    img.putpixel((x, y), INK)


def ground(img, d, y0):
    d.line([0, y0, W - 1, y0], fill=INK)
    dither_rect(img, 0, y0 + 1, W - 1, H - 1, 2)
    for x in range(0, W, 9):
        d.line([x, y0 + 3, x + 4, y0 + 3], fill=PAPER)
    for x in range(4, W, 11):
        d.line([x, y0 + 7, x + 3, y0 + 7], fill=PAPER)


# ------------------------------------------------------------------- Etemenanki
def stair_band(img, d, xa, ya, xb, yb):
    """Diagonal flight of steps from (xa, ya) up to (xb, yb), 3 px thick."""
    n = abs(xb - xa)
    for s in range(n + 1):
        x = xa + s if xb > xa else xa - s
        y = round(ya + (yb - ya) * s / n)
        px(img, x, y - 3, INK)
        px(img, x, y - 2, PAPER)
        px(img, x, y - 1, PAPER)
        px(img, x, y, INK)
        if s % 2 == 0:
            px(img, x, y - 1, INK)      # step edges


def etemenanki():
    """The great ziggurat of Babylon: stepped tiers, niched walls, the triple
    stairway on the front and the high temple on top."""
    img, d = new()
    cx = 34

    sun(img, d, 13, 15, 5)
    for b in ((44, 12), (52, 9), (58, 15)):
        bird(img, *b)
    cloud(img, d, 50, 30, 20, 7)

    ground_y = 129
    ground(img, d, ground_y)

    widths = [64, 52, 42, 34, 27, 21]
    heights = [20, 13, 11, 10, 9, 8]
    y1 = ground_y
    tiers = []
    for w, h in zip(widths, heights):
        tiers.append((cx - w // 2, y1 - h, cx + w // 2, y1))
        y1 -= h

    for i, (x0, y0, x1, y1_) in enumerate(tiers):
        d.rectangle([x0, y0, x1, y1_], fill=PAPER, outline=INK)
        # niched brick walls: vertical recesses
        for x in range(x0 + 3, x1 - 1, 3):
            d.line([x, y0 + 3, x, y1_ - 1], fill=INK)
        # shadow on the right-hand third
        shade_x = x1 - (x1 - x0) // 3
        dither_rect(img, shade_x, y0 + 2, x1 - 1, y1_ - 1, 2, phase=i)
        # terrace ledge
        d.rectangle([x0 - 1, y0, x1 + 1, y0 + 1], fill=INK)

    # the triple stairway: two side flights along the front of the first stage
    t0x0, t0y0, t0x1, _ = tiers[0]
    stair_band(img, d, t0x0 + 2, ground_y - 1, cx - 6, t0y0 + 4)
    stair_band(img, d, t0x1 - 2, ground_y - 1, cx + 6, t0y0 + 4)

    # ...and the great central flight running straight up to the second stage
    top_of_central = tiers[1][1]
    d.rectangle([cx - 4, top_of_central, cx + 4, ground_y], fill=PAPER)
    d.line([cx - 5, top_of_central, cx - 5, ground_y], fill=INK)
    d.line([cx + 5, top_of_central, cx + 5, ground_y], fill=INK)
    for y in range(top_of_central + 1, ground_y, 2):
        d.line([cx - 4, y, cx + 4, y], fill=INK)
    d.rectangle([cx - 7, ground_y - 3, cx - 6, ground_y], fill=INK)   # gate posts
    d.rectangle([cx + 6, ground_y - 3, cx + 7, ground_y], fill=INK)

    # narrower path continuing up the upper stages to the temple
    shrine_base = tiers[-1][1]
    d.rectangle([cx - 2, shrine_base, cx + 2, top_of_central], fill=PAPER)
    d.line([cx - 3, shrine_base, cx - 3, top_of_central], fill=INK)
    d.line([cx + 3, shrine_base, cx + 3, top_of_central], fill=INK)
    for y in range(shrine_base + 1, top_of_central, 2):
        d.line([cx - 2, y, cx + 2, y], fill=INK)

    # the high temple of Marduk on the summit (glazed brick, so darker)
    sx0, sx1 = cx - 8, cx + 8
    sy0, sy1 = shrine_base - 12, shrine_base
    d.rectangle([sx0, sy0, sx1, sy1], fill=PAPER, outline=INK)
    dither_rect(img, sx0 + 1, sy0 + 3, sx1 - 1, sy1 - 1, 2)
    d.line([sx0, sy0 + 2, sx1, sy0 + 2], fill=INK)
    for x in range(sx0, sx1 + 1, 3):                     # stepped battlements
        d.rectangle([x, sy0 - 2, x + 1, sy0], fill=INK)
    d.rectangle([cx - 2, sy0 + 5, cx + 2, sy1], fill=INK)  # doorway
    px(img, cx - 2, sy0 + 5, PAPER)
    px(img, cx + 2, sy0 + 5, PAPER)

    return img


# ------------------------------------------------------- Hanging Gardens of Babylon
def plant_band(img, d, x0, x1, y, rng, vine_max):
    """Thick band of greenery on a terrace edge with vines draping down the wall."""
    d.rectangle([x0, y - 2, x1, y + 1], fill=INK)
    x = x0
    while x <= x1:                              # bushy top outline
        r = rng.choice((2, 2, 3))
        d.ellipse([x - r, y - 2 - r, x + r, y - 2 + r], fill=INK)
        x += r + 1
    for x in range(x0, x1 + 1):                 # leaf speckles
        if rng.random() < 0.3:
            px(img, x, y - 1 - rng.randint(0, 2), PAPER)
    for vx in range(x0 + 1, x1, 2):             # vines
        if rng.random() < 0.75:
            length = rng.randint(3, vine_max)
            for k in range(length):
                px(img, vx, y + 2 + k, INK)
                if k % 3 == 1:
                    px(img, vx + (1 if (vx + k) % 2 else -1), y + 2 + k, INK)


def round_tree(img, d, x, base_y, r):
    d.line([x, base_y, x, base_y - r], fill=INK)
    d.line([x + 1, base_y, x + 1, base_y - r], fill=INK)
    cy = base_y - r - r
    d.ellipse([x - r, cy - r, x + r + 1, cy + r], fill=PAPER, outline=INK)
    for yy in range(cy - r + 1, cy + r):
        for xx in range(x - r + 1, x + r + 1):
            inside = (xx - x - 0.5) ** 2 + (yy - cy) ** 2 < (r - 1) ** 2
            if inside and (xx + yy) % 2 == 0 and xx > x - r // 3:
                px(img, xx, yy, INK)


def palm(img, d, x, base_y, height, lean):
    pts = [(round(x + lean * (k / height) ** 2 * 3), base_y - k) for k in range(height + 1)]
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=INK)
        d.line([(a[0] + 1, a[1]), (b[0] + 1, b[1])], fill=INK)
    for k in range(1, height, 3):
        px(img, pts[k][0] + 2, pts[k][1], INK)
    tx, ty = pts[-1]
    for ang, ln in ((175, 11), (140, 9), (105, 7), (75, 7), (40, 9), (5, 11)):
        a = math.radians(ang)
        prev = (tx, ty)
        for s in range(1, ln + 1):
            cur = (round(tx + math.cos(a) * s), round(ty - math.sin(a) * s + s * s / 22.0))
            d.line([prev, cur], fill=INK)
            if s >= 4 and s % 2 == 0:
                px(img, cur[0], cur[1] + 1, INK)
            prev = cur
    d.rectangle([tx - 1, ty - 1, tx + 2, ty + 1], fill=INK)


def hanging_gardens():
    img, d = new()
    rng = random.Random(5)
    cx = 34

    sun(img, d, 55, 12, 5)
    for b in ((10, 9), (17, 14), (24, 8)):
        bird(img, *b)

    river_y = 130
    d.line([0, river_y, W - 1, river_y], fill=INK)
    for y in range(river_y + 2, H, 3):
        for x in range(W):
            if (x + (y // 3) * 3) % 8 < 3:
                px(img, x, y + (1 if (x // 4) % 2 else 0), INK)

    widths = [66, 54, 42, 30]
    heights = [22, 20, 18, 16]
    y1 = river_y - 1
    levels = []
    for w, h in zip(widths, heights):
        levels.append((cx - w // 2, y1 - h, cx + w // 2, y1))
        y1 -= h

    for i, (x0, y0, x1, y1_) in enumerate(levels):
        d.rectangle([x0, y0, x1, y1_], fill=PAPER, outline=INK)
        # colonnade of arches (dark openings), leaving room for the central stair
        top = y0 + 8
        for ax in range(x0 + 3, x1 - 3, 6):
            if abs((ax + 2) - cx) < 5:
                continue
            d.rectangle([ax, top + 2, ax + 3, y1_ - 2], fill=INK)
            d.line([ax + 1, top + 1, ax + 2, top + 1], fill=INK)
            for yy in range(top + 4, y1_ - 2, 2):
                px(img, ax + 1, yy, PAPER)
        # central stairway
        for yy in range(y0 + 3, y1_, 2):
            d.line([cx - 3, yy, cx + 3, yy], fill=INK)
        d.line([cx - 4, y0 + 2, cx - 4, y1_], fill=INK)
        d.line([cx + 4, y0 + 2, cx + 4, y1_], fill=INK)
        plant_band(img, d, x0, x1, y0, rng, vine_max=9)

    # trees on the roof garden
    tx0, ty0, tx1, _ = levels[-1]
    round_tree(img, d, tx0 + 5, ty0 - 4, 4)
    round_tree(img, d, tx1 - 6, ty0 - 4, 4)
    palm(img, d, cx, ty0 - 4, 22, 1)
    return img


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    etemenanki().save(f"{out}/etemenanki.png")
    hanging_gardens().save(f"{out}/gardens.png")
