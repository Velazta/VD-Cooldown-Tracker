# Week 3 — Development References (Day 1–7)

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 3 — Gameplay Dataset, Leap Recognition & CV Baseline  
**Schedule:** 23–29 November 2026  
**Target branch:** `dev`  
**Primary stack:** Python 3.14, OpenCV, NumPy, PySide6  
**Optional experiments:** Ultralytics YOLO / YOLO Pose, MediaPipe  
**Purpose:** Day-by-day learning and implementation references aligned with `PRD_WEEK_3.md`.

> Week 2 is complete on `dev`. Reuse the capture, ROI, preprocessing, monitoring, `AbilityEvent`, `CooldownManager`, and overlay modules. Week 3 is a data + detection feasibility milestone. Do not assume a pretrained pose model will understand stylized Roblox avatars.

---

## How to use this guide

1. Read **Required** references before starting the day's work.
2. Use supporting references only when the selected experiment needs them.
3. Preserve original recordings; make extraction reproducible.
4. Split by whole matches/sessions, never by randomly shuffled frames from the same match.
5. Measure event-level performance. Frame accuracy alone is insufficient.
6. Add optional ML dependencies only after the OpenCV baseline and feasibility evidence justify them.

## Day 1 — Recording Protocol & Dataset Design (23 Nov)

**Goal:** Define how gameplay is recorded, indexed, annotated, and stored before collecting a large dataset.

### Required references

