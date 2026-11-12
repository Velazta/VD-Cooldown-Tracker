# PRD — Week 3: Gameplay Dataset, Leap Recognition & CV Baseline

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 3 — Dataset & Initial Visual Detection  
**Schedule:** 23–29 November 2026  
**Target branch:** `dev`  
**Primary stack:** Python 3.14 (64-bit), OpenCV, NumPy, PySide6  
**Optional experiments:** Ultralytics YOLO Pose / object detection, MediaPipe (evaluation only)  
**Prerequisite:** Week 2 milestone completed on `dev`  
**Status:** Proposed execution specification

---

## 1. Week 2 Handover — Verified Baseline

This PRD is based on the repository's `dev` branch and the Week 2 completion artifacts:

- `TODO.md` marks Week 2 Day 8–14 complete.
- `dataset/WEEK2_FINAL_REPORT.md` reports 94/94 automated tests passing and release tag `v0.2.0-week2`.
- `cooldown/ability_event.py` defines a validated, source-neutral `AbilityEvent` contract, including `source="vision"`.
- `cooldown/cooldown_manager.py` implements trigger-aware monotonic cooldown state and duplicate-event suppression.
- `overlay/` provides the transparent overlay, circular indicator, and controller.
- `main.py` integrates capture, ROI, manual events, hotkeys, and overlay.
- Existing Week 1 capture, processing, database, settings, and monitoring modules remain the foundation.

The reported Week 2 results are repository-reported evidence, not a fresh independent benchmark in this review.

### 1.1 Do not rebuild

Week 3 must reuse:
- Capture backend and latest-frame buffer.
- ROI model/processor and preprocessing options.
- Existing template matcher and performance monitor.
- Killer/ability database and settings manager.
- `AbilityEvent`, `CooldownManager`, and overlay controller.

Only make focused changes when a verified integration requirement or defect justifies them.

### 1.2 Current gaps

- `detection/` currently contains only its package initializer; no detector implementation is present.
- `dataset/` contains Week 1/2 reports, benchmark artifacts, and ROI samples, but no curated Leap video dataset or annotation manifest is evidenced.
- `RISK.md` identifies skin variation and lack of a Survivor-facing Killer identity banner as unresolved challenges.
- The database's Leap cooldown value remains `cooldown_verified: false`; Week 3 must not present it as a confirmed game fact.

---

## 2. Product Objective

Build a repeatable, evidence-based visual dataset and a first detector prototype that can recognize **The Hidden — Leap** from the Survivor POV using only rendered screen frames.

Week 3 is primarily a data and feasibility milestone. It must establish:
1. What visual evidence distinguishes Leap from ordinary gameplay?
2. Whether the Killer can be localized reliably enough in the gameplay viewport.
3. Whether a temporal visual baseline can recognize the Leap action.
4. Whether pose/keypoint or learned detection is actually useful for this stylized game character.
5. What event timestamp and confidence can be emitted to the existing Week 2 event contract.

**Do not assume YOLO Pose is the answer.** Pretrained human-pose models are generally trained for human-like keypoints; a stylized/blocky Roblox avatar may not match their training domain. Evaluate their outputs on real footage before committing to annotation format, training, or dependencies.

## 3. Week 3 Objectives

By the end of the week:

1. Define a consistent recording and annotation protocol.
2. Record representative Survivor-POV footage containing Leap and hard-negative gameplay.
3. Preserve original recordings and extract reproducible timestamped frames/clips.
4. Build a dataset manifest with match/session-level provenance.
5. Annotate Leap phases and event onset; annotate Killer localization only where useful.
6. Split data by independent recording/session/match to prevent frame leakage.
7. Establish and measure at least one non-ML temporal CV baseline.
8. Evaluate candidate localization/pose models on actual Roblox footage.
9. Select a justified detector direction for Week 4.
10. Define a detector output adapter that can later emit the existing `AbilityEvent` without coupling detection to UI.

## 4. Scope

### 4.1 In scope

- OBS recording protocol for Survivor POV.
- Capture of multiple matches, camera distances/angles, lighting/map conditions, occlusions, and available The Hidden skin variations.
- Timestamped video metadata and event log.
- Frame/clip extraction with source timestamps retained.
- Annotation schema for action phase, event onset, visibility/occlusion, and optional bounding box.
- Hard-negative collection: idle, walking/running, ordinary jump/fall, vault, attack, stun/recovery, camera movement, other Killer actions, partial visibility, and no Killer visible.
- Dataset quality audit and session-level train/validation/test split.
- OpenCV baseline experiments: ROI crop/downscale, grayscale/contrast variants, template matching, silhouette/contour features, optical flow, and temporal trajectory features.
- Feasibility evaluation of object detection or pose/keypoint estimation on stylized avatars.
- Event-level evaluation: precision, recall, F1, false triggers per minute, missed events, and detection delay.
- Local dataset tools/scripts, documentation, and reproducible experiment records.
- A detector adapter/interface proposal compatible with `AbilityEvent`.

