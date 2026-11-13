# Architecture — Violence District Cooldown Tracker

## 1. Purpose
This document describes the proposed architecture for the external Computer Vision Cooldown Overlay. It prioritizes a replaceable capture backend, low-latency visual processing, clear module boundaries, and an extensible killer/ability database.

## 2. Architecture Principles
1. **External observation:** use rendered screen output only.
2. **Local-first:** capture and inference run locally.
3. **Low latency:** process recent frames and avoid stale queues.
4. **Separation of concerns:** UI, capture, CV, detection, cooldown logic, and persistence remain independent.
5. **Replaceable components:** capture backend and detection strategy can change behind interfaces.
6. **Incremental intelligence:** begin with deterministic OpenCV methods; add ML only when evidence justifies it.
7. **Graceful degradation:** manual selection and timer controls remain possible if automatic detection is uncertain.

## 3. High-Level Component Diagram

```mermaid
flowchart TD
    GAME[Roblox / Violence District Window]
    CAP[Capture Backend]
    BUF[Latest-Frame Buffer]
    ROI[ROI Processor]
    PRE[Image Preprocessing]
    DET[Visual Detection]
    EVT[Event Validator / State Machine]
    DB[(Local JSON Database)]
    CD[Cooldown Manager]
    OVL[Transparent Overlay]
    UI[PySide6 Application Panel]
    MON[Performance Monitor / Logger]

    GAME --> CAP
    CAP --> BUF
    BUF --> ROI
    ROI --> PRE
    PRE --> DET
    DET --> EVT
    DB --> DET
    DB --> CD
    EVT --> CD
    CD --> OVL
    UI --> CAP
    UI --> ROI
    UI --> DB
    UI --> OVL
    CAP --> MON
    PRE --> MON
    DET --> MON
```

Week 1 validates the path through capture, buffering, ROI, preprocessing, preview, and monitoring. Detection, event validation, cooldown management, and full overlay behavior are later milestones.

## 4. Runtime Data Flow

### 4.1 Capture
1. User selects an available source.
2. Capture backend starts a session.
3. Frames arrive with dimensions and timestamps.
4. The newest frame is published to a bounded buffer.
5. Capture status and metrics are updated.

### 4.2 Processing
1. Processing worker obtains the newest available frame.
2. Older unprocessed frames may be discarded.
3. ROI coordinates are validated against frame dimensions.
4. ROI is cropped.
5. Optional preprocessing is applied.
6. Preview and performance metrics are updated.
7. Later milestones pass the processed ROI to a detector.

### 4.3 Detection and Cooldown (future path)
1. Detector returns a candidate visual state and confidence.
2. Event validator checks temporal consistency and debounce rules.
3. Confirmed event identifies killer/ability configuration.
4. Cooldown manager starts one timer for the event.
5. Overlay renders remaining time and READY state.

A candidate detection must not directly create repeated cooldown timers without event validation.

## 5. Module Responsibilities and Boundaries

| Module | Core Responsibility | Concrete Implementation (Week 1 & 2 Verified) | Boundary Constraints (Must Not Do) |
|---|---|---|---|
| `capture` | Frame acquisition, target HWND tracking, timestamps, drop-oldest ring buffer | `BaseCaptureEngine`, `MSSWindowsCapture`, `LatestFrameBuffer`, `window_helper.py` | Must not perform CV inference, killer selection, or UI rendering |
| `processing` | ROI cropping, image preprocessing pipelines, normalized template matching | `ROIProcessor`, `ImagePreprocessor`, `TemplateMatcher` | Must not retain frame queues, mutate capture settings, or own timers |
| `database` | Strongly-typed killer/ability persistence, schema validation, cooldown values | `DatabaseManager`, `KillerDatabase`, `KillerConfig`, `AbilityConfig` | Must not import UI libraries, CV modules, or hard-code detection logic |
| `monitoring` | Non-blocking process telemetry, CPU/RAM sampling, rolling FPS & latency | `PerformanceMonitor`, `PerformanceSnapshot` | Must not block capture/UI loops or modify system state |
| `app` | Application composition, runtime configuration loading, PySide6 main window | `SettingsManager`, `AppConfig`, `OverlaySettings`, `CapturePreviewWindow` (`main.py`) | Must not perform monolithic CV calculations in Qt UI thread |
| `cooldown` *(Week 2)* | Timer lifecycle, ability state machine (READY, WAITING_FOR_RELEASE, COOLDOWN), monotonic deadline, duplicate event suppression | `AbilityEvent`, `CooldownState`, `CooldownSnapshot`, `CooldownManager` | Must not import PySide6/Qt or OpenCV; pure Python only |
| `overlay` *(Week 2)* | Transparent, frameless, click-through HUD overlay, radial circular progress widget, repaint cadence controller | `OverlayWindow`, `CooldownWidget`, `OverlayController` | Must not run heavy image processing or block game input |

