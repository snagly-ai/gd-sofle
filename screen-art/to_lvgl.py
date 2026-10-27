"""Convert the screen-up 68x140 pictures into nice!view LVGL 1-bit images (140x68 native)."""
import sys
from PIL import Image

def encode(path, name):
    user = Image.open(path).convert("1")
    assert user.size == (68, 140), user.size
    native = user.rotate(-90, expand=True)           # screen is mounted turned 90 degrees
    w, h = native.size                                # 140 x 68
    stride = (w + 7) // 8
    data = []
    for y in range(h):
        for bx in range(stride):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                white = x < w and native.getpixel((x, y)) != 0
                byte |= (1 if white else 0) << (7 - bit)
            data.append(byte)
    lines = []
    for i in range(0, len(data), 15):
        lines.append("        " + ", ".join(f"0x{b:02x}" for b in data[i:i + 15]) + ",")
    upper = name.upper()
    return f"""
#ifndef LV_ATTRIBUTE_IMG_{upper}
#define LV_ATTRIBUTE_IMG_{upper}
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_{upper} uint8_t
    {name}_map[] = {{
#if CONFIG_NICE_VIEW_BABYLON_INVERTED
        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#else
        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#endif

{chr(10).join(lines)}
}};

const lv_img_dsc_t {name} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {w},
    .header.h = {h},
    .data_size = {len(data) + 8},
    .data = {name}_map,
}};
"""

out = sys.argv[1]
body = "".join(encode(f"{n}.png", n) for n in
               ("etemenanki", "gardens", "etemenanki_night", "gardens_night"))
header = """/*
 * Screen pictures for the nice!view (1-bit, 140x68, stored turned 90 degrees
 * to match how the display is mounted).
 *   etemenanki       - the ziggurat Etemenanki (left half), day (PC two)
 *   gardens          - Hanging Gardens of Babylon (right half), day (PC two)
 *   etemenanki_night - the same at night (PC one)
 *   gardens_night    - the same at night (PC one)
 * Original pixel art. Regenerate with the scripts in screen-art/ in this repo.
 *
 * SPDX-License-Identifier: MIT
 */

#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif
"""
open(out, "w").write(header + body)
print("wrote", out)
