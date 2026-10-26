# "Sigma aura" server icons: troll face shrunk to the middle, glowing halo along its outline,
# flame-like energy tongues and sparks. Usage: aura_icons.py <src_dir> <out_dir> [preview.png]
import math, os, random, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
PREVIEW = sys.argv[3] if len(sys.argv) > 3 else None
SIZE, FACE = 64, 44

AURAS = [  # name, base icon, outer glow, inner glow, spark color
    ("purple", "server-icon.png", (170, 60, 255), (225, 170, 255), (245, 225, 255)),
    ("cyan", "troll2.png", (0, 200, 255), (150, 245, 255), (230, 255, 255)),
    ("gold", "troll3.png", (255, 170, 0), (255, 230, 120), (255, 250, 220)),
    ("toxic", "troll4.png", (60, 255, 40), (190, 255, 120), (240, 255, 220)),
    ("red", "server-icon.png", (255, 30, 30), (255, 150, 110), (255, 230, 210)),
    ("pink", "troll2.png", (255, 50, 190), (255, 170, 230), (255, 235, 250)),
]


def solid(rgb, mask):
    layer = Image.new("RGBA", mask.size, rgb + (0,))
    layer.putalpha(mask)
    return layer


def scale_alpha(mask, k):
    return mask.point(lambda v: min(255, int(v * k)))


def make(name, base, outer, inner, spark, seed):
    rnd = random.Random(seed)
    face = Image.open(os.path.join(SRC, base)).convert("RGBA").resize((FACE, FACE), Image.LANCZOS)
    off = ((SIZE - FACE) // 2, (SIZE - FACE) // 2 + 1)
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask.paste(face.getchannel("A"), off)
    mask = mask.point(lambda v: 255 if v > 100 else 0)

    # energy tongues: random outward spikes from the outline, blurred into flames
    tongues = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(tongues)
    cx, cy = SIZE / 2, SIZE / 2 + 1
    r0 = FACE / 2 - 1
    for _ in range(16):
        a = rnd.uniform(0, 2 * math.pi)
        length = rnd.uniform(5, 10) * (1.25 if math.sin(a) < 0 else 0.8)  # taller on top, like rising energy
        w = rnd.uniform(0.18, 0.32)
        tip = (cx + math.cos(a) * (r0 + length), cy + math.sin(a) * (r0 + length) - 2)
        b1 = (cx + math.cos(a - w) * r0, cy + math.sin(a - w) * r0)
        b2 = (cx + math.cos(a + w) * r0, cy + math.sin(a + w) * r0)
        d.polygon([b1, tip, b2], fill=rnd.randint(150, 255))
    tongues = tongues.filter(ImageFilter.GaussianBlur(1.6))

    halo_wide = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4.5))
    halo_tight = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5))

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    img.alpha_composite(solid(outer, scale_alpha(ImageChops.lighter(halo_wide, tongues), 1.15)))
    img.alpha_composite(solid(inner, scale_alpha(ImageChops.lighter(halo_tight, scale_alpha(tongues, 0.55)), 1.0)))

    # face, slightly tinted rim from the aura
    face_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    face_layer.paste(face, off)
    img.alpha_composite(face_layer)
    rim = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(3)))
    img.alpha_composite(solid(inner, scale_alpha(rim, 0.55)))

    # sparks: small plus-shaped stars outside the head
    sd = ImageDraw.Draw(img)
    for _ in range(7):
        for _try in range(30):
            a = rnd.uniform(0, 2 * math.pi)
            r = rnd.uniform(r0 + 3, r0 + 9)
            x, y = int(cx + math.cos(a) * r), int(cy + math.sin(a) * r - 1)
            if 1 <= x < SIZE - 1 and 1 <= y < SIZE - 1 and mask.getpixel((x, y)) == 0:
                break
        sd.point((x, y), fill=spark + (255,))
        if rnd.random() < 0.6:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sd.point((x + dx, y + dy), fill=outer + (190,))
    return img


os.makedirs(OUT, exist_ok=True)
icons = []
for i, (name, base, outer, inner, spark) in enumerate(AURAS):
    im = make(name, base, outer, inner, spark, seed=1000 + i)
    im.save(os.path.join(OUT, "aura-%s.png" % name))
    icons.append((name, im))
    print("aura-%s.png" % name)

if PREVIEW:
    # sheet: each icon at 64 (x4) on the dark list background and at 32 (x4) like the server list draws it
    cell = 64 * 4
    sheet = Image.new("RGBA", (len(icons) * (cell + 16) + 16, cell + 32 * 4 + 48), (20, 20, 22, 255))
    for i, (name, im) in enumerate(icons):
        x = 16 + i * (cell + 16)
        sheet.alpha_composite(im.resize((cell, cell), Image.NEAREST), (x, 16))
        small = im.resize((32, 32), Image.LANCZOS).resize((128, 128), Image.NEAREST)
        sheet.alpha_composite(small, (x + (cell - 128) // 2, cell + 32))
    sheet.save(PREVIEW)
