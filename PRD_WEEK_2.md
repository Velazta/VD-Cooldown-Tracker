# PRD — Week 2: Cooldown State Machine & Transparent Overlay

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 2 — Desktop Application, Cooldown Logic & Overlay  
**Schedule:** 16–22 November 2026  
**Primary stack:** Python 3.14 (64-bit), PySide6, OpenCV, NumPy  
**Persistence:** Existing local JSON configuration/database  
**Target branch:** dev  
**Status:** Proposed execution specification  
**Prerequisite:** Week 1 Foundation & Technical Feasibility completed

---

## 1. Week 1 Handover and Verified Baseline

This PRD is based on the repository's **dev** branch, not main. The Week 1 checklist in `TODO.md` marks Day 1–7 and the Week 1 acceptance checklist complete.

### 1.1 Existing capabilities — do not rebuild

The following foundations already exist in the dev branch:

- Python environment, project structure, logging, and configuration.
- MSS/Win32 GDI BitBlt capture implementation behind a capture interface.
- Background capture worker, frame timestamps/dimensions, bounded latest-frame buffer, capture status and clean-shutdown handling.
- PySide6 capture/preview application in `main.py`.
- ROI model, coordinate validation/clamping, cropping, bounding-box preview, and settings persistence.
- OpenCV preprocessing modes: RAW, GRAYSCALE, CLAHE, THRESHOLD, and CANNY.
- Template matching baseline using `TM_CCOEFF_NORMED`.
- Killer/ability JSON database with strongly typed models and validation.
- Settings manager and performance telemetry for capture/processing FPS, latency, CPU, and RAM.
- Unit tests for capture buffer, ROI, and database modules.

Week 2 must **extend and refactor only where needed**, not recreate the capture panel, ROI controls, database manager, or performance monitor.

### 1.2 Important Week 1 decisions

1. The user operates the application from a **Survivor POV**. Killer ability icons are not available in the Survivor HUD.
2. The initial visual detection target is therefore the **3D Killer pose/action animation in the central gameplay viewport**, not a HUD cooldown icon.
3. Week 1 records a major performance concern: CLAHE over a 1280×780 ROI was measured at approximately 54 ms/frame in the risk register. Do not run expensive preprocessing by default in Week 2; localized processing/downscaling is a Week 3 investigation.
4. The database already includes `trigger_type` values such as `on_cast_start` and `on_release`. Week 2 cooldown logic must preserve and use this distinction.
5. Cooldown values in the database are explicitly unverified. Treat them as editable configuration, not authoritative game facts.
6. The current code/config contains naming drift worth resolving carefully: the configured backend label says `windows_capture`, while the active implementation class is `MSSWindowsCapture`. Do not change a working backend merely to make the label look different; align the label/documentation with the actual implementation and test behavior.

### 1.3 Week 1 performance/risk evidence recorded in repository

The current `RISK.md` records:
- MSS capture throughput around 29.5–35.4 FPS and capture latency around 11.1–16.9 ms in the stated test conditions.
- Application RAM around 38.6–85.6 MB in the recorded benchmark.
- A game FPS reduction from 174 to 89 FPS in one full-frame capture/scaling scenario, with ROI and preview optimizations applied afterward.
- CLAHE at approximately 54 ms/frame on a 1280×780 region.
- Clean shutdown, bounded buffer behavior, target-lost handling, UI responsiveness, and strict JSON validation recorded as closed/verified risks.

These are repository-reported measurements, not a new independent benchmark performed during this review. Week 2 should preserve the measurement method and record any new comparisons separately.

---

## 2. Purpose

Week 2 converts the existing Week 1 technical prototype into a usable companion application with a separate transparent overlay and a reliable cooldown state machine.

The primary integration path is:

**Existing PySide6 Application → Select Killer/Ability → Manual or Simulated Trigger → Cooldown State Machine → Transparent Overlay → READY**

Week 2 validates the complete timer/overlay path using manual test controls. Automatic recognition of Killer poses and ability animations is a Week 3/4 objective, not a Week 2 deliverable.

## 3. Objectives

By the end of Week 2:

1. Preserve and improve the existing application rather than replacing it.
2. Provide a standalone cooldown state machine independent of Qt widgets.
3. Interpret each ability's configured `trigger_type`.
4. Implement a transparent, independently controlled overlay.
5. Display ability identity, cooldown progress, remaining time, and READY state.
6. Connect the existing JSON database to cooldown selection.
7. Add manual controls for repeatable integration testing and fallback use.
8. Test overlay stacking, click-through, persistence, timing, and shutdown on the actual Windows/Roblox setup.
9. Prepare a clean interface for Week 3's visual event detector.

