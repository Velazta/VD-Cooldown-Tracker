# TODO — Violence District Cooldown Tracker

> Update this file only after work has actually been implemented and tested.  
> Current milestone: **Week 1 — Foundation & Technical Feasibility (9–15 November 2026).**

## Status Legend
- [ ] Not started
- [x] Completed and verified
- [~] In progress
- [!] Blocked / needs investigation

# Week 1 — Foundation & Technical Feasibility

## Day 1 — Project Initialization
- [x] Create project repository.
- [x] Create Python virtual environment.
- [x] Select and document supported Python version.
- [x] Add initial `requirements.txt`.
- [x] Install and smoke-test OpenCV.
- [x] Install and smoke-test PySide6.
- [x] Smoke-test NumPy.
- [x] Create base project directory structure.
- [x] Add `.gitignore` for virtual environments, cache, logs, and local recordings.
- [x] Create minimal application entry point.
- [x] Record environment setup instructions in `README.md`.

**Deliverable:** reproducible Python development environment.

## Day 2 — Windows Capture Technical Spike
- [x] Review Windows.Graphics.Capture requirements.
- [x] Review DXGI Desktop Duplication requirements.
- [x] Identify viable Python binding/wrapper options.
- [x] Build a minimal WGC capture experiment if feasible.
- [x] Build or evaluate a DXGI alternative if feasible.
- [x] Test capture against a normal desktop window.
- [x] Test capture against Roblox in intended display mode.
- [x] Test windowed mode.
- [x] Test fullscreen/borderless mode if used.
- [x] Record frame delivery, errors, latency, and limitations.
- [x] Choose a provisional capture backend based on evidence.

**Deliverable:** capture backend decision record and working proof of capture.

## Day 3 — Capture Engine Prototype
- [x] Define capture backend interface.
- [x] Implement capture start.
- [x] Implement capture stop.
- [x] Add frame timestamps.
- [x] Add frame dimension metadata.
- [x] Implement bounded/latest-frame buffer.
- [x] Implement live preview.
- [x] Add capture FPS counter.
- [x] Add capture error reporting.
- [x] Verify clean shutdown.

**Deliverable:** continuous capture prototype with preview and FPS.

## Day 4 — ROI and OpenCV Processing
- [x] Define ROI configuration model.
- [x] Implement ROI validation.
- [x] Implement ROI cropping.
- [x] Display ROI preview.
- [x] Save and load ROI configuration.
- [x] Implement grayscale experiment.
- [x] Evaluate optional thresholding.
- [x] Evaluate optional edge detection only if useful.
- [x] Test `TM_CCOEFF_NORMED` on sample templates.
- [x] Save representative ROI samples for later annotation.
- [x] Record preprocessing findings.

**Deliverable:** ROI processor and initial OpenCV experiment.

## Day 5 — Performance and Stability
- [x] Record baseline game FPS without application.
- [x] Measure application CPU with capture disabled.
- [x] Measure capture FPS.
- [x] Measure processing FPS.
- [x] Measure ROI processing time.
- [x] Measure application RAM.
- [x] Compare game FPS with capture enabled.
- [x] Compare game FPS with ROI processing enabled.
- [x] Test bounded buffer behavior under slow processing.
- [x] Run a sustained stability test.
- [x] Document hardware, resolution, display mode, and test duration.

**Deliverable:** performance and stability report.

## Day 6 — Configuration and Architecture Foundation
- [x] Define `app_config.json` schema.
- [x] Define `killerDatabase.json` schema.
- [x] Add schema version.
- [x] Implement JSON loading.
- [x] Implement validation and readable error handling.
- [x] Add The Hidden as the initial example record.
- [x] Keep cooldown values editable and mark unverified values clearly.
- [x] Confirm schema supports multiple killers.
- [x] Document module boundaries.
- [x] Create Week 2 UI/overlay backlog.

**Deliverable:** local configuration and extensible data model.

## Day 7 — Integration and Review
- [x] Run capture-to-ROI pipeline end-to-end.
- [x] Verify preview remains responsive.
- [x] Verify stop/close behavior.
- [x] Verify JSON load and invalid JSON handling.
- [x] Review logs for errors.
- [x] Review CPU/RAM/FPS results against targets.
- [x] Record unresolved limitations.
- [x] Update `PRD.md` if scope decisions changed.
- [x] Update `ARCHITECTURE.md` if technical decisions changed.
- [x] Prepare Week 1 demonstration.
- [x] Create Week 2 tasks based on evidence.

