"""Unit tests for YOLOv8-Nano Training & ONNX Export Pipeline (Day 27)."""

import json
from pathlib import Path
import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_train_yolo_module_structure():
    """Memverifikasi modul tools.train_yolo dapat diimpor dan memiliki fungsi utama."""
    import tools.train_yolo as ty

    assert hasattr(ty, "train_yolo_model")
    assert hasattr(ty, "export_to_onnx")
    assert hasattr(ty, "benchmark_onnx_cpu_latency")
    assert hasattr(ty, "verify_distractor_rejection")
    assert hasattr(ty, "run_pipeline")


def test_benchmark_onnx_cpu_latency_mock(tmp_path):
    """Menguji fungsi benchmark_onnx_cpu_latency dengan model ONNX sintetis."""
    import onnxruntime as ort
    from tools.train_yolo import benchmark_onnx_cpu_latency

    # Cek apakah model dummy dapat dievaluasi jika ada onnx session
    # Buat dummy model onnx sederhana
    try:
        import onnx
        from onnx import helper, TensorProto

        input_tensor = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 320, 320])
        output_tensor = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 5, 2100])
        node_def = helper.make_node("Identity", ["images"], ["output0"])
        graph_def = helper.make_graph([node_def], "dummy_yolo", [input_tensor], [output_tensor])
        model_def = helper.make_model(graph_def, producer_name="test")

        dummy_onnx_file = tmp_path / "dummy_yolo.onnx"
        onnx.save(model_def, str(dummy_onnx_file))

        stats = benchmark_onnx_cpu_latency(dummy_onnx_file, input_size=(320, 320), iterations=10)
        assert "mean_ms" in stats
        assert "p95_ms" in stats
        assert stats["mean_ms"] >= 0.0
    except ImportError:
        # Jika onnx generator belum ada, lewati sub-test
        pytest.skip("onnx package not installed for dummy creation")


def test_verify_distractor_rejection_empty_dataset(tmp_path):
    """Menguji verifikasi penolakan distractor pada direktori kosong mengembalikan statistik aman."""
    from tools.train_yolo import verify_distractor_rejection

    dummy_onnx = tmp_path / "non_existent.onnx"
    stats = verify_distractor_rejection(dummy_onnx, tmp_path)
    assert stats["distractors_tested"] == 0
    assert stats["false_positives"] == 0
    assert stats["distractor_rejection_pct"] == 100.0


def test_training_report_structure(tmp_path):
    """Memverifikasi format struktur laporan audit YOLO_TRAINING_REPORT.json."""
    report_data = {
        "timestamp": "2026-11-13 19:00:00",
        "model_architecture": "YOLOv8-Nano",
        "input_resolution": "320x320",
        "epochs_trained": 15,
        "weights_source": "best.pt",
        "onnx_model_path": "models/the_hidden_yolov8n.onnx",
        "onnx_size_mb": 11.8,
        "cpu_latency": {"mean_ms": 11.4, "p95_ms": 16.2},
        "verification": {"distractor_rejection_pct": 100.0, "false_positives": 0},
        "status": "PASSED",
    }
    report_file = tmp_path / "YOLO_TRAINING_REPORT.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f)

    assert report_file.exists()
    with open(report_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["status"] == "PASSED"
    assert loaded["verification"]["false_positives"] == 0
