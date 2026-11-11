"""
Main Application Entry Point — Day 3 Capture Engine Prototype
Violence District Cooldown Tracker
"""
import sys
import json
import time
from pathlib import Path
import cv2
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QFrame, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont

from capture.windows_capture import MSSWindowsCapture
from capture.capture_interface import CaptureStatus


class CapturePreviewWindow(QMainWindow):
    """
    Jendela GUI Utama untuk Prototype Capture Engine (Day 3).
    Menerima frame dari Capture Engine (Consumer) dan me-render secara real-time.
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.capture_engine = MSSWindowsCapture(buffer_size=1)

        self.setWindowTitle("Violence District Tracker — Capture Prototype")
        self.resize(800, 560)
        self.setMinimumSize(640, 420)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121214;
            }
            QLabel {
                color: #ECECEC;
            }
            QPushButton {
                background-color: #26262B;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34343C;
            }
            QLineEdit {
                background-color: #1A1A1E;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 6px;
                padding: 5px 10px;
            }
        """)

        self.setup_ui()

        # Timer untuk polling UI (Consumer Loop) pada ~30 FPS
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update_frame_preview)
        self.render_timer.start(33)  # ~30 Hz refresh rate

    def setup_ui(self):
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title_label = QLabel("<b>Screen Capture Engine (Day 3)</b>")
        title_label.setFont(QFont("Segoe UI", 12))
        top_bar.addWidget(title_label)

        top_bar.addSpacing(20)
        top_bar.addWidget(QLabel("Target Window:"))
        self.target_input = QLineEdit(self.config.get("capture", {}).get("target_title", "Roblox"))
        self.target_input.setFixedWidth(140)
        top_bar.addWidget(self.target_input)

        top_bar.addStretch()

        self.status_badge = QLabel("STOPPED")
        self.status_badge.setStyleSheet("""
            background-color: #3E1E24;
            color: #FF6B6B;
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
        """)
        top_bar.addWidget(self.status_badge)
        root_layout.addLayout(top_bar)

        # 2. Frame Preview Viewport
        self.preview_label = QLabel("Capture belum aktif.\nKlik 'Start Capture' untuk memulai.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            background-color: #0A0A0C;
            border: 1px solid #282830;
            border-radius: 8px;
            color: #7A7A85;
            font-size: 13px;
        """)
        self.preview_label.setMinimumHeight(320)
        root_layout.addWidget(self.preview_label, stretch=1)

        # 3. Metrics Panel
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            background-color: #1A1A1E;
            border: 1px solid #2E2E36;
            border-radius: 6px;
        """)
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(12, 8, 12, 8)

        self.fps_metric = QLabel("FPS: <b>0.0</b>")
        self.latency_metric = QLabel("Latency: <b>0.0 ms</b>")
        self.res_metric = QLabel("Resolution: <b>0 x 0</b>")
        self.frame_num_metric = QLabel("Frames: <b>0</b>")

        metrics_layout.addWidget(self.fps_metric)
        metrics_layout.addWidget(self.latency_metric)
        metrics_layout.addWidget(self.res_metric)
        metrics_layout.addWidget(self.frame_num_metric)
        root_layout.addWidget(metrics_frame)

        # 4. Action Buttons
        button_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start Capture")
        self.btn_start.setStyleSheet("background-color: #1E4620; color: #4ADE80; border: 1px solid #2A662E;")
        self.btn_start.clicked.connect(self.on_start_capture)
        button_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Stop Capture")
        self.btn_stop.setStyleSheet("background-color: #4A1E24; color: #F87171; border: 1px solid #6E2A34;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop_capture)
        button_layout.addWidget(self.btn_stop)

        button_layout.addStretch()

        self.btn_snapshot = QPushButton("📸 Save Snapshot")
        self.btn_snapshot.clicked.connect(self.on_save_snapshot)
        self.btn_snapshot.setEnabled(False)
        button_layout.addWidget(self.btn_snapshot)

        root_layout.addLayout(button_layout)
        self.setCentralWidget(central_widget)

    def on_start_capture(self):
        target = self.target_input.text().strip()
        if not target:
            target = "Roblox"

        fps_target = self.config.get("capture", {}).get("target_fps", 30)
        self.capture_engine.start(target_title=target, target_fps=fps_target)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snapshot.setEnabled(True)
        self.target_input.setEnabled(False)

    def on_stop_capture(self):
        self.capture_engine.stop()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snapshot.setEnabled(False)
        self.target_input.setEnabled(True)

        self.status_badge.setText("STOPPED")
        self.status_badge.setStyleSheet("background-color: #3E1E24; color: #FF6B6B; border-radius: 4px; padding: 3px 8px; font-weight: bold;")
        self.preview_label.setText("Capture dihentikan.")

    def on_save_snapshot(self):
        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is not None:
            output_dir = Path("dataset")
            output_dir.mkdir(exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            file_path = output_dir / f"snapshot_{timestamp_str}.png"
            cv2.imwrite(str(file_path), frame_data.image)
            QMessageBox.information(self, "Snapshot Tersimpan", f"Frame berhasil disimpan ke:\n{file_path}")

    def update_frame_preview(self):
        """Polling frame dari buffer capture engine dan render ke label."""
        status = self.capture_engine.status

        # Update Badge
        if status == CaptureStatus.RUNNING:
            self.status_badge.setText("RUNNING")
            self.status_badge.setStyleSheet("background-color: #14381C; color: #4ADE80; border-radius: 4px; padding: 3px 8px; font-weight: bold;")
        elif status == CaptureStatus.TARGET_LOST:
            self.status_badge.setText("TARGET LOST")
            self.status_badge.setStyleSheet("background-color: #4A3A10; color: #FBBF24; border-radius: 4px; padding: 3px 8px; font-weight: bold;")
        elif status == CaptureStatus.ERROR:
            self.status_badge.setText("ERROR")
            self.status_badge.setStyleSheet("background-color: #4A1E24; color: #F87171; border-radius: 4px; padding: 3px 8px; font-weight: bold;")

        # Update Metrik
        self.fps_metric.setText(f"FPS: <b>{self.capture_engine.current_fps:.1f}</b>")
        self.latency_metric.setText(f"Latency: <b>{self.capture_engine.current_latency_ms:.1f} ms</b>")

        if not self.capture_engine.is_running:
            return

        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is None:
            if status == CaptureStatus.TARGET_LOST:
                self.preview_label.setText(f"Menunggu jendela target '{self.target_input.text()}' aktif...")
            return

        # Update Metadata Dimensi & Jumlah Frame
        self.res_metric.setText(f"Resolution: <b>{frame_data.width}x{frame_data.height}</b>")
        self.frame_num_metric.setText(f"Frames: <b>{frame_data.frame_index}</b>")

        # Konversi OpenCV BGR -> QImage RGB untuk render Qt
        bgr = frame_data.image
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # Scale sesuai viewport dengan mempertahankan aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        """Memastikan clean shutdown worker thread saat window ditutup (Mitigasi RSK-20261111-01)."""
        self.render_timer.stop()
        if self.capture_engine.is_running:
            self.capture_engine.stop()
        event.accept()


def main():
    config_path = Path("config/app_config.json")
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    app = QApplication(sys.argv)
    window = CapturePreviewWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