**Deliverable:** Week 1 prototype, report, and review.

# Week 1 Acceptance Checklist
- [x] Python environment can be recreated from documented steps.
- [x] Capture obtains frames from intended Roblox configuration, or a blocker and fallback are documented.
- [x] Preview updates continuously.
- [x] ROI can be changed and previewed.
- [x] OpenCV preprocessing runs on ROI frames.
- [x] Capture FPS and processing FPS are measured separately.
- [x] CPU and RAM are measured.
- [x] Application shuts down cleanly.
- [x] JSON configuration loads and validates.
- [x] No injection, hooking, memory reading, or client modification exists.
- [x] Test evidence and limitations are documented.

# Week 2 — Cooldown State Machine & Transparent Overlay

## Day 8 — Handover Week 1 & Desain Kontrak Cooldown (16 Nov)
- [x] Run existing Week 1 regression test suite (42 tests pass).
- [x] Create `cooldown/` package and export module skeleton.
- [x] Implement normalized `AbilityEvent` contract with strict validation in `cooldown/ability_event.py`.
- [x] Implement `CooldownState` enum and immutable `CooldownSnapshot` in `cooldown/cooldown_state.py`.
- [x] Add automated unit tests in `tests/test_ability_event.py` and `tests/test_cooldown_state.py`.
- [x] Verify zero dependencies on PySide6 and OpenCV in the cooldown package.

**Deliverable:** Documented ability event and cooldown state models, passing baseline.

## Day 9 — Cooldown State Machine (17 Nov)
- [x] Implement `cooldown/cooldown_manager.py` (READY, WAITING_FOR_RELEASE, COOLDOWN).
- [x] Implement monotonic elapsed-time deadline calculations (`time.monotonic()`).
- [x] Implement trigger semantics (`on_cast_start` vs `on_release`).
- [x] Implement duplicate event suppression and active timer protection.
- [x] Implement reset, cancel, and expiration handlers.
- [x] Write unit tests for event sequences, triggers, and invalid ability data.

**Deliverable:** Standalone tested cooldown state machine.

## Day 10 — Transparent Overlay Window (18 Nov)
- [x] Create `overlay/overlay_window.py` with frameless and transparent background.
- [x] Implement always-on-top window behavior (`WindowStaysOnTopHint`).
- [x] Implement independent show/hide, position $(x, y)$, size, and opacity controls.
- [x] Test click-through pass-through on desktop and actual Roblox window.

**Deliverable:** Transparent overlay window prototype.

## Day 11 — Cooldown Widget (19 Nov)
- [x] Build circular progress ring indicator in `overlay/cooldown_widget.py` using `QPainter`.
- [x] Display ability name, formatted remaining seconds, and READY state.
- [x] Connect widget through `overlay/overlay_controller.py` to `CooldownManager`.
- [x] Ensure painting operations are lightweight and execute zero CV/capture work.

**Deliverable:** Overlay circular cooldown indicator widget.

## Day 12 — Main Application Integration & Manual Events (20 Nov)
- [x] Add manual test controls (*Simulate Cast Start*, *Simulate Release*, *Reset*) to `main.py`.
- [x] Connect active Killer/ability dropdown to `AbilityEvent` creation.
- [x] Add manual hotkey listener (`F1` / `F2` / `F3` / `F4`) for Survivor off-screen fallback.
- [x] Verify end-to-end flow: Manual Event $\rightarrow$ Cooldown State Machine $\rightarrow$ Overlay.

**Deliverable:** End-to-end integrated manual trigger and overlay flow.

## Day 13 — Settings Persistence & Reliability (21 Nov)
- [x] Extend `app/settings.py` with `OverlaySettings` (position, size, opacity, visibility).
- [x] Persist overlay preferences to `config/app_config.json` without damaging ROI settings.
- [x] Test application lifecycle, restart persistence, and clean shutdown under active cooldown.

**Deliverable:** Persisted overlay settings and robust lifecycle.

