"""Strikers 2013 text container (BE): [nsect][end][hdrsize][(off,cnt)*n] ... data ... [reloc count][reloc offsets]"""
import struct


def u(d, o):
    return struct.unpack_from('>I', d, o)[0]


class TextFile:
    def __init__(self, d):
        self.d = d
        self.end = u(d, 4)
        rc = u(d, self.end)
        self.relocs = [u(d, self.end + 4 + 4 * k) for k in range(rc)]
        self.reloc_tail = d[self.end + 4 + 4 * rc:]
        targets = {}
        for r in self.relocs:
            targets.setdefault(u(d, r), []).append(r)
        self.targets = targets
        # find string region start: smallest S such that all targets >= S are string starts
        # and [S,end) is a run of NUL-terminated SJIS strings (with padding)
        cand = sorted(t for t in targets if t < self.end)
        # strings start: earliest target after which everything is text
        # determine by scanning from the largest table-ish targets: use relocs located in tables
        self.S = self._find_S(cand)
        self.strings = {}
        for t in cand:
            if t >= self.S:
                e = d.index(b'\0', t)
                self.strings[t] = d[t:e]
        for r in self.relocs:
            assert r < self.S, 'reloc inside string region'

    def _find_S(self, cand):
        d = self.d
        # walk backwards from end: string region contains only bytes that are text (>=0x20 or 0x0a) or NUL
        def is_text_run(a, b):
            seg = d[a:b]
            for x in seg:
                if x != 0 and x != 0x0a and x != 0x09 and x < 0x20:
                    return False
            return True
        S = self.end
        for t in reversed(cand):
            if is_text_run(t, S):
                S = t
            else:
                break
        return S

    def order(self):
        return sorted(self.strings)

    dedupe = True

    def build(self, new):
        """new: {oldoff: bytes} (any target). strings >=S are repacked, earlier ones appended."""
        d = self.d
        out = bytearray(d[:self.S])
        early = {}
        for t, v in new.items():
            if t >= self.S:
                continue
            olen = d.index(b'\0', t) - t
            if len(v) <= olen:
                out[t:t + olen] = v + bytes(olen - len(v))
            else:
                early[t] = v
        newpos = {}
        cache = {}
        for t in self.order():
            s = new.get(t, self.strings[t])
            newpos[t] = len(out)
            out += s + b'\0'
            while len(out) % 4:
                out += b'\0'
        for t, v in sorted(early.items()):
            newpos[t] = len(out)
            out += v + b'\0'
            while len(out) % 4:
                out += b'\0'
        end = len(out)
        for t, rs in self.targets.items():
            if t in early:
                for r in rs:
                    struct.pack_into('>I', out, r, newpos[t])
            if t >= self.S and t < self.end:
                for r in rs:
                    struct.pack_into('>I', out, r, newpos[t])
        struct.pack_into('>I', out, 4, end)
        out += struct.pack('>I', len(self.relocs))
        for r in self.relocs:
            out += struct.pack('>I', r)
        out += self.reloc_tail
        return bytes(out)
