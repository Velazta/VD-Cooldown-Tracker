"""
Window Helper & Coordinate Resolution
Violence District Cooldown Tracker
"""
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple, List, Dict

# Setup DPI Awareness agar koordinat pixel 1:1 akurat di layar dengan scaling Windows
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


def get_window_bounds(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Mengambil (x, y, width, height) yang presisi via DWM API
    dengan menyaring invisible borders bawaan Windows.
    Mengembalikan None jika window tidak valid atau diminimalkan.
    """
    if not user32.IsWindow(hwnd) or user32.IsIconic(hwnd):
        return None

    rect = RECT()
    res = dwmapi.DwmGetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect)
    )
    if res == 0:
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        return (rect.left, rect.top, w, h) if w > 0 and h > 0 else None

    # Fallback standard GetWindowRect
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    return (rect.left, rect.top, w, h) if w > 0 and h > 0 else None


def find_target_window(title_keyword: str = "Roblox") -> Optional[Dict]:
    """Mencari jendela utama aktif berdasarkan kata kunci judul."""
    found = []

    def enum_cb(hwnd, extra):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if title_keyword.lower() in title.lower():
                    bounds = get_window_bounds(hwnd)
                    if bounds and bounds[2] > 200 and bounds[3] > 200:
                        found.append({
                            "hwnd": hwnd,
                            "title": title,
                            "bounds": bounds
                        })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

    return found[0] if found else None
