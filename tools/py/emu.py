"""Emulator helper.
python emu.py start <iso>      start DSU server + Dolphin (no focus steal)
python emu.py cmd "press cross" "wait 1" ...
python emu.py shot <out.png>   capture Dolphin render window (PrintWindow)
python emu.py stop
"""
import sys, os, socket, subprocess, time, ctypes
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOL = os.path.join(ROOT, 'tools', 'Dolphin', 'Dolphin.exe')
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def cmd(lines):
    s = socket.create_connection(('127.0.0.1', 26801))
    f = s.makefile('rw')
    for l in lines:
        f.write(l + '\n'); f.flush(); f.readline()
    s.close()


def find_windows():
    res = []
    pids = set()
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Dolphin.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split('","')
        if len(p) > 1:
            pids.add(int(p[1]))

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            n = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, n, 256)
            r = wintypes.RECT(); user32.GetClientRect(h, ctypes.byref(r))
            res.append((h, n.value, r.right, r.bottom))
        return True
    user32.EnumWindows(cb, 0)
    return res


def shot(path):
    from PIL import Image
    import glob, shutil
    fd = os.path.join(os.path.dirname(DOL), 'User', 'Dump', 'Frames')
    fr = sorted(glob.glob(os.path.join(fd, '*.png')), key=os.path.getmtime)
    if fr:
        time.sleep(0.3)
        Image.open(fr[-2] if len(fr) > 1 else fr[-1]).convert('RGB').save(path)
        for f in fr[:-1]:
            try: os.remove(f)
            except OSError: pass
        print('captured dump'); return
    wins = find_windows()
    # render window: largest client area whose title isn't the main 'Dolphin' list window or a title containing game id
    wins.sort(key=lambda w: -(w[2] * w[3]))
    cand = [w for w in wins if '|' in w[1] or 'GO' in w[1] or 'Strikers' in w[1] or 'イナズマ' in w[1]] or wins
    h, title, w, hgt = cand[0]
    hdc = user32.GetDC(h)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, hgt)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(h, mdc, 3)
    class BMI(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD),
                    ('a', wintypes.LONG), ('b', wintypes.LONG), ('c', wintypes.DWORD), ('d', wintypes.DWORD)]
    bmi = BMI(); bmi.biSize = ctypes.sizeof(BMI); bmi.biWidth = w; bmi.biHeight = -hgt; bmi.biPlanes = 1; bmi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * hgt * 4)
    gdi32.GetDIBits(mdc, bmp, 0, hgt, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer('RGBA', (w, hgt), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    img.save(path)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(h, hdc)
    print('captured', title, w, hgt)


def start(iso):
    py = sys.executable
    subprocess.Popen([py, os.path.join(os.path.dirname(__file__), 'dsu.py')], creationflags=0x08000000)
    si = subprocess.STARTUPINFO()
    si.dwFlags = 1  # STARTF_USESHOWWINDOW
    si.wShowWindow = 4  # SW_SHOWNOACTIVATE
    subprocess.Popen([DOL, '-b', '-e', iso], startupinfo=si)


def stop():
    try:
        cmd(['quit'])
    except Exception:
        pass
    subprocess.run(['taskkill', '/IM', 'Dolphin.exe', '/F'], capture_output=True)


if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'start':
        start(sys.argv[2])
    elif a == 'cmd':
        cmd(sys.argv[2:])
    elif a == 'shot':
        shot(sys.argv[2])
    elif a == 'stop':
        stop()
    elif a == 'wins':
        print(find_windows())
