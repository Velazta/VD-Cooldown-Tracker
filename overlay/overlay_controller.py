"""Overlay Controller Module for Violence District Cooldown Tracker.

Violence District Cooldown Tracker — Week 2 / Manual Milestone (Phase M4)
Bridges CooldownBank / CooldownManager state snapshots to OverlayWindow and CooldownWidget.
Manages UI repaint cadence independently of timer accuracy.
"""

from __future__ import annotations

from typing import Optional, Union

from PySide6.QtCore import QObject, QTimer, Signal

from app.logger import get_logger
from cooldown.cooldown_bank import CooldownBank
from cooldown.cooldown_manager import CooldownManager
from cooldown.cooldown_state import CooldownSnapshot
from overlay.cooldown_widget import CooldownWidget
from overlay.overlay_window import OverlayWindow

logger = get_logger("overlay.controller")


class OverlayController(QObject):
    """Controller untuk mengoordinasikan CooldownBank / CooldownManager dengan Overlay visual."""

    overlay_moved = Signal(int, int)
    """Dipancarkan saat posisi jendela overlay digeser oleh pengguna."""

    def __init__(
        self,
        cooldown_manager: Optional[CooldownManager] = None,
        cooldown_bank: Optional[CooldownBank] = None,
        overlay_window: Optional[OverlayWindow] = None,
        refresh_fps: int = 30,
        sound_on_ready: bool = False,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.cooldown_manager = cooldown_manager
        self.cooldown_bank = cooldown_bank
        self.overlay_window = overlay_window or OverlayWindow()

        # Inisialisasi Widget Indikator Cooldown di dalam Jendela Overlay
        self.cooldown_widget = CooldownWidget(self.overlay_window)
        self.cooldown_widget.set_sound_on_ready(sound_on_ready)
        self.overlay_window.main_layout.addWidget(self.cooldown_widget)

        # Teruskan sinyal pergeseran posisi jendela
        self.overlay_window.position_changed.connect(self.overlay_moved)

        # 1. Daftarkan diri sebagai listener push event
        if self.cooldown_bank is not None:
            self.cooldown_bank.add_listener(lambda ab_id, snap: self.update_widget())
        elif self.cooldown_manager is not None:
            self.cooldown_manager.add_listener(self.on_state_changed)

        # 2. Timer Polling untuk refresh rendering GUI (~30 FPS = 33ms)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_widget)
        self.set_refresh_fps(refresh_fps)

        # Inisialisasi status awal widget
        self.update_widget()
        logger.info("OverlayController initialized at %d FPS repaint cadence.", refresh_fps)

    def set_sound_on_ready(self, enabled: bool) -> None:
        """Mengatur apakah bunyi diputar saat cooldown siap."""
        self.cooldown_widget.set_sound_on_ready(enabled)

    def set_cooldown_bank(self, bank: CooldownBank) -> None:
        """Mengganti atau menghubungkan CooldownBank aktif."""
        self.cooldown_bank = bank
        bank.add_listener(lambda ab_id, snap: self.update_widget())
        self.update_widget()

    def set_refresh_fps(self, fps: int) -> None:
        """Mengatur frekuensi refresh visual overlay (15 s/d 60 FPS)."""
        clamped_fps = max(15, min(60, fps))
        interval_ms = max(16, int(1000.0 / clamped_fps))
        self.refresh_timer.setInterval(interval_ms)

    def start(self) -> None:
        """Memulai timer rendering visual."""
        if not self.refresh_timer.isActive():
            self.refresh_timer.start()
            logger.info("OverlayController repaint timer started.")

    def stop(self) -> None:
        """Menghentikan timer rendering visual."""
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            logger.info("OverlayController repaint timer stopped.")

    def show_overlay(self) -> None:
        """Menampilkan jendela overlay transparan di atas game."""
        self.overlay_window.show()
        self.start()
        logger.info("Overlay window shown.")

    def hide_overlay(self) -> None:
        """Menyembunyikan jendela overlay."""
        self.overlay_window.hide()
        self.stop()
        logger.info("Overlay window hidden.")

    def toggle_overlay(self) -> bool:
        """Toggle visibilitas overlay (kembalikan True jika sekarang tampil)."""
        if self.overlay_window.isVisible():
            self.hide_overlay()
            return False
        else:
            self.show_overlay()
            return True

    def set_calibration_mode(self, enabled: bool) -> None:
        """Mengatur mode kalibrasi posisi.
        
        Jika True: Click-through dimatikan agar overlay bisa diklik dan digeser mouse.
        Jika False: Click-through diaktifkan kembali untuk gameplay mode.
        """
        self.overlay_window.set_click_through(not enabled)
        logger.info("Overlay calibration mode set to: %s", enabled)

    def on_state_changed(self, snapshot: CooldownSnapshot) -> None:
        """Callback listener saat terjadi transisi status di CooldownManager."""
        self.cooldown_widget.update_snapshot(snapshot)

    def update_widget(self) -> None:
        """Polling sisa waktu monotonic terbaru dan update widget visual."""
        if self.cooldown_bank is not None:
            self.cooldown_widget.update_snapshots(self.cooldown_bank.snapshots())
        elif self.cooldown_manager is not None:
            snapshot = self.cooldown_manager.get_snapshot()
            self.cooldown_widget.update_snapshot(snapshot)

    def close(self) -> None:
        """Pembersihan bersih saat penutupan aplikasi."""
        self.stop()
        if self.cooldown_manager is not None:
            self.cooldown_manager.remove_listener(self.on_state_changed)
        self.overlay_window.close()
        logger.info("OverlayController cleanly closed.")