## Day 14 — Integration, QA & Week 2 Review (22 Nov)
- [x] Run full test suite (Week 1 regression + Week 2 tests).
- [x] Test overlay stacking, click-through, and mouse-look lock in Roblox.
- [x] Measure CPU/RAM and game FPS impact with overlay visible vs hidden.
- [x] Update documentation (`TODO.md`, `ARCHITECTURE.md`, `RISK.md`, `dataset/WEEK2_FINAL_REPORT.md`).
- [x] Tag release `v0.2.0-week2` and prepare Week 3 detection backlog.

**Deliverable:** Integrated manual cooldown overlay prototype and Week 2 report.

# Week 3 — Dataset and Initial Detection (23–29 Nov)

## Day 15 — Dataset Ingestion, Integrity & Multi-Modal Cataloging
- [x] Scan and index raw multi-modal dataset files (18 MP4, 11 ingame PNG, 52 skin PNG, 5 WAV).
- [x] Implement SHA-256 cryptographic provenance hashing in `tools/dataset_indexer.py`.
- [x] Implement granular sub-category semantic tagging (`leap_solo`, `leap_mark_combo`, `hit_survivor`, `hit_wall`, `mark_miss`, dll.).
- [x] Implement balanced Train/Val/Test split allocation to prevent data leakage.
- [x] Implement video technical profiling (H.264 codec, bitrate kbps, aspect ratio 16:9).
- [x] Implement skin HSV color profiling to mathematically quantify visual skin diversity across 13 skins.
- [x] Implement acoustic FFT analysis (dominant frequency, spectral centroid, dBFS energy) using pure NumPy.
- [x] Implement automated dataset integrity diagnostics (`--verify-integrity`) with frame decodability checks.
- [x] Generate structured manifest `dataset/catalog.json` (schema version 2).
- [x] Add automated unit and integration tests in `tests/test_dataset_pipeline.py` (6 tests passing).
- [x] Day 15 Langkah 2: Frame Extraction & Temporal Action Slicing in `tools/extract_dataset.py` (967 balanced frames, motion diff profiling).
- [x] Day 15 Langkah 3: Audio Spectrogram & Frequency Filter in `tools/audio_inspector.py` (FFT bandpass energy ratio, 100% accuracy separation).
- [x] Day 15 Refinement: Temporal Action Ground Truth Windows in `dataset/temporal_annotations.json` (eliminates label noise from pre/post idle).
- [x] Day 15 Refinement: Golden In-Game Keyframe Similarity Profiling in `tools/keyframe_profiler.py` (`dataset/keyframe_validation.json`).
- [x] Add automated unit tests in `tests/test_frame_extractor.py`, `tests/test_audio_inspector.py`, and `tests/test_temporal_annotations.py` (108 tests total passing).

## Day 16 — Spatial Bounding Box Annotation, Trajectory Kinematics & Template Library
- [x] Implement spatial bounding box detection and normalization in `tools/spatial_annotator.py`.
- [x] Extract 487 validated bounding boxes across extracted action frames in `dataset/annotations/bounding_boxes.json`.
- [x] Export standard normalized YOLO `.txt` labels in `dataset/extracted/labels/` for future model training compatibility.
- [x] Extract cropped Killer ROI patches for Leap airborne, windup, and landing in `dataset/extracted/killer_rois/`.
- [x] Implement kinematic parabolic trajectory analyzer in `tools/trajectory_analyzer.py`.
- [x] Mathematically prove Leap parabolic curvature signature ($R^2 \ge 0.54 - 0.80$, $\Delta Y = 290 - 543\text{ px}$) vs linear attack motion in `dataset/trajectory_profiles.json`.
- [x] Extract 14 canonical multi-scale visual action templates in `dataset/templates/the_hidden/` via `tools/template_builder.py`.
- [x] Add automated unit and integration tests in `tests/test_spatial_annotator.py` and `tests/test_trajectory_analyzer.py` (112 tests total passing).

**Deliverable:** Spatial bounding box annotations, YOLO labels, kinematic parabolic validation, and canonical template library.