### 4.2 Out of scope

- Full production-grade AI or guaranteed perfect Leap recognition.
- Automatic multi-Killer support beyond a limited first-visual-contact feasibility experiment.
- Full cooldown timer/overlay redesign.
- Automated gameplay input, macros, or key injection.
- Roblox process memory access, injection, hooking, executors, client modification, or anti-cheat bypass.
- Cloud upload or hosted model inference.
- Mandatory YOLO training. Training is conditional on dataset quality and baseline evidence.
- Treating configured cooldown seconds as confirmed game truth.

---

## 5. Detection Problem Definition

### 5.1 User perspective and observable limits

The user operates from **Survivor POV**. Killer ability icons are not available on the Survivor HUD. The system must observe the Killer's visible 3D avatar/action in the central gameplay viewport.

Screen-only CV cannot know that Leap happened while the Killer is off-screen, fully occluded, outside the captured window, or visually indistinguishable from another action. Such cases must be labeled as unobservable/ambiguous, not silently treated as detector failures or inferred from hidden game state.

### 5.2 MVP event target

Initial target: **The Hidden — Leap**.

Recommended phase labels:
- `background`: ordinary gameplay / no Leap event.
- `leap_windup`: visually distinguishable preparation/start of Leap, if present.
- `leap_airborne`: Killer is in the Leap trajectory.
- `leap_landing_recovery`: landing/recovery phase, if visually distinguishable.
- `ambiguous`: evidence insufficient to assign a reliable phase.
- `not_visible`: Killer cannot be observed in the relevant viewport.

The annotation protocol must define the exact event-onset convention. Prefer the earliest frame where a human annotator can consistently identify the Leap action beginning. Record uncertainty when the onset is between two frames or obscured.

### 5.3 Hard negatives

Collect examples that could resemble Leap:
- Normal jump/fall and ordinary locomotion.
- Vaulting, climbing, falling from map geometry.
- Normal attack/weapon swing.
- Stun, knockback, recovery, or other animations.
- Sudden camera pitch/yaw changes.
- Killer partially occluded, distant, cropped, or entering/leaving frame.
- Other Killer abilities and other Killer identities where available.

### 5.4 First Visual Contact

Treat automatic Killer identity detection as a **secondary feasibility task**, not a dependency for Leap detection. Week 3 may test whether a first clear visual encounter can identify/lock The Hidden, but the detector must not assume the game provides a reliable Survivor HUD announcement.

---

## 6. Dataset Requirements

### 6.1 Recording protocol

Use OBS Studio or another user-controlled screen recorder. Record the game window/display externally. Keep original source videos unchanged.

For each recording, store:
- Unique recording/session ID.
- Date/time and game/map/session identifier where available.
- POV (must be Survivor for the primary dataset).
- Game display mode, resolution, and capture FPS.
- Available Killer skin/appearance notes.
- Camera distance/angle and visibility conditions.
- Recording filename, duration, codec/container, and checksum if practical.
- Event log with approximate Leap timestamps and annotator notes.

Do not upload raw gameplay footage to cloud tools by default. Keep it local and respect other players' privacy; avoid publishing usernames/voice/chat when not necessary.

### 6.2 Initial dataset target

Targets are planning goals, not permission to fabricate or over-sample near-identical frames:
- Aim for at least **20–30 distinct Leap events** across multiple independent matches/sessions.
- Aim for at least **30 minutes of hard-negative footage**.
- Include more than one camera distance/angle and lighting condition.
- Include multiple The Hidden appearances/skins if they are available during recording.
- Include examples where the Killer is partially visible, far away, or briefly occluded.
- If these targets cannot be reached, document the shortfall and narrow the claims. Do not duplicate frames to inflate dataset size.

The unit of diversity is the independent gameplay recording/match, not the number of extracted frames.

### 6.3 Dataset organization

Suggested structure (adapt to current repository conventions):

