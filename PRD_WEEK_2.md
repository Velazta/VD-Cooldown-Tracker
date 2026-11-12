# PRD — Week 2: Desktop Application & Cooldown Overlay

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 2 — Desktop Application & Overlay  
**Schedule:** 16–22 November 2026  
**Primary stack:** Python 64-bit, PySide6, OpenCV, NumPy  
**Persistence:** Local JSON  
**Status:** Proposed execution specification  
**Dependency:** Week 1 capture foundation and outstanding verification items

---

## 1. Purpose

Week 2 turns the technical capture prototype into a usable desktop application shell. The user must be able to open the application, inspect capture status, configure basic settings, and operate a separate transparent cooldown overlay.

The Week 2 result is a **manual-control MVP shell**, not an automatic AI detector. A user-triggered manual timer will validate the cooldown and overlay path while Week 3 focuses on gameplay data and visual event recognition.

## 2. Week 2 Objective

By the end of Week 2, the application should support this demonstrable flow:

1. Launch the PySide6 desktop application.
2. Select or configure the supported Roblox capture target.
3. Start and stop the existing capture engine from the application panel.
4. View capture status and available capture metrics.
5. Open, hide, move, and configure the transparent overlay.
6. Select a configured killer ability from the local database.
7. Start or reset its cooldown manually for testing.
8. See the remaining time update in the overlay and transition to READY.
9. Close the application without leaving capture workers running.

**Primary demonstration path:** Application Panel → Manual Start Leap → Cooldown Overlay → READY.

Automatic killer identification and automatic Leap recognition are explicitly deferred.

## 3. Scope

### 3.1 In scope

- Main PySide6 application window and navigation/layout structure.
- Capture target configuration and capture lifecycle integration.
- Capture status, preview, and existing capture metrics.
- Transparent, always-on-top overlay window.
- Overlay position, size, visibility, opacity, and click-through configuration where technically supported.
- Circular cooldown indicator with remaining-time display and READY state.
- Cooldown manager independent from UI rendering.
- Manual ability selection, timer start, reset, and cancel/clear controls.
- Loading killer/ability configuration from the existing local JSON database.
- Persisting user-facing application and overlay settings locally.
- Basic validation and error messages for invalid/missing configuration.
- Unit and manual tests for timer logic, UI lifecycle, overlay behavior, and integration.
- Documentation and Week 2 review.

### 3.2 Out of scope

- Automatic killer detection.
- Automatic ability-use / Leap detection.
- YOLO training, PyTorch training, OCR, or temporal action recognition.
- Support for every killer and ability as a completed feature.
- Online database synchronization or cloud processing.
- Installer/production packaging.
- Advanced overlay themes, animations, drag-and-drop layout editor, or multiple simultaneous cooldown slots unless core requirements are already stable.
- Any interaction with Roblox internals, process memory, injection, hooks, executors, client modification, anti-cheat bypass, or automated gameplay input.

## 4. Users and Core Use Cases

**Primary user:** A Violence District player running Roblox on Windows who wants a configurable visual cooldown reminder.

| ID | Use case | Expected result |
|---|---|---|
| UC-W2-01 | Launch application | Main panel opens and loads local settings. |
| UC-W2-02 | Start/stop capture | Capture lifecycle is controlled from the panel and status is visible. |
| UC-W2-03 | View capture preview | Latest available frame is displayed without freezing the UI. |
| UC-W2-04 | Show/hide overlay | Overlay visibility can be controlled independently of the panel. |
| UC-W2-05 | Configure overlay | Position, size, and opacity settings are applied and persisted. |
| UC-W2-06 | Select ability | Killer and ability options are loaded from JSON. |
| UC-W2-07 | Start manual cooldown | Selected ability timer starts and appears in the overlay. |
| UC-W2-08 | Reset/cancel cooldown | Timer returns to a known state without duplicate timers. |
| UC-W2-09 | Reach READY | Overlay clearly indicates when the configured duration has elapsed. |
| UC-W2-10 | Exit application | Capture and timer resources shut down cleanly. |

## 5. Functional Requirements

### FR-W2-01 — Main Application Window

The application shall provide a main PySide6 window that acts as the control panel.

Minimum content:
- Application title and version.
- Capture section with target/source, Start, Stop, and status.
- Preview area for the latest captured frame when capture is enabled.
- Basic metrics available from the capture engine: capture FPS, frame latency, resolution, and frame count.
- Ability selection and manual cooldown controls.
- Overlay settings and visibility control.

