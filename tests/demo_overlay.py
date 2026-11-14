"""Interactive Manual Test Script for Transparent Overlay & Cooldown Widget.

Violence District Cooldown Tracker — Day 11 / Phase M4 Multi-Ability Verification
Jalankan script ini di terminal untuk melihat dan berinteraksi langsung
dengan jendela overlay transparan melayang di atas desktop Anda:

    python tests/demo_overlay.py

Fitur Pengujian Interaktif:
- Pemicuan simulasi skill The Hidden (Leap & Mark berjalan bersamaan)
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.logger import setup_logging
from cooldown.cooldown_bank import CooldownBank
from database.database_manager import DatabaseManager
from overlay.overlay_controller import OverlayController
from overlay.overlay_window import OverlayWindow


class OverlayDemoWindow(QMainWindow):
    """Panel Kontrol Pengujian Manual Overlay Multi-Ability (Leap + Mark)."""

    def __init__(self) -> None:
        super().__init__()

        # Inisialisasi Database & Cooldown Bank
        self.db_manager = DatabaseManager()
        self.cooldown_bank = CooldownBank()
        self.cooldown_bank.load_killer("the_hidden", db_manager=self.db_manager)

        # Inisialisasi Overlay Window & Controller
        self.overlay_window = OverlayWindow(
            x=200,
            y=200,
            width=220,
            height=130,
            opacity=0.95,
            click_through=False,  # Buka dalam mode kalibrasi agar bisa digeser
            always_on_top=True,
        )
        self.overlay_controller = OverlayController(
            cooldown_bank=self.cooldown_bank,
            overlay_window=self.overlay_window,
            refresh_fps=30,
            sound_on_ready=True,
        )

        self.setWindowTitle("Overlay Multi-Ability Manual Tester — Phase M4")
        self.resize(460, 400)
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
        self.overlay_controller.show_overlay()

    def setup_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("<b>Violence District Multi-Ability Overlay Preview</b>")
        header.setFont(QFont("Segoe UI", 12))
        layout.addWidget(header)

        desc = QLabel(
            "Overlay transparan melayang di layar dengan tampilan multi-ability (Leap + Mark).\n"
            "Kedua ability dapat berjalan bersamaan dan menghitung mundur secara independen."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(desc)

        # Grup 1: Tombol Simulasi Event Multi-Ability
        group_sim = QGroupBox("Simulasi Pemicuan Kemampuan (The Hidden)")
        g_layout = QVBoxLayout(group_sim)

        row1 = QHBoxLayout()
        self.btn_leap = QPushButton("⚡ Trigger Leap (25s)")
        self.btn_leap.setStyleSheet("background-color: #1E3A8A; color: #93C5FD;")
        self.btn_leap.clicked.connect(lambda: self.cooldown_bank.trigger("leap"))
        row1.addWidget(self.btn_leap)

        self.btn_mark = QPushButton("🎯 Trigger Mark (30s)")
        self.btn_mark.setStyleSheet("background-color: #701A75; color: #F0ABFC;")
        self.btn_mark.clicked.connect(lambda: self.cooldown_bank.trigger("mark"))
        row1.addWidget(self.btn_mark)
        g_layout.addLayout(row1)

        self.btn_reset = QPushButton("🔄 Reset Semua ke READY")
        self.btn_reset.setStyleSheet("background-color: #4C1D24; color: #FCA5A5;")
        self.btn_reset.clicked.connect(lambda: self.cooldown_bank.reset())
        g_layout.addWidget(self.btn_reset)
        layout.addWidget(group_sim)

        # Grup 2: Mode Kalibrasi & Click-Through
        group_mode = QGroupBox("Kontrol Posisi & Tembus Klik")
        g2_layout = QVBoxLayout(group_mode)

        self.chk_calibration = QCheckBox("Mode Kalibrasi (Bisa digeser mouse)")
        self.chk_calibration.setChecked(True)
        self.chk_calibration.toggled.connect(self.overlay_controller.set_calibration_mode)
        g2_layout.addWidget(self.chk_calibration)

        info_mode = QLabel(
            "• <b>Mode Kalibrasi:</b> Geser kartu overlay ke posisi yang diinginkan di atas game.\n"
            "• <b>Mode Gameplay (Uncheck):</b> Mouse klik tembus 100% ke Roblox."
        )
        info_mode.setWordWrap(True)
        info_mode.setStyleSheet("color: #FBBF24; font-size: 11px;")
        g2_layout.addWidget(info_mode)
        layout.addWidget(group_mode)

        self.setCentralWidget(central)

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
