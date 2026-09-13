"""Tabata Clock app icon — the dial, with the ring split at the protocol's
own 20:10 ratio (two thirds work red, one third rest mint)."""
import zlib, struct, math

GROUND = (0x0E, 0x11, 0x16)
WORK   = (0xFF, 0x45, 0x36)
REST   = (0x2F, 0xD8, 0xA6)

def clamp(v, a=0.0, b=1.0): return a if v < a else (b if v > b else v)
def mix(c1, c2, t): return tuple(round(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

def render(size):
    c  = (size - 1) / 2.0
    R  = size * 0.365          # outer radius
    th = size * 0.105          # stroke thickness
    ri = R - th
    aa = size * 0.006          # antialias width
    GAP = math.radians(7.0)    # gap between the two arcs
    SPAN_WORK = math.radians(240.0)   # 20s : 10s  ->  240deg : 120deg

    rows = []
    for y in range(size):
        row = []
        dy = y - c
        for x in range(size):
            dx = x - c
            d = math.hypot(dx, dy)
            # radial coverage of the ring band
            cov = clamp((R - d)/aa + 0.5) * clamp((d - ri)/aa + 0.5)
            if cov <= 0.0:
                row.append(GROUND); continue
            # angle measured clockwise from 12 o'clock
            a = (math.atan2(dx, -dy)) % (2*math.pi)
            col = WORK if a < SPAN_WORK else REST
            # carve a gap at each arc boundary
            for edge in (0.0, SPAN_WORK):
                da = abs(((a - edge + math.pi) % (2*math.pi)) - math.pi)
                cov *= clamp(da/(GAP/2) - 0.35)
            row.append(mix(GROUND, col, clamp(cov)))
        rows.append(row)
    return rows

def write_png(path, size, rows):
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in r) for r in rows)
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    out = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    open(path, "wb").write(out)

if __name__ == "__main__":
    import sys
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 512
    write_png(sys.argv[1], size, render(size))
    print("wrote", sys.argv[1], size)