## 4. Scope

### 4.1 In scope

- Review and preserve current `main.py` capture/ROI/database/telemetry features.
- Refactor application composition only as needed to separate UI coordination from business logic.
- Standalone cooldown manager/state machine.
- Support for configured `trigger_type`: `on_cast_start`, `on_release`, and any other explicitly supported database value.
- Ability selection from existing `DatabaseManager`.
- Manual trigger controls to simulate the event types for tests.
- Transparent, frameless, always-on-top overlay.
- Configurable overlay visibility, position, dimensions, opacity, and click-through preference.
- Circular/radial cooldown progress indicator, remaining time, ability name, and READY state.
- Persistence through the existing settings architecture, without mixing app settings into the killer database.
- Unit tests, GUI integration tests, manual Windows tests, and documentation updates.
- A detector-facing event interface that Week 3 can call without importing UI classes.

### 4.2 Out of scope

- Automatic Killer identification.
- Automatic Leap/Mark/Through The Veil recognition.
- YOLO training, PyTorch training, OCR, or dataset annotation.
- Claiming that the cooldown timer reflects hidden server-side game state.
- Multi-slot/multi-killer simultaneous timers unless the single-slot implementation is stable and there is a demonstrated requirement.
- Cloud synchronization, online APIs, installer/production packaging.
- Game process memory reading, injection, hooking, executor APIs, client modification, anti-cheat bypass, or automated gameplay input/macros.

## 5. User Flow and Use Cases

| ID | Use case | Expected result |
|---|---|---|
| UC-W2-01 | Launch tracker | Existing capture/ROI application opens and loads validated settings/database. |
| UC-W2-02 | Select active Killer | Killer selection uses existing database records. |
| UC-W2-03 | Select ability | Enabled abilities appear with duration and verification status. |
| UC-W2-04 | Show/hide overlay | Overlay visibility is controlled independently of main panel. |
| UC-W2-05 | Configure overlay | Position, size, opacity, and click-through preference are applied and persisted. |
| UC-W2-06 | Simulate cast start | Ability configured as `on_cast_start` begins cooldown at simulated cast-start event. |
| UC-W2-07 | Simulate release | Ability configured as `on_release` begins cooldown only when simulated release event is sent. |
| UC-W2-08 | Reset/cancel timer | Timer returns to a deterministic state. |
| UC-W2-09 | Cooldown expires | Overlay transitions to READY. |
| UC-W2-10 | Exit application | Overlay, timers, and existing capture worker shut down cleanly. |

## 6. Functional Requirements

### FR-W2-01 — Preserve Existing Application and Capture Pipeline

The existing `main.py` already provides capture controls, preview, metrics, Killer selection, ROI configuration, preprocessing selection, snapshot saving, and settings/database integration.

Week 2 shall:
- Preserve these capabilities during integration.
- Avoid replacing the existing main window with a reduced prototype.
- Keep capture lifecycle under the existing capture engine/controller.
- Ensure the overlay and cooldown timer do not block capture preview or Qt event processing.
- Correct only verified defects or inconsistencies.

**Acceptance criteria**
- [ ] Existing capture Start/Stop still works.
- [ ] Existing full-frame and ROI previews still work.
- [ ] Existing database/Killer selection still works.
- [ ] Existing capture/processing metrics remain available.
- [ ] UI remains responsive while capture is active and overlay is visible.
- [ ] No duplicate capture engine/worker is introduced.

### FR-W2-02 — Cooldown State Machine

Implement a standalone module under `cooldown/`, independent of PySide6.

Minimum states:
- `READY`: no active cooldown.
- `WAITING_FOR_RELEASE`: an ability with `on_release` trigger has entered its pre-release/cast phase; cooldown has not started.
- `COOLDOWN`: cooldown timer is active.
- `DISABLED/INVALID`: optional error representation for disabled/malformed ability data; do not treat as a gameplay state.

Required operations:
- Select/load ability configuration by Killer ID and Ability ID.
- Receive a normalized ability event.
- Start cooldown only when the received event matches the ability's configured trigger.
- Return remaining time and normalized progress.
- Reset, cancel, and clear state.
- Emit state changes through a UI-agnostic callback/signal boundary.