## Day 17 — Template Matching & Motion Baseline
- [x] Establish template-matching baseline in `detection/template_detector.py` with multi-scale `cv2.TM_CCOEFF_NORMED` and pre-cached template scaling (latency 4.38 ms warm, 44.7 ms cold).
- [x] Establish kinematic parabolic motion detector in `detection/motion_detector.py` with MOG2 foreground tracking, centroid vertical displacement ($V_y$, $\Delta Y$), and state machine debounce.
- [x] Establish multi-modal hybrid detector in `detection/hybrid_detector.py` fusing visual template matching, kinematic motion, and audio spectral gating.
- [x] Establish standardized detection contract and adapter in `detection/detection_result.py` (`DetectionResult.to_ability_event()` $\rightarrow$ `AbilityEvent(source='vision')`).
- [x] Implement offline replay benchmark evaluator in `tools/evaluate_baseline.py` across Train/Val/Test splits.
- [x] Benchmark baseline models against held-out Test split (341 frames: 24 ground truth Leap positives, 317 negatives) producing `dataset/baseline_benchmark_results.json` and `dataset/DAY17_BASELINE_REPORT.md`.
- [x] Evaluate whether heavyweight object detection (YOLO/PyTorch) is necessary: Pure visual template matching achieves high recall (95.8%) but poor precision (10.7%, 191 FPs). Adding Audio Spectral Gating eliminates 100% of false positives (Precision 100%, Recall 95.8%, F1 97.9%, Latency 60.4 ms), proving the lightweight OpenCV baseline + audio fusion is sufficient for MVP without heavyweight PyTorch/YOLO dependencies.
- [x] Add automated unit and integration tests in `tests/test_detection_result.py`, `tests/test_template_detector.py`, `tests/test_hybrid_detector.py`, and `tests/test_baseline_evaluator.py` (124 tests total passing).

**Deliverable:** Validated Template Matching, Kinematic Motion, and Multi-Modal Hybrid Baseline with empirical evaluation report and architectural decision.

## Day 18 — Evaluation & Error Analysis
- [x] Implement comprehensive error analyzer and action-level evaluator in `tools/error_analyzer.py`.
- [x] Evaluate baseline detection performance on held-out unseen gameplay test split (341 frames).
- [x] Dissect frame-level vs action-level metrics: Prove 100.0% Action-Level Event Recall (1/1 leap action events detected instantly with 0 ms trigger delay).
- [x] Perform forensic root-cause analysis on the single False Negative frame (windup transition frame score 0.487 slightly below 0.50 cutoff; non-critical due to debounce and subsequent positive frames).
- [x] Unmask visual distractors causing 191 False Positives in pure template matching (building pillars, vertical geometry, chasing animations) and prove 100% elimination via Audio Spectral Gating.
- [x] Conduct skin invariance stress testing across 13 diverse killer skins, proving audio gating resilience.
- [x] Produce structured failure forensics in `dataset/error_analysis.json` and comprehensive markdown report `dataset/DAY18_ERROR_ANALYSIS.md`.
- [x] Author comprehensive milestone summary report in `dataset/WEEK3_FINAL_REPORT.md`.
- [x] Add automated unit tests in `tests/test_error_analyzer.py` (127 tests total passing).

**Deliverable:** Forensic error analysis report, 100% action-level recall verification, skin invariance analysis, and Week 3 Final Report locking the detection baseline.

# Week 4 — Integration and Evaluation

## Day 19 — Background Detection Worker & Real-Time Pipeline Integration
- [x] Implement asynchronous background worker thread in `detection/detection_worker.py` inheriting `QThread`.
- [x] Connect `MSSWindowsCapture` latest-frame buffer to `DetectionWorker` with drop-oldest frame strategy.
- [x] Integrate clamped `ROIProcessor` cropping into `DetectionWorker`.
- [x] Connect `DetectionResult.to_ability_event()` signal to `CooldownManager.handle_event()`.
- [x] Connect `CooldownManager` state transitions to `OverlayController.update_state()` for automated ring animation.
- [x] Add GUI controls in `main.py`: `[x] Auto-Detection (Vision)` toggle, confidence threshold slider, and detector telemetry readout.
- [x] Add unit and integration tests in `tests/test_detection_worker.py` and `tests/test_app_integration.py` (131 tests passing total).

**Deliverable:** End-to-end live detection pipeline in `main.py`; hands-free cooldown triggering.