```text
dataset/
  raw_videos/                 # local-only; normally gitignored
  clips/
    leap_positive/
    hard_negative/
    ambiguous/
  frames/
    leap_windup/
    leap_airborne/
    leap_landing_recovery/
    background/
  annotations/
    events.csv
    frames.jsonl
    README.md
  splits/
    train_sessions.txt
    val_sessions.txt
    test_sessions.txt
  manifests/
    recordings.csv
    dataset_manifest.json
  experiments/
    baseline_results.csv
    model_comparison.md
```

Never commit large raw recordings or private footage to Git by default. Commit schemas, scripts, small permitted samples, and documentation. Document storage paths and checksums for local assets.

### 6.4 Annotation schema

At minimum, each event annotation should include:
- `recording_id`, `match_id`, `clip_id`.
- `event_label` and `phase`.
- `start_time_ms`, `end_time_ms`, and `onset_uncertainty_ms` where possible.
- `killer_visible`, `occlusion_level`, and `visibility_quality`.
- Optional normalized bounding box for Killer localization.
- `skin_or_appearance` if known.
- `annotator_id`, `annotation_version`, and notes.

Do not require skeletal keypoints for every frame until a pose model has demonstrated that its landmarks are meaningful on the game's stylized avatars. If custom keypoints are tested, define a consistent avatar-specific skeleton and document visibility/occlusion rules first.

### 6.5 Dataset split and leakage prevention

- Split by complete recording/session/match, never randomly by individual frames from the same match.
- A recording or match must appear in exactly one of train, validation, or test.
- Keep a held-out test set untouched during threshold/model tuning.
- Record split IDs and random seed.
- If data is too small for a stable three-way split, use session-grouped cross-validation and clearly label the result as preliminary.

---

## 7. Detection Strategy and Experiment Order

### Stage A — Data inspection before model selection

1. Review representative positive and negative clips manually.
2. Identify the visible cues that consistently precede/during Leap.
3. Check whether the Killer is sufficiently large and visible in the current ROI.
4. Determine whether a tighter ROI and downscaling preserve useful cues.
5. Record which skins, distances, camera angles, and occlusions break visual consistency.

### Stage B — Non-ML baseline first

Implement an offline/replay baseline using existing OpenCV components:
- Crop the existing gameplay ROI and optionally localize the candidate Killer region.
- Compare raw, grayscale, and carefully selected contrast normalization.
- Evaluate template matching only for stable visual cues; do not rely on RGB skin-specific templates as the only signal.
- Evaluate silhouette/contour or shape descriptors where backgrounds permit.
- Evaluate sparse optical flow / motion direction and temporal trajectory features.
- Use a temporal state machine/window to distinguish a multi-frame Leap sequence from a single-frame visual match.

All thresholds must be selected on validation sessions, not the held-out test set.

### Stage C — Learned-model feasibility gate

Only after reviewing the baseline:
- Test a small pretrained object detector on actual footage to see whether it can localize the stylized Killer.
- Test pretrained pose estimation only as a feasibility experiment. Record keypoint count, confidence, stability across frames/skins, and failure cases.
- A model trained on COCO human keypoints must not be assumed to understand Roblox blocky avatars.
- If custom pose annotation is justified, define an avatar-specific keypoint schema before collecting large-scale labels.
- Train a small custom detector/classifier only if there is sufficient independent labeled data and the baseline is inadequate.
- Review model package licensing before adding it as a project dependency or distributing a packaged application.

### Model-selection decision

Choose the simplest approach that meets the measured event-level requirements:
1. OpenCV temporal baseline if it is sufficiently discriminative.
2. Object detector + temporal event classifier if localization is the primary failure point.
3. Custom pose/keypoint model only if avatar landmarks are consistently observable and materially improve Leap discrimination.
4. Do not select YOLO solely because it is popular or because a training tutorial exists.

---

## 8. Functional Requirements

### FR-W3-01 — Recording and Provenance

- Define a repeatable OBS recording protocol.
- Store recording metadata and session IDs.
- Preserve source videos and source timestamps.
- Keep raw recordings local and out of Git unless explicitly approved.

**Acceptance criteria**
- [ ] Recording instructions are documented.
- [ ] Each recording has a unique ID and metadata row.
- [ ] Positive Leap and hard-negative examples are present, or the shortfall is documented.
- [ ] Original footage can be traced to each extracted clip/frame.

### FR-W3-02 — Extraction and Annotation

- Implement or document reproducible frame/clip extraction.
- Preserve frame timestamps and source recording IDs.
- Define annotation labels, event onset, ambiguity, visibility, and optional bounding box.
- Provide a compact annotation guide and schema.