Timer requirements:
- Use `time.monotonic()` or an equivalent monotonic source.
- Store an end timestamp and calculate remaining time from elapsed time; do not decrement a counter by one each UI tick.
- Prevent duplicate event notifications from restarting an active timer.
- Validate positive cooldown duration and ability enabled state.
- Keep duration sourced from the database; do not hard-code game cooldowns.

**Trigger semantics**
- `on_cast_start`: begin cooldown when a confirmed cast-start event is delivered.
- `on_release`: do not begin cooldown at aim/stance start; begin only when a release event is delivered.
- Unknown trigger values must fail safely with a readable validation/error result. Do not silently reinterpret them.

**Acceptance criteria**
- [ ] Cooldown manager runs in unit tests without creating QApplication/QWidget.
- [ ] READY → COOLDOWN → READY works.
- [ ] `on_cast_start` starts only on cast-start event.
- [ ] `on_release` waits for release event and does not start early.
- [ ] Duplicate events do not create duplicate/restarted timers.
- [ ] Reset/cancel behavior is deterministic.
- [ ] Invalid, disabled, or missing ability data is handled safely.
- [ ] Timer remains accurate through a sustained test using monotonic timestamps.

### FR-W2-03 — Normalized Ability Event Interface

Define a small UI-independent event contract for future integration with Week 3 detection.

Suggested conceptual payload:

```python
AbilityEvent(
    killer_id="the_hidden",
    ability_id="leap",
    event_type="cast_start",
    timestamp=time.monotonic(),
    confidence=1.0,
    source="manual"
)
```

Requirements:
- Manual controls in Week 2 shall emit the same normalized event contract expected from a future detector.
- Event types must be explicit, e.g. `cast_start` and `release`.
- Keep event source metadata, such as `manual` or future `vision`, for logs/debugging.
- Confidence may be optional for manual events and required/validated for future vision events.
- The cooldown manager must not import OpenCV or depend on detector internals.

**Acceptance criteria**
- [ ] Manual cast-start/release controls create normalized events.
- [ ] Event payload identifies Killer, ability, event type, timestamp, and source.
- [ ] Cooldown manager consumes events without knowing whether they came from UI or CV.
- [ ] A future detector can call the same interface without changing overlay rendering code.

### FR-W2-04 — Transparent Overlay Window

Create a separate PySide6 overlay window.

Required behavior:
- Frameless and transparent background outside visible UI.
- Always-on-top where supported.
- Independent show/hide.
- Configurable position and size.
- Configurable opacity.
- Optional click-through mode.
- No capture, inference, or expensive image processing in paint/update routines.

Platform note:
Qt flags such as transparent-for-mouse-events do not automatically guarantee desktop-level click-through in all Windows/game configurations. Test on the actual Roblox display mode. Do not use injection, hooks, process manipulation, or anti-cheat bypass to force behavior.

**Acceptance criteria**
- [ ] Overlay is independently shown/hidden.
- [ ] Transparent area reveals the game behind it.
- [ ] Always-on-top behavior is verified in the supported Roblox mode.
- [ ] Position and size are configurable.
- [ ] Opacity is configurable and persisted.
- [ ] Click-through behavior is tested and documented, including unsupported conditions.
- [ ] When click-through is reported as enabled, gameplay input is not intercepted in the tested configuration.

### FR-W2-05 — Cooldown Indicator

The overlay shall show one active ability timer for the Week 2 MVP.

Minimum display:
- Killer/ability name.
- Circular or radial progress indicator.
- Remaining time in seconds.
- READY state when expired.
- Optional unverified-data marker or tooltip so users can distinguish configured cooldown data from verified data.

Requirements:
- Progress derives from cooldown manager state.
- UI refresh cadence is independent of timer accuracy.
- Repainting must not change the timer's end timestamp.
- No timer value is presented as authoritative game state.

**Acceptance criteria**
- [ ] Manual trigger visibly starts the correct ability timer.
- [ ] Remaining time updates smoothly enough to read.
- [ ] Progress reaches completion and READY appears at expiration.
- [ ] UI refresh does not restart or extend the timer.
- [ ] Unverified cooldown data remains identifiable in the UI or supporting settings.

### FR-W2-06 — Existing Database Integration

Use `database/killerDatabase.json` and the existing `DatabaseManager`.

The database already models:
- Killer and ability stable IDs.
- `cooldown_seconds`.
- `cooldown_verified`.
- `enabled`.
- `trigger_type`.
- `interact_input`.
- `detection_method`.

