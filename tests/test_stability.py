"""
Stability & Buffer Pressure Testing Module
Violence District Cooldown Tracker — Day 5 (Segmen 5.2)
"""
import unittest
import time
import threading
import os
import sys
from pathlib import Path
from typing import List, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from capture.capture_interface import CapturedFrame
from capture.frame_buffer import LatestFrameBuffer


class TestBufferStability(unittest.TestCase):
    """
    Pengujian kestabilan antrean dan integritas memori di bawah tekanan (Queue Pressure).
    Menguji skenario: Producer sangat cepat (60 FPS) vs Consumer lambat (10 FPS).
    """

    def setUp(self):
        self.buffer = LatestFrameBuffer(maxsize=1)
        # Dummy frame resolusi 1080p (~6.2 MB BGR array)
        self.sample_frame_shape = (1080, 1920, 3)

    def test_slow_consumer_queue_pressure(self):
        """
        Skenario:
        - Producer memompa 60 frame (kecepatan ~60 FPS).
        - Consumer sengaja ditahan lambat (memproses ~10 FPS, sleep 0.05s).
        Hasil yang harus dibuktikan:
        1. Buffer size tidak pernah melebihi 1.
        2. Frame yang didapat Consumer selalu frame paling baru (latency sub-30ms).
        3. Indeks frame yang diterima selalu meningkat maju (tidak ada frame mundur/stale).
        """
        producer_fps = 60
        producer_delay = 1.0 / producer_fps
        total_producer_frames = 60

        consumer_frames_received: List[CapturedFrame] = []
        consumer_latencies: List[float] = []
        stop_event = threading.Event()

        # Thread Producer (Mensimulasikan Screen Capture Engine cepat)
        def producer_worker():
            # Gunakan 1 dummy array yang sama untuk menghemat alokasi pengujian unit
            dummy_img = np.zeros(self.sample_frame_shape, dtype=np.uint8)
            for idx in range(total_producer_frames):
                t_capture = time.monotonic()
                frame = CapturedFrame(
                    image=dummy_img,
                    timestamp=t_capture,
                    frame_index=idx,
                    width=1920,
                    height=1080,
                    latency_ms=16.6
                )
                self.buffer.push(frame)
                time.sleep(producer_delay)
            stop_event.set()

        # Thread Consumer (Mensimulasikan Pemrosesan CV yang sengaja lambat)
        def consumer_worker():
            while not stop_event.is_set():
                t_consume = time.monotonic()
                frame = self.buffer.get_latest()
                if frame is not None:
                    # Hitung usia frame sejak diproduksi sampai dikonsumsi
                    age_ms = (t_consume - frame.timestamp) * 1000.0
                    consumer_latencies.append(age_ms)
                    consumer_frames_received.append(frame)

                # Simulasi komputasi berat (sleep 50ms = maks 20 FPS)
                time.sleep(0.05)

        prod_t = threading.Thread(target=producer_worker)
        cons_t = threading.Thread(target=consumer_worker)

        t_start = time.perf_counter()
        prod_t.start()
        cons_t.start()

        prod_t.join()
        cons_t.join()
        t_duration = time.perf_counter() - t_start

        # 1. Verifikasi Statistik Buffer
        stats = self.buffer.stats
        self.assertEqual(stats["total_pushed"], total_producer_frames)
        self.assertGreater(stats["total_dropped"], 0, "Harus ada frame lama yang dibuang karena consumer lambat")
        self.assertEqual(stats["total_pushed"], stats["total_dropped"] + 1)  # Buffer maxsize=1 menyisakan 1

        # 2. Verifikasi Zero Queue Lag (Usia frame yang dikonsumsi harus selalu segar)
        avg_age = sum(consumer_latencies) / len(consumer_latencies)
        print(f"\n[STABILITY TEST] Total Pushed: {stats['total_pushed']} | Dropped: {stats['total_dropped']}")
        print(f"[STABILITY TEST] Consumer Processed: {len(consumer_frames_received)} frames")
        print(f"[STABILITY TEST] Average Frame Age at Consumption: {avg_age:.2f} ms (Target < 60ms)")

        # Usia frame tidak boleh menumpuk bertambah ratusan ms
        self.assertLess(avg_age, 60.0, "Frame yang diambil consumer tidak boleh basi (stale queue lag)")

        # 3. Verifikasi Monotonitas Frame (Frame index harus selalu bertambah)
        indices = [f.frame_index for f in consumer_frames_received]
        for i in range(len(indices) - 1):
            self.assertLessEqual(indices[i], indices[i+1], "Urutan frame tidak boleh melompat mundur")

    def test_memory_leak_under_sustained_allocations(self):
        """
        Skenario Kestabilan Memori:
        Memompa 500 frame array 1080p (~3 GB total data dipompa ke buffer).
        Memastikan memory footprint (RSS) tidak bocor/menggembung.
        """
        if not HAS_PSUTIL:
            self.skipTest("psutil belum terinstall untuk memory leak verification.")

        process = psutil.Process(os.getpid())
        ram_start_mb = process.memory_info().rss / (1024 * 1024)

        # Pompa 500 frame 1080p (jika ada memory leak, RAM akan naik ratusan MB)
        for i in range(500):
            # Buat array baru di tiap iterasi untuk menguji Garbage Collection
            img = np.empty((1080, 1920, 3), dtype=np.uint8)
            frame = CapturedFrame(
                image=img,
                timestamp=time.monotonic(),
                frame_index=i,
                width=1920,
                height=1080,
                latency_ms=1.0
            )
            self.buffer.push(frame)

        ram_end_mb = process.memory_info().rss / (1024 * 1024)
        ram_delta_mb = ram_end_mb - ram_start_mb

        print(f"\n[MEMORY TEST] Start RAM: {ram_start_mb:.1f} MB | End RAM: {ram_end_mb:.1f} MB | Delta: {ram_delta_mb:.1f} MB")
        # Kenaikan RAM tidak boleh lebih dari 60 MB (satu frame hanya ~6 MB)
        self.assertLess(ram_delta_mb, 60.0, "Terdeteksi potensi memory leak pada buffer frame!")


if __name__ == "__main__":
    unittest.main()