Requirements:
- The UI must remain responsive while capture is active.
- Long-running capture or processing work must not execute in the Qt UI thread.
- UI widgets must only be updated through safe Qt communication, such as signals/slots or UI-thread polling of thread-safe state.
- The panel must display actionable errors rather than silently failing.

**Acceptance criteria**
- [ ] Main window launches using the documented environment.
- [ ] Required controls are visible and usable at the target minimum window size.
- [ ] UI remains responsive during a 10-minute capture test.
- [ ] Closing the panel initiates orderly shutdown.

### FR-W2-02 — Capture Integration

Reuse the existing capture abstraction and backend where possible. Do not rewrite the capture engine without a reproducible defect or a demonstrated architectural need.

The panel shall:
- Start and stop capture.
- Display STOPPED, STARTING, RUNNING, TARGET LOST, and ERROR states where supported by the backend.
- Display the latest available frame.
- Display capture metrics already exposed by the engine.
- Handle a missing/minimized target without freezing the panel.
- Prevent multiple capture workers from being started accidentally.

**Acceptance criteria**
- [ ] Start begins one capture session.
- [ ] Stop ends the session and clears or freezes the preview in a clear state.
- [ ] Repeated Start/Stop cycles do not create duplicate workers.
- [ ] Target loss is visible to the user.
- [ ] Application can close after capture has been started.

### FR-W2-03 — Transparent Overlay Window

The application shall provide a separate overlay window using PySide6.

Required behavior:
- Transparent background outside drawn UI elements.
- Always-on-top behavior when supported by Windows.
- Independent show/hide control.
- Configurable initial screen position and dimensions.
- Configurable opacity.
- Optional click-through mode.
- No capture or computer-vision workload inside the overlay paint routine.

**Important platform note:** Qt widget attributes alone do not guarantee desktop click-through behavior in every Windows configuration or game display mode. Verify click-through with the actual Roblox target. If the selected method is unreliable, expose the limitation and propose a safe alternative; do not bypass anti-cheat or platform protections.

**Acceptance criteria**
- [ ] Overlay can be shown and hidden without closing the main panel.
- [ ] Transparent regions reveal the content behind the overlay.
- [ ] Overlay remains above the game window in the tested configuration.
- [ ] Position and size can be changed and restored after restart.
- [ ] Click-through behavior is explicitly tested and its supported conditions documented.
- [ ] Overlay does not intercept gameplay input when click-through is reported as enabled and working.

### FR-W2-04 — Cooldown Indicator

The overlay shall display one active cooldown slot for the Week 2 manual demonstration.

Minimum visual states:
- **READY:** no active cooldown; ability can be manually started.
- **COOLDOWN:** remaining time is displayed.
- **PAUSED/INVALID:** optional only if the timer can genuinely enter that condition; do not display unsupported states.

Minimum indicator:
- Circular progress/ring or a clear equivalent.
- Remaining time in seconds.
- Ability name.
- Clear READY indication after expiration.

Requirements:
- Timer calculations must use a monotonic clock, not repeated subtraction from a nominal one-second UI tick.
- UI refresh cadence and timer accuracy must be treated separately.
- The display must not drift materially during a sustained timer test.
- The timer must not restart simply because the UI repaints.

**Acceptance criteria**
- [ ] Starting a configured timer displays the expected initial duration.
- [ ] Remaining time decreases based on elapsed monotonic time.
- [ ] Timer transitions to READY once elapsed time reaches the configured duration.
- [ ] Repeated UI refreshes do not alter the timer's end time.
- [ ] Reset and cancel produce deterministic states.
- [ ] A timer test of at least 5 minutes completes without visible timing drift beyond the agreed tolerance.

### FR-W2-05 — Cooldown Manager

Implement cooldown logic as a standalone component, separate from PySide6 widgets.

Minimum responsibilities:
- Receive a killer ID and ability ID.
- Resolve configured duration from the database/configuration layer.
- Start a cooldown using a monotonic end timestamp.
- Report remaining time and state.
- Reset, cancel, and clear the active timer.
- Emit or expose state changes for the overlay.

Suggested state model: READY → COOLDOWN → READY, with an explicit reset/cancel path.

Rules:
- Store duration in configuration; do not hard-code it in UI code.
- Do not assume a configured cooldown value is authoritative server state.
- Week 2 manual controls are a test harness, not automatic game detection.
- Prevent accidental duplicate starts for the same active ability unless an explicit reset/restart action is requested.