## 6. Project Structure (Week 2 Verified)

```text
ViolenceDistrictTracker/
├── main.py                     # Integrated PySide6 GUI with capture, ROI, telemetry, and overlay controls
├── requirements.txt
├── README.md
├── PRD.md
├── PRD_WEEK_2.md
├── REFERENCES_WEEK_2.md
├── AGENTS.md
├── ARCHITECTURE.md
├── TODO.md
├── WORKFLOW.md
├── RISK.md
├── app/
│   ├── __init__.py
│   ├── logger.py               # Hierarchical dual console + rotating file logging
│   └── settings.py             # AppConfig, CaptureSettings, OverlaySettings persistence
├── capture/
│   ├── __init__.py
│   ├── capture_interface.py    # BaseCaptureEngine and CaptureFrame models
│   ├── windows_capture.py      # MSS Windows BitBlt background producer thread
│   ├── window_helper.py       # DWM bounds resolution & SetWindowDisplayAffinity
│   └── frame_buffer.py         # Thread-safe drop-oldest ring buffer (maxlen=1)
├── processing/
│   ├── __init__.py
│   ├── roi_processor.py        # Clamped ROI coordinate cropping & annotation
│   ├── preprocessing.py        # OpenCV RAW, Gray, CLAHE, Threshold, Canny filters
│   └── template_matcher.py     # Normalized TM_CCOEFF_NORMED matcher
├── cooldown/                   # Pure Python Cooldown Engine (Week 2)
│   ├── __init__.py
│   ├── ability_event.py        # Normalized AbilityEvent dataclass
│   ├── cooldown_state.py       # CooldownState enum & immutable CooldownSnapshot
│   └── cooldown_manager.py     # Deterministic zero-drift monotonic state machine
├── overlay/                    # PySide6 HUD Display Engine (Week 2)
│   ├── __init__.py
│   ├── overlay_window.py       # Frameless, transparent, Win32 click-through window
│   ├── cooldown_widget.py      # Radial circular progress ring via QPainter
│   └── overlay_controller.py   # State snapshot bridge & 30 FPS repaint cadence
├── detection/                  # Multi-Modal Action Detector Engine (Week 3)
│   ├── __init__.py
│   ├── detection_result.py     # Normalized DetectionResult contract & AbilityEvent adapter
│   ├── template_detector.py    # Multi-scale TM_CCOEFF_NORMED matcher with pre-cached scaling
│   ├── motion_detector.py      # MOG2 background subtractor & parabolic trajectory tracker
│   └── hybrid_detector.py      # Vision-Motion-Audio multi-modal fusion engine
├── database/
│   ├── __init__.py
│   ├── database_manager.py     # Schema validator and strongly-typed data models
│   └── killerDatabase.json     # The Hidden & Veil killer configurations
├── config/
│   └── app_config.json         # Runtime capture, ROI, and overlay configuration
├── monitoring/
│   ├── __init__.py
│   └── performance_monitor.py  # psutil non-blocking hardware & FPS telemetry
├── dataset/
│   ├── catalog.json            # Multi-modal dataset provenance catalog
│   ├── baseline_benchmark_results.json # Day 17 test split benchmark data
│   ├── DAY17_BASELINE_REPORT.md# Comprehensive empirical baseline benchmark report
│   ├── DAY18_ERROR_ANALYSIS.md # Forensic failure & action-level evaluation report
│   ├── WEEK1_FINAL_REPORT.md   # Week 1 acceptance and benchmark report
│   ├── WEEK2_FINAL_REPORT.md   # Week 2 acceptance and benchmark report
│   └── WEEK3_FINAL_REPORT.md   # Week 3 acceptance and benchmark report
├── tools/                      # Dataset indexing, extraction, and evaluation tools
│   ├── dataset_indexer.py
│   ├── extract_dataset.py
│   ├── audio_inspector.py
│   ├── keyframe_profiler.py
│   ├── spatial_annotator.py
│   ├── trajectory_analyzer.py
│   ├── template_builder.py
│   ├── evaluate_baseline.py
│   └── error_analyzer.py
└── tests/                      # 27 test modules (127 automated tests passing)
```