**Acceptance criteria**
- [ ] Extraction can be repeated from the same source video.
- [ ] Annotation schema validates.
- [ ] At least a pilot set of positive and negative clips is annotated.
- [ ] Ambiguous/off-screen events are explicitly labeled.
- [ ] Annotation examples and edge cases are documented.

### FR-W3-03 — Dataset Quality and Split

- Build a recording manifest and dataset summary.
- Detect missing files, duplicate frames, invalid timestamps, and inconsistent labels.
- Split by independent sessions/matches.
- Keep the test split isolated from tuning.

**Acceptance criteria**
- [ ] Every clip/frame has a source recording ID.
- [ ] No match/session leaks across splits.
- [ ] Class/phase counts and recording diversity are reported.
- [ ] Dataset limitations and imbalance are documented.

### FR-W3-04 — OpenCV Temporal Baseline

- Use existing capture/ROI/preprocessing abstractions where practical.
- Build an offline replay experiment so the same clips can be evaluated repeatedly.
- Evaluate at least two candidate visual cues/approaches.
- Include a temporal confirmation window rather than triggering on one isolated frame.
- Log predictions, confidence/score, event timestamps, and processing latency.

**Acceptance criteria**
- [ ] Baseline can replay labeled clips deterministically.
- [ ] Results are measured on validation and held-out test sessions.
- [ ] False positives and missed events are inspectable by clip/time.
- [ ] Baseline limitations across skin, distance, angle, and occlusion are documented.

### FR-W3-05 — Learned Model / Pose Feasibility Evaluation

- Test pretrained object detection or pose estimation only on actual project footage.
- Compare results with the OpenCV baseline.
- Do not add heavyweight dependencies to the production requirements unless the experiment justifies them.
- If training is attempted, document data split, model/version, hyperparameters, seed, hardware, and artifacts.

**Acceptance criteria**
- [ ] Feasibility report contains representative successes and failures.
- [ ] Pose model is rejected if landmarks are unstable or not meaningful on blocky avatars.
- [ ] Any training uses session-level split and held-out test footage.
- [ ] A decision is recorded: baseline-only, detector + temporal classifier, or custom pose path.

### FR-W3-06 — Detector Event Adapter Contract

Define a detector output that can be converted to the existing Week 2 event interface.

Conceptual output:

```python
DetectionResult(
    killer_id="the_hidden",
    ability_id="leap",
    event_type="cast_start",
    timestamp=<monotonic_event_time>,
    confidence=0.0_to_1.0,
    source="vision",
    evidence_id="recording_id:clip_id"
)
```

The adapter shall:
- Validate target IDs and event type.
- Use monotonic timestamps compatible with `AbilityEvent`.
- Avoid importing overlay widgets.
- Not call the cooldown manager directly from image-processing code; emit a normalized result/event through a clear boundary.
- Include an evidence reference for debugging and evaluation.

**Acceptance criteria**
- [ ] Detector result can be mapped to `AbilityEvent(source="vision")`.
- [ ] Existing manual/hotkey event paths remain unchanged.
- [ ] No detector output directly manipulates Qt widgets.
- [ ] Event timestamp convention is documented and tested.

---

## 9. Day-by-Day Execution Plan

### Day 1 — Recording Protocol & Dataset Design (23 Nov)

Tasks:
- Review Week 2 handover and current open risks RSK-20261120-17/18.
- Inspect existing `dataset/roi_samples` and determine whether any samples are reusable.
- Define recording IDs, metadata fields, event log format, and local storage policy.
- Define Leap phase labels and event-onset convention.
- Write OBS recording protocol and annotation guide.
- Decide initial recording matrix: camera distance, angle, map lighting, skin/appearance, visibility.

**Deliverable:** recording protocol, annotation schema, dataset manifest template.

### Day 2 — Gameplay Recording (24 Nov)

Tasks:
- Record Survivor POV sessions containing The Hidden where available.
- Capture distinct Leap events and long hard-negative segments.
- Include normal jumps, vaults, attacks, falls, camera motion, occlusion, and off-screen conditions.
- Record approximate event timestamps while the session is fresh.
- Keep original footage local and unchanged.

**Deliverable:** first batch of indexed raw recordings and event logs.

### Day 3 — Clip/Frame Extraction & Pilot Annotation (25 Nov)

Tasks:
- Build a repeatable extraction script or documented FFmpeg workflow.
- Extract event-centered clips and selected background/hard-negative intervals.
- Preserve original timestamps and recording IDs.
- Annotate a pilot batch with phase, onset, visibility, ambiguity, and optional Killer bounding box.
- Review annotation consistency and refine label definitions.

