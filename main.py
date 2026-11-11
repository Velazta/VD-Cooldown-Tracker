"""
Main Application Entry Point — Day 4 ROI Calibration & Visual Preview
Violence District Cooldown Tracker
"""
import sys
import json
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QFrame, QLineEdit, QMessageBox,
    QSpinBox, QFormLayout, QGroupBox, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont

from capture.windows_capture import MSSWindowsCapture
from capture.capture_interface import CaptureStatus
from processing.roi_processor import ROIConfig, ROIProcessor
from processing.preprocessing import ImagePreprocessor, PreprocessingConfig, PreprocessorMode


class CapturePreviewWindow(QMainWindow):
    """
    Jendela GUI Utama untuk Prototype Capture Engine & Kalibrasi Visual ROI (Day 4).
    Mendukung penyesuaian bounding box interaktif dan preview 1:1 area HUD.
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.config_path = Path("config/app_config.json")

        # Inisialisasi ROI Configuration dari file config
        roi_dict = self.config.get("capture", {}).get("roi", {})
        self.roi_config = ROIConfig(
            x=roi_dict.get("x", 0),
            y=roi_dict.get("y", 0),
            width=roi_dict.get("width", 450),
            height=roi_dict.get("height", 250),
            enabled=roi_dict.get("enabled", roi_dict.get("enable", True))
        )
        self.roi_processor = ROIProcessor(self.roi_config)

        # Inisialisasi OpenCV Preprocessor (Step 4.3)
        self.preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.RAW))

        # Inisialisasi Capture Engine
        self.capture_engine = MSSWindowsCapture(buffer_size=1)

        self.setWindowTitle("Violence District Tracker — HUD ROI Calibration (Day 4)")
        self.resize(1020, 640)
        self.setMinimumSize(850, 500)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121214;
            }
            QLabel {
                color: #ECECEC;
            }
            QGroupBox {
                color: #A0A0B0;
                font-weight: bold;
                border: 1px solid #2E2E36;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
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
            QLineEdit, QSpinBox {
                background-color: #1A1A1E;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 5px;
                padding: 4px 8px;
            }
        """)

        self.setup_ui()

        # Timer untuk polling UI (Consumer Loop) ~30 FPS
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update_frame_preview)
        self.render_timer.start(33)

    def setup_ui(self):
        central_widget = QWidget(self)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        # ==========================================
        # KOLOM KIRI: Full Capture Viewport & Metrics
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Top Bar (Toolbar)
        top_bar = QHBoxLayout()
        title_label = QLabel("<b>Screen Capture Viewport</b>")
        title_label.setFont(QFont("Segoe UI", 11))
        top_bar.addWidget(title_label)

        top_bar.addSpacing(15)
        top_bar.addWidget(QLabel("Target:"))
        self.target_input = QLineEdit(self.config.get("capture", {}).get("target_title", "Roblox"))
        self.target_input.setFixedWidth(120)
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
        left_col.addLayout(top_bar)

        # Full Viewport Preview Label
        self.preview_label = QLabel("Capture belum aktif.\nKlik 'Start Capture' untuk memulai.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            background-color: #0A0A0C;
            border: 1px solid #282830;
            border-radius: 8px;
            color: #7A7A85;
            font-size: 13px;
        """)
        self.preview_label.setMinimumHeight(380)
        left_col.addWidget(self.preview_label, stretch=1)

        # Metrics Panel
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            background-color: #1A1A1E;
            border: 1px solid #2E2E36;
            border-radius: 6px;
        """)
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(10, 6, 10, 6)

        self.fps_metric = QLabel("FPS: <b>0.0</b>")
        self.latency_metric = QLabel("Latency: <b>0.0 ms</b>")
        self.cv_proc_metric = QLabel("CV Proc: <b>0.0 ms</b>")
        self.res_metric = QLabel("Resolution: <b>0x0</b>")
        self.frame_num_metric = QLabel("Frames: <b>0</b>")

        metrics_layout.addWidget(self.fps_metric)
        metrics_layout.addWidget(self.latency_metric)
        metrics_layout.addWidget(self.cv_proc_metric)
        metrics_layout.addWidget(self.res_metric)
        metrics_layout.addWidget(self.frame_num_metric)
        left_col.addWidget(metrics_frame)

        # Capture Control Buttons
        btn_bar = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start Capture")
        self.btn_start.setStyleSheet("background-color: #1E4620; color: #4ADE80; border: 1px solid #2A662E;")
        self.btn_start.clicked.connect(self.on_start_capture)
        btn_bar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Stop Capture")
        self.btn_stop.setStyleSheet("background-color: #4A1E24; color: #F87171; border: 1px solid #6E2A34;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.on_stop_capture)
        btn_bar.addWidget(self.btn_stop)

        btn_bar.addStretch()

        self.btn_snapshot = QPushButton("📸 Snapshot Full")
        self.btn_snapshot.clicked.connect(self.on_save_snapshot)
        self.btn_snapshot.setEnabled(False)
        btn_bar.addWidget(self.btn_snapshot)

        left_col.addLayout(btn_bar)
        root_layout.addLayout(left_col, stretch=7)

        # ==========================================
        # KOLOM KANAN: Visual ROI Calibration Panel
        # ==========================================
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        roi_group = QGroupBox("HUD Region of Interest (ROI)")
        roi_layout = QVBoxLayout(roi_group)
        roi_layout.setSpacing(10)

        # Dedicated Cropped ROI Viewport
        self.roi_preview_label = QLabel("Area ROI")
        self.roi_preview_label.setAlignment(Qt.AlignCenter)
        self.roi_preview_label.setStyleSheet("""
            background-color: #060608;
            border: 2px dashed #4ADE80;
            border-radius: 6px;
            color: #4ADE80;
        """)
        self.roi_preview_label.setFixedHeight(180)
        roi_layout.addWidget(self.roi_preview_label)

        self.roi_size_label = QLabel("Ukuran: 0 x 0 px")
        self.roi_size_label.setAlignment(Qt.AlignCenter)
        self.roi_size_label.setStyleSheet("color: #9E9EB0; font-size: 11px;")
        roi_layout.addWidget(self.roi_size_label)

        # ROI Coordinates Form Controls (SpinBoxes)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 3840)
        self.spin_x.setSingleStep(10)
        self.spin_x.setValue(self.roi_config.x)
        self.spin_x.valueChanged.connect(self.on_roi_spin_changed)
        form_layout.addRow("Koordinat X:", self.spin_x)

        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 2160)
        self.spin_y.setSingleStep(10)
        self.spin_y.setValue(self.roi_config.y)
        self.spin_y.valueChanged.connect(self.on_roi_spin_changed)
        form_layout.addRow("Koordinat Y:", self.spin_y)

        self.spin_w = QSpinBox()
        self.spin_w.setRange(10, 1920)
        self.spin_w.setSingleStep(10)
        self.spin_w.setValue(self.roi_config.width)
        self.spin_w.valueChanged.connect(self.on_roi_spin_changed)
        form_layout.addRow("Lebar (W):", self.spin_w)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(10, 1080)
        self.spin_h.setSingleStep(10)
        self.spin_h.setValue(self.roi_config.height)
        self.spin_h.valueChanged.connect(self.on_roi_spin_changed)
        form_layout.addRow("Tinggi (H):", self.spin_h)

        self.check_roi_enable = QCheckBox("Aktifkan ROI Overlay")
        self.check_roi_enable.setChecked(self.roi_config.enabled)
        self.check_roi_enable.toggled.connect(self.on_roi_toggle_changed)
        form_layout.addRow("", self.check_roi_enable)

        # Dropdown OpenCV Preprocessor Mode (Step 4.3)
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("Raw BGR (No Filter)", PreprocessorMode.RAW)
        self.combo_filter.addItem("Grayscale (Luminance)", PreprocessorMode.GRAYSCALE)
        self.combo_filter.addItem("CLAHE (Night Contrast Boost)", PreprocessorMode.CLAHE)
        self.combo_filter.addItem("Threshold (Binary Shapes)", PreprocessorMode.THRESHOLD)
        self.combo_filter.addItem("Canny (Edge Contours)", PreprocessorMode.CANNY)
        self.combo_filter.currentIndexChanged.connect(self.on_filter_mode_changed)
        form_layout.addRow("Filter CV:", self.combo_filter)

        roi_layout.addLayout(form_layout)

        # ROI Action Buttons
        self.btn_save_roi = QPushButton("💾 Simpan ROI ke Config")
        self.btn_save_roi.setStyleSheet("background-color: #1A365D; color: #90CDF4; border: 1px solid #2B6CB0;")
        self.btn_save_roi.clicked.connect(self.on_save_roi_config)
        roi_layout.addWidget(self.btn_save_roi)

        self.btn_save_roi_sample = QPushButton("✂️ Simpan Sampel Crop ROI")
        self.btn_save_roi_sample.clicked.connect(self.on_save_roi_sample)
        self.btn_save_roi_sample.setEnabled(False)
        roi_layout.addWidget(self.btn_save_roi_sample)

        roi_layout.addStretch()
        right_col.addWidget(roi_group)
        root_layout.addLayout(right_col, stretch=3)

        self.setCentralWidget(central_widget)

    def on_roi_spin_changed(self):
        """Memperbarui model ROI saat nilai spinbox digeser pengguna."""
        self.roi_config.x = self.spin_x.value()
        self.roi_config.y = self.spin_y.value()
        self.roi_config.width = self.spin_w.value()
        self.roi_config.height = self.spin_h.value()
        self.roi_processor.update_config(self.roi_config)

    def on_roi_toggle_changed(self, checked: bool):
        self.roi_config.enabled = checked
        self.roi_processor.update_config(self.roi_config)

    def on_filter_mode_changed(self, index: int):
        """Memperbarui filter OpenCV saat dropdown diubah."""
        mode = self.combo_filter.currentData()
        self.preprocessor.config.mode = mode

    def on_save_roi_config(self):
        """Menyimpan konfigurasi ROI terkini ke config/app_config.json."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}

            if "capture" not in data:
                data["capture"] = {}

            data["capture"]["roi"] = self.roi_config.to_dict()

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            QMessageBox.information(
                self,
                "Konfigurasi Tersimpan",
                f"Koordinat ROI berhasil disimpan ke {self.config_path}:\n"
                f"X: {self.roi_config.x}, Y: {self.roi_config.y}\n"
                f"Ukuran: {self.roi_config.width} x {self.roi_config.height}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Menyimpan", f"Error menyimpan file: {exc}")

    def on_save_roi_sample(self):
        """Menyimpan potongan frame ROI terkini ke dataset/ sesuai filter yang sedang aktif."""
        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is not None:
            cropped = self.roi_processor.crop(frame_data.image)
            if cropped is not None:
                # Terapkan filter yang sedang aktif pada dropdown
                processed, _ = self.preprocessor.process(cropped)
                mode_name = self.preprocessor.config.mode.value

                output_dir = Path("dataset/roi_samples")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                file_path = output_dir / f"roi_crop_{timestamp_str}_{mode_name}.png"
                cv2.imwrite(str(file_path), processed)
                QMessageBox.information(
                    self,
                    "Crop Tersimpan",
                    f"Sampel ROI ({mode_name.upper()}) berhasil disimpan ke:\n{file_path}"
                )

    def on_start_capture(self):
        target = self.target_input.text().strip() or "Roblox"
        fps_target = self.config.get("capture", {}).get("target_fps", 30)
        self.capture_engine.start(target_title=target, target_fps=fps_target)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snapshot.setEnabled(True)
        self.btn_save_roi_sample.setEnabled(True)
        self.target_input.setEnabled(False)

    def on_stop_capture(self):
        self.capture_engine.stop()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snapshot.setEnabled(False)
        self.btn_save_roi_sample.setEnabled(False)
        self.target_input.setEnabled(True)

        self.status_badge.setText("STOPPED")
        self.status_badge.setStyleSheet("background-color: #3E1E24; color: #FF6B6B; border-radius: 4px; padding: 3px 8px; font-weight: bold;")
        self.preview_label.setText("Capture dihentikan.")
        self.roi_preview_label.setText("Area ROI")

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
        """Polling frame dari buffer capture engine dan render ke viewport & panel ROI."""
        status = self.capture_engine.status

        # Update Status Badge
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

        self.res_metric.setText(f"Resolution: <b>{frame_data.width}x{frame_data.height}</b>")
        self.frame_num_metric.setText(f"Frames: <b>{frame_data.frame_index}</b>")

        # 1. Proses Pemotongan ROI (Step 4.1) & OpenCV Preprocessing (Step 4.3)
        cropped_roi = self.roi_processor.crop(frame_data.image)
        if cropped_roi is not None and cropped_roi.size > 0:
            roi_h, roi_w = cropped_roi.shape[:2]
            self.roi_size_label.setText(f"Ukuran: {roi_w} x {roi_h} px")

            # Jalankan Pipeline Preprocessing OpenCV terukur
            processed_roi, proc_time_ms = self.preprocessor.process(cropped_roi)
            self.cv_proc_metric.setText(f"CV Proc: <b>{proc_time_ms:.1f} ms</b>")

            # Konversi format citra ke RGB untuk render Qt
            if len(processed_roi.shape) == 2:
                # 1-Channel (Grayscale, Threshold, Canny) -> Konversi ke RGB untuk display
                roi_rgb = cv2.cvtColor(processed_roi, cv2.COLOR_GRAY2RGB)
            else:
                # 3-Channel (Raw, CLAHE) -> Konversi BGR ke RGB
                roi_rgb = cv2.cvtColor(processed_roi, cv2.COLOR_BGR2RGB)

            ph, pw = roi_rgb.shape[:2]
            q_roi = QImage(roi_rgb.data, pw, ph, 3 * pw, QImage.Format_RGB888)
            pix_roi = QPixmap.fromImage(q_roi).scaled(
                self.roi_preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.roi_preview_label.setPixmap(pix_roi)
        else:
            self.roi_size_label.setText("Ukuran: ROI Dinonaktifkan")
            self.cv_proc_metric.setText("CV Proc: <b>0.0 ms</b>")

        # 2. Gambar Bounding Box Hijau pada Full Frame
        annotated_frame = self.roi_processor.draw_roi_box(frame_data.image)

        # 3. Optimasi Downsampling C++ sebelum ke QImage Viewport Kiri
        target_size = self.preview_label.size()
        lbl_w = max(100, target_size.width())
        lbl_h = max(100, target_size.height())

        h, w = annotated_frame.shape[:2]
        scale = min(lbl_w / w, lbl_h / h)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))

        thumb_bgr = cv2.resize(annotated_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(thumb_bgr, cv2.COLOR_BGR2RGB)

        q_img = QImage(rgb.data, new_w, new_h, 3 * new_w, QImage.Format_RGB888)
        self.preview_label.setPixmap(QPixmap.fromImage(q_img))

    def closeEvent(self, event):
        """Memastikan clean shutdown worker thread saat window ditutup."""
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
