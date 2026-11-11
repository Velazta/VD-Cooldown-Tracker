"""
Unit Tests for Capture Module
Violence District Cooldown Tracker
"""
import unittest
import time
import numpy as np

from capture.capture_interface import CapturedFrame, CaptureStatus
from capture.frame_buffer import LatestFrameBuffer


class TestFrameBuffer(unittest.TestCase):
    """Pengujian Unit untuk Ring Buffer Bounded."""

    def setUp(self):
        self.buffer = LatestFrameBuffer(maxsize=1)
        self.dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

    def test_single_frame_push_and_peek(self):
        frame = CapturedFrame(
            image=self.dummy_img,
            timestamp=time.monotonic(),
            frame_index=1,
            width=100,
            height=100,
            latency_ms=15.0
        )
        self.buffer.push(frame)
        latest = self.buffer.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.frame_index, 1)
        self.assertEqual(latest.width, 100)

    def test_drop_oldest_strategy(self):
        """Memastikan frame terlama dibuang saat frame baru masuk (zero queue lag)."""
        frame1 = CapturedFrame(
            image=self.dummy_img,
            timestamp=time.monotonic(),
            frame_index=1,
            width=100,
            height=100,
            latency_ms=10.0
        )
        frame2 = CapturedFrame(
            image=self.dummy_img,
            timestamp=time.monotonic(),
            frame_index=2,
            width=100,
            height=100,
            latency_ms=12.0
        )

        self.buffer.push(frame1)
        self.buffer.push(frame2)

        stats = self.buffer.stats
        self.assertEqual(stats["total_pushed"], 2)
        self.assertEqual(stats["total_dropped"], 1)

        latest = self.buffer.get_latest()
        self.assertEqual(latest.frame_index, 2)

    def test_clear_buffer(self):
        frame = CapturedFrame(
            image=self.dummy_img,
            timestamp=time.monotonic(),
            frame_index=1,
            width=100,
            height=100,
            latency_ms=5.0
        )
        self.buffer.push(frame)
        self.buffer.clear()
        self.assertIsNone(self.buffer.get_latest())


if __name__ == "__main__":
    unittest.main()
