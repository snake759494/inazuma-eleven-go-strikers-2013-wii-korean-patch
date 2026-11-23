"""Inazuma Eleven GO Strikers 2013 helper library: ShadeLZ, BIN archives, BLN."""
import struct, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORIG = os.path.join(ROOT, 'work', 'witx', 'files')

MAXTRIES = 48
MAGIC = b'\xFC\xAA\x55\xA7'


def lz_decompress(c):
    if c[:4] == MAGIC:
        dsize, csize = struct.unpack_from('<II', c, 4)
        pos = 12
        end = csize
    else:
        dsize = None
        pos = 0
        end = len(c)
    out = bytearray()
    prev = 0
    n = len(c)
    while pos < end and (dsize is None or len(out) < dsize):
        fl = c[pos]; pos += 1
        if fl & 0x80:
            cnt = ((fl >> 5) & 3) + 4
            off = ((fl & 0x1F) << 8) | c[pos]; pos += 1
            prev = off
            s = len(out) - off
            for i in range(cnt):
                out.append(out[s + i])
        elif (fl & 0x60) == 0x60:
            cnt = fl & 0x1F
            s = len(out) - prev
            for i in range(cnt):
                out.append(out[s + i])
        elif fl & 0x40:
            if fl & 0x10:
                cnt = (((fl & 0xF) << 8) | c[pos]) + 4; pos += 1
            else:
                cnt = (fl & 0xF) + 4
            out += bytes([c[pos]]) * cnt; pos += 1
        else:
            if fl & 0x20:
                cnt = ((fl & 0x1F) << 8) | c[pos]; pos += 1
            else:
                cnt = fl
            if dsize is None and cnt == 0:
                # padding zeros at end of headerless stream
                continue
            out += c[pos:pos + cnt]; pos += cnt
    return bytes(out)


def _raw(out, data):
    p = 0
    L = len(data)
    while L - p > 0:
        k = min(0x1FFF, L - p)
        if k < 0x20:
            out.append(k)
        else:
            out.append(0x20 | (k >> 8)); out.append(k & 0xFF)
        out += data[p:p + k]
        p += k


def lz_compress(data, header=True):
    data = bytes(data)
    L = len(data)
    out = bytearray()
    hist = {}
    pos = 0
    rawstart = 0
    while pos < L:
        best_len = 0; best_off = 0
        if pos + 3 <= L:
            key = data[pos:pos + 3]
            lst = hist.get(key)
            if lst:
                # search recent candidates
                tries = 0
                for cand in reversed(lst):
                    off = pos - cand
                    if off > 0x1FFF:
                        break
                    if data[cand + best_len:cand + best_len + 1] == data[pos + best_len:pos + best_len + 1] or best_len == 0:
                        m = 3
                        mx = L - pos
                        while m < mx and data[cand + m] == data[pos + m]:
                            m += 1
                        if m > best_len:
                            best_len = m; best_off = off
                            if m >= 512:
                                break
                    tries += 1
                    if tries > MAXTRIES:
                        break
        # RLE
        run = 1
        b = data[pos]
        while pos + run < L and data[pos + run] == b and run < 0x1003:
            run += 1
        if best_len < 4 and run < 4:
            if pos + 3 <= L:
                hist.setdefault(data[pos:pos + 3], []).append(pos)
            pos += 1
            continue
        if pos > rawstart:
            _raw(out, data[rawstart:pos])
        if run >= best_len:
            n = run
            if n - 4 < 0x10:
                out.append(0x40 | (n - 4)); out.append(b)
            else:
                out.append(0x50 | ((n - 4) >> 8)); out.append((n - 4) & 0xFF); out.append(b)
        else:
            n = best_len
            if n < 8:
                out.append(0x80 | ((n - 4) << 5) | (best_off >> 8)); out.append(best_off & 0xFF)
            else:
                out.append(0xE0 | (best_off >> 8)); out.append(best_off & 0xFF)
                r = n - 7
                while r > 0x1F:
                    out.append(0x7F); r -= 0x1F
                if r:
                    out.append(0x60 | r)
        for i in range(pos, pos + n):
            if i + 3 <= L:
                hist.setdefault(data[i:i + 3], []).append(i)
        pos += n
        rawstart = pos
    if pos > rawstart:
        _raw(out, data[rawstart:pos])
    if header:
        return MAGIC + struct.pack('<II', L, len(out) + 12) + bytes(out)
    return bytes(out) + bytes(1)  # headerless streams are terminated by a 0 command