- [OBS Standard Recording Output Guide](https://obsproject.com/kb/standard-recording-output-guide) — recording format, quality, output path, and reliable source-video handling. MKV is a sensible capture container; preserve the original.
- [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) — command-line reference for inspecting, trimming, and extracting video streams while retaining a reproducible workflow.
- [Python csv](https://docs.python.org/3/library/csv.html) — recording manifest and event timestamp log.
- [Python json](https://docs.python.org/3/library/json.html) — structured annotation and dataset manifest formats.

### Supporting references

- [Python pathlib](https://docs.python.org/3/library/pathlib.html) — deterministic local dataset paths.
- [Python hashlib](https://docs.python.org/3/library/hashlib.html) — optional file checksums to identify source recordings and detect accidental replacement.

### Apply to the project

- Define recording/session IDs and metadata fields.
- Write a Survivor POV recording matrix: match, camera distance, angle, visibility, map lighting, and available The Hidden appearance.
- Define positive Leap event onset and phase labels.
- Define hard negatives and unobservable/ambiguous labels.
- Set local-only storage policy for raw footage; keep large/private videos out of Git.

**Deliverable:** recording protocol, annotation guide outline, and manifest templates.

**Completion evidence:** one test recording indexed end-to-end and metadata can be traced to the source file.

---

## Day 2 — Gameplay Recording (24 Nov)

**Goal:** Collect distinct Leap events and representative hard-negative footage.

### Required references

- [OBS Standard Recording Output Guide](https://obsproject.com/kb/standard-recording-output-guide) — choose recording quality/container and output directory.
- [OBS Overview Guide](https://obsproject.com/kb/OBS-Studio-Overview) — review recording path, encoder selection, and video settings.
- [OBS Quick Start](https://obsproject.com/kb/quick-start-guide) — configure sources and begin recording if needed.

### Supporting references

- [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) — inspect recording metadata and duration after capture.

### Apply to the project

- Record only Survivor POV for the primary detection set.
- Capture several distinct matches/sessions, not one long session alone.
- Record Leap and negatives: ordinary jump, vault, fall, attack, stun/recovery, camera motion, occlusion, and no Killer visible.
- Record rough event timestamps and appearance/visibility notes immediately after each session.
- Do not fabricate samples or duplicate near-identical frames to meet a target.

**Deliverable:** indexed raw videos and event logs.

**Completion evidence:** manifest entries, source file checks, and a short coverage report showing distinct sessions and event counts.

---

## Day 3 — Clip/Frame Extraction & Pilot Annotation (25 Nov)

**Goal:** Create repeatable event-centered clips and define annotation consistency.

### Required references

- [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html) — trim clips and extract frames; preserve source offsets and record extraction commands.
- [OpenCV VideoCapture](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) — read video frames and inspect frame positions/timestamps in Python.
- [CVAT documentation](https://docs.cvat.ai/) — reference for video/image annotation workflows, tracks, and annotation task organization.
- [Ultralytics Pose Dataset Format](https://docs.ultralytics.com/datasets/pose) — consult only if the pose feasibility test justifies custom keypoint annotations.

### Supporting references

- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) — typed annotation records if implemented in Python.
- [Python csv](https://docs.python.org/3/library/csv.html) — event-level annotation table.

### Apply to the project

- Extract short clips around Leap onset plus context before and after.
- Extract hard-negative clips from similar-looking animations.
- Preserve recording ID, source timestamp, frame index, and extraction parameters.
- Annotate phase, onset, end, visibility, occlusion, and optional Killer bounding box.
- Do not annotate human COCO keypoints on Roblox avatars unless those joints are genuinely visible and consistently definable. If needed, design an avatar-specific skeleton first.

**Deliverable:** pilot annotated dataset and annotation guide.

**Completion evidence:** two reviewers or a repeat review agree on event-onset rules for a sample; ambiguous examples are explicitly marked.

---

## Day 4 — Dataset Audit & Split (26 Nov)

**Goal:** Validate annotation quality and create leakage-safe train/validation/test partitions.

### Required references

- [Python csv](https://docs.python.org/3/library/csv.html) — parse event and recording manifests.
- [Python json](https://docs.python.org/3/library/json.html) — validate annotation records and manifests.
- [scikit-learn GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html) — group samples by recording/session when cross-validation is needed.
- [scikit-learn GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html) — create randomized splits that keep groups intact.

### Supporting references

- [Python hashlib](https://docs.python.org/3/library/hashlib.html) — optional duplicate/source integrity checks.
- [pytest documentation](https://docs.pytest.org/en/stable/) — test dataset validators and malformed annotation handling.

### Apply to the project

- Check broken video paths, invalid timestamps, duplicate frames, missing labels, and inconsistent event boundaries.
- Group by full recording/match ID before splitting.
- Lock the test sessions and do not use them for threshold selection.
- Report counts by phase, match, appearance, camera distance, and visibility.
- If too few independent sessions exist, use group-based cross-validation and mark results preliminary.

**Deliverable:** dataset manifest, split files, and quality report.

**Completion evidence:** automated validation report and proof that no session ID appears in more than one split.

---

## Day 5 — OpenCV Temporal Baseline (27 Nov)

**Goal:** Build a reproducible non-ML baseline and discover which visible cues distinguish Leap.

### Required references

- [OpenCV Template Matching](https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html) — evaluate template matching for stable local patterns, while measuring failures from skin/scale variation.
- [OpenCV Optical Flow — Lucas-Kanade](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html) — track local feature motion between frames.
- [OpenCV Background Subtraction](https://docs.opencv.org/4.x/d1/dc5/tutorial_background_subtraction.html) — optional motion segmentation experiment; assess camera-motion sensitivity before use.
- [OpenCV Video I/O tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) — deterministic video replay and frame iteration.

### Supporting references

- [NumPy absolute beginners](https://numpy.org/doc/stable/user/absolute_beginners.html) — array operations for simple frame-difference and trajectory features.
- Existing project code: `processing/roi_processor.py`, `processing/preprocessing.py`, `processing/template_matcher.py`, and `monitoring/performance_monitor.py`.

### Apply to the project

- Reuse the existing ROI and processing abstractions.
- Compare at least two cues: template/shape and temporal motion/trajectory.
- Test raw, grayscale, and downscaled crops before expensive CLAHE.
- Include a temporal window/state validator; one matching frame must not emit an event.
- Replay the same labeled clips and log predictions, scores, event timestamps, and processing time.

**Deliverable:** offline OpenCV baseline and validation results.

**Completion evidence:** reproducible run configuration, event-level metrics, and inspectable false-positive/false-negative clips.

---

## Day 6 — Model Feasibility & Comparison (28 Nov)

**Goal:** Determine whether object detection or pose estimation adds measurable value on stylized Roblox footage.

### Required references

- [Ultralytics Pose Estimation](https://docs.ultralytics.com/tasks/pose) — understand pose prediction outputs, keypoints, confidence, and validation metrics.
- [Ultralytics Pose Dataset Format](https://docs.ultralytics.com/datasets/pose) — understand custom keypoint annotation requirements before creating labels.
- [MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker) — evaluate an alternative pose pipeline and its landmark outputs.
- [PyTorch Reproducibility](https://pytorch.org/docs/stable/notes/randomness.html) — record seeds and understand limits of reproducible training if PyTorch training is attempted.

### Supporting references

- [Ultralytics license information](https://www.ultralytics.com/license) — review licensing before adopting the package or distributing a product built with it.
- [Ultralytics YOLO detection task](https://docs.ultralytics.com/tasks/detect) — object localization alternative if pose landmarks are not reliable.
- [PyTorch documentation](https://pytorch.org/docs/stable/index.html) — consult only if a justified training experiment requires it.

### Apply to the project

- Run pretrained models on representative Roblox footage before training.
- Record whether the Killer is localized and whether keypoints are stable across frames, skins, camera angles, and distances.
- Do not assume COCO human keypoints map to blocky R6/R15 avatar geometry.
- Compare model output against the same OpenCV baseline and held-out sessions.
- Train only if dataset volume/quality is sufficient and the baseline has a measured limitation.
- Record model version, weights, license, hardware, latency, and failure examples.

**Deliverable:** model feasibility comparison and documented model-selection decision.

**Completion evidence:** visual prediction samples, validation metrics, runtime measurements, and explicit accept/reject rationale.

---

## Day 7 — Evaluation & Week 4 Handover (29 Nov)

**Goal:** Evaluate the selected baseline/model on untouched sessions and prepare integration requirements.

### Required references

- [scikit-learn precision_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_score.html) — quantify the fraction of emitted positive predictions that are correct.
- [scikit-learn recall_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html) — quantify observable Leap events recovered by the detector.
- [scikit-learn classification_report](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html) — summarize precision, recall, F1, and support.
- [scikit-learn confusion_matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) — inspect false positives and false negatives.
- [Python time](https://docs.python.org/3/library/time.html) — measure processing latency and event delay with monotonic/performance clocks.

### Supporting references

- [pytest documentation](https://docs.pytest.org/en/stable/) — test deterministic replay and event adapter.
- [Python logging](https://docs.python.org/3/library/logging.html) — retain structured evidence for event decisions.

### Apply to the project

- Score event-level predictions on held-out recording sessions.
- Define and report event matching tolerance and onset uncertainty.
- Report precision, recall, F1, false triggers/minute, missed events, detection delay, and coverage.
- Review every false positive and false negative by source clip.
- Verify the result adapter maps confirmed Leap to `AbilityEvent(source="vision")`.
- Prepare Week 4 integration backlog without claiming production readiness.

**Deliverable:** Week 3 final report, baseline/model comparison, and Week 4 backlog.

**Completion evidence:** held-out metrics, known limitations, test results, and reproducible experiment configuration.

---

## Technical decision rules

1. **Collect data before choosing the model.** Do not train on a handful of adjacent frames.
2. **Split by match/session.** Frames from one match must not leak into both training and test.
3. **Start with an OpenCV temporal baseline.** Reuse existing code and measure the simplest cues first.
4. **Treat pose estimation as a hypothesis.** COCO-trained pose models may not detect blocky Roblox avatars reliably.
5. **Do not confuse localization with action recognition.** A bounding box identifies where the Killer is; it does not prove Leap occurred.
6. **Use temporal evidence.** Leap is an action sequence, not just a static appearance.
7. **Score events, not just frames.** False cooldown starts are operationally costly.
8. **No hidden-state inference.** If the Killer is off-screen or fully occluded, screen-only CV cannot know the ability was used.
9. **Keep recordings local.** Avoid committing large/private gameplay recordings or uploading them without explicit review.
10. **Do not weaken safety constraints.** No process memory access, injection, hooks, executors, client modification, anti-cheat bypass, or automated gameplay input.

## Official documentation index

- OBS: https://obsproject.com/kb/
- FFmpeg: https://ffmpeg.org/ffmpeg.html
- OpenCV: https://docs.opencv.org/4.x/
- CVAT: https://docs.cvat.ai/
- Ultralytics: https://docs.ultralytics.com/
- MediaPipe: https://developers.google.com/edge/mediapipe
- scikit-learn: https://scikit-learn.org/stable/
- PyTorch: https://pytorch.org/docs/stable/
- Python: https://docs.python.org/3/
