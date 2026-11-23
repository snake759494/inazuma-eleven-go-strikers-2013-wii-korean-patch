"""Optimal-parse ShadeLZ compressor (slow, used only where greedy output doesn't fit)."""
import struct

MAGIC = b'\xFC\xAA\x55\xA7'
INF = 1 << 60


def _mcost(L):
    if L < 8:
        return 2
    r = L - 7
    return 2 + (r + 30) // 31


def _rcost(L):
    return 2 if L - 4 < 0x10 else 3


def compress(data, header=True, tries=256):
    data = bytes(data)
    n = len(data)
    # match finder: best (len, off) per position using 3-byte hash chains
    best = [None] * n
    head = {}
    prev = [-1] * n
    for i in range(n):
        if i + 3 <= n:
            k = data[i:i + 3]
            j = head.get(k, -1)
            prev[i] = j
            head[k] = i
            bl, bo, t = 0, 0, 0
            while j >= 0 and i - j <= 0x1FFF and t < tries:
                if data[j + bl:j + bl + 1] == data[i + bl:i + bl + 1]:
                    m = 3
                    mx = n - i
                    while m < mx and data[j + m] == data[i + m]:
                        m += 1
                    if m > bl:
                        bl, bo = m, i - j
                        if m >= 1024:
                            break
                j = prev[j]
                t += 1
            if bl >= 4:
                best[i] = (bl, bo)
    # run lengths
    run = [1] * n
    for i in range(n - 2, -1, -1):
        if data[i] == data[i + 1]:
            run[i] = min(run[i + 1] + 1, 0x1003)
    # DP backwards: cost[i][s] s=0 not in literal run, s=1 in literal run (header already paid)
    c0 = [INF] * (n + 1)
    c1 = [INF] * (n + 1)
    ch0 = [None] * (n + 1)
    ch1 = [None] * (n + 1)
    c0[n] = c1[n] = 0
    for i in range(n - 1, -1, -1):
        # literal
        lit_cont = 1 + c1[i + 1]
        b0 = 2 + c1[i + 1]  # start a literal run (header ~1, plus byte)
        o0 = ('L',)
        b1 = lit_cont
        o1 = ('L',)
        cands = []
        bm = best[i]
        if bm:
            M, off = bm
            ls = set(range(4, min(8, M + 1)))
            ls.add(M)
            k = 7 + 31
            while k < M:
                ls.add(k); k += 31
            for L in ls:
                cands.append((_mcost(L) + c0[i + L], ('M', L, off)))
        R = run[i]
        if R >= 4:
            for L in {4, min(R, 19), R}:
                if L >= 4:
                    cands.append((_rcost(L) + c0[i + L], ('R', L)))
        for c, o in cands:
            if c < b0:
                b0, o0 = c, o
            if c < b1:
                b1, o1 = c, o
        c0[i], ch0[i] = b0, o0
        c1[i], ch1[i] = b1, o1
    # emit
    out = bytearray()
    i = 0
    state = 0
    lit = bytearray()

    def flush():
        p = 0
        L = len(lit)
        while L - p > 0:
            k = min(0x1FFF, L - p)
            if k < 0x20:
                out.append(k)
            else:
                out.append(0x20 | (k >> 8)); out.append(k & 0xFF)
            out.extend(lit[p:p + k]); p += k
        lit.clear()

    while i < n:
        op = (ch1 if state else ch0)[i]
        if op[0] == 'L':
            lit.append(data[i]); i += 1; state = 1
            continue
        flush(); state = 0
        if op[0] == 'M':
            _, L, off = op
            if L < 8:
                out.append(0x80 | ((L - 4) << 5) | (off >> 8)); out.append(off & 0xFF)
            else:
                out.append(0xE0 | (off >> 8)); out.append(off & 0xFF)
                r = L - 7
                while r > 0x1F:
                    out.append(0x7F); r -= 0x1F
                if r:
                    out.append(0x60 | r)
            i += L
        else:
            _, L = op
            b = data[i]
            if L - 4 < 0x10:
                out.append(0x40 | (L - 4)); out.append(b)
            else:
                out.append(0x50 | ((L - 4) >> 8)); out.append((L - 4) & 0xFF); out.append(b)
            i += L
    flush()
    if header:
        return MAGIC + struct.pack('<II', n, len(out) + 12) + bytes(out)
    return bytes(out) + bytes(1)
