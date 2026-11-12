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
- [ ] Run full test suite (Week 1 regression + Week 2 tests).
- [ ] Test overlay stacking, click-through, and mouse-look lock in Roblox.
- [ ] Measure CPU/RAM and game FPS impact with overlay visible vs hidden.
- [ ] Update documentation (`TODO.md`, `ARCHITECTURE.md`, `RISK.md`, `dataset/WEEK2_FINAL_REPORT.md`).
- [ ] Tag release `v0.2.0-week2` and prepare Week 3 detection backlog.

**Deliverable:** Integrated manual cooldown overlay prototype and Week 2 report.

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
