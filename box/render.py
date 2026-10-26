# Approximate vanilla server-list render of status JSON using the real 26.3 client font + atlases.
import base64, io, json, sys, zipfile
from PIL import Image
sys.path.insert(0, "/home/bomj/src/motdtools")
import ping

JAR = zipfile.ZipFile("/tmp/mcjars/client-26.3.jar")
S = 2  # image px per GUI px (unifont needs half pixels)


def tex(path):
    return Image.open(io.BytesIO(JAR.read("assets/minecraft/textures/" + path + ".png"))).convert("RGBA")


class Glyph:
    def __init__(self, img, adv, top, bold_off=1):
        self.img, self.adv, self.top, self.bold_off = img, adv, top, bold_off


GLYPHS = {}


def load_bitmap(p):
    f = p["file"].split(":")[1]
    img = Image.open(io.BytesIO(JAR.read("assets/minecraft/textures/" + f))).convert("RGBA")
    rows = p["chars"]
    cw = img.width // len(rows[0]); ch = img.height // len(rows)
    h = p.get("height", 8); sc = h / ch
    for r, row in enumerate(rows):
        for c, chr_ in enumerate(row):
            if chr_ in GLYPHS or chr_ == "\0":
                continue
            cell = img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            w = 0
            for x in range(cw - 1, -1, -1):
                if any(cell.getpixel((x, y))[3] for y in range(ch)):
                    w = x + 1; break
            adv = int(0.5 + w * sc) + 1
            g = cell.crop((0, 0, max(w, 1), ch)).resize((max(1, int(w * sc * S)), int(h * S)), Image.NEAREST)
            GLYPHS[chr_] = Glyph(g, adv, 7 - p["ascent"])


UNI = {}


def load_unihex():
    z = zipfile.ZipFile("/tmp/mcjars/unifont.zip")
    for n in z.namelist():
        if n.endswith(".hex"):
            for line in z.read(n).decode().splitlines():
                cp, bits = line.split(":")
                UNI[int(cp, 16)] = bits


UCACHE = {}