Requirements:
- Populate Killer/ability selection from validated database records.
- Respect disabled abilities.
- Resolve timer duration and trigger behavior from the selected ability.
- Do not create a parallel JSON schema.
- Do not silently change existing records or cooldown values.
- Treat all currently unverified values as configurable, unverified data.

**Acceptance criteria**
- [ ] The Hidden and Veil records load from the existing database.
- [ ] Leap and other enabled abilities are selectable.
- [ ] Ability selection resolves the exact configured trigger and duration.
- [ ] Invalid JSON/schema is reported through the existing database error boundary.
- [ ] Editing a valid record changes behavior without editing cooldown-manager source code.

### FR-W2-07 — Overlay Settings Persistence

Extend the existing settings model/manager instead of creating a second settings file without a clear reason.

Minimum persisted settings:
- Overlay visible preference.
- Overlay x/y position.
- Overlay width/height.
- Overlay opacity.
- Always-on-top preference.
- Click-through preference.
- Selected Killer/ability if useful.

Requirements:
- Validate values on load.
- Use safe defaults when fields are missing.
- Keep overlay settings separate from killer ability data.
- Avoid overwriting unrelated app/capture/ROI settings.

**Acceptance criteria**
- [ ] Overlay settings load on startup.
- [ ] Changes persist after normal close/restart.
- [ ] Invalid values are rejected or replaced with documented defaults.
- [ ] Existing capture/ROI settings remain intact after saving overlay settings.

### FR-W2-08 — Lifecycle and Error Handling

The application shall:
- Stop overlay UI timers on shutdown.
- Close/hide overlay cleanly.
- Preserve existing capture worker shutdown behavior.
- Avoid duplicate Qt timers or repeated signal connections.
- Handle missing/invalid ability selection safely.
- Avoid leaving background threads/processes running.

**Acceptance criteria**
- [ ] Repeated show/hide does not create duplicate overlay windows.
- [ ] Repeated manual start/reset does not create duplicate timer loops.
- [ ] Closing while capture is active shuts down capture cleanly.
- [ ] Closing while cooldown is active exits cleanly.
- [ ] Repeated launch/close cycles do not leave the application running.

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Timing accuracy | Monotonic end timestamp; no accumulated tick drift. |
| Responsiveness | Main Qt event loop remains responsive with capture and overlay active. |
| Performance | Overlay rendering and timer refresh should add minimal overhead; measure actual results. |
| Resource use | Do not add unbounded frame/timer/event histories. |
| Reliability | Repeated show/hide, start/reset, and capture lifecycle actions are safe. |
| Maintainability | Cooldown state machine, overlay rendering, database, and capture remain separated. |
| Compatibility | Windows 10/11 64-bit; test the Roblox display mode actually used. |
| Privacy | Local processing; no gameplay frame upload or cloud requirement. |
| Safety | External visual observation only; no Roblox process interaction or gameplay automation. |

Week 2 should record a baseline comparison with overlay hidden and visible. Do not assume Week 1 performance targets are automatically preserved after adding UI components.

---

## 8. Proposed Architecture and Module Boundaries

Reuse the existing modules. Add only the following Week 2 responsibilities:

```text
app/
  main_window.py              # Optional extraction from current main.py if justified
  settings.py                 # Extend existing AppConfig/SettingsManager

cooldown/
  __init__.py
  cooldown_manager.py         # UI-independent state machine
  cooldown_state.py           # State and immutable status model
  ability_event.py            # Normalized event contract

overlay/
  __init__.py
  overlay_window.py           # Transparent top-level window
  cooldown_widget.py          # Circular/radial display
  overlay_controller.py       # Connects cooldown state to overlay

tests/
  test_cooldown_manager.py
  test_ability_event.py
  test_overlay_settings.py
  test_cooldown_integration.py
```

Expected flow:

```text
Existing Main Application
  |-- Existing Capture Engine -> Latest Frame -> Existing ROI/Preprocessing
  |-- Existing Database Manager -> Selected Ability Configuration
  |-- Manual Test Control -> Normalized Ability Event
                                  |
                                  v
                           Cooldown State Machine
                                  |
                                  v
                           Overlay Controller
                                  |
                                  v
                           Transparent Overlay
```

