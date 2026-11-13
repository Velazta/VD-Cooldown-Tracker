"""Main Application Entry Point — Day 12 Integrated Application & Manual Events.

Violence District Cooldown Tracker
Integrates:
- Logging: Structured dual console + file logging (logs/app.log)
- SettingsManager: Runtime application configuration (config/app_config.json)
- DatabaseManager: Strongly-typed killer & ability database (database/killerDatabase.json)
- CooldownManager: Deterministic monotonic cooldown state machine (cooldown/)
- OverlayController: Frameless always-on-top transparent cooldown ring overlay (overlay/)
- MSSWindowsCapture: Background producer thread screen capture
- ROIProcessor: Centered gameplay viewport cropping and coordinate clamping
- ImagePreprocessor: OpenCV computer vision filters (Raw, Gray, CLAHE, Threshold, Canny)
- PerformanceMonitor: Non-blocking resource and latency telemetry
"""

from __future__ import annotations

import sys
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
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QImage, QPixmap, QFont

from app.logger import setup_logging, get_logger
from app.settings import SettingsManager, AppConfig
from database.database_manager import DatabaseManager, KillerConfig
from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_manager import CooldownManager
from cooldown.cooldown_state import CooldownState
from overlay.overlay_window import OverlayWindow
from overlay.overlay_controller import OverlayController
from capture.windows_capture import MSSWindowsCapture
from capture.capture_interface import CaptureStatus
from capture.window_helper import set_window_capture_invisible
from processing.roi_processor import ROIConfig, ROIProcessor
from processing.preprocessing import ImagePreprocessor, PreprocessingConfig, PreprocessorMode
from monitoring.performance_monitor import PerformanceMonitor
from detection.detection_worker import DetectionWorker
from detection.audio_monitor import AudioMonitor

logger = get_logger("gui")


