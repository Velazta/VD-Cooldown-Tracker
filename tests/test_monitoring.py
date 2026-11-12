"""
Unit Tests for Performance Monitor
Violence District Cooldown Tracker
"""
import unittest
import time
import threading
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from monitoring.performance_monitor import PerformanceMonitor, PerformanceSnapshot


class TestPerformanceMonitor(unittest.TestCase):
    """Pengujian Unit untuk Performance Monitor & Telemetry."""

    def setUp(self):
        self.monitor = PerformanceMonitor(history_size=20)

    def test_record_and_calculate_fps(self):
        # Simulasi 5 frame capture berturut-turut
        for i in range(5):
            self.monitor.record_capture_frame(latency_ms=10.0 + i)
            time.sleep(0.01)

        snapshot = self.monitor.sample_metrics()
        self.assertIsInstance(snapshot, PerformanceSnapshot)
        self.assertGreater(snapshot.capture_fps, 0.0)
        self.assertGreaterEqual(snapshot.capture_latency_ms, 10.0)

    def test_summary_calculation(self):
        # Rekam beberapa frame processing
        for _ in range(5):
            self.monitor.record_processing_frame(latency_ms=5.0)
            self.monitor.sample_metrics()

        summary = self.monitor.get_summary()
        self.assertIn("sample_count", summary)
        self.assertGreaterEqual(summary["sample_count"], 1)
        self.assertIn("cpu_avg", summary)
        self.assertIn("ram_avg_mb", summary)

    def test_thread_safety(self):
        """Memastikan pencatatan aman dipanggil secara paralel oleh beberapa thread."""
        def worker():
            for _ in range(20):
                self.monitor.record_capture_frame(latency_ms=15.0)
                self.monitor.record_processing_frame(latency_ms=3.0)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snapshot = self.monitor.sample_metrics()
        self.assertIsNotNone(snapshot)


if __name__ == "__main__":
    unittest.main()
