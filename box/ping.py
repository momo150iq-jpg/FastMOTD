import json, socket, struct, sys
def varint(n):
    out = b""
    while True:
        b = n & 0x7F; n >>= 7
        if n: out += bytes([b | 0x80])
        else: return out + bytes([b])
def read_varint(s):
    n = shift = 0
    while True:
        b = s.recv(1)[0]; n |= (b & 0x7F) << shift; shift += 7
        if not b & 0x80: return n
def ping(host, port, proto):
    s = socket.create_connection((host, port), timeout=5)
    h = host.encode()
    data = varint(0) + varint(proto) + varint(len(h)) + h + struct.pack(">H", port) + varint(1)
    s.sendall(varint(len(data)) + data + b"\x01\x00")
    read_varint(s); read_varint(s); ln = read_varint(s)
    buf = b""
    while len(buf) < ln: buf += s.recv(ln - len(buf))
    s.close()
    return json.loads(buf.decode("utf-8"))
def flat(c, out):
    if isinstance(c, str): out.append(c); return
    if isinstance(c, list):
        for x in c: flat(x, out)
        return
    if c.get("type") == "object" or "sprite" in c or "player" in c:
        out.append("[%s]" % (("sprite " + c.get("atlas","blocks").replace("minecraft:","") + ":" + c["sprite"].replace("minecraft:","")) if "sprite" in c else "head " + json.dumps(c["player"])))
    out.append(c.get("text", ""))
    for x in c.get("extra", []): flat(x, out)
if __name__ == "__main__":
    host, port = sys.argv[1], int(sys.argv[2])
    for p in [int(x) for x in sys.argv[3].split(",")]:
        r = ping(host, port, p)
        d = r["description"]; parts = []; flat(d, parts)
        js = json.dumps(d, ensure_ascii=False)
        print("== proto %d  version=%s/%s  players=%s/%s  favicon=%s  json=%dB  object=%s shadow=%s font=%s" % (p, r["version"]["name"], r["version"]["protocol"], r["players"]["online"], r["players"]["max"], "favicon" in r, len(js), "\"sprite\"" in js, "shadow_color" in js, "\"font\"" in js))
        print("   " + "".join(parts).replace("\n", "\n   "))
