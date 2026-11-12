"""Circular Cooldown Indicator Widget for Transparent Overlay.

Week 2 — Day 11 (Cooldown Widget)
Renders a smooth circular/radial progress ring, formatted remaining seconds,
ability identity, and READY transition using PySide6 QPainter.
Lightweight 2D graphics with zero capture/CV overhead in paintEvent.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from cooldown.cooldown_state import CooldownSnapshot, CooldownState
from app.logger import get_logger

logger = get_logger("overlay.widget")


class CooldownWidget(QWidget):
    """Custom Widget PySide6 untuk indikator radial circular cooldown."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._snapshot: Optional[CooldownSnapshot] = None
        self.setMinimumSize(120, 120)

        # Palet Warna Visual
        self.COLOR_BG = QColor(14, 14, 18, 200)             # Latar belakang piringan gelap semi-transparan
        self.COLOR_TRACK = QColor(40, 40, 50, 160)          # Jalur cincin kosong
        self.COLOR_READY = QColor(16, 185, 129, 240)        # Emerald / Neon Green saat READY
        self.COLOR_COOLDOWN = QColor(239, 68, 68, 240)      # Coral Red saat Cooldown aktif
        self.COLOR_AIMING = QColor(245, 158, 11, 240)       # Amber / Emas saat Waiting for Release
        self.COLOR_DISABLED = QColor(100, 116, 139, 180)    # Muted Slate saat Disabled
        self.COLOR_TEXT_MAIN = QColor(248, 250, 252, 255)   # Putih bersih untuk teks angka
        self.COLOR_TEXT_SUB = QColor(148, 163, 184, 230)    # Abu-abu kebiruan untuk nama kemampuan
        self.COLOR_UNVERIFIED = QColor(251, 191, 36, 230)   # Kuning peringatan unverified

    def update_snapshot(self, snapshot: CooldownSnapshot) -> None:
        """Memperbarui data snapshot status cooldown dan memicu repaint.

        Args:
            snapshot: Objek CooldownSnapshot immutable terbaru dari CooldownManager.
        """
        self._snapshot = snapshot
        self.update()

    @property
    def snapshot(self) -> Optional[CooldownSnapshot]:
        return self._snapshot

    def paintEvent(self, event) -> None:
        """Rendering grafis 2D indikator cooldown radial.

        Sangat ringan: hanya menggunakan operasi geometris QPainter sederhana.
        Dilarang memuat I/O, capture, atau kalkulasi CV di metode ini.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        size = min(w, h)
        center_x = w / 2.0
        center_y = h / 2.0

        # Margin dan radius
        padding = 10.0
        radius = (size / 2.0) - padding
        ring_thickness = max(4.0, size * 0.055)

        # 1. Gambar Piringan Latar Belakang (Dark Disc)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.COLOR_BG)
        painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))

        # 2. Gambar Jalur Cincin Kosong (Background Ring Track)
        ring_rect = QRectF(
            center_x - radius + (ring_thickness / 2.0),
            center_y - radius + (ring_thickness / 2.0),
            (radius * 2) - ring_thickness,
            (radius * 2) - ring_thickness,
        )
        track_pen = QPen(self.COLOR_TRACK, ring_thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(ring_rect)

        # Status & Parameter Kemampuan
        state = self._snapshot.state if self._snapshot else CooldownState.READY
        progress = self._snapshot.progress if self._snapshot else 0.0
        ability_name = self._snapshot.ability_name if self._snapshot else "NO ABILITY"
        formatted_time = self._snapshot.formatted_remaining if self._snapshot else "READY"
        is_verified = self._snapshot.verified if self._snapshot else False

        # 3. Gambar Busur Progress Radial Berwarna (Active Progress Arc)
        # 12 o'clock = 90 derajat. Di Qt: 1 derajat = 16 unit sudut.
        start_angle = 90 * 16

        if state == CooldownState.READY:
            # Lingkaran penuh 360 derajat warna hijau neon
            arc_pen = QPen(self.COLOR_READY, ring_thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(ring_rect, start_angle, -360 * 16)

        elif state == CooldownState.COOLDOWN:
            # Busur berputar mundur searah jarum jam proporsional terhadap sisa waktu
            span_angle = -int(progress * 360.0 * 16.0)
            arc_pen = QPen(self.COLOR_COOLDOWN, ring_thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(ring_rect, start_angle, span_angle)

        elif state == CooldownState.WAITING_FOR_RELEASE:
            # Lingkaran penuh berkedip/warna amber menandakan fase ancang-ancang
            arc_pen = QPen(self.COLOR_AIMING, ring_thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(ring_rect, start_angle, -360 * 16)

        elif state == CooldownState.DISABLED:
            arc_pen = QPen(self.COLOR_DISABLED, ring_thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(ring_rect, start_angle, -360 * 16)

        # 4. Gambar Teks Header: Nama Kemampuan (Atas)
        name_font = QFont("Segoe UI", max(7, int(size * 0.055)), QFont.Bold)
        painter.setFont(name_font)
        painter.setPen(self.COLOR_TEXT_SUB)
        top_rect = QRectF(center_x - radius, center_y - (radius * 0.65), radius * 2, radius * 0.4)
        painter.drawText(top_rect, Qt.AlignCenter, ability_name.upper())

        # 5. Gambar Teks Tengah: Hitungan Detik / Status READY
        val_font_size = max(11, int(size * 0.13))
        val_font = QFont("Segoe UI", val_font_size, QFont.Bold)
        painter.setFont(val_font)

        if state == CooldownState.READY:
            painter.setPen(self.COLOR_READY)
        elif state == CooldownState.WAITING_FOR_RELEASE:
            painter.setPen(self.COLOR_AIMING)
        else:
            painter.setPen(self.COLOR_TEXT_MAIN)

        center_rect = QRectF(center_x - radius, center_y - (radius * 0.25), radius * 2, radius * 0.5)
        painter.drawText(center_rect, Qt.AlignCenter, formatted_time)

        # 6. Gambar Footer: Status Verifikasi / Input Trigger (Bawah)
        sub_font = QFont("Segoe UI", max(6, int(size * 0.045)))
        painter.setFont(sub_font)
        bot_rect = QRectF(center_x - radius, center_y + (radius * 0.28), radius * 2, radius * 0.35)

        if not is_verified and state != CooldownState.DISABLED:
            painter.setPen(self.COLOR_UNVERIFIED)
            painter.drawText(bot_rect, Qt.AlignCenter, "⚠️ Unverified CD")
        else:
            painter.setPen(self.COLOR_TEXT_SUB)
            trigger_lbl = self._snapshot.interact_input if self._snapshot else ""
            painter.drawText(bot_rect, Qt.AlignCenter, trigger_lbl)

        painter.end()
