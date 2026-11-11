import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, Dict, List

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_EXTENDED_FRAME_BOUNDS = 9

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

def get_window_bounds(hwnd: int) -> Tuple[int, int, int, int]:
    rect = RECT()
    res = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect)
    )
    if res == 0:
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    
    # Fallback ke GetWindowRect standar
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

def find_target_windows(keyword: str = "Roblox") -> List[Dict]:
    """Mencari semua window aktif yang memiliki judul mengandung keyword."""
    results = []
    def enum_cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if keyword.lower() in title.lower():
                    x, y, w, h = get_window_bounds(hwnd)
                    if w > 100 and h > 100:  # Abaikan ghost/hidden tooltips
                        results.append({
                            "hwnd": hwnd,
                            "title": title,
                            "bounds": (x, y, w, h)
                        })
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return results
if __name__ == "__main__":
    print("[INFO] Mencari jendela target...")
    targets = find_target_windows("Roblox")
    if not targets:
        print("[WARN] Jendela 'Roblox' tidak ditemukan! Menampilkan semua jendela aktif sebagai referensi:")
        all_wins = find_target_windows("")
        for w in all_wins[:10]:
            print(f" - HWND: {w['hwnd']} | Rect: {w['bounds']} | Title: {w['title']}")
    else:
        for t in targets:
            print(f"[FOUND] HWND: {t['hwnd']} | Bounds: {t['bounds']} | Title: '{t['title']}'")