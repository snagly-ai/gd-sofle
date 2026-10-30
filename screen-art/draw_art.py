"""Draw the nice!view pictures (68 x 140, 1-bit) in screen-up orientation:
day versions (PC two) and night versions (PC one) of both.

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


# ---------------------------------------------------------------------- night
def sky_mask(img):
    """White pixels connected to the top edge: the open sky (and terrace tops)."""
    mask = [[False] * W for _ in range(H)]
    stack = [(x, 0) for x in range(W) if img.getpixel((x, 0)) == PAPER]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < W and 0 <= y < H) or mask[y][x] or img.getpixel((x, y)) != PAPER:
            continue
        mask[y][x] = True
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return mask


def moon(img, d, cx, cy, r):
    """White crescent moon (the night sky is already black)."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAPER)
    d.ellipse([cx - r + 3, cy - r - 2, cx + r + 3, cy + r - 2], fill=INK)


def to_night(img, d, moon_xy, seed):
    """Turn a daytime picture (drawn without sun, birds or clouds) into night:
    black sky, buildings lit white by the moon, a crescent moon and stars."""
    mask = sky_mask(img)
    sky = lambda x, y: 0 <= x < W and 0 <= y < H and mask[y][x]
    rim = [(x, y) for y in range(H) for x in range(W)
           if not mask[y][x] and img.getpixel((x, y)) == INK
           and any(sky(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for y in range(H):
        for x in range(W):
            if mask[y][x]:
                img.putpixel((x, y), INK)
    for x, y in rim:                     # moonlight catches the edges facing the sky
        img.putpixel((x, y), PAPER)

    moon(img, d, *moon_xy, 6)
    rng = random.Random(seed)
    mx, my = moon_xy
    clear = lambda x, y: all(sky(x + a, y + b) for a in range(-2, 3) for b in range(-2, 3))
    placed = 0
    while placed < 22:
        x, y = rng.randint(1, W - 2), rng.randint(1, 75)
        if (x - mx) ** 2 + (y - my) ** 2 < 120 or not clear(x, y):
            continue
        px(img, x, y, PAPER)
        if placed % 7 == 0:              # a few brighter, twinkling stars
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                px(img, x + a, y + b, PAPER)
        placed += 1


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


def etemenanki(night=False, stage=4):
    """The great ziggurat of Babylon: stepped tiers, niched walls, the triple
    stairway on the front and the high temple on top.
    stage: 4 finished, 3 temple missing, 2 three tiers, 1 first tier, 0 foundations."""
    img, d = new()
    cx = 34

    if not night:
        sun(img, d, 13, 15, 5)
        for b in ((44, 12), (52, 9), (58, 15)):
            bird(img, *b)
        cloud(img, d, 50, 30, 20, 7)

    ground_y = 129
    ground(img, d, ground_y)

    widths = [64, 52, 42, 34, 27, 21]
    heights = [20, 13, 11, 10, 9, 8]
    n_tiers = {4: 6, 3: 6, 2: 3, 1: 1, 0: 0}[stage]
    y1 = ground_y
    tiers = []
    for w, h in zip(widths[:n_tiers], heights[:n_tiers]):
        if stage == 1:
            h = 12                                   # first tier only half built
        tiers.append((cx - w // 2, y1 - h, cx + w // 2, y1))
        y1 -= h

    for i, (x0, y0, x1, y1_) in enumerate(tiers):
        d.rectangle([x0, y0, x1, y1_], fill=PAPER, outline=INK)
        for x in range(x0 + 3, x1 - 1, 3):          # niched brick walls
            d.line([x, y0 + 3, x, y1_ - 1], fill=INK)
        shade_x = x1 - (x1 - x0) // 3
        dither_rect(img, shade_x, y0 + 2, x1 - 1, y1_ - 1, 2, phase=i)
        d.rectangle([x0 - 1, y0, x1 + 1, y0 + 1], fill=INK)

    if stage == 0:
        foundations(img, d, cx, ground_y, widths[0])
    else:
        t0x0, t0y0, t0x1, _ = tiers[0]
        if stage >= 2:
            stair_band(img, d, t0x0 + 2, ground_y - 1, cx - 6, t0y0 + 4)
            stair_band(img, d, t0x1 - 2, ground_y - 1, cx + 6, t0y0 + 4)
            top_of_central = tiers[1][1]
        else:
            top_of_central = t0y0
        d.rectangle([cx - 4, top_of_central, cx + 4, ground_y], fill=PAPER)
        d.line([cx - 5, top_of_central, cx - 5, ground_y], fill=INK)
        d.line([cx + 5, top_of_central, cx + 5, ground_y], fill=INK)
        for y in range(top_of_central + 1, ground_y, 2):
            d.line([cx - 4, y, cx + 4, y], fill=INK)
        d.rectangle([cx - 7, ground_y - 3, cx - 6, ground_y], fill=INK)
        d.rectangle([cx + 6, ground_y - 3, cx + 7, ground_y], fill=INK)

        if len(tiers) > 2:
            shrine_base = tiers[-1][1]
            d.rectangle([cx - 2, shrine_base, cx + 2, top_of_central], fill=PAPER)
            d.line([cx - 3, shrine_base, cx - 3, top_of_central], fill=INK)
            d.line([cx + 3, shrine_base, cx + 3, top_of_central], fill=INK)
            for y in range(shrine_base + 1, top_of_central, 2):
                d.line([cx - 2, y, cx + 2, y], fill=INK)

    sx0 = sy0 = sy1 = None
    if stage == 4:
        shrine_base = tiers[-1][1]
        sx0, sx1 = cx - 8, cx + 8
        sy0, sy1 = shrine_base - 12, shrine_base
        d.rectangle([sx0, sy0, sx1, sy1], fill=PAPER, outline=INK)
        dither_rect(img, sx0 + 1, sy0 + 3, sx1 - 1, sy1 - 1, 2)
        d.line([sx0, sy0 + 2, sx1, sy0 + 2], fill=INK)
        for x in range(sx0, sx1 + 1, 3):
            d.rectangle([x, sy0 - 2, x + 1, sy0], fill=INK)
        d.rectangle([cx - 2, sy0 + 5, cx + 2, sy1], fill=INK)
        px(img, cx - 2, sy0 + 5, PAPER)
        px(img, cx + 2, sy0 + 5, PAPER)
    elif stage == 3:
        tx0, ty0, tx1, _ = tiers[-1]
        scaffold(img, d, tx0 + 1, tx1 - 1, ty0 - 12, ty0)       # where the temple goes
        bricks(img, d, tx0 + 2, ty0)
        worker(img, tx1 - 4, ty0, carry=True)
    elif stage == 2:
        tx0, ty0, tx1, _ = tiers[-1]
        scaffold(img, d, tx0 + 3, tx1 - 3, ty0 - 11, ty0)       # next tier going up
        for wx, wy in ((t0x0 + 8, ground_y - 6), (t0x1 - 10, ground_y - 6), (cx - 2, tiers[1][1] + 6)):
            worker(img, wx, wy, carry=True)                      # hauling bricks up the stairs
        bricks(img, d, 2, ground_y)
        bricks(img, d, W - 9, ground_y)
    elif stage == 1:
        t0x0, t0y0, t0x1, _ = tiers[0]
        shaduf(img, d, 8, ground_y, t0y0)
        bricks(img, d, t0x1 - 10, t0y0)
        worker(img, t0x1 - 3, t0y0)
        worker(img, 56, ground_y)
        bricks(img, d, 60, ground_y)

    if night:
        to_night(img, d, (14, 14), seed=11)
        if stage == 4:
            d.rectangle([cx - 1, sy0 + 7, cx + 1, sy1 - 1], fill=PAPER)   # lamp-lit temple door
    return img


# --------------------------------------------------------------- construction
def scaffold(img, d, x0, x1, y0, y1):
    """Wooden scaffolding: poles every 5 px, lashed cross-bars every 4 px."""
    for x in range(x0, x1 + 1, 5):
        d.line([x, y0, x, y1], fill=INK)
    for y in range(y0 + 1, y1, 4):
        d.line([x0, y, x1, y], fill=INK)
    d.line([x0, y1 - 1, min(x0 + 5, x1), y0 + 1], fill=INK)  # diagonal brace


def bricks(img, d, x, base_y):
    """Small stack of mud bricks standing on base_y."""
    for row, (dx, w) in enumerate(((0, 7), (1, 5), (2, 3))):
        y = base_y - 2 - row * 2
        d.rectangle([x + dx, y, x + dx + w - 1, y + 1], fill=INK)
        px(img, x + dx + w // 2, y, PAPER)


def worker(img, x, feet_y, carry=False):
    """Tiny labourer, 6 px tall, feet on feet_y; optionally with a brick load."""
    px(img, x, feet_y - 6)                                # head
    for y in range(feet_y - 5, feet_y - 2):               # body
        px(img, x, y)
    px(img, x - 1, feet_y - 1); px(img, x + 1, feet_y - 1)  # legs
    px(img, x - 1, feet_y - 2); px(img, x + 1, feet_y - 2)
    if carry:
        for a in (-1, 0, 1):                              # basket on the head
            px(img, x + a, feet_y - 8)
        px(img, x - 1, feet_y - 7); px(img, x + 1, feet_y - 7)
    else:
        px(img, x - 1, feet_y - 4); px(img, x + 1, feet_y - 5)  # arms


def shaduf(img, d, x, ground_y, top_y):
    """Lifting crane: an upright post with a pivoting beam and a bucket."""
    post_top = top_y - 10
    d.line([x, ground_y, x, post_top], fill=INK)
    d.line([x + 1, ground_y, x + 1, post_top], fill=INK)
    d.line([x - 5, post_top + 6, x + 14, post_top - 4], fill=INK)   # beam
    d.rectangle([x - 7, post_top + 5, x - 4, post_top + 8], fill=INK)  # counterweight
    d.line([x + 14, post_top - 4, x + 14, post_top + 4], fill=INK)  # rope
    d.rectangle([x + 13, post_top + 5, x + 15, post_top + 7], fill=INK)  # bucket of bricks


def foundations(img, d, cx, ground_y, width):
    """Footprint marked out with stakes and string, first course of bricks laid."""
    x0, x1 = cx - width // 2, cx + width // 2
    d.rectangle([x0, ground_y - 3, x1, ground_y], fill=PAPER, outline=INK)
    for x in range(x0 + 2, x1 - 1, 4):
        d.line([x, ground_y - 3, x, ground_y - 2], fill=INK)
    for x in (x0 - 1, cx, x1 + 1):                        # stakes
        d.line([x, ground_y - 8, x, ground_y - 4], fill=INK)
    d.line([x0 - 1, ground_y - 7, x1 + 1, ground_y - 7], fill=INK)  # string line
    bricks(img, d, x0 + 4, ground_y - 3)
    bricks(img, d, x1 - 12, ground_y - 3)
    worker(img, cx - 8, ground_y - 3, carry=True)
    worker(img, cx + 9, ground_y - 3)


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


def sapling(img, x, base_y):
    for y in range(base_y - 4, base_y):
        px(img, x, y)
    for a, b in ((-1, -4), (1, -5), (-2, -5), (2, -6), (-1, -6), (0, -6), (1, -4)):
        px(img, x + a, base_y + b)


def hanging_gardens(night=False, stage=4):
    """stage: 4 finished, 3 roof garden bare, 2 two terraces, 1 arches only,
    0 foundations by the river."""
    img, d = new()
    rng = random.Random(5)
    cx = 34

    if not night:
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
    n_levels = {4: 4, 3: 4, 2: 2, 1: 1, 0: 0}[stage]
    y1 = river_y - 1
    levels = []
    for w, h in zip(widths[:n_levels], heights[:n_levels]):
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
            if night and (ax // 6 + i) % 3 == 0:          # a few lamp-lit arches
                d.rectangle([ax + 1, top + 4, ax + 2, y1_ - 3], fill=PAPER)
        # central stairway
        for yy in range(y0 + 3, y1_, 2):
            d.line([cx - 3, yy, cx + 3, yy], fill=INK)
        d.line([cx - 4, y0 + 2, cx - 4, y1_], fill=INK)
        d.line([cx + 4, y0 + 2, cx + 4, y1_], fill=INK)
        greenery = (stage == 4 or (stage == 3 and i < 3) or (stage == 2 and i == 0))
        if greenery:
            plant_band(img, d, x0, x1, y0, rng, vine_max=9)
        else:
            d.rectangle([x0 - 1, y0, x1 + 1, y0 + 1], fill=INK)   # bare terrace ledge

    if stage == 4:                               # trees on the roof garden
        tx0, ty0, tx1, _ = levels[-1]
        round_tree(img, d, tx0 + 5, ty0 - 4, 4)
        round_tree(img, d, tx1 - 6, ty0 - 4, 4)
        palm(img, d, cx, ty0 - 4, 22, 1)
    elif stage == 3:                             # roof garden still bare
        tx0, ty0, tx1, _ = levels[-1]
        scaffold(img, d, tx0 + 2, tx1 - 2, ty0 - 9, ty0)
        sapling(img, tx0 + 4, ty0)
        worker(img, tx1 - 3, ty0, carry=True)
    elif stage == 2:
        tx0, ty0, tx1, _ = levels[-1]
        for x in range(tx0 + 4, tx1 - 2, 8):
            if abs(x - cx) > 5:
                sapling(img, x, ty0)
        scaffold(img, d, cx - 21, cx + 21, ty0 - 12, ty0)     # next terrace going up
        worker(img, cx - 13, ty0, carry=True)
        worker(img, cx + 12, ty0)
        bricks(img, d, 2, river_y - 1)
    elif stage == 1:
        tx0, ty0, tx1, _ = levels[0]
        shaduf(img, d, 6, river_y, ty0)
        bricks(img, d, tx0 + 6, ty0)
        worker(img, tx1 - 6, ty0, carry=True)
        worker(img, cx + 9, ty0)
    else:
        foundations(img, d, cx, river_y - 1, widths[0] - 4)

    if night:
        to_night(img, d, (54, 13), seed=7)
    return img


STAGES = range(5)   # 0 foundations ... 4 finished

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for night in (False, True):
        tod = "night" if night else "day"
        for stage in STAGES:
            etemenanki(night, stage).save(f"{out}/etemenanki_{tod}_{stage}.png")
            hanging_gardens(night, stage).save(f"{out}/gardens_{tod}_{stage}.png")
