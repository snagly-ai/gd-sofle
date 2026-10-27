# Screen pictures

Pixel art for the nice!view screens (68 x 140, black and white), drawn by code.

- `draw_art.py` draws `etemenanki.png` (left half) and `gardens.png` (right half),
  plus `_night` versions of both. Night shows while PC one (Bluetooth profile 1)
  is active, day while PC two is active.
- `preview.py preview.png` shows both screens with the status strip, 4x size.
- `to_lvgl.py art.c` converts the PNGs into the display's image format; copy
  the result to `boards/shields/nice_view_babylon/widgets/art.c`.

You can also draw your own 68 x 140 black-and-white PNGs and run `to_lvgl.py`.
Needs Python with Pillow.
