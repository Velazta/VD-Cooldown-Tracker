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
- [ ] Define `app_config.json` schema.
- [ ] Define `killer_database.json` schema.
- [ ] Add schema version.
- [ ] Implement JSON loading.
- [ ] Implement validation and readable error handling.
- [ ] Add The Hidden as the initial example record.
- [ ] Keep cooldown values editable and mark unverified values clearly.
- [ ] Confirm schema supports multiple killers.
- [ ] Document module boundaries.
- [ ] Create Week 2 UI/overlay backlog.

**Deliverable:** local configuration and extensible data model.

## Day 7 — Integration and Review
- [ ] Run capture-to-ROI pipeline end-to-end.
- [ ] Verify preview remains responsive.
- [ ] Verify stop/close behavior.
- [ ] Verify JSON load and invalid JSON handling.
- [ ] Review logs for errors.
- [ ] Review CPU/RAM/FPS results against targets.
- [ ] Record unresolved limitations.
- [ ] Update `PRD.md` if scope decisions changed.
- [ ] Update `ARCHITECTURE.md` if technical decisions changed.
- [ ] Prepare Week 1 demonstration.
- [ ] Create Week 2 tasks based on evidence.

**Deliverable:** Week 1 prototype, report, and review.

# Week 1 Acceptance Checklist
- [ ] Python environment can be recreated from documented steps.
- [ ] Capture obtains frames from intended Roblox configuration, or a blocker and fallback are documented.
- [ ] Preview updates continuously.
- [ ] ROI can be changed and previewed.
- [ ] OpenCV preprocessing runs on ROI frames.
- [ ] Capture FPS and processing FPS are measured separately.
- [ ] CPU and RAM are measured.
- [ ] Application shuts down cleanly.
- [ ] JSON configuration loads and validates.
- [ ] No injection, hooking, memory reading, or client modification exists.
- [ ] Test evidence and limitations are documented.

# Week 2 — Desktop Application and Overlay (Preview)
- [ ] Build main PySide6 application window.
- [ ] Add capture source/status panel.
- [ ] Add ROI calibration controls.
- [ ] Build transparent overlay window.
- [ ] Test always-on-top behavior.
- [ ] Test click-through behavior.
- [ ] Build circular cooldown indicator.
- [ ] Implement cooldown manager.
- [ ] Add manual timer start/reset.
- [ ] Connect JSON database to UI.
- [ ] Add overlay position and size settings.
- [ ] Integrate capture prototype with application lifecycle.

# Week 3 — Dataset and Initial Detection (Preview)
- [ ] Record representative The Hidden gameplay using OBS.
- [ ] Extract frames and timestamped clips.
- [ ] Annotate positive Leap states.
- [ ] Annotate hard negatives (normal attack, vault, stun, similar motion).
- [ ] Split data by independent recordings/matches.
- [ ] Establish template-matching baseline.
- [ ] Evaluate whether object detection is necessary.
- [ ] Train a model only if baseline is insufficient.
- [ ] Evaluate on unseen gameplay footage.
- [ ] Record precision, recall, false positives, and false negatives.

# Week 4 — Integration and Evaluation (Preview)
- [ ] Integrate detection output with cooldown manager.
- [ ] Add confidence threshold.
- [ ] Add temporal confirmation/debounce.
- [ ] Add duplicate-event suppression.
- [ ] Test missed detections and false positives.
- [ ] Test cooldown timer against observed events.
- [ ] Measure end-to-end latency.
- [ ] Measure game FPS impact.
- [ ] Run one-hour stability test.
- [ ] Fix critical issues.
- [ ] Prepare MVP evaluation report.

# Finalization (Preview)
- [ ] Package application for local use.
- [ ] Document installation and configuration.
- [ ] Document supported capture modes.
- [ ] Document known limitations.
- [ ] Prepare final demonstration.