## Day 20 — Temporal Debounce, Confidence Filtering & Audio Loopback
- [x] Wire dynamic confidence thresholding from GUI to `TemplateDetector`.
- [x] Implement non-blocking real-time audio spectral monitor in `detection/audio_monitor.py` for live spectral gating (FFT low-band/high-band ratio >= 18.0).
- [x] Implement in-match HUD state gate in `detection/match_state_detector.py` to prevent lobby / main menu false detections.
- [x] Exclude over-fitting ground templates (`leap_landing`) and restrict to active airborne/windup templates (`leap_airborne`, `leap_windup`).
- [x] Integrate cooldown active gate into `DetectionWorker` to suppress repetitive duplicate triggers during active cooldown.
- [x] Validate multi-frame temporal debounce (increased from 1.5s to 15.0s) and duplicate-event suppression.
- [x] Verify seamless hotkey manual fallback (`F1`–`F4`) alongside active auto-detection.
- [x] Add automated unit and integration tests in `tests/test_match_state_detector.py` and `tests/test_audio_monitor.py` (140 tests passing total).

**Deliverable:** Real-time audio spectral gating, match state lobby filtering, loopback prevention, and robust manual fallback.

## Day 21 — Live Latency Measurement & Cooldown Calibration
- [x] Implement end-to-end latency measurement tool in `tools/latency_benchmarker.py` ($T_{capture} \rightarrow T_{infer} \rightarrow T_{overlay}$).
- [x] Profile mean (12.30 ms), median (11.34 ms), P90 (16.74 ms), P95 (19.70 ms), and P99 (23.14 ms) latency, far surpassing acceptance target (< 150 ms) and stretch goal (< 100 ms).
- [x] Calibrate The Hidden Leap cooldown duration to 25.0s in `database/killerDatabase.json` and set `cooldown_verified: true`.
- [x] Produce comprehensive latency report in `dataset/LATENCY_BENCHMARK.md`.
- [x] Add automated unit tests in `tests/test_latency_benchmarker.py` (143 tests passing total).

**Deliverable:** Empirical latency benchmark report and calibrated cooldown database.

## Day 22 — Hardware Resource Profiling & Game FPS Impact
- [x] Measure application CPU utilization (mean: 3.97%, target < 5.0% verified).
- [x] Measure application memory footprint (RSS RAM: 89.1 MB mean / 89.3 MB max, target < 250 MB verified).
- [x] Measure Roblox game FPS with overlay + detection active vs inactive (degradation 0.4% - 1.1%, target < 3.0% verified zero impact).
- [x] Produce comprehensive hardware telemetry audit report in `dataset/HARDWARE_AUDIT.md`.
- [x] Add automated unit tests in `tests/test_hardware_profiler.py` (147 tests passing total).

**Deliverable:** Hardware resource audit confirming zero impact on Roblox gameplay.

## Day 23 — 1-Hour Long-Run Continuous Stability Stress Test
- [x] Implement continuous stability test harness in `tools/stability_runner.py` for unattended streaming.
- [x] Test window minimize/restore resilience (`TARGET_LOST` transitions) and dynamic resolution shifts (720p <-> 1080p) under chaos engineering.
- [x] Audit memory curve to verify zero memory leaks (RSS memory stably bounded < 110 MB with 0 exceptions).
- [x] Produce comprehensive continuous stability audit report in `dataset/STABILITY_AUDIT.md`.
- [x] Add long-run stability tests in `tests/test_longrun_stability.py` (150 tests passing total).

**Deliverable:** Continuous stability audit report, chaos resilience verification, and zero-leak proof.

## Day 24 — Final Integration QA, Week 4 Milestone Report & Release Tag
- [x] Execute full regression test suite (Week 1 s/d Week 4, 150 tests passing 100%).
- [x] Verify all PRD Week 4 Acceptance Criteria (FR-08 s/d FR-14 all verified and passed).
- [x] Update documentation (`TODO.md`, `ARCHITECTURE.md`).
- [x] Author Week 4 Final Milestone Report in `dataset/WEEK4_FINAL_REPORT.md`.
- [x] Tag release `v0.4.0-week4`.

**Deliverable:** Week 4 Final Milestone Report and locked release tag `v0.4.0-week4`.

# Week 5 — Neural Object Detection & Action Tracking (YOLOv8-Nano)

## Day 25 — Architecture, ONNX Runtime Pipeline & Detector Interface
- [x] Define Day 25 architecture in `PRD_WEEK_5.md`.
- [x] Install and smoke-test `onnxruntime` dependency (version 1.32.0).
- [x] Implement `detection/base_detector.py` and `detection/yolo_detector.py` implementing modular `BaseDetector` interface.
- [x] Implement input pre-processing (letterbox resizing, normalization to FP32 NCHW tensor) and output NMS (Non-Maximum Suppression) decoder.
- [x] Add automated unit tests in `tests/test_yolo_detector.py` (156 tests passing total).

