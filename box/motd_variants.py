# Builds a FastMOTD config with 5 MOTD variants (each: 773+ with TNT, 769-772 with bolts, -768 legacy colors).
# Usage: motd_variants.py <base config.yml> <out config.yml> <active 1..5 or 0>
import re, sys

base, out, active = sys.argv[1], sys.argv[2], int(sys.argv[3])
s = open(base, encoding="utf-8").read()

TNT = "<sprite:block/tnt_side>"
SK = "<#D8D8D8>☠</#D8D8D8>"


def sh(color, body, bold=True):
    inner = "<bold>%s</bold>" % body if bold else body
    return "<shadow:%s:1>%s</shadow>" % (color, inner)


def grad(a, b, text):
    return "<gradient:%s:%s>%s</gradient>" % (a, b, text) if a != b else "<%s>%s</%s>" % (a, text, a)


# name, BOMJ (from, to), logo shadow, title, title (from, to), title shadow, slogan, slogan color, slogan shadow,
# tail, tail color, bolt color, legacy (logo, title, slogan) named colors
V = [
    ("neon", ("#FF5BD6", "#B06BFF"), "#2A0A45", "БОМЖ-ГОРОД", ("#6CF0FF", "#4FA8FF"), "#062740",
     "ВЫБЕЙСЯ В ЛЮДИ", "#FFFFFF", "#2A0A45", "кланы · кейсы · PvP", "#A9A3C2", "#6CF0FF", ("light_purple", "aqua", "white")),
    ("gold", ("#FFE27A", "#FFAA2E"), "#3A2200", "КЕЙСЫ ЖДУТ", ("#FF7A4A", "#FF4A3D"), "#3A0C00",
     "ОТ ПОМОЙКИ К ТРОНУ", "#FFF1CF", "#3A2200", "заходи", "#B8AD93", "#FFAA2E", ("gold", "red", "yellow")),
    ("ice", ("#9BEBFF", "#4FB2FF"), "#0A2240", "ДЕРЖИ РАЙОН", ("#FFFFFF", "#CFEFFF"), "#0A2240",
     "СОБЕРИ БАНДУ", "#BFF1FF", "#08263A", "захвати точки", "#93A7BC", "#9BEBFF", ("aqua", "white", "aqua")),
    ("toxic", ("#D2FF4A", "#4CFF7A"), "#0E2E00", "ЛАКИ-БЛОКИ", ("#FFE14A", "#FFB300"), "#3A2600",
     "ЛОМАЙ И ЛУТАЙ", "#F2FFE0", "#0E2E00", "богатей с нуля", "#A3B39A", "#D2FF4A", ("green", "yellow", "white")),
    ("blood", ("#FF6A55", "#FF2E3A"), "#3A0006", "СТАНЬ КОРОЛЁМ", ("#FFD85A", "#FFB12E"), "#3A2400",
     "ИЗ БОМЖА В МАЖОРЫ", "#FFFFFF", "#3A0006", "за один вечер", "#B3A3A3", "#FF6A55", ("red", "gold", "white")),
]

favs = re.search(r"    wipe:\n(?:      .*\n|        - .*\n)*?      favicons:\n((?:        - .*\n)+)", s)
favicons = favs.group(1) if favs else ""

block = ""
for i, (name, bomj, lsh, title, tg, tsh, slogan, sc, ssh, tail, tc, bolt, legacy) in enumerate(V, 1):
    on = i == active
    logo = sh(lsh, grad(bomj[0], bomj[1], "BOMJ") + "<#FFFFFF>PVP</#FFFFFF>")
    head = sh(tsh, grad(tg[0], tg[1], title))
    line2 = sh(ssh, "<%s>%s</%s>" % (sc, slogan, sc)) + " <%s>· %s</%s>" % (tc, tail, tc)
    b = "<%s>⚡</%s>" % (bolt, bolt)
    lines = {
        "": (("773+" if on else "off"), TNT + " " + SK + " " + logo + " " + SK + " " + TNT + "  " + head + "{NL}" + line2),
        "_smooth": (("769-772" if on else "off"), b + " " + SK + " " + logo + " " + SK + " " + b + "  " + head + "{NL}" + line2),
        "_legacy": (("-768" if on else "off"),
                    "<{0}>⚡</{0}> <gray>☠</gray> <bold><{0}>BOMJ</{0}><white>PVP</white></bold> <gray>☠</gray> <{0}>⚡</{0}>  "
                    "<bold><{1}>{3}</{1}></bold>{{NL}}<bold><{2}>{4}</{2}></bold> <gray>· {5}</gray>".format(
                        legacy[0], legacy[1], legacy[2], title, slogan, tail)),
    }
    for suffix, (proto, desc) in lines.items():
        block += "    motd%d_%s%s:\n      protocols: \"%s\"\n      center: true\n      descriptions:\n        - \"%s\"\n" % (
            i, name, suffix, proto, desc.replace('"', '\\"'))
        block += ("      favicons:\n" + favicons) if favicons else "      favicons: []\n"
        block += "      information: []\n"

s = re.sub(r"    motd\d_[a-z_]+:\n(?:      .*\n|        - .*\n)+", "", s)
if active:
    # live tiers stay in the file but are switched off on the preview proxies
    s = re.sub(r"(\n    wipe[a-z_]*:\n      protocols: )\"[^\"]*\"", r'\1"off"', s)
assert s.count("  tiers:\n") == 1
s = s.replace("  tiers:\n", "  tiers:\n" + block, 1)
open(out, "w", encoding="utf-8").write(s)
print("ok", out, "active", active, "favicons", favicons.count("- "))