Boundary rules:
- Cooldown manager must not import PySide6 widgets.
- Overlay must not own capture lifecycle.
- Main window coordinates components; it must not contain the timer state machine.
- Future CV detector must emit normalized ability events rather than directly starting a QWidget timer.
- Existing capture, ROI, preprocessing, database, and monitoring modules remain authoritative.

---

## 9. Day-by-Day Execution Plan

### Day 1 — Week 1 Handover and Cooldown Design (16 Nov)

Tasks:
- Review current dev branch implementation and run existing Week 1 tests.
- Confirm existing database fields and actual trigger values.
- Design cooldown states and normalized ability-event contract.
- Define behavior for `on_cast_start` and `on_release`.
- Decide whether current main.py needs small extraction/refactoring; avoid broad rewrite.
- Add Week 2 module skeleton and tests first.

Deliverable:
- Cooldown state/event design documented.
- Existing Week 1 functionality regression-tested.
- Week 2 module boundaries agreed.

### Day 2 — Cooldown State Machine (17 Nov)

Tasks:
- Implement READY, WAITING_FOR_RELEASE, and COOLDOWN behavior as required.
- Implement monotonic timing.
- Implement event matching by Killer ID, ability ID, and trigger type.
- Implement reset/cancel/expiration and duplicate-event suppression.
- Add unit tests for valid and invalid event sequences.

Deliverable:
- Standalone tested cooldown manager.

### Day 3 — Overlay Window Foundation (18 Nov)

Tasks:
- Create separate frameless transparent overlay.
- Implement always-on-top and show/hide.
- Implement position, size, and opacity.
- Test on desktop and actual Roblox display mode.
- Investigate click-through behavior and record exact outcome.

Deliverable:
- Transparent overlay prototype independent of cooldown logic.

### Day 4 — Cooldown Widget (19 Nov)

Tasks:
- Build circular/radial progress indicator.
- Display selected ability name and remaining time.
- Display READY state.
- Connect widget through overlay controller to cooldown manager.
- Ensure rendering does not perform capture/CV work.

Deliverable:
- Overlay renders cooldown manager state correctly.

### Day 5 — Main Application Integration and Manual Events (20 Nov)

Tasks:
- Add manual cast-start and release test controls to existing application.
- Connect Killer/ability selection to normalized ability events.
- Connect cooldown manager to overlay controller.
- Preserve existing capture/ROI/preview/telemetry controls.
- Test Leap's configured `on_cast_start` flow and an `on_release` example from the database.

Deliverable:
- End-to-end manual trigger → cooldown → overlay flow.

### Day 6 — Settings Persistence and Reliability (21 Nov)

Tasks:
- Extend existing settings model with overlay configuration.
- Persist and restore position, size, opacity, visibility, always-on-top, and click-through preference.
- Validate settings and preserve existing capture/ROI configuration.
- Test malformed/missing settings and database records.
- Test duplicate timer/signal prevention and application shutdown.

Deliverable:
- Overlay configuration persists and application lifecycle remains stable.

### Day 7 — Integration, QA, and Week 2 Review (22 Nov)

Tasks:
- Run full manual end-to-end demonstration.
- Run existing Week 1 regression tests plus all Week 2 tests.
- Test overlay with Roblox in the target display mode.
- Test click-through and always-on-top behavior.
- Measure CPU/RAM/game FPS with overlay hidden and visible.
- Run a sustained combined capture + overlay test.
- Update TODO, ARCHITECTURE, RISK, README, and PRD with verified results.
- Prepare Week 3 dataset/detection tasks around Survivor POV and 3D Killer animation.

Deliverable:
- Integrated manual cooldown overlay prototype.
- Test evidence, limitations, and Week 3 readiness report.

---

## 10. Definition of Done — Week 2

Week 2 is complete only when all required items below have implementation and test evidence.

### Cooldown state machine
- [ ] Cooldown manager is independent of PySide6.
- [ ] Monotonic timing is implemented and unit-tested.
- [ ] `on_cast_start` behavior is correct.
- [ ] `on_release` behavior is correct.
- [ ] Duplicate events do not restart an active timer.
- [ ] Reset/cancel/expiration behavior passes tests.
- [ ] Database values and verification flags are respected.

### Overlay
- [ ] Separate transparent overlay works.
- [ ] Show/hide and always-on-top are tested.
- [ ] Position, size, and opacity are configurable.
- [ ] Click-through is tested and accurately documented.
- [ ] Cooldown indicator displays ability, remaining time, progress, and READY.