**Deliverable:** pilot clips/frames, annotation schema, and annotation guide.

### Day 4 — Dataset Audit & Split (26 Nov)

Tasks:
- Generate dataset summary by session, phase, appearance, and visibility.
- Check duplicate frames, corrupt clips, invalid timestamps, and missing annotations.
- Split by independent session/match, not by frame.
- Lock a held-out test session list.
- Record class imbalance and collection gaps.

**Deliverable:** versioned dataset manifest, split files, and quality report.

### Day 5 — OpenCV Temporal Baseline (27 Nov)

Tasks:
- Build an offline replay harness using the existing ROI and processing modules where appropriate.
- Establish a simple baseline with stable visual cues.
- Evaluate template matching limitations across skins and scales.
- Test motion/trajectory cues using optical flow or frame-difference features.
- Add temporal confirmation and event onset estimation.
- Measure event-level precision, recall, F1, false triggers per minute, detection delay, and processing time.

**Deliverable:** reproducible OpenCV baseline and validation report.

### Day 6 — Model Feasibility & Comparison (28 Nov)

Tasks:
- Evaluate pretrained object detection and/or pose estimation on representative real footage.
- Check whether the model actually detects blocky/stylized Killer avatars and whether keypoints remain stable.
- Compare model outputs with the OpenCV baseline on the same validation clips.
- Train only if dataset size/quality and baseline results justify it.
- Review licensing and runtime cost before adding dependencies.
- Record the model-selection decision and unresolved risks.

**Deliverable:** model feasibility comparison and Week 4 detector direction.

### Day 7 — Week 3 Evaluation & Handover (29 Nov)

Tasks:
- Run the baseline and any candidate model on the held-out test sessions.
- Review false-positive and false-negative clips manually.
- Report event-level metrics and per-condition weaknesses.
- Confirm the detector-to-`AbilityEvent` adapter contract.
- Update `TODO.md`, `RISK.md`, `ARCHITECTURE.md`, and dataset documentation.
- Prepare Week 4 integration tasks; do not claim production readiness.

**Deliverable:** Week 3 dataset + baseline milestone report, experiment artifacts, and Week 4 backlog.

---

## 10. Evaluation Metrics

Report metrics at the **event level**, not only per-frame accuracy.

| Metric | Definition / purpose |
|---|---|
| Precision | Of emitted Leap events, how many correspond to real annotated Leap events. |
| Recall | Of annotated observable Leap events, how many were detected. |
| F1 | Harmonic mean of precision and recall. |
| False triggers/minute | Operational cost of false cooldown starts during hard-negative footage. |
| Missed events | Observable Leap events with no matching detector event. |
| Detection delay | Time from annotated Leap onset to detector confirmation. |
| Processing latency | Time spent processing a frame/window, separate from event delay. |
| Coverage | Fraction of annotated events where the Killer was sufficiently visible to evaluate. |

Define an event matching tolerance before scoring (for example, a bounded window around annotated onset) and keep it consistent across experiments. Report the chosen tolerance and onset uncertainty.

Do not let high frame-level accuracy hide poor event-level recall or frequent false cooldown starts.

### Week 3 planning targets

These are pilot targets for deciding whether the approach is promising, not a production guarantee:
- Obtain a pilot dataset with at least 20 distinct Leap events where feasible.
- Achieve a reproducible baseline evaluation on held-out sessions.
- Target precision ≥ 0.90 and recall ≥ 0.75 on observable test events as an initial feasibility gate; report actual values even if lower.
- Record false triggers per minute and event detection delay; do not hide poor results behind aggregate accuracy.
- Keep detector processing within the existing frame-processing budget where feasible; measure rather than assume.

If dataset volume or visibility makes these targets statistically unreliable, report the limitation and use Week 4 to collect more data rather than overfit.

---

## 11. Architecture and Suggested Module Boundaries

Reuse existing modules. Add responsibilities incrementally:

```text
detection/
  __init__.py
  detection_result.py       # Detector-neutral result contract
  leap_detector.py          # First baseline interface/implementation
  temporal_validator.py     # Multi-frame event confirmation
  event_adapter.py          # Maps confirmed result to AbilityEvent

dataset/
  README.md
  annotations/
    schema.json
    events.csv
    annotation_guide.md
  manifests/
    recordings.csv
    dataset_manifest.json
  splits/
    train_sessions.txt
    val_sessions.txt
    test_sessions.txt
  experiments/
    baseline_results.csv
    model_comparison.md
  scripts/
    extract_frames.py
    validate_dataset.py
    summarize_dataset.py
```

