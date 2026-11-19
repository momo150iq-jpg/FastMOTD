# FastMOTD config with 5 MOTD variants (layout: [TNT] skull BOMJPVP skull [TNT]  title / slogan · tail, centered).
# Usage: motd_variants.py <base config.yml> <out config.yml> <mode>
#   mode rotate : the live tiers wipe / wipe_smooth / wipe_legacy get all 5 variants (random per ping)
#   mode 1..5   : preview proxy, tiers motdN_* added and only variant N switched on, live tiers off
#   mode 0      : tiers motdN_* added, all off
# BOMJPVP keeps the exact styling of the base config per tier.
import re, sys

base, out, mode = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(base, encoding="utf-8").read()

TNT = "<sprite:block/tnt_side>"
LIVE_TIERS = {"": "wipe", "_smooth": "wipe_smooth", "_legacy": "wipe_legacy"}


def sh(color, body):
    return "<shadow:%s:1><bold>%s</bold></shadow>" % (color, body)


def grad(a, b, text):
    return "<gradient:%s:%s>%s</gradient>" % (a, b, text)


def tier_body(name):
    m = re.search(r"\n    %s:\n((?:      .*\n|        - .*\n)+)" % name, s)
    return m.group(1) if m else ""


def live_logo(tier):
    body = tier_body(tier)
    m = re.search(r"<shadow:[^>]*><bold><gradient:[^>]*>BOMJ</gradient><[^>]*>PVP</[^>]*></bold></shadow>", body)
    if m:
        return m.group(0)
    m = re.search(r"<(#[0-9A-Fa-f]{6}|[a-z_]+)><bold>BOMJ<(#[0-9A-Fa-f]{6}|[a-z_]+)>PVP</bold>", body)
    if m:  # legacy line leaves tags open; close them for a self-contained segment
        return "<%s><bold>BOMJ<%s>PVP</%s></bold></%s>" % (m.group(1), m.group(2), m.group(2), m.group(1))
    raise SystemExit("no BOMJPVP in tier " + tier)


LOGO = {suffix: live_logo(tier) for suffix, tier in LIVE_TIERS.items()}

# name, title, title gradient, slogan, slogan color, tail, tail color, bolt color, legacy (accent, title, slogan)
V = [
    ("neon", "БОМЖ-ГОРОД", ("#6CF0FF", "#4FA8FF"), "ВЫБЕЙСЯ В ЛЮДИ", "#E2CCFF", "кланы · кейсы · PvP", "#A9A3C2", "#6CF0FF", ("aqua", "aqua", "white")),
    ("gold", "КЕЙСЫ ЖДУТ", ("#FF7A4A", "#FF4A3D"), "ОТ ПОМОЙКИ К ТРОНУ", "#FFF1CF", "заходи", "#B8AD93", "#FFAA2E", ("gold", "red", "yellow")),
    ("ice", "ДЕРЖИ РАЙОН", ("#FFFFFF", "#CFEFFF"), "СОБЕРИ БАНДУ", "#D2F2FF", "захвати точки", "#93A7BC", "#9BEBFF", ("aqua", "white", "aqua")),
    ("toxic", "ЛАКИ-БЛОКИ", ("#FFE14A", "#FFB300"), "ЛОМАЙ И ЛУТАЙ", "#F2FFE0", "богатей с нуля", "#A3B39A", "#D2FF4A", ("green", "yellow", "white")),
    ("blood", "СТАНЬ КОРОЛЁМ", ("#FFD85A", "#FFB12E"), "ИЗ БОМЖА В МАЖОРЫ", "#FFFFFF", "за один вечер", "#B3A3A3", "#FF6A55", ("red", "gold", "white")),
]
# shadows: very dark tone of each element's hue (V ~0.2): title, slogan, tail, skull
SH = {
    "neon": ("#0A1E4A", "#2A0A4A", "#1C2030", "#241838"),
    "gold": ("#3A0610", "#3A2006", "#1C2030", "#2E1E08"),
    "ice": ("#0A2A4A", "#0A1E4A", "#1C2030", "#121E38"),
    "toxic": ("#3A2006", "#06301A", "#1C2030", "#102A12"),
    "blood": ("#3A2006", "#3A0610", "#1C2030", "#300A0A"),
}


def variant(v):
    name, title, tg, slogan, sc, tail, tc, bolt, legacy = v
    tsh, ssh, tailsh, sksh = SH[name]
    skull = "<shadow:%s:1><#D8D8D8>☠</#D8D8D8></shadow>" % sksh
    head = sh(tsh, grad(tg[0], tg[1], title))
    line2 = sh(ssh, "<%s>%s</%s>" % (sc, slogan, sc)) + " <shadow:%s:1><%s>· %s</%s></shadow>" % (tailsh, tc, tail, tc)
    b = "<shadow:%s:1><%s>⚡</%s></shadow>" % (tsh, bolt, bolt)
    return {
        "": TNT + " " + skull + " " + LOGO[""] + " " + skull + " " + TNT + "  " + head + "{NL}" + line2,
        "_smooth": b + " " + skull + " " + LOGO["_smooth"] + " " + skull + " " + b + "  " + head + "{NL}" + line2,
        "_legacy": "<{0}>⚡</{0}> <gray>☠</gray> {L} <gray>☠</gray> <{0}>⚡</{0}>  <bold><{1}>{3}</{1}></bold>{{NL}}"
                   "<bold><{2}>{4}</{2}></bold> <gray>· {5}</gray>".format(legacy[0], legacy[1], legacy[2], title, slogan, tail,
                                                                       L=LOGO["_legacy"]),
    }


def q(desc):
    return '        - "%s"\n' % desc.replace('"', '\\"')


favs = re.search(r"\n    wipe:\n(?:      .*\n|        - .*\n)*?      favicons:\n((?:        - .*\n)+)", s)
favicons = favs.group(1) if favs else ""
s = re.sub(r"    motd\d+_[a-z_]+:\n(?:      .*\n|        - .*\n)+", "", s)
built = [variant(v) for v in V]

if mode == "rotate":
    for suffix, tier in LIVE_TIERS.items():
        pat = re.compile(r"(\n    %s:\n      protocols: \"[^\"]*\"\n      center: )\w+(\n      descriptions:\n)((?:        - .*\n)+)" % tier)
        s, n = pat.subn(lambda m: m.group(1) + "true" + m.group(2) + "".join(q(b[suffix]) for b in built), s)
        assert n == 1, tier
else:
    active = int(mode)
    block = ""
    for i, (v, b) in enumerate(zip(V, built), 1):
        on = i == active
        for suffix, proto in (("", "773+"), ("_smooth", "769-772"), ("_legacy", "-768")):
            block += "    motd%d_%s%s:\n      protocols: \"%s\"\n      center: true\n      descriptions:\n" % (
                i, v[0], suffix, proto if on else "off") + q(b[suffix])
            block += ("      favicons:\n" + favicons) if favicons else "      favicons: []\n"
            block += "      information: []\n"
    if active:
        s = re.sub(r"(\n    wipe[a-z_]*:\n      protocols: )\"[^\"]*\"", r'\1"off"', s)
    assert s.count("  tiers:\n") == 1
    s = s.replace("  tiers:\n", "  tiers:\n" + block, 1)

open(out, "w", encoding="utf-8").write(s)
print("ok", out, "mode", mode, "favicons", favicons.count("- "))
