# Builds glyph-widths.bin for FastMOTD centering from a vanilla client jar + unifont assets.
# Format: two 65536-byte tables (minecraft:default, then minecraft:uniform), one byte per BMP codepoint:
#   bits 0-6 = advance in half pixels, bit 7 = unihex glyph (bold adds 0.5 px instead of 1 px), 0 = missing glyph.
import io, json, sys, zipfile
from PIL import Image

jar = zipfile.ZipFile(sys.argv[1])
unifont = zipfile.ZipFile(sys.argv[2])
unifont_json = json.load(open(sys.argv[3]))
out_path = sys.argv[4]

SPACE = {}
for p in json.loads(jar.read("assets/minecraft/font/include/space.json"))["providers"]:
    for ch, adv in p["advances"].items():
        SPACE[ord(ch)] = adv

BITMAP = {}
for p in json.loads(jar.read("assets/minecraft/font/include/default.json"))["providers"]:
    if p["type"] != "bitmap":
        continue
    img = Image.open(io.BytesIO(jar.read("assets/minecraft/textures/" + p["file"].split(":")[1]))).convert("RGBA")
    rows = p["chars"]
    cw, ch = img.width // len(rows[0]), img.height // len(rows)
    scale = p.get("height", 8) / ch
    px = img.load()
    for r, row in enumerate(rows):
        for c, chr_ in enumerate(row):
            cp = ord(chr_)
            if cp == 0 or cp in BITMAP:
                continue
            w = 0
            for x in range(cw - 1, -1, -1):
                if any(px[c * cw + x, r * ch + y][3] for y in range(ch)):
                    w = x + 1
                    break
            BITMAP[cp] = int(0.5 + w * scale) + 1

overrides = []
for p in unifont_json["providers"]:
    if p["type"] == "unihex" and not p.get("filter"):
        for o in p.get("size_overrides", []):
            overrides.append((ord(o["from"]), ord(o["to"]), o["left"], o["right"]))

UNI = {}
for n in unifont.namelist():
    if not n.endswith(".hex"):
        continue
    for line in unifont.read(n).decode().splitlines():
        cps, bits = line.split(":")
        cp = int(cps, 16)
        if cp > 0xFFFF:
            continue
        ov = next(((l, r) for a, b, l, r in overrides if a <= cp <= b), None)
        if ov:
            width = ov[1] - ov[0] + 1
        else:
            w = len(bits) * 4 // 16
            cols = [x for x in range(w) if any(int(bits[i * w // 4:(i + 1) * w // 4], 16) >> (w - 1 - x) & 1 for i in range(16))]
            width = (cols[-1] - cols[0] + 1) if cols else 0
        UNI[cp] = width // 2 + 1


def table(use_bitmap):
    t = bytearray(65536)
    for cp in range(65536):
        if cp in SPACE:
            t[cp] = min(127, SPACE[cp] * 2)
        elif use_bitmap and cp in BITMAP:
            t[cp] = min(127, BITMAP[cp] * 2)
        elif cp in UNI:
            t[cp] = 0x80 | min(127, UNI[cp] * 2)
    return t


open(out_path, "wb").write(bytes(table(True)) + bytes(table(False)))
print("bitmap", len(BITMAP), "unihex", len(UNI), "A", BITMAP.get(ord("A")), "Б", BITMAP.get(ord("Б")), "☠", UNI.get(0x2620))
