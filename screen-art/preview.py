import sys
from PIL import Image, ImageDraw
def screen(art):
    s = Image.new("1", (68, 160), 1)
    d = ImageDraw.Draw(s)
    # battery like the firmware draws it
    d.rectangle([0, 2, 28, 13], fill=0); d.rectangle([1, 3, 27, 12], fill=1)
    d.rectangle([2, 4, 2 + 20, 11], fill=0); d.rectangle([30, 5, 32, 10], fill=0); d.rectangle([31, 6, 31, 9], fill=1)
    # stand-in for the connection symbol (right aligned)
    for r in (3, 6, 9):
        d.arc([60 - r, 13 - r, 60 + r, 13 + r], 225, 315, fill=0)
    d.rectangle([59, 12, 61, 14], fill=0)
    s.paste(art, (0, 20))
    return s
a = screen(Image.open("etemenanki.png")); b = screen(Image.open("gardens.png"))
canvas = Image.new("L", (68 * 2 + 12, 160), 200)
canvas.paste(a.convert("L"), (0, 0)); canvas.paste(b.convert("L"), (80, 0))
canvas.resize((canvas.width * 4, canvas.height * 4), Image.NEAREST).save(sys.argv[1])