Create modules incrementally. Empty placeholder files are not a substitute for working functionality.

## 7. Capture Backend Abstraction

Define a small capture interface. Conceptual example:

```python
class CaptureBackend:
    def start(self, source_id: str) -> None:
        ...

    def get_frame(self):
        # Return newest frame plus capture timestamp, or None.
        ...

    def stop(self) -> None:
        ...
```

The actual interface should include typed frame metadata and explicit error/status handling.

### Backend candidates
- **Windows.Graphics.Capture (WGC):** technical spike for application-window/display capture.
- **DXGI Desktop Duplication:** alternative to test for frame acquisition and performance.

Choose based on measured compatibility with target Roblox display mode, frame delivery, stability, and Python integration effort. Do not assume either API works in every fullscreen or anti-cheat configuration.

## 8. Threading and Frame Buffer

Recommended separation:
- UI thread: PySide6 event loop and widget updates.
- Capture worker: obtains frames and timestamps.
- Processing worker: consumes latest frame, applies ROI and preprocessing.
- Future inference worker: only if model inference is expensive enough to require isolation.

Use a bounded latest-frame buffer. A capacity of one or two frames is a reasonable starting experiment. The consumer should prefer the newest frame instead of processing an ever-growing queue.

Never update Qt widgets directly from a worker thread. Use signals or appropriate Qt thread-safe communication.

Shutdown order:
1. Stop accepting new capture frames.
2. Signal workers to stop.
3. Stop capture session.
4. Wait for workers to finish.
5. Release image/buffer resources.
6. Close UI.

## 9. Image Processing Pipeline

```text
Raw Frame
  -> Validate Frame
  -> ROI Crop
  -> Optional Resize
  -> Optional Grayscale
  -> Optional Contrast / Threshold Experiment
  -> Preview / Template Matching Experiment
```

Keep preprocessing configurable. Avoid irreversible transformations before collecting comparison results.

### Template matching
Initial baseline: OpenCV `TM_CCOEFF_NORMED`.

Store templates as assets with metadata describing:
- Killer ID.
- Ability ID or visual state.
- Resolution/scale assumptions.
- Capture conditions.
- Template version.

Thresholds must be empirically selected from representative positive and negative footage.

### Machine learning escalation
Use YOLO only when object localization is required and template matching/classification is insufficient. Use temporal methods for animation recognition. Keep model inference behind a detector interface so it can be replaced without changing cooldown or overlay modules.

### Architectural Decision Record: Baseline vs. Deep Learning (Week 3 / Day 17)
- **Status:** APPROVED & BENCHMARKED.
- **Context:** `PRD.md` dan `AGENTS.md` mewajibkan evaluasi baseline OpenCV sebelum mengevaluasi model deep learning (YOLO/PyTorch).
- **Hasil Benchmark (Held-Out Test Set, 341 frame):**
  - *Template Matching Sendiri:* Recall 95.8%, namun Precision hanya 10.7% (191 False Positives akibat variasi terrain).
  - *Kinematika Gerak Sendiri:* Precision 0.0%, Recall 0.0% (Kibasan kamera survivor mengaburkan estimasi optik).
  - *Multi-Modal Audio-Vision Hybrid:* Precision **100.0%**, Recall **95.8%**, F1-Score **97.9%**, Latensi **60.4 ms**.
- **Keputusan:**
  1. Pelatihan model YOLO berat (PyTorch > 700 MB, ketergantungan CUDA, pemborosan GPU yang merusak performa game Roblox) **TIDAK DIPERLUKAN** untuk MVP The Hidden Leap.
  2. Multi-Modal Audio-Vision Hybrid Engine (`detection/hybrid_detector.py`) diadopsi sebagai *primary detector engine*.
  3. Audio spectral bandpass (100–3.500 Hz low/high energy ratio ~98.5x) berfungsi sebagai *precision gate*, mengeliminasi 100% false positive visual terrain tanpa membebani performa CPU (< 5% usage, latensi ~60 ms).

