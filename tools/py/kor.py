"""Korean <-> game SJIS code mapping. KS X 1001 Hangul syllables are placed in JIS kuten slots from row 16."""
import struct

BASE_KUTEN = 15 * 94  # row 16, col 1 (0-based index 1410)


def _ks_list():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            ch = bytes([hi, lo]).decode('euc-kr')
            out.append(ch)
    return out


def _extra():
    import os, json, glob
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ks = set(_ks_list())
    ex = set()
    for p in glob.glob(os.path.join(root, 'work', 'text', 'out', '*.json')) + glob.glob(os.path.join(root, 'work', 'text', 'manual.json')):
        for v in json.load(open(p, encoding='utf-8')).values():
            ex.update(c for c in v if '가' <= c <= '힣' and c not in ks)
    return sorted(ex)


HANGUL = _ks_list() + _extra()  # 2350 + extras (max 2979)
assert len(HANGUL) <= 4389 - 1410
IDX = {c: i for i, c in enumerate(HANGUL)}


def kuten_to_sjis(k):
    row, col = divmod(k, 94)  # 0-based
    # row r (0-based) -> JIS row r+1
    j1 = row + 0x21
    j2 = col + 0x21
    s1 = (j1 + 1) // 2 + (0x70 if j1 <= 0x5E else 0xB0)
    if j1 % 2:
        s2 = j2 + (0x1F if j2 <= 0x5F else 0x20)
    else:
        s2 = j2 + 0x7E
    return bytes([s1, s2])


def sjis_to_kuten(b):
    s1, s2 = b
    row = (s1 - 0x81) * 2 if s1 < 0xA0 else (s1 - 0xC1) * 2
    if s2 >= 0x9F:
        row += 1
        col = s2 - 0x9F
    else:
        col = s2 - 0x40 if s2 < 0x80 else s2 - 0x41
    return row * 94 + col


def encode(s):
    out = bytearray()
    for ch in s:
        if ch in IDX:
            out += kuten_to_sjis(BASE_KUTEN + IDX[ch])
        else:
            out += ch.encode('cp932')
    return bytes(out)


def decode(b):
    out = []
    i = 0
    while i < len(b):
        c = b[i]
        if (0x81 <= c <= 0x9F) or (0xE0 <= c <= 0xEF):
            k = sjis_to_kuten(b[i:i + 2])
            if BASE_KUTEN <= k < BASE_KUTEN + len(HANGUL):
                out.append(HANGUL[k - BASE_KUTEN])
            else:
                out.append(b[i:i + 2].decode('cp932', 'replace'))
            i += 2
        else:
            out.append(b[i:i + 1].decode('cp932', 'replace'))
            i += 1
    return ''.join(out)


if __name__ == '__main__':
    assert len(HANGUL) == 2350
    for k in (0, 1410, 3759, 4388):
        b = kuten_to_sjis(k)
        assert sjis_to_kuten(b) == k, (k, b)
    print(kuten_to_sjis(1410).hex(), kuten_to_sjis(1410 + 2349).hex(), '亜'.encode('cp932').hex())
    print(decode(encode('안녕하세요 테스트!')))