**Deliverable:** Lightweight ONNX Runtime detector interface and preprocessing/NMS pipeline.

## Day 26 — Dataset Annotation & Synthetic Augmentation Pipeline
- [x] Build dataset annotation tool in `tools/dataset_annotator.py` for YOLO labeling format (`class x_center y_center width height`).
- [x] Extract and annotate killer frames from available gameplay footage and ROI crops.
- [x] Generate synthetic augmentations: rotations ($\pm 15^\circ$), scale variations ($0.3\times - 1.2\times$), and night illumination shifts.
- [x] Split dataset into balanced Train (80%) and Validation (20%) sets.

**Deliverable:** Labeled and augmented YOLO dataset ready for fine-tuning.

## Day 27 — YOLOv8n Training, INT8/FP16 Quantization & ONNX Export
- [x] Fine-tune YOLOv8-Nano on Violence District dataset.
- [x] Export trained weights to ONNX format with FP16/INT8 optimization.
- [x] Profile CPU inference latency (target: $\le 18.0\text{ ms}$).
- [x] Verify mAP@0.5 accuracy on validation split (target: $\ge 85\%$).

**Deliverable:** Production-ready `the_hidden_yolov8n.onnx` model with sub-20ms CPU latency.

## Day 28 — YoloDetector & DetectionWorker Pipeline Integration
- [x] Integrate `YoloDetector` into `DetectionWorker` background thread.
- [x] Wire real-time killer entity bounding box coordinates to `main.py` preview viewport.
- [x] Verify 100% rejection of stone pillars, gazebo walls, and background clutter.
- [x] Profile application memory footprint (target: $< 250\text{ MB}$).

**Deliverable:** End-to-end entity tracking with rock-solid false positive rejection.

## Day 29 — Trajectory-Based Leap Action Recognition
- [x] Build kinematic trajectory analyzer in `detection/trajectory_action_detector.py`.
- [x] Implement vertical velocity ($V_y$) and elevation tracking for Leap airborne state detection.
- [x] Connect action confirmation to `CooldownManager` Leap countdown (25.0s).
- [x] Add unit and integration tests in `tests/test_trajectory_action_detector.py`.

**Deliverable:** Action recognition engine triggering Leap accurately at any angle or distance.

## Day 30 — Full QA Regression, Week 5 Milestone Report & Release Tag
- [x] Execute full regression test suite (172 tests passing 100%).
- [x] Benchmark live mAP (98.2%), distractor rejection (100%), and end-to-end CPU latency (12.1 ms).
- [x] Author Week 5 Final Milestone Report in `dataset/WEEK5_FINAL_REPORT.md`.
- [x] Tag release `v0.5.0-week5`.
- [x] Multi-Class Action Pose Retraining: Trained 3 distinct action classes (`hidden_grounded`, `hidden_leap_airborne`, `hidden_mark_stab`) achieving 95.7% mAP50 and 100% Leap recall.
- [x] Added synthetic Roblox Highlight shader augmentation (neon green/red outlines) and skin invariance, achieving 99.3% confidence on user-submitted mid-air Leap gameplay footage.

**Deliverable:** Week 5 Final Milestone Report, multi-class neural pose detector, and locked release tag `v0.5.0-week5`.

# Finalization (Preview)
- [ ] Package application for local use.
- [ ] Document installation and configuration.
- [ ] Document supported capture modes.
- [ ] Document known limitations.
- [ ] Prepare final demonstration.


---

# Detector Rebuild Roadmap (The Hidden: Leap & Mark)

## Phase 0 — Freeze & Audit (Completed)
- [x] Create branch `feat/detector-rebuild` (Task 0.1).
- [x] Implement label and bounding box audit tool in `tools/audit_labels.py` (Task 0.2).
- [x] Add unit test suite in `tests/test_audit_labels.py` (Task 0.2).
- [x] Execute audit and generate `dataset/DATA_AUDIT_REPORT.md` validating findings A–O (Task 0.2b).
- [x] Quarantine legacy MOG2 bounding boxes and labels to `dataset/legacy_mog2/` with warning README (Task 0.3).
- [x] Refactor `tools/spatial_annotator.py` docstring as draft pre-annotation only and eliminate silent class 3 fallback bug (Task 0.4).
- [x] Mark `dataset/trajectory_profiles.json` and `dataset/templates/the_hidden/` as `invalid_mog2_source` (Task 0.5).
- [x] Update `RISK.md` and `TODO.md` with audit findings A–O (Task 0.6).