**Acceptance criteria**
- [ ] Cooldown manager can be tested without launching the UI.
- [ ] Start, remaining-time, expiration, reset, and cancel behavior pass unit tests.
- [ ] Invalid or missing ability IDs return a readable error.
- [ ] Timer state is communicated to the overlay without coupling the manager to QWidget classes.

### FR-W2-06 — Local Killer/Ability Database Integration

Use the existing local JSON database as the initial source of killer and ability configuration.

The application shall:
- Load killer and ability records on startup.
- Populate the ability selector from enabled records.
- Resolve cooldown duration by stable IDs.
- Handle missing, malformed, or incomplete JSON with a useful message.
- Preserve existing user data when saving unrelated settings.
- Keep cooldown values editable in data rather than hard-coded.

Potential data issue to review before relying on the file:
- Existing database contains The Hidden abilities Leap and Mark. Verify all values against current in-game observations before treating them as correct.
- The JSON structure should be validated consistently. Avoid creating a second conflicting schema during Week 2.

**Acceptance criteria**
- [ ] The Hidden and its configured abilities appear in the selector.
- [ ] Selected ability resolves to the correct ID and configured duration.
- [ ] Invalid JSON does not crash the application.
- [ ] Adding or changing a data record does not require editing the cooldown manager.

### FR-W2-07 — Application and Overlay Settings

Persist only settings required by the Week 2 application.

Minimum settings:
- Target window title/source identifier, if supported by the selected backend.
- Overlay visible/hidden preference.
- Overlay x/y position.
- Overlay width/height.
- Overlay opacity.
- Click-through preference.
- Selected killer/ability, if useful and valid.

Requirements:
- Validate values on load.
- Apply safe defaults when settings are missing.
- Do not overwrite the killer database when saving UI settings.
- Keep configuration paths explicit and consistent with the project structure.

**Acceptance criteria**
- [ ] Settings load on application startup.
- [ ] Changes are saved when the user applies them or exits normally.
- [ ] Invalid values are rejected or replaced with documented safe defaults.
- [ ] Restart restores the last valid overlay configuration.

### FR-W2-08 — Application Lifecycle and Error Handling

The application shall:
- Prevent duplicate capture sessions.
- Stop capture workers on shutdown.
- Stop UI timers and retire relevant callbacks safely.
- Handle missing configuration/database files.
- Show capture and overlay errors clearly.
- Avoid leaving background threads active after the main window closes.

**Acceptance criteria**
- [ ] Repeated application open/close tests do not leave the process running.
- [ ] Capture worker exits within the documented shutdown timeout under normal conditions.
- [ ] Missing or malformed configuration produces a recoverable error.
- [ ] No unhandled exception occurs during the normal manual cooldown flow.

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Responsiveness | UI remains interactive during capture and timer updates. |
| Timing | Cooldown is calculated from monotonic timestamps, not accumulated UI tick counts. |
| Performance | Overlay rendering and timer updates must add minimal work; measure rather than assume. |
| Resource use | Avoid retaining unnecessary full-resolution frames or unbounded histories. |
| Reliability | Repeated start/stop and show/hide operations must be safe. |
| Maintainability | Keep UI, capture, cooldown logic, database, and overlay responsibilities separated. |
| Compatibility | Target Windows 10/11 64-bit and Roblox display modes verified in Week 1. |
| Privacy | Local processing only; no gameplay frame upload or cloud dependency. |
| Safety | External screen observation only; no Roblox process interaction or gameplay automation. |

Week 2 is not required to meet final MVP CPU/RAM/game-FPS targets conclusively, but it must record a baseline comparison with the overlay visible and hidden.

## 7. Proposed Architecture and Module Boundaries

Preserve the current project architecture and add only the components needed for this milestone.

Suggested Week 2 modules:

- app/application.py — application composition and lifecycle.
- app/main_window.py — main control panel.
- app/settings.py — settings model/load/save.
- overlay/overlay_window.py — transparent top-level window.
- overlay/cooldown_widget.py — circular indicator rendering.
- overlay/overlay_controller.py — overlay show/hide/configuration.
- cooldown/cooldown_manager.py — timer state and monotonic timing.
- cooldown/cooldown_state.py — state/data structures if needed.
- database/database_manager.py — existing JSON loading/validation boundary.
- tests/test_cooldown_manager.py
- tests/test_settings.py
- tests/test_database.py
- tests/test_overlay_logic.py — logic/config tests; GUI behavior may need manual tests.