Potential data flow:

```text
Existing Capture Engine
  -> Latest Frame Buffer
  -> Existing ROI Processor
  -> Lightweight Visual Features / Candidate Localization
  -> Temporal Validator
  -> DetectionResult
  -> Event Adapter
  -> AbilityEvent(source="vision")
  -> Existing CooldownManager (Week 4 integration)
  -> Existing Overlay
```

Week 3 may validate the event adapter with offline/replay data. Full live detector-to-cooldown integration belongs to Week 4 unless the baseline is already stable and a small isolated integration test is useful.

### Boundary rules

- Dataset tooling must not be imported into the production UI startup path.
- Offline evaluation must be deterministic and replayable.
- Detector modules must not import overlay widgets.
- The detector must not assume the Killer is always visible.
- Keep raw footage out of Git and out of cloud services by default.
- Keep capture and cooldown lifecycle ownership in their existing modules.

---

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Skin/weapon variation | Static templates fail across appearances | Prefer motion/shape/temporal cues; test per appearance. |
| Survivor camera movement | False motion detections | Include camera-motion negatives; compensate or use local relative motion. |
| Killer off-screen/occluded | Impossible visual inference | Label unobservable; do not emit event without evidence. |
| Similar animations | False Leap triggers | Hard-negative dataset and temporal confirmation. |
| Too few independent events | Overfitting / unreliable metrics | Expand sessions; avoid frame-level random split. |
| Pretrained pose model domain mismatch | Missing/unstable keypoints | Treat as feasibility experiment; reject if not robust. |
| Heavy model impacts FPS | Gameplay performance loss | Offline test first; profile ROI, resolution, inference rate, and CPU/GPU. |
| Timestamp mismatch | Cooldown starts late/early | Define source timestamps and monotonic conversion carefully. |
| Cooldown value unverified | Displayed timer may not match game | Keep unverified marker and editable data; verify separately. |

---

## 13. Safety, Privacy, and Data Handling

Allowed:
- OBS or standard external screen recording.
- Local frame extraction and local CV.
- Local annotations and model experiments.
- External visual observation of rendered game output.

Prohibited:
- Roblox process memory reading.
- DLL injection, hooking, executor APIs, or client modification.
- Anti-cheat bypass or capture evasion.
- Automated gameplay inputs/macros.
- Uploading gameplay footage to cloud services without explicit user decision and privacy review.

A transparent overlay or screen capture does not guarantee platform-policy approval. Do not make safety or account-risk guarantees.

---

## 14. Definition of Done — Week 3

Week 3 is complete when:

### Dataset
- [ ] Recording and annotation protocol is documented.
- [ ] Raw sessions are indexed with metadata and kept local.
- [ ] Positive Leap and hard-negative clips are collected, or shortfall is documented.
- [ ] Annotation schema and event-onset convention are documented.
- [ ] Pilot annotations are reviewed for consistency.
- [ ] Dataset splits are grouped by session/match with no leakage.
- [ ] Dataset quality and limitations report exists.

### Baseline and feasibility
- [ ] Offline replay baseline runs reproducibly.
- [ ] At least two visual cue approaches are compared.
- [ ] Event-level metrics are reported on held-out sessions.
- [ ] False-positive and missed-event examples are reviewed.
- [ ] Object detection/pose feasibility is evaluated on actual Roblox footage.
- [ ] A justified model-selection decision is recorded.

### Integration readiness
- [ ] Detector-neutral result contract is documented.
- [ ] Confirmed result maps to `AbilityEvent(source="vision")`.
- [ ] Existing manual/hotkey and cooldown/overlay flows remain unchanged.
- [ ] Week 4 integration backlog is ready.

### Documentation
- [ ] `TODO.md`, `RISK.md`, `ARCHITECTURE.md`, and dataset docs reflect verified results.
- [ ] Experiment parameters, dataset split IDs, and limitations are reproducible.

---

## 15. Week 4 Handover

Week 4 should integrate the selected detector with the existing cooldown pipeline, add confidence thresholds and temporal debounce, suppress duplicate visual events, measure end-to-end latency, evaluate game FPS impact, and run sustained stability tests.

Week 4 must not silently promote an experimental model to production if Week 3 evidence shows poor generalization. If data is insufficient, prioritize collection and a narrower observable-event claim.