class CapturePreviewWindow(QMainWindow):
    """Jendela GUI Utama Terintegrasi untuk Violence District Cooldown Tracker."""

    def __init__(
        self,
        settings_manager: Optional[SettingsManager] = None,
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        super().__init__()

        # 1. Manajer Konfigurasi & Database
        self.settings_manager = settings_manager or SettingsManager()
        self.config: AppConfig = self.settings_manager.config

        self.db_manager = db_manager or DatabaseManager()
        try:
            self.database = self.db_manager.database
        except Exception as exc:
            logger.error("Failed to initialize database: %s", exc)
            self.database = None

        # 2. Inisialisasi ROI Configuration dari Settings
        self.roi_config: ROIConfig = self.config.capture.roi
        self.roi_processor = ROIProcessor(self.roi_config)

        # 3. Inisialisasi OpenCV Preprocessor
        self.preprocessor = ImagePreprocessor(PreprocessingConfig(mode=PreprocessorMode.RAW))

        # 4. Inisialisasi Capture Engine & Performance Telemetry
        self.capture_engine = MSSWindowsCapture(buffer_size=1)
        self.monitor = PerformanceMonitor(
            history_size=60,
            target_process_name=self.config.capture.target_title,
        )
        self._telemetry_tick_counter = 0

        # 5. Inisialisasi Cooldown Manager & Overlay Controller (Week 2 Integration)
        self.cooldown_manager = CooldownManager()
        ovl_cfg = self.config.overlay
        self.overlay_window = OverlayWindow(
            x=ovl_cfg.x,
            y=ovl_cfg.y,
            width=ovl_cfg.width,
            height=ovl_cfg.height,
            opacity=ovl_cfg.opacity,
            click_through=ovl_cfg.click_through,
            always_on_top=ovl_cfg.always_on_top,
        )
        self.overlay_controller = OverlayController(
            cooldown_manager=self.cooldown_manager,
            overlay_window=self.overlay_window,
            refresh_fps=30,
            parent=self,
        )
        self.overlay_controller.overlay_moved.connect(self.on_overlay_moved)

        # 6. Inisialisasi Detection Worker & Audio Monitor (Multi-Modal Pipeline)
        self.audio_monitor = AudioMonitor(parent=self)
        self.detection_worker = DetectionWorker(
            capture_engine=self.capture_engine,
            roi_processor=self.roi_processor,
            cooldown_manager=self.cooldown_manager,
            confidence_threshold=0.54,
            parent=self,
        )
        self.detection_worker.ability_detected.connect(self.on_auto_ability_detected)
        self.detection_worker.telemetry_updated.connect(self.on_detector_telemetry_updated)
        self.detection_worker.target_tracked.connect(self.on_target_tracked)
        self.detection_worker.worker_error.connect(self.on_detector_error)
        self.audio_monitor.audio_surge_detected.connect(lambda t: self.detection_worker.set_audio_confirmed(True))

        # Target Bounding Box Visualization Tracking
        self._latest_target_bbox: Optional[Tuple[int, int, int, int]] = None
        self._latest_bbox_label: str = ""
        self._latest_bbox_time: float = 0.0
        self._latest_bbox_is_leap: bool = False

        # Setup Tampilan Jendela
        self.setWindowTitle(
            f"{self.config.app.name} v{self.config.app.version} — Day 7 / Day 19 Live Detection Pipeline"
        )
        self.resize(1160, 720)
        self.setMinimumSize(960, 600)
        self._apply_stylesheet()
        self.setup_ui()

        # Proteksi OS: Cegah efek rekursif Hall of Mirrors
        set_window_capture_invisible(int(self.winId()))

        # Pasang event filter global agar hotkey F1-F4 tidak direbut QComboBox / widget anak
        app_inst = QApplication.instance()
        if app_inst is not None:
            app_inst.installEventFilter(self)

        # Timer untuk polling UI (Consumer Loop) ~30 FPS (33 ms)
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update_frame_preview)
        init_fps = getattr(self.config.capture, "target_fps", 60)
        self.render_timer.start(16 if init_fps == 60 else 33)

        logger.info("Main GUI window initialized successfully.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        set_window_capture_invisible(int(self.winId()))

    def _apply_stylesheet(self) -> None:
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
            QLineEdit, QSpinBox, QComboBox {
                background-color: #1A1A1E;
                color: #FFFFFF;
                border: 1px solid #3E3E46;
                border-radius: 5px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A1E;
                color: #FFFFFF;
                selection-background-color: #2B6CB0;
            }
        """)

    def setup_ui(self) -> None:
        central_widget = QWidget(self)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        # ==========================================
        # KOLOM KIRI: Capture Viewport & Metrics
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
        self.target_input = QLineEdit(self.config.capture.target_title)
        self.target_input.setFixedWidth(120)
        top_bar.addWidget(self.target_input)

        top_bar.addSpacing(10)
        top_bar.addWidget(QLabel("FPS:"))
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 FPS", "30 FPS"])
        if getattr(self.config.capture, "target_fps", 60) == 30:
            self.combo_fps.setCurrentText("30 FPS")
        else:
            self.combo_fps.setCurrentText("60 FPS")
        self.combo_fps.currentTextChanged.connect(self.on_fps_changed)
        top_bar.addWidget(self.combo_fps)

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
        self.preview_label = QLabel("Capture belum aktif.\nKlik 'Start Capture' untuk memulai pemantauan.")
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

        # Metrics Panel (Frame Telemetry & Hardware Telemetry)
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            background-color: #1A1A1E;
            border: 1px solid #2E2E36;
            border-radius: 6px;
        """)
        metrics_root_layout = QVBoxLayout(metrics_frame)
        metrics_root_layout.setContentsMargins(10, 6, 10, 6)
        metrics_root_layout.setSpacing(4)

        # Baris 1: Frame Telemetry
        row1 = QHBoxLayout()
        self.fps_metric = QLabel("FPS: <b>0.0</b>")
        self.latency_metric = QLabel("Capture Lat: <b>0.0 ms</b>")
        self.cv_proc_metric = QLabel("CV Proc: <b>0.0 ms</b>")
        self.res_metric = QLabel("Resolution: <b>0x0</b>")
        self.frame_num_metric = QLabel("Frames: <b>0</b>")

        row1.addWidget(self.fps_metric)
        row1.addWidget(self.latency_metric)
        row1.addWidget(self.cv_proc_metric)
        row1.addWidget(self.res_metric)
        row1.addWidget(self.frame_num_metric)
        metrics_root_layout.addLayout(row1)

        # Baris 2: Hardware Telemetry (psutil)
        row2 = QHBoxLayout()
        self.app_cpu_metric = QLabel("App CPU: <b>0.0%</b>")
        self.app_ram_metric = QLabel("App RAM: <b>0.0 MB</b>")
        self.roblox_cpu_metric = QLabel("Roblox CPU: <b>--</b>")
        self.roblox_ram_metric = QLabel("Roblox RAM: <b>--</b>")

        self.app_cpu_metric.setStyleSheet("color: #60A5FA;")
        self.app_ram_metric.setStyleSheet("color: #60A5FA;")
        self.roblox_cpu_metric.setStyleSheet("color: #F472B6;")
        self.roblox_ram_metric.setStyleSheet("color: #F472B6;")

        row2.addWidget(self.app_cpu_metric)
        row2.addWidget(self.app_ram_metric)
        row2.addWidget(self.roblox_cpu_metric)
        row2.addWidget(self.roblox_ram_metric)
        metrics_root_layout.addLayout(row2)

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
        # KOLOM KANAN: Database & Visual ROI Controls
        # ==========================================
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Panel 1: Active Killer & Abilities (Day 6 Database Integration)
        killer_group = QGroupBox("Active Killer & Cooldowns")
        killer_layout = QVBoxLayout(killer_group)
        killer_layout.setSpacing(8)

        killer_select_row = QHBoxLayout()
        killer_select_row.addWidget(QLabel("Killer:"))
        self.combo_killer = QComboBox()
        killer_select_row.addWidget(self.combo_killer, stretch=1)
        killer_layout.addLayout(killer_select_row)

        ability_select_row = QHBoxLayout()
        ability_select_row.addWidget(QLabel("Ability:"))
        self.combo_ability = QComboBox()
        ability_select_row.addWidget(self.combo_ability, stretch=1)
        killer_layout.addLayout(ability_select_row)

        self.killer_desc_label = QLabel()
        self.killer_desc_label.setWordWrap(True)
        self.killer_desc_label.setStyleSheet("color: #9E9EB0; font-size: 11px;")
        killer_layout.addWidget(self.killer_desc_label)

        self.abilities_container = QLabel()
        self.abilities_container.setWordWrap(True)
        self.abilities_container.setStyleSheet("""
            background-color: #16161A;
            border: 1px solid #282830;
            border-radius: 4px;
            padding: 6px;
            font-size: 11px;
            color: #E2E8F0;
        """)
        killer_layout.addWidget(self.abilities_container)

        self._populate_killer_combobox()
        self.combo_killer.currentIndexChanged.connect(self.on_killer_selection_changed)

        self._populate_ability_combobox()
        self.combo_ability.currentIndexChanged.connect(self.on_ability_selection_changed)

        self._update_killer_display()
        right_col.addWidget(killer_group)

        # Panel 2: Overlay & Event Simulation Controls (Day 12 Integration)
        overlay_group = QGroupBox("Overlay & Event Simulation")
        overlay_layout = QVBoxLayout(overlay_group)
        overlay_layout.setSpacing(8)

        # Baris Checkbox: Visibilitas & Kalibrasi
        overlay_check_row = QHBoxLayout()
        self.check_overlay_visible = QCheckBox("👁️ Overlay (F4)")
        self.check_overlay_visible.toggled.connect(self.on_toggle_overlay_checked)
        self.check_overlay_visible.setChecked(self.config.overlay.visible)
        overlay_check_row.addWidget(self.check_overlay_visible)

        self.check_calibration_mode = QCheckBox("⚙️ Mode Kalibrasi")
        self.check_calibration_mode.setToolTip("Nonaktifkan click-through agar posisi overlay dapat diklik dan digeser mouse.")
        self.check_calibration_mode.toggled.connect(self.on_toggle_calibration_mode)
        overlay_check_row.addWidget(self.check_calibration_mode)
        overlay_layout.addLayout(overlay_check_row)

        # Baris Tombol: Simulasi Manual
        sim_btn_row = QHBoxLayout()
        self.btn_simulate_cast = QPushButton("⚡ Cast (F1)")
        self.btn_simulate_cast.setToolTip("Kirim event 'cast_start'. Leap langsung cooldown; Veil masuk stance aiming.")
        self.btn_simulate_cast.setStyleSheet("background-color: #854D0E; color: #FDE047; border: 1px solid #CA8A04;")
        self.btn_simulate_cast.clicked.connect(lambda: self.simulate_cast_start(source="manual"))
        sim_btn_row.addWidget(self.btn_simulate_cast)

        self.btn_simulate_release = QPushButton("🚀 Release (F2)")
        self.btn_simulate_release.setToolTip("Kirim event 'release'. Memicu cooldown untuk kemampuan bertipe on_release (Veil).")
        self.btn_simulate_release.setStyleSheet("background-color: #075985; color: #7DD3FC; border: 1px solid #0284C7;")
        self.btn_simulate_release.clicked.connect(lambda: self.simulate_release(source="manual"))
        sim_btn_row.addWidget(self.btn_simulate_release)

        self.btn_reset_cd = QPushButton("🔄 Reset (F3)")
        self.btn_reset_cd.setToolTip("Reset status cooldown kemampuan aktif kembali ke READY.")
        self.btn_reset_cd.setStyleSheet("background-color: #374151; color: #D1D5DB; border: 1px solid #4B5563;")
        self.btn_reset_cd.clicked.connect(self.reset_cooldown)
        sim_btn_row.addWidget(self.btn_reset_cd)
        overlay_layout.addLayout(sim_btn_row)

        hotkey_help = QLabel(
            "<small style='color:#718096;'>Hotkey: <b>F1</b>=Cast | <b>F2</b>=Release | <b>F3</b>=Reset | <b>F4</b>=Overlay</small>"
        )
        hotkey_help.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(hotkey_help)

        right_col.addWidget(overlay_group)

        # Panel 3: Live Auto-Detection Engine (Week 4 Day 19)
        auto_detect_group = QGroupBox("🤖 Live Auto-Detection (Vision)")
        auto_detect_layout = QVBoxLayout(auto_detect_group)
        auto_detect_layout.setSpacing(6)

        detect_top_row = QHBoxLayout()
        self.check_auto_detect = QCheckBox("⚡ Aktifkan Auto-Detection")
        self.check_auto_detect.setChecked(True)
        self.check_auto_detect.toggled.connect(self.on_toggle_auto_detection)
        detect_top_row.addWidget(self.check_auto_detect)
        detect_top_row.addStretch()

        self.detector_badge = QLabel("READY")
        self.detector_badge.setStyleSheet("""
            background-color: #14381C;
            color: #4ADE80;
            border: 1px solid #16A34A;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
        """)
        detect_top_row.addWidget(self.detector_badge)
        auto_detect_layout.addLayout(detect_top_row)

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Ambang Batas (Conf):"))
        self.spin_confidence = QSpinBox()
        self.spin_confidence.setRange(20, 95)
        self.spin_confidence.setSingleStep(5)
        self.spin_confidence.setValue(54)
        self.spin_confidence.setSuffix("%")
        self.spin_confidence.setToolTip("Rekomendasi ambang batas: 40% - 60%. Nilai > 75% berisiko menyaring deteksi karakter.")
        self.spin_confidence.valueChanged.connect(self.on_confidence_changed)
        conf_row.addWidget(self.spin_confidence)
        auto_detect_layout.addLayout(conf_row)

        # Baris Opsi Filter Match State & Audio Gating
        filter_check_row = QVBoxLayout()
        self.check_filter_match = QCheckBox("🛡️ Filter Lobby (Hanya Aktif Saat Match)")
        self.check_filter_match.setChecked(True)
        self.check_filter_match.toggled.connect(self.detection_worker.set_filter_match_state)
        filter_check_row.addWidget(self.check_filter_match)

        self.check_audio_gate = QCheckBox("🔊 Filter Audio Gating (Stereo Mix / Loopback)")
        self.check_audio_gate.setToolTip("Aktifkan jika perangkat Windows Stereo Mix / Loopback game terhubung.")
        self.check_audio_gate.setChecked(False)
        self.audio_monitor.set_enabled(False)
        self.check_audio_gate.toggled.connect(self.on_toggle_audio_gate)
        filter_check_row.addWidget(self.check_audio_gate)
        auto_detect_layout.addLayout(filter_check_row)

        self.detector_telemetry_label = QLabel("Status: <b>IDLE</b> | Lat: <b>0.0 ms</b> | FPS: <b>0.0</b>")
        self.detector_telemetry_label.setStyleSheet("color: #9E9EB0; font-size: 11px;")
        auto_detect_layout.addWidget(self.detector_telemetry_label)

        right_col.addWidget(auto_detect_group)

        # Panel 4: HUD Region of Interest (ROI)
        roi_group = QGroupBox("HUD Region of Interest (ROI)")
        roi_layout = QVBoxLayout(roi_group)
        roi_layout.setSpacing(8)

        # Dedicated Cropped ROI Viewport
        self.roi_preview_label = QLabel("Area ROI")
        self.roi_preview_label.setAlignment(Qt.AlignCenter)
        self.roi_preview_label.setStyleSheet("""
            background-color: #060608;
            border: 2px dashed #4ADE80;
            border-radius: 6px;
            color: #4ADE80;
        """)
        self.roi_preview_label.setFixedHeight(120)
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

        # Dropdown OpenCV Preprocessor Mode
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("Raw BGR (No Filter)", PreprocessorMode.RAW)
        self.combo_filter.addItem("Grayscale (Luminance)", PreprocessorMode.GRAYSCALE)
        self.combo_filter.addItem("CLAHE (Night Boost)", PreprocessorMode.CLAHE)
        self.combo_filter.addItem("Threshold (Binary)", PreprocessorMode.THRESHOLD)
        self.combo_filter.addItem("Canny (Edges)", PreprocessorMode.CANNY)
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

        # Cegah tombol dan checkbox mencuri fokus keyboard dari jendela utama
        for widget in (
            self.btn_start, self.btn_stop, self.btn_snapshot,
            self.btn_simulate_cast, self.btn_simulate_release, self.btn_reset_cd,
            self.btn_save_roi, self.btn_save_roi_sample,
            self.check_overlay_visible, self.check_calibration_mode, self.check_roi_enable,
            self.check_auto_detect, self.spin_confidence, self.check_filter_match, self.check_audio_gate
        ):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setCentralWidget(central_widget)

    def _populate_killer_combobox(self) -> None:
        """Mengisi pilihan dropdown killer dari DatabaseManager."""
        self.combo_killer.blockSignals(True)
        self.combo_killer.clear()
        if not self.database or not self.database.killers:
            self.combo_killer.addItem("Database Kosong", None)
            self.combo_killer.blockSignals(False)
            return

        selected_idx = 0
        for idx, killer in enumerate(self.database.killers):
            self.combo_killer.addItem(killer.name, killer.id)
            if killer.id == self.config.active_killer_id:
                selected_idx = idx

        self.combo_killer.setCurrentIndex(selected_idx)
        self.combo_killer.blockSignals(False)

    def _populate_ability_combobox(self) -> None:
        """Mengisi pilihan dropdown kemampuan sesuai killer yang dipilih."""
        self.combo_ability.blockSignals(True)
        self.combo_ability.clear()

        killer_id = self.combo_killer.currentData()
        if not killer_id or not self.database:
            self.combo_ability.addItem("Tidak Ada Kemampuan", None)
            self.combo_ability.blockSignals(False)
            return

        killer = self.database.get_killer(killer_id)
        if not killer or not killer.abilities:
            self.combo_ability.addItem("Tidak Ada Kemampuan", None)
            self.combo_ability.blockSignals(False)
            return

        for ab in killer.abilities:
            label = f"{ab.name} ({ab.cooldown_seconds:.1f}s - {ab.trigger_type})"
            self.combo_ability.addItem(label, ab.id)

        self.combo_ability.blockSignals(False)
        if self.combo_ability.count() > 0:
            self.combo_ability.setCurrentIndex(0)
            self._sync_active_ability()

    def _sync_active_ability(self) -> None:
        """Sinkronisasi kemampuan aktif ke CooldownManager dan overlay."""
        killer_id = self.combo_killer.currentData()
        ability_id = self.combo_ability.currentData()
        if not killer_id or not ability_id or not self.database:
            return

        killer = self.database.get_killer(killer_id)
        if not killer:
            return

        ability = killer.get_ability(ability_id)
        if not ability:
            return

        self.cooldown_manager.set_ability(killer_id, ability)
        self.overlay_controller.update_widget()
        logger.info(
            "Synchronized active ability '%s' (%s) for killer '%s' to CooldownManager.",
            ability.name,
            ability.id,
            killer_id,
        )

    def _update_killer_display(self) -> None:
        """Memperbarui label rincian kemampuan killer sesuai pilihan aktif."""
        killer_id = self.combo_killer.currentData()
        if not killer_id or not self.database:
            self.killer_desc_label.setText("Tidak ada killer yang dipilih.")
            self.abilities_container.setText("Data kemampuan tidak tersedia.")
            return

        killer = self.database.get_killer(killer_id)
        if killer is None:
            return

        self.killer_desc_label.setText(killer.description)

        ability_lines = []
        for ab in killer.abilities:
            status_symbol = "⚡" if ab.enabled else "⏸️"
            verified_tag = "✓ Verified" if ab.cooldown_verified else "⚠️ Unverified"
            line = (
                f"<b>{status_symbol} {ab.name}</b>: <b>{ab.cooldown_seconds:.1f}s</b> "
                f"<span style='color:#A0AEC0;'>({verified_tag})</span><br>"
                f"&nbsp;&nbsp;↳ Trigger: <code>{ab.trigger_type}</code> | Input: <i>{ab.interact_input}</i>"
            )
            ability_lines.append(line)

        self.abilities_container.setText("<br>".join(ability_lines))

    def on_killer_selection_changed(self, index: int) -> None:
        """Event listener saat pengguna mengganti killer aktif di GUI."""
        killer_id = self.combo_killer.currentData()
        if killer_id and killer_id != self.config.active_killer_id:
            self.config.active_killer_id = killer_id
            self.settings_manager.save(self.config)
            logger.info("Active killer changed to '%s'. Updated app config.", killer_id)

        self._update_killer_display()
        self._populate_ability_combobox()
        self.combo_killer.clearFocus()
        self.setFocus()

    def on_ability_selection_changed(self, index: int) -> None:
        """Event listener saat pengguna mengganti kemampuan aktif di GUI."""
        self._sync_active_ability()
        self.combo_ability.clearFocus()
        self.setFocus()

    def on_toggle_overlay_checked(self, checked: bool) -> None:
        """Mengatur visibilitas overlay sesuai checkbox dan menyimpan preferensi."""
        if checked:
            self.overlay_controller.show_overlay()
        else:
            self.overlay_controller.hide_overlay()
        if self.config.overlay.visible != checked:
            self.config.overlay.visible = checked
            self.settings_manager.save(self.config)
            logger.info("Saved overlay visibility preference: %s", checked)

    def on_toggle_calibration_mode(self, checked: bool) -> None:
        """Mengatur mode kalibrasi posisi overlay."""
        self.overlay_controller.set_calibration_mode(checked)

    def on_overlay_moved(self, x: int, y: int) -> None:
        """Callback saat jendela overlay digeser pengguna pada mode kalibrasi."""
        self.config.overlay.x = x
        self.config.overlay.y = y
        self.config.overlay.position = {"x": x, "y": y}
        self.settings_manager.save(self.config)
        logger.debug("Overlay position changed to: (%d, %d). Saved to config.", x, y)

    def simulate_cast_start(self, source: str = "manual") -> None:
        """Memicu simulasi event cast_start untuk kemampuan aktif."""
        killer_id = self.combo_killer.currentData()
        ability_id = self.combo_ability.currentData()
        if not killer_id or not ability_id:
            logger.warning("Simulate cast_start ignored: No killer or ability selected.")
            return

        event = AbilityEvent(
            killer_id=killer_id,
            ability_id=ability_id,
            event_type="cast_start",
            timestamp=time.monotonic(),
            confidence=1.0,
            source=source,
        )
        logger.info("Simulating '%s' event from source '%s': %s/%s", event.event_type, source, killer_id, ability_id)
        self.cooldown_manager.handle_event(event)

    def simulate_release(self, source: str = "manual") -> None:
        """Memicu simulasi event release untuk kemampuan aktif."""
        killer_id = self.combo_killer.currentData()
        ability_id = self.combo_ability.currentData()
        if not killer_id or not ability_id:
            logger.warning("Simulate release ignored: No killer or ability selected.")
            return

        event = AbilityEvent(
            killer_id=killer_id,
            ability_id=ability_id,
            event_type="release",
            timestamp=time.monotonic(),
            confidence=1.0,
            source=source,
        )
        logger.info("Simulating '%s' event from source '%s': %s/%s", event.event_type, source, killer_id, ability_id)
        self.cooldown_manager.handle_event(event)

    def reset_cooldown(self) -> None:
        """Mereset status cooldown kemampuan aktif kembali ke READY."""
        logger.info("Resetting cooldown timer back to READY.")
        self.cooldown_manager.reset()

    def on_toggle_auto_detection(self, checked: bool) -> None:
        """Mengaktifkan atau menonaktifkan proses inferensi detektor background."""
        self.detection_worker.set_enabled(checked)
        if checked:
            self.detector_badge.setText("ACTIVE")
            self.detector_badge.setStyleSheet(
                "background-color: #14381C; color: #4ADE80; border: 1px solid #16A34A; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
            if self.capture_engine.is_running and not self.detection_worker.isRunning():
                self.detection_worker.start()
        else:
            self.detector_badge.setText("DISABLED")
            self.detector_badge.setStyleSheet(
                "background-color: #3E1E24; color: #FF6B6B; border: 1px solid #DC2626; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )

    def on_confidence_changed(self, value: int) -> None:
        """Mengatur confidence threshold detektor dari spinbox GUI."""
        thresh = value / 100.0
        self.detection_worker.set_confidence_threshold(thresh)

    def on_auto_ability_detected(self, event: AbilityEvent) -> None:
        """Handler saat DetectionWorker memancarkan deteksi kemampuan Killer secara otomatis."""
        logger.info(
            "Auto-Detection triggered: %s/%s [confidence=%.2f, source=%s]",
            event.killer_id,
            event.ability_id,
            event.confidence,
            event.source,
        )

        # Beri indikasi visual kilatan pada badge
        self.detector_badge.setText(f"🔥 {event.ability_id.upper()} DETECTED!")
        self.detector_badge.setStyleSheet(
            "background-color: #78350F; color: #FDE047; border: 1px solid #CA8A04; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )
        QTimer.singleShot(1500, self._reset_detector_badge)

        # Teruskan ke CooldownManager
        self.cooldown_manager.handle_event(event)

    def _reset_detector_badge(self) -> None:
        """Mengembalikan badge status detektor ke status normal setelah kilatan deteksi."""
        if self.detection_worker.is_enabled:
            self.detector_badge.setText("ACTIVE" if self.capture_engine.is_running else "READY")
            self.detector_badge.setStyleSheet(
                "background-color: #14381C; color: #4ADE80; border: 1px solid #16A34A; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
        else:
            self.detector_badge.setText("DISABLED")
            self.detector_badge.setStyleSheet(
                "background-color: #3E1E24; color: #FF6B6B; border: 1px solid #DC2626; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )

    def on_toggle_audio_gate(self, checked: bool) -> None:
        """Mengaktifkan atau menonaktifkan filter konfirmasi audio spectral."""
        if hasattr(self, "audio_monitor"):
            self.audio_monitor.set_enabled(checked)
        if hasattr(self, "detection_worker") and not checked:
            self.detection_worker.set_audio_confirmed(False)

    def on_detector_telemetry_updated(self, data: dict) -> None:
        """Memperbarui label telemetri detektor dari background worker."""
        state = data.get("state", "IDLE")
        lat = data.get("latency_ms", 0.0)
        fps = data.get("worker_fps", 0.0)
        conf = data.get("confidence", 0.0)
        self.detector_telemetry_label.setText(
            f"State: <b>{state}</b> | Lat: <b>{lat:.1f}ms</b> | FPS: <b>{fps:.1f}</b> | Conf: <b>{conf*100:.0f}%</b>"
        )
        if state == "LOBBY_STANDBY":
            self.detector_badge.setText("LOBBY")
            self.detector_badge.setStyleSheet(
                "background-color: #374151; color: #D1D5DB; border: 1px solid #4B5563; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )
        elif state == "COOLDOWN_ACTIVE":
            self.detector_badge.setText("COOLDOWN")
            self.detector_badge.setStyleSheet(
                "background-color: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )

    def on_target_tracked(self, data: dict) -> None:
        """Menyimpan data bounding box target terbaru untuk digambar di viewport preview."""
        bbox = data.get("bbox")
        if bbox and bbox[2] > 0 and bbox[3] > 0:
            self._latest_target_bbox = bbox
            self._latest_bbox_time = time.monotonic()
            self._latest_bbox_is_leap = data.get("is_detected", False)
            tmpl = data.get("template", "the_hidden")
            conf = data.get("confidence", 0.0)
            strategy = data.get("strategy", "").replace("YOLO_", "")
            if self._latest_bbox_is_leap:
                self._latest_bbox_label = f"LEAP CAST ({int(conf * 100)}%)"
            elif strategy:
                self._latest_bbox_label = f"The Hidden [{strategy}] ({int(conf * 100)}%)"
            else:
                self._latest_bbox_label = f"{tmpl} ({int(conf * 100)}%)"

    def on_detector_error(self, err_msg: str) -> None:
        logger.error("Detector worker error: %s", err_msg)

    def _handle_hotkey(self, key: int) -> bool:
        """Menangani aksi hotkey F1-F4 secara terpusat.

        Returns:
            bool: True jika tombol dikenali dan ditangani, False jika tidak.
        """
        if key == Qt.Key.Key_F1 or key == Qt.Key_F1:
            self.simulate_cast_start(source="hotkey")
            return True
        elif key == Qt.Key.Key_F2 or key == Qt.Key_F2:
            self.simulate_release(source="hotkey")
            return True
        elif key == Qt.Key.Key_F3 or key == Qt.Key_F3:
            self.reset_cooldown()
            return True
        elif key == Qt.Key.Key_F4 or key == Qt.Key_F4:
            is_visible = self.overlay_controller.toggle_overlay()
            self.check_overlay_visible.blockSignals(True)
            self.check_overlay_visible.setChecked(is_visible)
            self.check_overlay_visible.blockSignals(False)
            return True
        return False

    def eventFilter(self, obj, event) -> bool:
        """Filter event global aplikasi untuk mencegat tombol F1-F4 sebelum dicuri QComboBox / widget anak."""
        if event.type() == QEvent.Type.KeyPress:
            if self._handle_hotkey(event.key()):
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        """Hotkey listener cadangan jika tidak tertangkap oleh eventFilter."""
        if self._handle_hotkey(event.key()):
            event.accept()
        else:
            super().keyPressEvent(event)

    def on_roi_spin_changed(self) -> None:
        """Memperbarui model ROI saat nilai spinbox digeser pengguna."""
        self.roi_config.x = self.spin_x.value()
        self.roi_config.y = self.spin_y.value()
        self.roi_config.width = self.spin_w.value()
        self.roi_config.height = self.spin_h.value()
        self.roi_processor.update_config(self.roi_config)
        if hasattr(self, "detection_worker"):
            self.detection_worker.set_roi_processor(self.roi_processor)

    def on_roi_toggle_changed(self, checked: bool) -> None:
        self.roi_config.enabled = checked
        self.roi_processor.update_config(self.roi_config)
        if hasattr(self, "detection_worker"):
            self.detection_worker.set_roi_processor(self.roi_processor)

    def on_filter_mode_changed(self, index: int) -> None:
        mode = self.combo_filter.currentData()
        self.preprocessor.config.mode = mode
        logger.debug("OpenCV preprocessor mode changed to: %s", mode.value)

    def on_save_roi_config(self) -> None:
        """Menyimpan konfigurasi ROI terkini melalui SettingsManager."""
        try:
            self.config.capture.roi = self.roi_config
            self.settings_manager.save(self.config)
            logger.info("ROI configuration saved to %s", self.settings_manager.path)
            QMessageBox.information(
                self,
                "Konfigurasi Tersimpan",
                f"Koordinat ROI berhasil disimpan ke {self.settings_manager.path}:\n"
                f"X: {self.roi_config.x}, Y: {self.roi_config.y}\n"
                f"Ukuran: {self.roi_config.width} x {self.roi_config.height}"
            )
        except Exception as exc:
            logger.error("Failed to save ROI configuration: %s", exc)
            QMessageBox.critical(self, "Gagal Menyimpan", f"Error menyimpan file: {exc}")

    def on_save_roi_sample(self) -> None:
        """Menyimpan potongan frame ROI terkini ke dataset/roi_samples/."""
        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is not None:
            cropped = self.roi_processor.crop(frame_data.image)
            if cropped is not None:
                processed, _ = self.preprocessor.process(cropped)
                mode_name = self.preprocessor.config.mode.value

                output_dir = Path("dataset/roi_samples")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                file_path = output_dir / f"roi_crop_{timestamp_str}_{mode_name}.png"
                cv2.imwrite(str(file_path), processed)
                logger.info("ROI crop sample saved to: %s", file_path)
                QMessageBox.information(
                    self,
                    "Crop Tersimpan",
                    f"Sampel ROI ({mode_name.upper()}) berhasil disimpan ke:\n{file_path}"
                )

    def on_fps_changed(self, text: str) -> None:
        """Mengatur target FPS capture (30 atau 60 FPS)."""
        fps = 60 if "60" in text else 30
        self.config.capture.target_fps = fps
        self.settings_manager.save(self.config)
        interval = 16 if fps == 60 else 33
        self.render_timer.setInterval(interval)
        if hasattr(self, "capture_engine") and self.capture_engine.is_running:
            target = self.target_input.text().strip() or "Roblox"
            self.capture_engine.start(target_title=target, target_fps=fps)
        logger.info("Capture & Render FPS set to: %d FPS", fps)

    def on_start_capture(self) -> None:
        target = self.target_input.text().strip() or "Roblox"
        fps_target = self.config.capture.target_fps
        logger.info("User initiated capture start on target '%s' (%d FPS)", target, fps_target)
        self.capture_engine.start(target_title=target, target_fps=fps_target)

        # Start audio monitor jika diaktifkan
        if hasattr(self, "check_audio_gate") and self.check_audio_gate.isChecked():
            self.audio_monitor.start()

        # Start detection worker jika auto-detection diaktifkan
        if hasattr(self, "check_auto_detect") and self.check_auto_detect.isChecked():
            if not self.detection_worker.isRunning():
                self.detection_worker.start()
                self.detector_badge.setText("ACTIVE")
                self.detector_badge.setStyleSheet(
                    "background-color: #14381C; color: #4ADE80; border: 1px solid #16A34A; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
                )

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_snapshot.setEnabled(True)
        self.btn_save_roi_sample.setEnabled(True)
        self.target_input.setEnabled(False)

    def on_stop_capture(self) -> None:
        logger.info("User initiated capture stop.")
        if hasattr(self, "audio_monitor"):
            self.audio_monitor.stop()
        if hasattr(self, "detection_worker") and self.detection_worker.isRunning():
            self.detection_worker.stop()
        self.capture_engine.stop()

        if hasattr(self, "detector_badge"):
            self.detector_badge.setText("READY")
            self.detector_badge.setStyleSheet(
                "background-color: #1F2937; color: #9CA3AF; border: 1px solid #374151; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
            )

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_snapshot.setEnabled(False)
        self.btn_save_roi_sample.setEnabled(False)
        self.target_input.setEnabled(True)

        self.status_badge.setText("STOPPED")
        self.status_badge.setStyleSheet(
            "background-color: #3E1E24; color: #FF6B6B; border-radius: 4px; padding: 3px 8px; font-weight: bold;"
        )
        self.preview_label.setText("Capture dihentikan.")
        self.roi_preview_label.setText("Area ROI")

    def on_save_snapshot(self) -> None:
        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is not None:
            output_dir = Path("dataset")
            output_dir.mkdir(exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            file_path = output_dir / f"snapshot_{timestamp_str}.png"
            cv2.imwrite(str(file_path), frame_data.image)
            logger.info("Full viewport snapshot saved to: %s", file_path)
            QMessageBox.information(self, "Snapshot Tersimpan", f"Frame berhasil disimpan ke:\n{file_path}")

    def update_frame_preview(self) -> None:
        """Polling frame dari buffer capture engine dan render ke viewport & panel ROI."""
        status = self.capture_engine.status

        # Update Status Badge
        if status == CaptureStatus.RUNNING:
            self.status_badge.setText("RUNNING")
            self.status_badge.setStyleSheet(
                "background-color: #14381C; color: #4ADE80; border-radius: 4px; padding: 3px 8px; font-weight: bold;"
            )
        elif status == CaptureStatus.TARGET_LOST:
            self.status_badge.setText("TARGET LOST")
            self.status_badge.setStyleSheet(
                "background-color: #4A3A10; color: #FBBF24; border-radius: 4px; padding: 3px 8px; font-weight: bold;"
            )
        elif status == CaptureStatus.ERROR:
            self.status_badge.setText("ERROR")
            self.status_badge.setStyleSheet(
                "background-color: #4A1E24; color: #F87171; border-radius: 4px; padding: 3px 8px; font-weight: bold;"
            )

        # Update Metrik Frame
        self.fps_metric.setText(f"FPS: <b>{self.capture_engine.current_fps:.1f}</b>")
        self.latency_metric.setText(f"Capture Lat: <b>{self.capture_engine.current_latency_ms:.1f} ms</b>")

        # Update Metrik Hardware Telemetry (psutil) setiap ~500ms (15 ticks)
        self._telemetry_tick_counter += 1
        if self._telemetry_tick_counter >= 15:
            self._telemetry_tick_counter = 0
            snapshot = self.monitor.sample_metrics()
            self.app_cpu_metric.setText(f"App CPU: <b>{snapshot.app_cpu_percent:.1f}%</b>")
            self.app_ram_metric.setText(f"App RAM: <b>{snapshot.app_ram_rss_mb:.1f} MB</b>")
            if snapshot.target_cpu_percent is not None:
                self.roblox_cpu_metric.setText(f"Roblox CPU: <b>{snapshot.target_cpu_percent:.1f}%</b>")
                self.roblox_ram_metric.setText(f"Roblox RAM: <b>{snapshot.target_ram_rss_mb:.1f} MB</b>")
            else:
                self.roblox_cpu_metric.setText("Roblox CPU: <b>--</b>")
                self.roblox_ram_metric.setText("Roblox RAM: <b>--</b>")

        if not self.capture_engine.is_running:
            return

        frame_data = self.capture_engine.get_latest_frame()
        if frame_data is None or status == CaptureStatus.TARGET_LOST:
            self.preview_label.clear()
            self.preview_label.setText(
                f"Target '{self.target_input.text()}' tidak terdeteksi atau sedang diminimalkan.\n"
                "Silakan buka / aktifkan jendela Roblox."
            )
            self.roi_preview_label.clear()
            self.roi_preview_label.setText("Target Lost")
            self.fps_metric.setText("FPS: <b>0.0</b>")
            self.latency_metric.setText("Capture Lat: <b>0.0 ms</b>")
            self.res_metric.setText("Resolution: <b>0x0</b>")
            return

        self.monitor.record_capture_frame(frame_data.latency_ms)
        self.res_metric.setText(f"Resolution: <b>{frame_data.width}x{frame_data.height}</b>")
        self.frame_num_metric.setText(f"Frames: <b>{frame_data.frame_index}</b>")

        # 1. Pemotongan ROI & Preprocessing
        cropped_roi = self.roi_processor.crop(frame_data.image)
        if cropped_roi is not None and cropped_roi.size > 0:
            roi_h, roi_w = cropped_roi.shape[:2]
            self.roi_size_label.setText(f"Ukuran: {roi_w} x {roi_h} px")

            processed_roi, proc_time_ms = self.preprocessor.process(cropped_roi)
            self.monitor.record_processing_frame(proc_time_ms)
            self.cv_proc_metric.setText(f"CV Proc: <b>{proc_time_ms:.1f} ms</b>")

            if len(processed_roi.shape) == 2:
                roi_rgb = cv2.cvtColor(processed_roi, cv2.COLOR_GRAY2RGB)
            else:
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

        # Gambar Bounding Box Target Killer jika sedang terdeteksi di dalam ROI (Entity Tracking Preview)
        now_mono = time.monotonic()
        if self._latest_target_bbox and (now_mono - self._latest_bbox_time) < 0.8:
            bx, by, bw, bh = self._latest_target_bbox
            if bw > 10 and bh > 10:
                box_color = (0, 69, 255) if self._latest_bbox_is_leap else (0, 240, 255)  # BGR (Red jika Leap, Neon Yellow jika Tracking)
                cv2.rectangle(annotated_frame, (bx, by), (bx + bw, by + bh), box_color, 2)
                # Label banner di atas kotak
                label = self._latest_bbox_label
                font_scale = 0.45
                thickness = 1
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                ty = max(by - 6, th + 6)
                cv2.rectangle(annotated_frame, (bx, ty - th - 4), (bx + tw + 6, ty + 2), (20, 20, 20), -1)
                cv2.putText(annotated_frame, label, (bx + 3, ty - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, box_color, thickness, cv2.LINE_AA)

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

    def closeEvent(self, event) -> None:
        """Memastikan clean shutdown worker thread & overlay saat window ditutup."""
        logger.info("Closing application window. Cleaning up timers and capture engine...")
        app_inst = QApplication.instance()
        if app_inst is not None:
            app_inst.removeEventFilter(self)

        # Simpan preferensi posisi overlay terkini ke config
        try:
            if hasattr(self, "overlay_window") and self.overlay_window is not None:
                self.config.overlay.x = self.overlay_window.x()
                self.config.overlay.y = self.overlay_window.y()
                self.config.overlay.width = self.overlay_window.width()
                self.config.overlay.height = self.overlay_window.height()
                self.config.overlay.visible = self.check_overlay_visible.isChecked()
                self.config.overlay.position = {"x": self.overlay_window.x(), "y": self.overlay_window.y()}
                self.settings_manager.save(self.config)
                logger.info("Overlay settings successfully persisted on exit.")
        except Exception as exc:
            logger.warning("Could not persist overlay settings on exit: %s", exc)

        self.render_timer.stop()
        if hasattr(self, "audio_monitor"):
            self.audio_monitor.stop()
        if hasattr(self, "detection_worker") and self.detection_worker.isRunning():
            self.detection_worker.stop()
        if hasattr(self, "overlay_controller") and self.overlay_controller is not None:
            self.overlay_controller.close()
        if self.capture_engine.is_running:
            self.capture_engine.stop()
        logger.info("Application cleanly closed.")
        event.accept()


def main() -> None:
    settings_mgr = SettingsManager()
    db_mgr = DatabaseManager()

    # Inisialisasi logging terpusat sesuai preferensi debug_mode di config
    setup_logging(debug_mode=settings_mgr.config.app.debug_mode)
    logger.info("==================================================")
    logger.info(" Starting %s v%s", settings_mgr.config.app.name, settings_mgr.config.app.version)
    logger.info(" Target Game: %s | Active Killer: %s", settings_mgr.config.capture.target_title, settings_mgr.config.active_killer_id)
    logger.info("==================================================")

    app = QApplication(sys.argv)
    window = CapturePreviewWindow(settings_manager=settings_mgr, db_manager=db_mgr)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