class Archive:
    NAMES = ['grp.bin', 'scn.bin', 'scn_sh.bin', 'ui.bin', 'dat.bin', 'strap.bin']

    def __init__(self, path):
        self.path = path
        f = open(path, 'rb')
        hdr = f.read(0x14)
        self.count, self.pad, self.mult, self.shift, self.mask = struct.unpack('<5I', hdr)
        tab = f.read(4 * self.count)
        self.entries = []
        for i in range(self.count):
            v = struct.unpack_from('<I', tab, 4 * i)[0]
            self.entries.append([(v >> self.shift) * self.pad, (v & self.mask) * self.mult])
        self.f = f
        self.replaced = {}

    def raw(self, i):
        if i in self.replaced:
            return self.replaced[i]
        o, s = self.entries[i]
        self.f.seek(o)
        return self.f.read(s)

    def get(self, i):
        return lz_decompress(self.raw(i))

    def is_dat(self):
        return os.path.basename(self.path).startswith('dat')

    def put(self, i, dec):
        self.replaced[i] = lz_compress(dec, header=not self.is_dat())

    def put_raw(self, i, raw):
        self.replaced[i] = raw

    def slot(self, i):
        o, s = self.entries[i]
        return (s + self.pad - 1) // self.pad * self.pad if s else self.pad

    def overflow(self):
        res = {}
        for i, d in self.replaced.items():
            if len(d) > self.slot(i):
                res[i] = len(d) - self.slot(i)
        return res

    def save_inplace(self, out):
        """keep original file bytes/offsets; overwrite changed entries in their slot."""
        import shutil
        ov = self.overflow()
        if ov:
            raise ValueError('overflow %r' % ov)
        shutil.copyfile(self.path, out)
        w = open(out, 'r+b')
        remap = {}
        tab = bytearray(4 * self.count)
        for i, d in self.replaced.items():
            o, s = self.entries[i]
            w.seek(o)
            w.write(d + b'\0' * (self.slot(i) - len(d)))
            size = (len(d) + self.mult - 1) // self.mult * self.mult
            w.seek(0x14 + 4 * i)
            w.write(struct.pack('<I', ((o // self.pad) << self.shift) | (size // self.mult)))
            remap[o] = (o, (len(d) + self.pad - 1) // self.pad * self.pad, d)
        w.close()
        return remap

    def save(self, out):
        """Rebuild archive. Returns map old_offset -> (new_offset, new_size, data_or_None)."""
        pad, mult = self.pad, self.mult
        w = open(out, 'wb')
        hdr_len = 0x14 + 4 * self.count
        w.write(b'\0' * ((hdr_len + pad - 1) // pad * pad))
        newtab = []
        remap = {}
        for i in range(self.count):
            o, s = self.entries[i]
            data = self.raw(i)
            if i in self.replaced:
                size = (len(data) + mult - 1) // mult * mult
            else:
                size = s
            no = w.tell()
            real = len(data)
            if data[:4] == MAGIC:
                real = min(real, struct.unpack_from('<I', data, 8)[0])
            w.write(data[:real])
            p = w.tell()
            w.write(b'\0' * ((-p) % pad))
            assert no % pad == 0
            assert (no // pad) < (1 << (32 - self.shift)), 'offset overflow'
            assert size // mult <= self.mask, 'size overflow'
            newtab.append(((no // pad) << self.shift) | (size // mult))
            remap[o] = (no, (len(data) + pad - 1) // pad * pad, data if i in self.replaced else None)
        w.seek(0)
        w.write(struct.pack('<5I', self.count, self.pad, self.mult, self.shift, self.mask))
        w.write(struct.pack('<%dI' % self.count, *newtab))
        w.close()
        return remap


def rebuild_bln(src_dir, dst_dir, remaps):
    """remaps: {archive_index: remap dict}. Rewrites mcb0/mcb1."""
    m0 = open(os.path.join(src_dir, 'mcb0.bln'), 'rb').read()
    m1 = open(os.path.join(src_dir, 'mcb1.bln'), 'rb')
    ents = []
    p = 0
    while struct.unpack_from('<I', m0, p)[0] != 0 or p == 0:
        ents.append(struct.unpack_from('<III', m0, p))
        p += 12
    tail = m0[p:]
    w = open(os.path.join(dst_dir, 'mcb1.bln'), 'wb')
    newents = []
    hits = 0
    for (eid, off, size) in ents:
        m1.seek(off)
        blk = m1.read(size)
        q = 0
        no = w.tell()
        while q + 12 <= len(blk):
            ai = struct.unpack_from('<I', blk, q)[0]
            if ai == 0x7FFF:
                break
            ai, ao, sz = struct.unpack_from('<III', blk, q)
            data = blk[q + 12:q + 12 + sz]
            q += 12 + sz
            r = remaps.get(ai, {}).get(ao)
            if r:
                nao, nsz, ndata = r
                if ndata is not None:
                    data = ndata + b'\0' * (nsz - len(ndata))
                    sz = nsz
                    hits += 1
                ao = nao
            w.write(struct.pack('<III', ai, ao, sz))
            w.write(data)
        w.write(struct.pack('<I', 0x7FFF))
        pp = w.tell()
        w.write(b'\0' * ((-pp) % 0x800))
        newents.append((eid, no, w.tell() - no))
    w.close()
    with open(os.path.join(dst_dir, 'mcb0.bln'), 'wb') as f:
        for e in newents:
            f.write(struct.pack('<III', *e))
        f.write(tail)
    return hits


def rebuild_bln_inplace(src_dir, dst_dir, remaps):
    """Keep every mcb0 block at its original offset/size; repack records inside each block."""
    import shutil
    m0 = open(os.path.join(src_dir, 'mcb0.bln'), 'rb').read()
    shutil.copyfile(os.path.join(src_dir, 'mcb1.bln'), os.path.join(dst_dir, 'mcb1.bln'))
    shutil.copyfile(os.path.join(src_dir, 'mcb0.bln'), os.path.join(dst_dir, 'mcb0.bln'))
    m1 = open(os.path.join(dst_dir, 'mcb1.bln'), 'r+b')
    p = 0
    hits = 0
    while True:
        eid, off, size = struct.unpack_from('<III', m0, p)
        if eid == 0 and p > 0:
            break
        p += 12
        m1.seek(off)
        blk = m1.read(size)
        q = 0
        out = bytearray()
        changed = False
        while q + 12 <= len(blk):
            ai = struct.unpack_from('<I', blk, q)[0]
            if ai == 0x7FFF:
                break
            ai, ao, sz = struct.unpack_from('<III', blk, q)
            data = blk[q + 12:q + 12 + sz]
            q += 12 + sz
            r = remaps.get(ai, {}).get(ao)
            if r and r[2] is not None:
                nd = r[2]
                nsz = r[1]
                data = nd + bytes(nsz - len(nd))
                sz = nsz
                changed = True
                hits += 1
            out += struct.pack('<III', ai, ao, sz) + data
        if not changed:
            continue
        out += struct.pack('<I', 0x7FFF)
        if len(out) > size:
            raise ValueError('mcb block %x grows %d > %d' % (eid, len(out), size))
        out += bytes(size - len(out))
        m1.seek(off)
        m1.write(out)
    m1.close()
    return hits
