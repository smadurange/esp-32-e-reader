"""
Converts PDFs to bitmaps for e-paper displays using Poppler and ImageMagick.

Usage: python -m doctoebm -o [path] [document]
       o: output directory
       document: path to PDF
"""
import io
import os
import re
import sys
import getopt
import subprocess
from pathlib import Path

dpi = "300"
screen_size = "480x800!"

doc = sys.argv[-1]
argv = sys.argv[1:-1]
opts, args = getopt.getopt(argv, "o:")

output_path = "."
for o, a in opts:
    if o == "-o":
        output_path = a.rstrip("/")
        if not os.path.exists(output_path):
            os.makedirs(output_path)

root = output_path + "/doc"
print("Converting PDF to JPEGs...")
subprocess.run(["pdftoppm", "-jpeg", "-progress", "-r", dpi, "-thinlinemode", "solid", doc, root])
print("Finished converting PDF to JPEGs.")

paths = list(Path(output_path).glob('*.jpg'))

print("Determining page size...")
w = h = 0
dx = dy = sys.maxsize
for p in paths:
    rv = subprocess.run(
            ["magick", p, "-trim", "-format", "%[fx:w] %[fx:h] %[fx:page.x] %[fx:page.y]", "info:"],
            capture_output=True,
            text=True
         )
    area = [int(x) for x in rv.stdout.split()]
    if w < area[0]:
        w = area[0]
    if h < area[1]:
        h = area[1]
    if dx > area[2]:
        dx = area[2]
    if dy > area[3]:
        dy = area[3]

crop = "{}x{}+{}+{}".format(w, h, dx, dy)
print("Crop area: {}".format(crop))

for i, p in enumerate(paths):
    print("Processing page {}/{}...".format(i+1, len(paths)))
    jpg = str(p)
    txt = jpg.replace(".jpg", ".txt")
    ebm = jpg.replace(".jpg", ".ebm")

    subprocess.run(["magick", jpg, "-crop", crop, jpg])
    subprocess.run(["convert", jpg, "-resize", screen_size, jpg]) 
    subprocess.run(["convert", jpg, "-threshold", "80%", jpg]) 
    subprocess.run(["mogrify", "-rotate", "-90", jpg])
    subprocess.run(["convert", jpg, "-depth", "1", "-format", "'txt'", txt])

    with open(txt, "r") as src, open(ebm, "wb") as dst:
        total = 0
        n = 7
        x = 0xFF
        count = 0
        src.readline()
        for line in src:
            px = re.search("\([^\)]+\)", line).group()
            if px == "(0)":                        
                x &= ~(1 << n)
            n -= 1
            if n < 0:
                dst.write(x.to_bytes(1))
                count += 1
                total += 1
                if count >= 12:
                    count = 0
                n = 7
                x = 0xFF
    os.remove(txt)
    os.remove(jpg)