## 10. Event Recognition and Cooldown State

Future event pipeline:

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Candidate: visual change detected
    Candidate --> Confirmed: temporal checks pass
    Candidate --> Idle: candidate rejected
    Confirmed --> Cooldown: event emitted once
    Cooldown --> Ready: duration elapsed
    Ready --> Idle
```

Requirements:
- Confidence threshold.
- Multi-frame confirmation.
- Debounce window.
- Duplicate-event suppression.
- Configurable cooldown duration.
- Manual start/reset fallback.
- Explicit READY and COOLDOWN states.

Do not treat configured duration as authoritative server state. It is an estimated timer based on local configuration and visible event.

## 11. Data Model

Suggested JSON shape:

```json
{
  "schema_version": 1,
  "game": "Violence District",
  "killers": [
    {
      "id": "the_hidden",
      "name": "The Hidden",
      "abilities": [
        {
          "id": "leap",
          "name": "Leap",
          "cooldown_seconds": 25,
          "enabled": true,
          "detection": {
            "method": "template_matching",
            "template": "assets/templates/the_hidden/leap_ready.png"
          }
        }
      ]
    }
  ]
}
```

The cooldown shown is an example value only. Verify it in the current game and keep it editable.

### Configuration rules
- IDs are stable, lowercase, and machine-friendly.
- Display names are user-facing.
- Durations are numeric seconds.
- JSON has a schema version.
- Missing/invalid data produces a readable error.
- Adding a killer should require data/configuration first, not edits throughout the codebase.

## 12. Overlay Architecture

PySide6 owns overlay window and rendering. OpenCV does not own desktop window lifecycle.

Overlay requirements:
- Transparent background.
- Always-on-top where supported.
- Configurable position and size.
- Click-through mode when enabled.
- No expensive image processing in UI thread.
- UI receives display-ready cooldown state from cooldown controller.

Test click-through behavior with the actual target environment. Window flags and platform behavior can differ.

## 13. Performance and Observability

Record at minimum:
- Capture FPS.
- Processing FPS.
- Frame dimensions.
- ROI dimensions.
- Processing time per frame.
- CPU usage of this application.
- RAM usage of this application.
- Capture errors/restarts.
- Detection confidence and event timestamps once detection exists.

Use monotonic clocks for elapsed-time measurement. Keep logs bounded or rotate them.

Performance targets from PRD are targets, not guarantees. Every report must include machine specifications, display resolution, game mode, and test duration.

## 14. Security and Platform Constraints

Allowed architecture:
- Public Windows capture APIs.
- Local image processing.
- Local JSON configuration.
- External overlay window.

Prohibited:
- Process injection or hooking.
- Reading Roblox process memory.
- Executors or exploit APIs.
- Modifying Roblox client files.
- Bypassing anti-cheat.
- Automated game input.

Screen capture does not guarantee policy approval. Do not describe overlay hiding or capture exclusion as an anti-cheat bypass.

## 15. Architecture Decision Records

| Decision | Current position | Revisit when |
|---|---|---|
| Primary language | Python | User approves stack change |
| Desktop UI | PySide6 | Concrete platform limitation is demonstrated |
| CV baseline | OpenCV | Measurements show learned model is necessary |
| Initial storage | JSON | Data complexity requires database features |
| Capture backend | MSS / Win32 BitBlt provisional backend (11.1-16.9ms @ 30 FPS) with WDA_EXCLUDEFROMCAPTURE, behind modular interface | Transition to WGC in-game if high-refresh game FPS requires GPU VRAM texture |
| Capture exclusion | WDA_EXCLUDEFROMCAPTURE via SetWindowDisplayAffinity & strict PID filtering | Revisit if Windows version < 2004 |
| Initial detector | Template matching baseline & Preprocessing pipeline (CLAHE/Canny/Gray) evaluated Day 4/5 | Full training in Week 3 (YOLO + Temporal Classifier for Survivor POV pose recognition) |
| First ability | The Hidden — Leap | First MVP path is validated |
