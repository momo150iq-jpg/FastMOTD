import asyncio, json, random, struct, sys, time
def varint(n):
    out = b""
    while True:
        b = n & 0x7F; n >>= 7
        if n: out += bytes([b | 0x80])
        else: return out + bytes([b])
async def rvar(r):
    n = s = 0
    while True:
        b = (await r.readexactly(1))[0]; n |= (b & 0x7F) << s; s += 7
        if not b & 0x80: return n
async def one(host, port, proto, stats):
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
        h = host.encode()
        d = varint(0) + varint(proto) + varint(len(h)) + h + struct.pack(">H", port) + varint(1)
        w.write(varint(len(d)) + d + b"\x01\x00"); await w.drain()
        await asyncio.wait_for(rvar(r), 10); await rvar(r); ln = await rvar(r)
        js = json.loads((await r.readexactly(ln)).decode())
        w.close()
        if js["version"]["protocol"] != proto: stats["badproto"] += 1
        else: stats["ok"] += 1
    except Exception as e:
        stats["err"] += 1; stats.setdefault("errs", {}).setdefault(type(e).__name__, 0); stats["errs"][type(e).__name__] += 1
async def main(host, port, total, conc):
    stats = {"ok": 0, "err": 0, "badproto": 0}
    protos = [775, 774, 773, 772, 769, 767, 758, 754, 47]
    sem = asyncio.Semaphore(conc)
    async def job():
        async with sem: await one(host, port, random.choice(protos), stats)
    t = time.time(); await asyncio.gather(*[job() for _ in range(total)])
    stats["secs"] = round(time.time() - t, 1); print(stats)
asyncio.run(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