def uni_glyph(ch):
    if ch in UCACHE:
        return UCACHE[ch]
    bits = UNI.get(ord(ch))
    if bits is None:
        return None
    w = len(bits) * 4 // 16
    rows = [int(bits[i * w // 4:(i + 1) * w // 4], 16) for i in range(16)]
    cols = [x for x in range(w) if any(r >> (w - 1 - x) & 1 for r in rows)]
    if not cols:
        g = Glyph(Image.new("RGBA", (1, 16)), 1, 0, 0.5)
    else:
        l, rgt = cols[0], cols[-1]
        img = Image.new("RGBA", (rgt - l + 1, 16))
        for y, r in enumerate(rows):
            for x in range(l, rgt + 1):
                if r >> (w - 1 - x) & 1:
                    img.putpixel((x - l, y), (255, 255, 255, 255))
        g = Glyph(img.resize((max(1, img.width * S // 2), 16 * S // 2), Image.NEAREST), (rgt - l + 1) // 2 + 1, 0, 0.5)
    UCACHE[ch] = g
    return g


for p in json.loads(JAR.read("assets/minecraft/font/include/default.json"))["providers"]:
    if p["type"] == "bitmap":
        load_bitmap(p)
load_unihex()

NAMED = {"black": 0x000000, "dark_blue": 0x0000AA, "dark_green": 0x00AA00, "dark_aqua": 0x00AAAA, "dark_red": 0xAA0000,
         "dark_purple": 0xAA00AA, "gold": 0xFFAA00, "gray": 0xAAAAAA, "dark_gray": 0x555555, "blue": 0x5555FF,
         "green": 0x55FF55, "aqua": 0x55FFFF, "red": 0xFF5555, "light_purple": 0xFF55FF, "yellow": 0xFFFF55, "white": 0xFFFFFF}


def col(c):
    return NAMED[c] if c in NAMED else int(c[1:], 16)


def glyph(ch, font):
    if font == "minecraft:uniform":
        return uni_glyph(ch)
    if ch == " ":
        return Glyph(Image.new("RGBA", (1, 1)), 4, 0)
    return GLYPHS.get(ch) or uni_glyph(ch)


def sprite_img(c):
    atlas = c.get("atlas", "minecraft:blocks").split(":")[1]
    sp = c["sprite"].split(":")[-1]
    t = tex(("gui/sprites/" + sp) if atlas == "gui" else sp)
    t = t.crop((0, 0, t.width, t.width))
    return t.resize((8 * S, 8 * S), Image.NEAREST)


def runs(c, st, out):
    if isinstance(c, str):
        c = {"text": c}
    if isinstance(c, list):
        for x in c:
            runs(x, st, out)
        return
    st = dict(st)
    for k in ("color", "bold", "font", "shadow_color"):
        if k in c:
            st[k] = c[k]
    if "sprite" in c:
        out.append(("sprite", c, st))
    for ch in c.get("text", ""):
        out.append(("ch", ch, st))
    for x in c.get("extra", []):
        runs(x, st, out)


def tint(img, rgb, a=255):
    out = Image.new("RGBA", img.size, ((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, 0))
    out.putalpha(img.getchannel("A").point(lambda v: v * a // 255))
    return out


def mul(img, rgb, a=255):
    r, g, b = (rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255
    px = img.load(); out = img.copy(); po = out.load()
    for yy in range(img.height):
        for xx in range(img.width):
            pr, pg, pb, pa = px[xx, yy]
            po[xx, yy] = (pr * r // 255, pg * g // 255, pb * b // 255, pa * a // 255)
    return out


def draw_text(canvas, x, y, comp, base="#AAAAAA"):
    items = []
    runs(comp, {"color": base}, items)
    lines = [[]]
    for it in items:
        if it[0] == "ch" and it[1] == "\n":
            lines.append([]); continue
        lines[-1].append(it)
    for li, line in enumerate(lines):
        cx = x; cy = y + li * 9
        for kind, v, st in line:
            if kind == "sprite":
                img = sprite_img(v)
                c = col(st.get("color", "white"))
                if "shadow_color" in st:
                    sc = st["shadow_color"] & 0xFFFFFFFF; sha = sc >> 24; shc = sc & 0xFFFFFF
                else:
                    sha, shc = 255, (c & 0xFCFCFC) >> 2
                if sha:
                    canvas.alpha_composite(mul(img, shc, sha), (int((cx + 1) * S), int((cy + 1) * S)))
                canvas.alpha_composite(mul(img, c), (int(cx * S), int(cy * S))); cx += 8; continue
            g = glyph(v, st.get("font"))
            if g is None:
                cx += 6; continue
            c = col(st.get("color", "white")); bold = st.get("bold")
            if "shadow_color" in st:
                sc = st["shadow_color"] & 0xFFFFFFFF
                sh = tint(g.img, sc & 0xFFFFFF, sc >> 24)
            else:
                sh = tint(g.img, (c & 0xFCFCFC) >> 2)
            fg = tint(g.img, c)
            offs = (0, 1) if bold else (0,)
            for dx in offs:
                canvas.alpha_composite(sh, (int((cx + dx + 1) * S), int((cy + g.top + 1) * S)))
            for dx in offs:
                canvas.alpha_composite(fg, (int((cx + dx) * S), int((cy + g.top) * S)))
            cx += g.adv + (g.bold_off if bold else 0)
    return cx


def width(comp):
    items = []
    runs(comp, {}, items)
    w = 0
    for kind, v, st in items:
        if kind == "sprite":
            w += 8
        else:
            g = glyph(v, st.get("font"))
            w += (g.adv if g else 6) + ((g.bold_off if g else 1) if st.get("bold") else 0)
    return w


def row(resp, name, caption):
    W, H = 305, 36 + 12
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    draw_text(img, 0, 0, {"text": caption, "color": "#7FA0FF"})
    oy = 12
    if "favicon" in resp:
        fav = Image.open(io.BytesIO(base64.b64decode(resp["favicon"].split(",")[1]))).convert("RGBA")
        img.alpha_composite(fav.resize((32 * S, 32 * S), Image.NEAREST), (0, oy * S))
    draw_text(img, 35, oy + 1, {"text": name, "color": "white"})
    draw_text(img, 35, oy + 12, resp["description"], base="#808080")
    pl = {"extra": [{"text": str(resp["players"]["online"]), "color": "gray"}, {"text": "/", "color": "dark_gray"},
                    {"text": str(resp["players"]["max"]), "color": "gray"}]}
    pi = tex("gui/sprites/server_list/ping_5")
    img.alpha_composite(pi.resize((pi.width * S, pi.height * S), Image.NEAREST), ((W - 15) * S, oy * S))
    draw_text(img, W - 15 - 2 - width(pl), oy + 1, pl)
    return img


if __name__ == "__main__":
    host, port, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    cases = [(775, "26.x / 1.21.11 (774+)"), (773, "1.21.9-1.21.10 (773)"), (770, "1.21.4-1.21.8 (769-772)"), (767, "1.21.3 and older (-768)"), (47, "1.8 (47)")]
    if len(sys.argv) > 4:
        cases = [(775, c) for c in sys.argv[4:]]
    rows = []
    for p, cap in cases:
        for _ in range(30):
            r = ping.ping(host, port, p)
            if not any(ord(ch) > 0xFFFF for ch in json.dumps(r["description"], ensure_ascii=False)):
                break
        rows.append(row(r, "BomjPVP", cap))
    pad = 6
    total_h = sum(r.height // S for r in rows) + pad * (len(rows) + 1)
    out = Image.new("RGBA", ((305 + pad * 2) * S, total_h * S), (20, 20, 22, 255))
    y = pad
    for r in rows:
        out.alpha_composite(r, (pad * S, y * S)); y += r.height // S + pad
    out = out.resize((out.width * 2, out.height * 2), Image.NEAREST)
    out.save(outp)
    print("saved", outp, out.size)
