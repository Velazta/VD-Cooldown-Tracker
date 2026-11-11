"""
Main Entry Point & Day 1 Verification Prototype
Violence District Cooldown Tracker
"""
import sys
import json
from pathlib import Path
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt

class Day1VerificationWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle(self.config.get("app", {}).get("name", "VD Tracker"))
        self.resize(480, 260)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        # Status Label
        cv_version = cv2.__version__
        self.status_label = QLabel(
            f"<h3>Day 1 Foundation Check</h3>"
            f"<p><b>OpenCV:</b> v{cv_version}</p>"
            f"<p><b>PySide6:</b> Ready</p>"
            f"<p><b>Config Target:</b> {self.config.get('capture', {}).get('target_title')}</p>"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Test OpenCV Button
        self.test_btn = QPushButton("Test OpenCV Processing")
        self.test_btn.clicked.connect(self.run_cv_smoke_test)
        layout.addWidget(self.test_btn)

        self.setCentralWidget(central_widget)

    def run_cv_smoke_test(self):
        # Buat dummy frame 100x100 dengan NumPy & OpenCV
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        dummy_frame[:] = (0, 255, 0) # Green frame
        gray = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2GRAY)
        mean_val = np.mean(gray)

        self.status_label.setText(
            self.status_label.text() + f"<br><span style='color:green;'>OpenCV Processed OK (Mean: {mean_val:.1f})</span>"
        )
        self.test_btn.setEnabled(False)

def main():
    config_path = Path("config/app_config.json")
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    app = QApplication(sys.argv)
    window = Day1VerificationWindow(config)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()