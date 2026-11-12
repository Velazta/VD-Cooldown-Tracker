"""Transparent Frameless Always-On-Top Overlay Window.

Week 2 — Day 10 (Fondasi Jendela Overlay Transparan)
Provides a click-through, frameless, transparent overlay window that floats
above the game without stealing keyboard/mouse focus or intercepting gameplay input.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout

from capture.window_helper import set_window_capture_invisible
from app.logger import get_logger

logger = get_logger("overlay.window")

# Win32 Extended Window Styles
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

# Setup 64-bit safe Win32 API calls
user32 = ctypes.windll.user32
if ctypes.sizeof(ctypes.c_void_p) == 8:
    GetWindowLong = user32.GetWindowLongPtrW
    SetWindowLong = user32.SetWindowLongPtrW
    GetWindowLong.restype = ctypes.c_longlong
    GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
    SetWindowLong.restype = ctypes.c_longlong
    SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
else:
    GetWindowLong = user32.GetWindowLongW
    SetWindowLong = user32.SetWindowLongW
    GetWindowLong.restype = ctypes.c_long
    GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
    SetWindowLong.restype = ctypes.c_long
    SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]


def apply_native_click_through(hwnd: int, enable: bool) -> bool:
    """Mengatur atribut tembus klik (WS_EX_TRANSPARENT) secara native pada Windows OS.

    Ketika enable=True, seluruh klik mouse dan pergerakan kursor akan tembus
    100% ke jendela di bawahnya (Roblox) tanpa menginterupsi gameplay.
    """
    try:
        hwnd_val = wintypes.HWND(hwnd)
        style = GetWindowLong(hwnd_val, GWL_EXSTYLE)
        if enable:
            new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            new_style = (style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED

        if new_style != style:
            SetWindowLong(hwnd_val, GWL_EXSTYLE, new_style)
            logger.debug("Applied native Win32 click-through (enable=%s) to HWND %s", enable, hwnd)
        return True
    except Exception as exc:
        logger.warning("Could not apply native Win32 click-through to HWND %s: %s", hwnd, exc)
        return False


class OverlayWindow(QWidget):
    """Jendela Overlay Transparan Melayang Independen."""

    position_changed = Signal(int, int)
    """Dipancarkan saat posisi overlay digeser oleh pengguna dalam mode kalibrasi."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        x: int = 100,
        y: int = 100,
        width: int = 220,
        height: int = 220,
        opacity: float = 0.95,
        click_through: bool = True,
        always_on_top: bool = True,
    ) -> None:
        super().__init__(parent)

        self._click_through: bool = click_through
        self._always_on_top: bool = always_on_top
        self._drag_start_pos: Optional[QPoint] = None

        # 1. Konfigurasi Window Flags
        flags = Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus | Qt.Tool
        if self._always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if self._click_through:
            flags |= Qt.WindowTransparentForInput
        self.setWindowFlags(flags)

        # 2. Konfigurasi Atribut Transparansi Qt
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if self._click_through:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # 3. Geometri dan Opasitas
        self.setGeometry(x, y, width, height)
        self.set_overlay_opacity(opacity)

        # Layout internal untuk menampung widget indikator cooldown (Day 11)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(0)

        logger.info(
            "OverlayWindow created. Pos: (%d, %d) | Size: %dx%d | Click-Through: %s | Always-On-Top: %s",
            x,
            y,
            width,
            height,
            click_through,
            always_on_top,
        )

    def showEvent(self, event) -> None:
        """Dipanggil saat jendela overlay ditampilkan."""
        super().showEvent(event)
        hwnd = int(self.winId())

        # Proteksi agar overlay tidak ikut terekam oleh capture engine
        set_window_capture_invisible(hwnd)

        # Terapkan click-through native Win32 jika diaktifkan
        if self._click_through:
            apply_native_click_through(hwnd, True)

    def set_click_through(self, enabled: bool) -> None:
        """Mengatur mode tembus klik.

        Args:
            enabled: Jika True, klik tembus ke game (gameplay mode).
                     Jika False, overlay dapat diklik dan digeser (calibration mode).
        """
        self._click_through = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)

        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowTransparentForInput
        else:
            flags &= ~Qt.WindowTransparentForInput
        self.setWindowFlags(flags)

        hwnd = int(self.winId())
        apply_native_click_through(hwnd, enabled)

        # Tampilkan ulang jendela untuk merefresh window flags
        self.show()

        # Repaint untuk menampilkan/menyembunyikan border kalibrasi
        self.update()
        logger.info("Overlay click-through set to %s (HWND: %s)", enabled, hwnd)

    @property
    def is_click_through(self) -> bool:
        return self._click_through

    def set_always_on_top(self, enabled: bool) -> None:
        """Mengatur apakah overlay selalu berada di lapisan terdepan."""
        self._always_on_top = enabled
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        logger.info("Overlay always-on-top set to %s", enabled)

    @property
    def is_always_on_top(self) -> bool:
        return self._always_on_top

    def set_overlay_opacity(self, opacity: float) -> None:
        """Mengatur tingkat transparansi overlay (rentang 0.1 s/d 1.0)."""
        clamped = max(0.1, min(1.0, float(opacity)))
        self.setWindowOpacity(clamped)

    def set_overlay_position(self, x: int, y: int) -> None:
        """Memindahkan posisi overlay pada layar desktop."""
        self.move(int(x), int(y))
        self.position_changed.emit(self.x(), self.y())

    def set_overlay_size(self, width: int, height: int) -> None:
        """Mengatur dimensi jendela overlay."""
        self.resize(max(80, int(width)), max(80, int(height)))

    # =========================================================================
    # Kontrol Interaksi Drag & Move (Hanya Aktif saat Click-Through Dinonaktifkan)
    # =========================================================================

    def mousePressEvent(self, event) -> None:
        if not self._click_through and event.button() == Qt.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self._click_through and self._drag_start_pos is not None and event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)
            self.position_changed.emit(self.x(), self.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if not self._click_through and event.button() == Qt.LeftButton:
            self._drag_start_pos = None
            self.position_changed.emit(self.x(), self.y())
            logger.info("Overlay moved to (%d, %d) via drag.", self.x(), self.y())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        """Rendering visual latar belakang overlay.

        Sangat ringan: hanya menggambar border bantu saat mode kalibrasi aktif.
        Dilarang menjalankan komputasi berat, capture, atau inferensi di sini.
        """
        if not self._click_through:
            # Mode Kalibrasi: Tampilkan border dashed kuning neon sebagai panduan visual
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            pen = QPen(QColor(250, 204, 21, 200), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(15, 15, 20, 140))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

            painter.setPen(QColor(250, 204, 21, 230))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(
                self.rect().adjusted(0, 6, 0, 0),
                Qt.AlignTop | Qt.AlignHCenter,
                "⚙️ Calibration Mode (Drag to Move)",
            )
            painter.end()
        else:
            # Mode Gameplay Tembus: Latar belakang 100% transparan
            pass