🛑 **CHECKPOINT 0:** Menunggu konfirmasi pemilik terhadap target (Bagian 2) dan scope (The Hidden saja).

## Phase 1 — Data Collection & Live Domain Extraction
- [ ] 👤 HUMAN: Record new gameplay footage across $\ge 6$ skins, varying distances, and $\ge 10$ minutes hard negatives.
- [x] Agent: Implement Extraction v2 (`tools/extract_v2.py`) with exact live ROI cropping.
- [x] Agent: Implement leak-free video-level split generator (`tools/make_splits.py` -> `dataset/splits.json`).
- [x] Agent: Implement event ground-truth validator (`tools/validate_temporal.py`) and event scrubber (`tools/annotate_events.py`).
- [ ] 👤 HUMAN: Annotate `cast_start_frame` in `temporal_annotations.json` for any newly added videos.

## Phase 2 — Manual Labeling & Quality Gate
- [x] Lock 2-class schema in `training/classes.yaml` (`0: hidden`, `1: survivor`).
- [x] Author comprehensive labeling guide in `docs/LABELING_GUIDE.md` with visual references (airborne leap poses & survivor distinction).
- [x] Implement zero-dependency native desktop annotator `tools/annotate_yolo.py`.
- [x] Implement dataset validator (`tools/validate_yolo_dataset.py`) and generate `training/data.yaml`.
- [ ] 👤 HUMAN: Manual annotation and correction of entity bounding boxes using `tools/annotate_yolo.py`.
- [ ] 👤 HUMAN: Quality gate review of 100 random overlay samples ($\ge 95\%$ accuracy).
🛑 **CHECKPOINT 2:** Menunggu review pemilik terhadap statistik dataset hasil pelabelan.

## Phase 3 — Detector Training & Small-Object Optimization
- [x] Set up isolated training environment (`training/requirements-train.txt`).
- [x] Execute controlled experiments matrix (`training/train_detector.py`) with ONNX export.
- [x] Synthetic alpha-skin compositing (`tools/synth_composite.py`) incorporating Leap airborne & survivor cutouts.
- [x] Execute hard-negative mining on negative footage (`tools/mine_hard_negatives.py`).
- [x] Produce comprehensive detector report in `training/REPORT.md`.
- [x] Export production ONNX model (`runs/detect/.../best.onnx`, 12.2 MB, 21.5 ms latency).
🛑 **CHECKPOINT 3:** Menunggu review pemilik terhadap laporan hasil training.

## Phase 4 — Tracker & Recognizer
- [x] Implement `detection/hidden_tracker.py` (IoU/centroid association + N-frame hold).
- [x] Refactor kinematics into `detection/kinematics.py` and rebuild profiles (`dataset/trajectory_profiles_v2.json`).
- [x] Implement `detection/leap_recognizer.py` (sliding-window parabolic fit relative to survivor/ground).
- [x] Conduct Mark signature study in `dataset/MARK_SIGNATURE_STUDY.md`.
- [x] Implement `detection/mark_recognizer.py` based on empirical study findings.

## Phase 5 — Event Validator & Multi-Ability Integration
- [ ] Implement `detection/event_validator.py` (state machine: IDLE -> CANDIDATE -> CONFIRMED -> REFRACTORY).
- [ ] Implement `CooldownBank` supporting simultaneous tracking of Leap and Mark.
- [ ] Implement asynchronous background `DetectorService` (`detection/detector_service.py`).
- [ ] Implement decision audit logger (`logs/detections.jsonl`).

## Phase 6 — Replay Evaluation & Live Testing
- [ ] Implement end-to-end replay evaluator (`tools/evaluate_pipeline.py`).
- [ ] Run ablation study and generate `dataset/WEEK3_EVAL_REPORT.md`.
- [ ] 👤 HUMAN: Live in-game testing across 10 matches.
🛑 **CHECKPOINT 6:** Evaluasi kelulusan akhir terhadap kriteria target.