Expected data flow:

Main Window → Capture Controller → Capture Backend → Frame Preview

Main Window → Database Manager → Ability Configuration

Manual Start/Reset → Cooldown Manager → Overlay Controller → Overlay Window

Design constraints:
- Cooldown manager must not import or manipulate QWidget.
- Overlay must not own capture lifecycle.
- Main window coordinates components but should not contain all business logic.
- Capture worker must not update widgets directly.
- Overlay controller is the bridge between cooldown state and visual presentation.

## 8. Day-by-Day Execution Plan

### Day 1 — Week 1 Handover and Application Skeleton (16 Nov)

Tasks:
- Review Week 1 code and verify outstanding Day 3–7 checklist items.
- Resolve blocking dependency/documentation mismatches, especially MSS installation.
- Confirm the actual capture backend name and configuration.
- Establish the main application window structure.
- Define the settings model and component wiring plan.
- Run capture prototype from the application lifecycle.

Deliverable: Main application skeleton opens and controls the existing capture prototype. Week 1 carry-over issues are listed and prioritized.

### Day 2 — Capture Panel and Preview Integration (17 Nov)

Tasks:
- Integrate Start/Stop controls with capture backend.
- Display capture status, frame dimensions, FPS, and latency.
- Display the latest frame preview.
- Handle target lost/error states.
- Test repeated Start/Stop and close behavior.
- Ensure frame conversion and UI updates do not create visible UI stalls.

Deliverable: Stable capture panel with preview and status/metrics.

### Day 3 — Overlay Window Foundation (18 Nov)

Tasks:
- Create separate transparent PySide6 overlay window.
- Implement show/hide and always-on-top behavior.
- Implement initial position, dimensions, and opacity.
- Test overlay over ordinary desktop windows and Roblox in the supported display mode.
- Investigate click-through behavior and document exact supported behavior.

Deliverable: Independently controllable transparent overlay prototype.

### Day 4 — Cooldown Manager and Unit Tests (19 Nov)

Tasks:
- Implement standalone cooldown manager.
- Use monotonic timestamps for timer accuracy.
- Implement READY and COOLDOWN states.
- Implement start, reset, cancel, and expiration.
- Add unit tests for normal and invalid cases.

Deliverable: Tested cooldown manager independent of UI.

### Day 5 — Circular Indicator and Manual Controls (20 Nov)

Tasks:
- Build the cooldown indicator visual.
- Display ability name and remaining time.
- Connect overlay to cooldown manager state.
- Add ability selection and manual start/reset/cancel controls to main panel.
- Test timer completion and repeated activation.

Deliverable: Manual Leap cooldown can be started from the panel and displayed in the overlay.

### Day 6 — JSON and Settings Integration (21 Nov)

Tasks:
- Load killer/ability data from the existing JSON database.
- Populate selection controls from enabled data.
- Persist overlay settings and relevant app preferences.
- Validate malformed/missing data and invalid settings.
- Verify that app settings and killer database remain separate.

Deliverable: Database-driven manual cooldown flow with persistent overlay settings.

### Day 7 — Integration, QA, and Review (22 Nov)

Tasks:
- Run end-to-end manual cooldown demonstration.
- Test capture and overlay together.
- Test click-through and always-on-top behavior.
- Test repeated start/stop, show/hide, reset, and application shutdown.
- Measure CPU/RAM and compare game FPS with overlay visible/hidden.
- Update README, TODO, ARCHITECTURE, and risk register based on verified results.
- Prepare Week 3 backlog for dataset collection and visual detection.

Deliverable: Week 2 integrated application shell and overlay prototype, test report, known limitations, and Week 3 readiness assessment.

## 9. Week 2 Acceptance / Definition of Done

Week 2 is complete only when all required items below have evidence.

### Application
- [ ] Main PySide6 panel launches.
- [ ] Capture Start/Stop and preview work from the panel.
- [ ] Status and available capture metrics update correctly.
- [ ] UI remains responsive during capture.
- [ ] Repeated Start/Stop does not create duplicate workers.

### Overlay
- [ ] Separate transparent overlay can be shown/hidden.
- [ ] Always-on-top behavior is verified in the target configuration.
- [ ] Position, size, and opacity can be configured.
- [ ] Settings persist across restart.
- [ ] Click-through behavior is tested and accurately documented.

