"""Interactive Manual Test Script for Transparent Overlay & Cooldown Widget.

Violence District Cooldown Tracker — Day 11 Manual Verification
Jalankan script ini di terminal untuk melihat dan berinteraksi langsung
dengan jendela overlay transparan melayang di atas desktop Anda:

    python tests/demo_overlay.py

Fitur Pengujian Interaktif:
- Pemicuan simulasi skill The Hidden (Leap - 25s) & Veil (Through The Veil - 20s)
- Mode Kalibrasi (geser posisi overlay dengan mouse)
- Mode Gameplay (tembus klik 100% / click-through)
- Reset timer seketika
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.logger import setup_logging
from database.database_manager import DatabaseManager, AbilityConfig
from cooldown.cooldown_manager import CooldownManager
from cooldown.ability_event import AbilityEvent
from overlay.overlay_window import OverlayWindow
from overlay.overlay_controller import OverlayController


class OverlayDemoWindow(QMainWindow):
    """Panel Kontrol Pengujian Manual Overlay & Cooldown Indicator."""

    def __init__(self) -> None:
        super().__init__()

        # Inisialisasi Database & Cooldown Manager
        self.db_manager = DatabaseManager()
        self.cooldown_manager = CooldownManager()

        # Inisialisasi Overlay Window & Controller
        self.overlay_window = OverlayWindow(
            x=200,
            y=200,
            width=200,
            height=200,
            opacity=0.95,
            click_through=False,  # Awalnya buka dalam mode kalibrasi agar pengguna bisa melihat letaknya
            always_on_top=True,
        )
        self.overlay_controller = OverlayController(
            cooldown_manager=self.cooldown_manager,
            overlay_window=self.overlay_window,
            refresh_fps=30,
        )

        self.setWindowTitle("Overlay Interactive Manual Tester — Day 11")
        self.resize(460, 380)
        self.setStyleSheet("""
            QMainWindow { background-color: #121214; }
            QLabel { color: #ECECEC; }
            QGroupBox {
                color: #A0A0B0;
                font-weight: bold;
                border: 1px solid #2E2E36;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QPushButton {
                background-color: #26262B;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #34343C; }
            QComboBox {
                background-color: #1A1A1E;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 5px;
                padding: 4px 8px;
            }
        """)

        self.setup_ui()
        self._load_active_ability()

        # Tampilkan jendela overlay secara default
        self.overlay_controller.show_overlay()

    def setup_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info
        header = QLabel("<b>Violence District Overlay Live Preview</b>")
        header.setFont(QFont("Segoe UI", 12))
        layout.addWidget(header)

        desc = QLabel(
            "Lingkaran overlay transparan saat ini sedang melayang di layar Anda.\n"
            "Gunakan tombol di bawah ini untuk memicu cooldown dan menguji mode tembus klik."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(desc)

        # Grup 1: Pilih Kemampuan
        group_ability = QGroupBox("Pilihan Kemampuan Killer")
        g1_layout = QVBoxLayout(group_ability)

        self.combo_killer = QComboBox()
        self.combo_killer.addItem("The Hidden — Leap (25s | on_cast_start)", ("the_hidden", "leap"))
        self.combo_killer.addItem("The Hidden — Mark (30s | on_cast_start)", ("the_hidden", "mark"))
        self.combo_killer.addItem("Veil — Through The Veil (20s | on_release)", ("veil", "through_the_veil"))
        self.combo_killer.currentIndexChanged.connect(self._on_ability_selection_changed)
        g1_layout.addWidget(self.combo_killer)
        layout.addWidget(group_ability)

        # Grup 2: Tombol Simulasi Event
        group_sim = QGroupBox("Simulasi Pemicu Cooldown")
        g2_layout = QVBoxLayout(group_sim)

        row_btn1 = QHBoxLayout()
        self.btn_cast_start = QPushButton("⚡ Simulate Cast Start")
        self.btn_cast_start.setStyleSheet("background-color: #1E3A8A; color: #93C5FD;")
        self.btn_cast_start.clicked.connect(self.on_simulate_cast_start)
        row_btn1.addWidget(self.btn_cast_start)

        self.btn_release = QPushButton("🚀 Simulate Release")
        self.btn_release.setStyleSheet("background-color: #14532D; color: #86EFAC;")
        self.btn_release.clicked.connect(self.on_simulate_release)
        row_btn1.addWidget(self.btn_release)
        g2_layout.addLayout(row_btn1)

        self.btn_reset = QPushButton("🔄 Reset ke READY")
        self.btn_reset.setStyleSheet("background-color: #4C1D24; color: #FCA5A5;")
        self.btn_reset.clicked.connect(self.on_simulate_reset)
        g2_layout.addWidget(self.btn_reset)
        layout.addWidget(group_sim)

        # Grup 3: Mode Kalibrasi & Click-Through
        group_mode = QGroupBox("Kontrol Posisi & Tembus Klik (Click-Through)")
        g3_layout = QVBoxLayout(group_mode)

        self.chk_calibration = QCheckBox("Mode Kalibrasi (Bisa digeser mouse)")
        self.chk_calibration.setChecked(True)
        self.chk_calibration.toggled.connect(self.on_toggle_calibration)
        g3_layout.addWidget(self.chk_calibration)

        info_mode = QLabel(
            "• <b>Centang aktif (Mode Kalibrasi):</b> Border kuning muncul, Anda bisa klik dan geser lingkaran ke mana saja.\n"
            "• <b>Centang mati (Mode Gameplay):</b> Border hilang, mouse klik tembus 100% ke game di belakangnya."
        )
        info_mode.setWordWrap(True)
        info_mode.setStyleSheet("color: #FBBF24; font-size: 11px;")
        g3_layout.addWidget(info_mode)
        layout.addWidget(group_mode)

        self.setCentralWidget(central)

    def _load_active_ability(self) -> None:
        killer_id, ability_id = self.combo_killer.currentData()
        ability = self.db_manager.get_ability(killer_id, ability_id)
        if ability:
            self.cooldown_manager.set_ability(killer_id, ability)

    def _on_ability_selection_changed(self, index: int) -> None:
        self._load_active_ability()

    def on_simulate_cast_start(self) -> None:
        killer_id, ability_id = self.combo_killer.currentData()
        event = AbilityEvent.create(killer_id, ability_id, "cast_start")
        self.cooldown_manager.handle_event(event)

    def on_simulate_release(self) -> None:
        killer_id, ability_id = self.combo_killer.currentData()
        event = AbilityEvent.create(killer_id, ability_id, "release")
        self.cooldown_manager.handle_event(event)

    def on_simulate_reset(self) -> None:
        self.cooldown_manager.reset()

    def on_toggle_calibration(self, checked: bool) -> None:
        self.overlay_controller.set_calibration_mode(checked)

    def closeEvent(self, event) -> None:
        self.overlay_controller.close()
        event.accept()


def main() -> None:
    setup_logging(debug_mode=True)
    app = QApplication(sys.argv)
    demo = OverlayDemoWindow()
    demo.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
