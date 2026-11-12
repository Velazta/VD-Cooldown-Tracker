# Week 2 — Development References (Day 1–7)

**Project:** Violence District Cooldown Tracker  
**Milestone:** Week 2 — Cooldown State Machine & Transparent Overlay  
**Schedule:** 16–22 November 2026  
**Target branch:** `dev`  
**Primary stack:** Python 3.14 (64-bit), PySide6, OpenCV, NumPy  
**Purpose:** Curated technical references mapped to the actual Week 2 execution plan in `PRD_WEEK_2.md`.

> Week 1 is complete on `dev`. Reuse its capture, ROI, preprocessing, database, settings, telemetry, and test foundations. Do not rebuild them unless a verified defect requires a focused change.

---

## How to use this reference guide

1. Read the **Required** references before implementing that day's task.
2. Use **Supporting** references only when the corresponding issue appears.
3. Follow the deliverable and validation checklist; reading documentation is not completion evidence.
4. Prefer the existing project abstractions and conventions over introducing a second framework or persistence layer.
5. Record any platform-specific behavior observed on the actual Windows/Roblox setup.

## Day 1 — Week 1 Handover & Cooldown Design (16 Nov)

**Goal:** Verify the completed Week 1 baseline, understand the existing database and settings models, and design a UI-independent cooldown/event contract.

### Required references

- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) — represent immutable or structured state/event data without coupling it to Qt widgets.
- [Python typing](https://docs.python.org/3/library/typing.html) — type aliases, Literal/Enum-oriented contracts, and readable interfaces.
- [pytest — Getting started](https://docs.pytest.org/en/stable/getting-started.html) — run the existing regression suite before changing code.
- [pytest — Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) — prepare reusable test data for ability records and event scenarios.
- [Python json](https://docs.python.org/3/library/json.html) — understand the existing local data format; do not create a parallel schema.

### Supporting references

- [Python logging](https://docs.python.org/3/library/logging.html) — log event source, ability IDs, transitions, and invalid inputs.
- [Git documentation](https://git-scm.com/docs) — inspect branch, status, diff, and commit history.

### Apply to the project

- Inspect the current `dev` branch and run all Week 1 tests.
- Inspect `DatabaseManager`, `AbilityConfig`, `SettingsManager`, and the actual values of `trigger_type`.
- Define normalized event fields: killer ID, ability ID, event type, monotonic timestamp, source, and optional confidence.
- Agree on states: `READY`, `WAITING_FOR_RELEASE`, and `COOLDOWN`.
- Keep the cooldown manager independent from PySide6 and OpenCV.

**Deliverable:** documented state/event contract, passing Week 1 regression baseline, and Week 2 module skeleton.

**Completion evidence:** test output, short design note, and a reviewed diff showing no unnecessary rewrite of Week 1 modules.

---

## Day 2 — Cooldown State Machine (17 Nov)

**Goal:** Implement deterministic cooldown behavior using elapsed-time calculations rather than decrementing a counter.

### Required references

- [Python time](https://docs.python.org/3/library/time.html) — use `time.monotonic()` for elapsed-time and deadline calculations. Wall-clock time can change; cooldown duration should not depend on calendar time.
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) — model cooldown status and event payloads.
- [pytest — Parametrizing tests](https://docs.pytest.org/en/stable/how-to/parametrize.html) — cover multiple event sequences and trigger types.
- [pytest — Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) — isolate test setup and controlled clock dependencies.

### Supporting references

- [Python Enum](https://docs.python.org/3/library/enum.html) — represent finite cooldown states and event types.
- [Python typing](https://docs.python.org/3/library/typing.html) — document manager input/output contracts.

### Apply to the project

- Implement `READY → COOLDOWN → READY` for `on_cast_start`.
- Implement `READY → WAITING_FOR_RELEASE → COOLDOWN → READY` for `on_release`, if that is the intended configured trigger flow.
- Calculate remaining time from a monotonic deadline.
- Handle duplicate events, reset, cancel, expiry, disabled abilities, missing IDs, invalid duration, and unknown trigger values.
- Do not hard-code Leap cooldown values; read the selected ability configuration.

**Deliverable:** standalone cooldown manager and automated unit tests.

**Completion evidence:** tests for both trigger types, duplicate suppression, invalid inputs, reset/cancel, and expiry. The manager must run without constructing a QApplication.

---

## Day 3 — Transparent Overlay Window (18 Nov)

**Goal:** Build a separate transparent top-level window and verify its behavior on the actual Windows/Roblox display configuration.

### Required references

- [PySide6 QWidget](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html) — top-level widgets, geometry, painting lifecycle, and window configuration.
- [PySide6 Qt window flags](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html) — investigate `FramelessWindowHint`, `WindowStaysOnTopHint`, `Tool`, `WindowDoesNotAcceptFocus`, and `WindowTransparentForInput`.
- [PySide6 QWidget painting](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html) — understand `paintEvent()` and why rendering should remain lightweight.

### Supporting references

- [Qt for Python — Getting started](https://doc.qt.io/qtforpython-6/) — official PySide6 API and examples.

### Apply to the project

- Create an independent overlay window; do not replace the existing capture/preview main window.
- Implement frameless, transparent, show/hide, always-on-top, position, size, and opacity.
- Investigate click-through with the appropriate native window flag. `WA_TransparentForMouseEvents` and desktop-level input transparency are not interchangeable guarantees.
- Test with Roblox in the display mode actually used; record whether input passes through and whether the overlay remains above the game.
- Do not use injection, hooks, process manipulation, or anti-cheat workarounds.

**Deliverable:** transparent overlay prototype independent of cooldown logic.

**Completion evidence:** screenshots or short recording plus a test table for transparency, stacking, position, opacity, focus, and click-through behavior.

---

## Day 4 — Cooldown Widget (19 Nov)

**Goal:** Render a circular/radial progress indicator driven by cooldown state.

### Required references

- [PySide6 QPainter](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainter.html) — custom widget painting and drawing primitives.
- [PySide6 QPen](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPen.html) — stroke width, cap style, and pen configuration for ring indicators.
- [PySide6 QWidget](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html) — implement a custom widget through `paintEvent()`.

### Supporting references

- [PySide6 QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html) — schedule UI refreshes. A UI timer is only for repaint cadence; it must not be the source of cooldown accuracy.
- [Qt signals and slots for Python](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html) — update the widget when state changes.

### Apply to the project

- Draw the circular progress ring, ability label, remaining seconds, and READY state.
- Derive progress from the cooldown manager's remaining-time/status snapshot.
- Keep the timer deadline in the manager; repainting must never restart or extend it.
- Keep paint operations cheap: no screen capture, OpenCV processing, file I/O, or inference in `paintEvent()`.
- Show a clear indication when the configured cooldown duration is unverified.

**Deliverable:** reusable cooldown indicator connected to the overlay controller.

**Completion evidence:** visual checks at READY, just-started, mid-cooldown, near-expiry, and expired states.

---

## Day 5 — Main Application Integration & Manual Events (20 Nov)

**Goal:** Connect the existing application, selected ability, normalized manual events, cooldown manager, and overlay without breaking Week 1 features.

### Required references

- [Qt signals and slots for Python](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html) — connect UI actions and state updates without tightly coupling modules.
- [PySide6 QComboBox](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QComboBox.html) — populate Killer/ability selectors from existing validated database records.
- [PySide6 QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html) — manage UI refresh cadence and understand timer thread affinity.
- [Python logging](https://docs.python.org/3/library/logging.html) — trace manual event → manager transition → overlay update.

### Supporting references

- [PySide6 QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) — consult only if integration touches worker-thread communication. Do not move the cooldown manager to a thread without a measured need.
- Existing project modules: `main.py`, `database/database_manager.py`, `config/`, `monitoring/`, and `capture/`.

### Apply to the project

- Add manual cast-start and release test controls.
- Ensure controls emit the same normalized event contract intended for the future CV detector.
- Resolve the selected Killer/ability from the existing database manager.
- Connect manager status to the overlay controller using a clean signal/callback boundary.
- Preserve capture start/stop, ROI preview, preprocessing selection, database selection, and telemetry.

**Deliverable:** end-to-end manual event → cooldown manager → overlay flow.

**Completion evidence:** demonstrate the configured Leap trigger and an `on_release` ability example; confirm existing Week 1 controls still work.

---

## Day 6 — Settings Persistence & Reliability (21 Nov)

**Goal:** Persist overlay preferences while preserving existing app, capture, and ROI settings.

### Required references

- [Python json](https://docs.python.org/3/library/json.html) — serialization, deserialization, and explicit handling of malformed or missing values.
- [Python pathlib](https://docs.python.org/3/library/pathlib.html) — safe, maintainable filesystem paths.
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) — structured settings models and defaults.
- [pytest — tmp_path fixture](https://docs.pytest.org/en/stable/how-to/tmp_path.html) — test settings persistence using isolated temporary files.

### Supporting references

- [Qt QSettings](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSettings.html) — alternative Qt-native settings storage. **Do not migrate to QSettings automatically**; the PRD requires extending the existing SettingsManager and current JSON architecture unless there is a concrete reason to change.
- [Python logging](https://docs.python.org/3/library/logging.html) — report invalid settings and fallback behavior.

### Apply to the project

- Extend the existing settings model/manager with overlay visibility, x/y, width/height, opacity, always-on-top, and click-through preference.
- Validate values and apply documented defaults for missing/invalid fields.
- Preserve unrelated capture and ROI settings when saving.
- Test restart persistence, malformed settings, repeated show/hide, repeated start/reset, and shutdown while capture/cooldown is active.

**Deliverable:** persistent overlay settings and stable application lifecycle.

**Completion evidence:** before/after settings file comparison, restart test, invalid-value test, and clean shutdown test.

---

## Day 7 — Integration, QA & Week 2 Review (22 Nov)

**Goal:** Verify the combined application, run regression and Week 2 tests, measure resource impact, and prepare Week 3.

### Required references

- [pytest — Running tests](https://docs.pytest.org/en/stable/how-to/usage.html) — run the full suite and interpret failures.
- [pytest — Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) — share controlled setup for integration tests.
- [psutil documentation](https://psutil.readthedocs.io/stable/) — measure process CPU and memory using the existing monitoring approach.
- [Python time](https://docs.python.org/3/library/time.html) — measure elapsed time and latency with monotonic/performance clocks.
- [Python logging](https://docs.python.org/3/library/logging.html) — collect lifecycle and integration evidence.

### Supporting references

- [Git documentation](https://git-scm.com/docs) — inspect final diff, commit history, and branch state.
- [pytest — Parametrizing tests](https://docs.pytest.org/en/stable/how-to/parametrize.html) — exercise multiple ability and state scenarios.

### Apply to the project

- Run all Week 1 regression tests and all Week 2 tests.
- Demonstrate the complete manual trigger → cooldown → overlay flow.
- Test overlay stacking and click-through in the target Roblox mode.
- Compare CPU, RAM, and game FPS with overlay hidden versus visible; record test conditions.
- Run a sustained capture + overlay test and verify shutdown.
- Update `TODO.md`, `RISK.md`, `ARCHITECTURE.md`, `README.md`, and the Week 2 PRD using measured evidence.
- Prepare Week 3 backlog for Survivor POV and 3D Killer action/pose recognition.

**Deliverable:** integrated manual cooldown overlay prototype, QA evidence, risk updates, and Week 3 readiness notes.

**Completion evidence:** test report, performance comparison, known-limitations list, and reviewed documentation diff.

---

## Cross-day engineering rules

1. **Do not rebuild Week 1.** Extend the existing capture, ROI, database, settings, and monitoring implementations.
2. **Keep cooldown logic UI-independent.** The manager must be testable without QApplication or QWidget.
3. **Use monotonic time for cooldown truth.** QTimer may request UI refreshes, but must not decrement the authoritative timer counter.
4. **Keep event source-neutral.** Manual controls and the future vision detector must emit the same normalized ability-event contract.
5. **Do not invent game facts.** Cooldown durations remain configurable and unverified until independently confirmed.
6. **Test actual Windows behavior.** Always-on-top and click-through must be verified in the actual Roblox display mode.
7. **No unsafe integration.** No process memory reading, injection, hooking, executors, client modification, anti-cheat bypass, or automated gameplay input.
8. **Evidence over checkboxes.** A task is complete only when implementation, tests, and observed behavior support it.

## Week 2 completion gate

Week 2 is ready to close only when:
- The cooldown manager passes tests for trigger semantics, timing, duplicate suppression, reset, cancel, and expiry.
- The overlay is transparent, independently controllable, and tested for stacking/click-through.
- Ability selection and duration/trigger values come from the existing validated database.
- Manual events drive the same event interface reserved for Week 3 detection.
- Overlay settings persist without damaging existing settings.
- Existing Week 1 functionality remains operational.
- Combined capture + overlay performance and stability are measured and documented.

---

## Official documentation index

- Python: https://docs.python.org/3/
- PySide6 / Qt for Python: https://doc.qt.io/qtforpython-6/
- pytest: https://docs.pytest.org/en/stable/
- psutil: https://psutil.readthedocs.io/stable/
- Git: https://git-scm.com/docs