### Cooldown
- [ ] Cooldown manager is independent from UI.
- [ ] Monotonic timer logic passes unit tests.
- [ ] Manual ability selection resolves data from JSON.
- [ ] Manual start/reset/cancel controls work.
- [ ] Circular indicator displays remaining time.
- [ ] Timer reaches READY at expiration.

### Reliability and documentation
- [ ] Missing/invalid JSON is handled safely.
- [ ] Application closes without leaving capture workers active.
- [ ] Capture + overlay combined test is completed.
- [ ] CPU/RAM and game-FPS comparison is recorded.
- [ ] TODO and risk register reflect only verified work.
- [ ] Week 3 backlog is prepared.

A checkbox must not be marked complete merely because code exists. Record the test or manual evidence.

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Overlay click-through does not work reliably over Roblox | Gameplay input may be intercepted | Test supported Windows behavior early; document limitations and safe fallback. |
| Always-on-top behavior changes with game display mode | Overlay may appear behind game | Test windowed/borderless modes and document supported configuration. |
| Timer drifts due to UI tick accumulation | Incorrect cooldown display | Calculate remaining time from monotonic end timestamp. |
| Capture work blocks UI | Frozen or laggy panel | Keep capture in worker thread; use safe signal/state handoff. |
| Shutdown leaves worker alive | Process remains open or hangs | Explicit stop event, bounded join, lifecycle tests. |
| JSON schema mismatch | Ability selector or timer fails | Reuse one authoritative schema and validate on load. |
| Dependency mismatch | Fresh installation fails | Keep requirements and README installation steps consistent. |
| Week 2 scope expands into AI detection | Core UI/overlay remains unfinished | Keep automatic detection out of scope; use manual timer for integration. |

## 11. Week 2 Test Plan

### Automated tests
- Cooldown start and end-time calculation.
- Remaining time before and after expiration.
- Reset and cancel behavior.
- Invalid ability ID and missing duration.
- Settings serialization/deserialization.
- Invalid settings fallback.
- Database parsing and validation.
- Duplicate timer-start behavior.

### Manual Windows tests

Record:
- Windows version.
- Python and PySide6 versions.
- Display resolution and scaling.
- Roblox display mode.
- Capture backend.
- Overlay position and dimensions.
- Click-through enabled/disabled result.
- Test duration.
- CPU/RAM and game FPS with overlay hidden/visible.
- Shutdown result and any errors.

Minimum manual scenarios:
1. Launch app with Roblox closed.
2. Launch app with Roblox open.
3. Start and stop capture repeatedly.
4. Show/hide overlay.
5. Move overlay and restart app.
6. Start manual cooldown and wait for READY.
7. Reset an active cooldown.
8. Minimize/restore Roblox during capture.
9. Close app while capture is active.
10. Run capture and overlay together for at least 10 minutes.

## 12. Week 1 Carry-over Items to Verify

The current repository checklist and source files indicate that some Week 1 work exists but is not fully marked as verified. Before treating the foundation as complete, review:

- requirements.txt needs to be checked against imports; the capture implementation imports mss, while the visible requirements list does not include it.
- README installation steps install extra capture packages separately; consolidate reproducible installation instructions.
- config/app_config.json backend label should match the actual active backend.
- TODO.md Day 3–7 items need evidence-based status updates.
- ROI processing, JSON validation/loader, and sustained performance measurements must be verified or explicitly carried forward.
- RISK.md should be updated after retesting shutdown, target-lost, and UI responsiveness behavior.

Do not block all Week 2 UI work on non-critical Week 1 documentation cleanup, but resolve dependency and capture lifecycle defects before relying on the integration.

## 13. Week 2 Deliverables

1. Main PySide6 application panel.
2. Capture panel with preview, status, and metrics.
3. Transparent overlay prototype.
4. Cooldown manager with automated tests.
5. Circular cooldown indicator.
6. Manual ability selection and timer controls.
7. JSON-backed ability selection and persisted overlay settings.
8. Week 2 test/evaluation report.
9. Updated project documentation and Week 3 backlog.

## 14. Week 3 Readiness Gate

Week 3 may begin when:
- Capture can be started/stopped reliably from the application.
- The overlay can display a manually started cooldown.
- Cooldown timing is independently tested.
- The local ability configuration can be loaded and validated.
- The combined application can run without blocking the UI or leaking capture workers.

Week 3 will then focus on collecting representative The Hidden gameplay footage, annotating Leap-related visual states, and evaluating a reproducible OpenCV baseline before considering learned models.