### Integration
- [ ] Existing capture/ROI/preview/database/telemetry functions still work.
- [ ] Manual events use the same normalized contract intended for the future detector.
- [ ] Existing settings remain intact after overlay settings are saved.
- [ ] Closing during capture/cooldown shuts down cleanly.

### QA and documentation
- [ ] Existing Week 1 regression tests pass.
- [ ] Week 2 automated tests pass.
- [ ] Combined capture + overlay test is completed.
- [ ] CPU/RAM/game-FPS comparison is recorded.
- [ ] TODO and RISK reflect evidence, not code presence alone.
- [ ] Week 3 backlog explicitly targets Survivor POV and 3D Killer action recognition.

---

## 11. Test Plan

### Automated tests
- State transitions for each trigger type.
- `on_cast_start` starts only on cast-start event.
- `on_release` waits until release event.
- Duplicate event suppression.
- Remaining-time calculation and expiration.
- Reset/cancel behavior.
- Invalid ability ID, disabled ability, and invalid duration.
- Settings serialization/deserialization and invalid-value fallback.
- Database integration with existing Killer/ability records.
- Integration event → cooldown manager → overlay state model.

### Manual Windows tests
Record:
- Windows version.
- Python/PySide6 versions.
- Display resolution and scaling.
- Roblox display mode.
- Overlay position, dimensions, and opacity.
- Click-through result.
- CPU/RAM with overlay hidden/visible.
- Game FPS baseline and overlay-enabled FPS under comparable gameplay.
- Test duration and shutdown result.

Minimum scenarios:
1. Launch tracker with Roblox closed.
2. Launch tracker with Roblox open.
3. Verify existing capture and ROI preview.
4. Show/hide overlay repeatedly.
5. Move/resize overlay and restart app.
6. Simulate The Hidden Leap cast-start and verify timer starts.
7. Simulate an `on_release` ability and verify timer waits until release.
8. Reset/cancel active timer.
9. Minimize/restore Roblox while capture runs.
10. Close app while capture and cooldown are active.
11. Run capture + overlay together for at least 15 minutes.

---

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Click-through unreliable in Roblox | Overlay intercepts gameplay input | Test actual Windows/game mode early; document limitation and safe fallback. |
| Always-on-top differs by display mode | Overlay appears behind game | Validate supported Roblox display mode. |
| Timer ignores trigger semantics | Cooldown begins at wrong animation phase | Enforce `trigger_type` in the state machine and unit-test event sequences. |
| Duplicate visual/manual events | Timer restarts incorrectly | Add event identity/debounce/active-state rules; Week 3 detector must use same event contract. |
| UI update blocks capture preview | Stutter or lost responsiveness | Keep work out of paint routine; use bounded state handoff and Qt-safe updates. |
| Existing settings are overwritten | ROI/capture configuration lost | Extend existing schema carefully and add round-trip tests. |
| CLAHE remains expensive | Processing throughput drops | Do not enable full-ROI CLAHE by default; investigate localized preprocessing in Week 3. |
| Week 2 expands into AI detection | Overlay remains unfinished | Keep detection implementation out of scope; use normalized manual events. |
| Cooldown values are unverified | Displayed READY time may be inaccurate | Preserve verification flag and allow configuration edits. |

---

## 13. Week 2 Deliverables

1. Cooldown state machine with trigger-aware behavior.
2. Normalized ability-event interface for manual and future vision sources.
3. Transparent PySide6 overlay window.
4. Circular/radial cooldown indicator.
5. Manual trigger controls integrated into the existing application.
6. Existing database-driven Killer/ability selection.
7. Persisted overlay settings.
8. Automated and manual test report.
9. Updated TODO, RISK, ARCHITECTURE, README, and Week 3 backlog.

## 14. Week 3 Readiness Gate

Week 3 may begin when:
- Existing Week 1 capture/ROI pipeline remains stable.
- Manual normalized ability events correctly drive the cooldown state machine.
- Both `on_cast_start` and `on_release` trigger semantics are tested.
- Overlay accurately renders cooldown state and READY.
- Overlay behavior and click-through limitations are documented.
- Combined capture + overlay runs without UI stalls or worker leaks.

Week 3 should then collect and annotate representative **Survivor POV** gameplay footage, focusing on visible 3D Killer poses/actions. Evaluate a reproducible OpenCV baseline and temporal sequence strategy before escalating to YOLO or another learned model. The detector must emit normalized ability events; it must not directly control the overlay.
