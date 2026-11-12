# Product Requirements Document (PRD)
## Computer Vision Cooldown Overlay — Violence District

| Metadata | Value |
|---|---|
| Project | Violence District Cooldown Tracker |
| Product | External Windows desktop companion |
| Primary language | Python |
| Current milestone | Week 1 — Foundation & Technical Feasibility |
| Roadmap | 9 November–8 December 2026 |
| Version | 1.0 — Working baseline |

## 1. Product Overview

### 1.1 Problem
Violence District abilities have cooldown periods. Players may benefit from a clear visual reminder of when an ability is expected to become available again.

This project is an external desktop companion application. It observes visible game output through screen capture, analyzes selected HUD/UI regions, and displays configurable cooldown timers in a transparent overlay. It must not obtain game state by inspecting Roblox process memory or modifying the game client.

### 1.2 Product Goal
Build a lightweight, configurable cooldown tracker that can:
1. Capture the visible game window or selected screen region.
2. Identify relevant HUD/UI changes using computer vision.
3. Associate visual events with a killer and ability configuration.
4. Start and display a cooldown timer in a transparent overlay.
5. Let users configure the overlay and local skill database.

The first proof of concept focuses on **The Hidden — Leap**. The architecture must remain extensible to additional killers and abilities.

### 1.3 Product Principles
- External visual observation only.
- Local-first processing; no cloud dependency for the MVP.
- Prefer the simplest reliable CV method before deep learning.
- Keep capture, image processing, detection, cooldown logic, and UI independent.
- Treat detections as uncertain; use confidence, debouncing, and manual correction.
- Never claim perfect detection or knowledge of hidden server-side game state.

## 2. Users and Use Cases

**Primary user:** a Violence District player running Roblox on Windows who wants a visual cooldown reminder.

Core use cases:
- Select a game window or capture source.
- Calibrate the HUD region to analyze.
- View capture status and performance metrics.
- Configure killer and ability cooldown data.
- See an overlay timer after a recognized ability-use event.
- Move or resize cooldown indicators.
- Correct a missed or false detection manually.

## 3. Scope and Priorities

### 3.1 Product Feature Set

| Feature | Requirement | MVP status |
|---|---|---|
| Real-time Screen Capture Engine | Capture frames from selected display/window with low overhead | Required foundation |
| HUD Region Calibration | Let user define Region of Interest (ROI) | Required foundation |
| Transparent Overlay Render | Transparent, always-on-top cooldown UI; click-through where supported | MVP feature |
| Basic Skill Database | Local killer, ability, and cooldown data | MVP feature |
| Application Panel | Configure capture, ROI, overlay, and skill data | MVP feature |
| Automatic Killer Detection | Infer killer identity from visible indicators | Later milestone |
| Multiple Killer Support | Store and select configurations for multiple killers | Data architecture now; detection later |
| Ability-use detection | Detect visual activation/cooldown transition | First AI milestone |

### 3.2 Week 1 Scope — Foundation & Technical Feasibility

**In scope**
- Initialize Python project and virtual environment.
- Evaluate Windows.Graphics.Capture and DXGI Desktop Duplication.
- Implement a working capture prototype using the viable backend.
- Display live frame preview.
- Implement configurable ROI cropping.
- Run basic OpenCV preprocessing experiments.
- Measure capture FPS, processing FPS, processing time, CPU, and RAM.
- Define local JSON configuration and multi-killer database schemas.
- Create a minimal PySide6 technical UI as needed.
- Document compatibility limitations and test results.

**Out of scope for Week 1**
- Fully automatic killer identification.
- Full multi-killer detection model.
- Automatic ability recognition.
- Production-ready cooldown overlay.
- YOLO training or custom PyTorch training.
- OCR-based cooldown modifier reading.
- Dynamic multi-monitor/resolution adaptation.
- Cloud synchronization or automatic game-data updates.
- Game memory reading, injection, hooking, or client modification.

### 3.3 MVP Focus
The initial end-to-end MVP prioritizes one path:

**The Hidden → Leap → visual event confirmation → cooldown timer → overlay.**

Do not expand to every killer or ability until this path has been measured and tested. The database schema must nevertheless support multiple killers without redesign.

## 4. Functional Requirements

### FR-01 — Real-Time Screen Capture
The application shall:
- Allow selection of an available capture source.
- Capture frames continuously while enabled.
- Expose frame dimensions and timestamps.
- Provide start, stop, and error states.
- Recover gracefully from capture-session failure where possible.
- Keep capture implementation behind an interface so the backend can be replaced.

**Acceptance checks**
- Target can be selected.
- Frames are received continuously.
- Preview updates while capture is active.
- Capture can stop without closing the application.
- Failure is surfaced through status/logging rather than silently freezing.

### FR-02 — HUD Region Calibration / ROI
The application shall:
- Let the user specify ROI using x, y, width, and height.
- Crop each incoming frame to that ROI.
- Display the cropped preview.
- Persist ROI settings locally.
- Validate coordinates against captured frame dimensions.

**Acceptance checks**
- ROI crop matches configured coordinates.
- Invalid/out-of-bounds values are rejected or safely clamped with an explicit message.
- Saved ROI settings can be loaded after restart.

### FR-03 — Transparent Overlay
The application shall provide an overlay that is:
- Transparent where no UI is drawn.
- Always-on-top when supported.
- Configurable in position and size.
- Click-through during gameplay where supported.
- Independently testable from capture and detection.

The overlay must not intercept mouse or keyboard input during normal gameplay when click-through is enabled. Test this behavior explicitly; do not assume a Qt flag guarantees correct behavior in every Windows/game mode.

### FR-04 — Local Skill Database
The application shall store killer ability and cooldown configuration in `database/killerDatabase.json`:
- Schema version and metadata (`schema_version: 1`, `last_updated`).
- Killer ID, display name, and optional description.
- Ability ID and display name.
- Cooldown duration in numeric seconds (`cooldown_seconds: float`).
- Cooldown verification state (`cooldown_verified: bool`).
- Trigger timing behavior (`trigger_type: "on_cast_start" | "on_release"`).
- Interaction input reference (`interact_input`).
- Detection method reference (`detection_method`).
- Enabled/disabled state (`enabled: bool`).

JSON is the default MVP format because the dataset is small, human-readable, and easy to edit. SQLite may be considered later if history or more complex persistence becomes necessary.

Cooldown values are configuration data, not hard-coded truths. Verify them in-game and keep them editable because balance may change.

### FR-05 — Application Panel
The panel shall eventually provide:
- Capture source selection and status.
- ROI calibration.
- Overlay position, size, and visibility.
- Killer/ability configuration.
- Performance metrics.
- Detection confidence and event status.
- Manual timer start/reset for fallback and testing.

Week 1 only needs a minimal technical UI for capture and preview. Full settings UI belongs primarily to Week 2.

### FR-06 — Automatic Killer Detection
The system may identify the active killer using visible, stable game indicators such as a HUD portrait or another distinctive visual element.

Before implementation, determine:
- Which indicator is consistently visible.
- Whether it is unique per killer.
- Whether its size and position vary.
- Whether it can be obscured or animated.

Do not infer identity without reliable visual evidence. Allow manual selection as fallback.

### FR-07 — Multiple Killer Support
The data model shall support multiple killer records and ability lists from the beginning. Automatic detection of all killers is not a Week 1 requirement.

### FR-08 — Ability Event Detection
The system shall detect a configured visual transition and convert it into a candidate ability-use event. Events should be confirmed across frames or by a temporal state machine to reduce false positives.

The first target is The Hidden's Leap. A single frame or one template score should not trigger a timer without temporal consistency and duplicate-event suppression.

## 5. Non-Functional Requirements

### 5.1 Performance Targets
These are engineering targets to validate experimentally, not guaranteed results.

| Metric | Target |
|---|---|
| CV processing rate | Configurable 15–30 FPS |
| Detection latency | Engineering target below 150 ms |
| Stretch latency goal | Below 100 ms in controlled conditions |
| Overlay appearance acceptance | Below 200 ms after confirmed visual state change |
| CPU usage | Initial target below 5% on standard quad-core reference system |
| Application RAM | Initial target below 250 MB |
| Game FPS impact | Target relative degradation below 3%; also record absolute FPS change |
| Stability | No application/game crash during a one-hour test |

CPU and RAM targets are ambitious and hardware-dependent. Record actual measurements and test machine. Do not hide a missed target.

### 5.2 Metric Definitions
- **Capture FPS:** frames successfully delivered by capture backend per second.
- **Processing FPS:** frames completing the CV pipeline per second.
- **Processing time:** elapsed time from processing start to completion for one frame.
- **Detection latency:** elapsed time from first observable visual change in source footage to confirmed event output.
- **Game FPS impact:** difference between comparable baseline and application-enabled gameplay tests.

Measure capture and processing separately. A high capture FPS does not mean every frame must be processed.

### 5.3 Reliability
- Threads/tasks must shut down cleanly.
- Frame buffers must be bounded.
- Stale frames should be discarded rather than accumulated.
- Invalid configuration must not crash the application.
- Capture failures must be logged.
- Avoid unbounded frame/image retention.

### 5.4 Compatibility
Initial target:
- Windows 10/11, 64-bit.
- Roblox Desktop.
- Python 64-bit.
- DirectX-capable graphics environment.

Test windowed and fullscreen/borderless modes where applicable. Capture support in one mode does not guarantee support in another.

### 5.5 Privacy
- Process frames locally by default.
- Do not upload gameplay frames unless a future feature explicitly requires it and user consents.
- Do not collect credentials or account tokens.
- Do not inspect unrelated windows when a specific capture source can be selected.
- Provide a clear capture-active indicator.

## 6. Computer Vision Strategy

### 6.1 Initial Pipeline
1. Acquire frame.
2. Timestamp frame.
3. Select/crop ROI.
4. Resize only if required.
5. Convert color space when useful.
6. Apply optional grayscale/contrast preprocessing.
7. Compare with visual templates or run selected detector.
8. Apply confidence threshold.
9. Validate across time.
10. Emit event to cooldown manager.

### 6.2 Algorithm Selection

| Problem | Initial method | Escalation path |
|---|---|---|
| Fixed-position HUD icon state | OpenCV template matching | Multiple templates / image classifier |
| Icon appearance changes | Grayscale or color features + template matching | Learned classifier |
| Killer portrait recognition | Template matching / classification | YOLO if location/scale varies |
| Object detection in broad screen region | Not needed initially | Small YOLO model |
| Skill animation recognition | Temporal state analysis | Optical flow / sequence classifier |
| Event stability | Multi-frame confirmation and debounce | Trained temporal model |

Use OpenCV `TM_CCOEFF_NORMED` as a baseline for normalized template matching. Test against actual footage before selecting thresholds. Thresholding and edge detection are optional experiments, not mandatory preprocessing: they can remove useful visual information.

### 6.3 YOLO and PyTorch Decision
YOLO is an object detector, not a complete action-recognition solution. It may help locate a killer portrait, icon, or character when position and scale vary. It does not inherently understand that a sequence of frames represents a Leap activation.

PyTorch is a machine-learning framework, not a detection algorithm by itself. Use it only when a learned classifier or temporal model is justified by test results.

**Week 1 decision:** OpenCV first; no model training until capture quality, ROI, and the visual recognition problem are understood.

## 7. Architecture Requirements

Separate:
- `capture`: source selection and frame acquisition.
- `processing`: ROI and image preprocessing.
- `detection`: visual pattern recognition.
- `cooldown`: event state and timer logic.
- `overlay`: rendering and user interaction.
- `database`: local configuration.
- `monitoring`: logs and performance metrics.

Data flow:

`Game Window → Capture Backend → Latest-Frame Buffer → ROI → Preprocessing → Detection → Event Validation → Cooldown Manager → Overlay`

During Week 1, implement and validate the pipeline through preprocessing/preview. Later modules can be stubbed behind interfaces.

## 8. Week 1 Plan (9–15 November 2026)

| Day | Focus | Deliverable |
|---|---|---|
| Day 1 | Repository, Python environment, dependencies, basic Qt/OpenCV smoke tests | Reproducible development environment |
| Day 2 | WGC/DXGI technical spike and Roblox capture compatibility | Capture backend decision and evidence |
| Day 3 | Capture loop, start/stop, timestamp, preview, FPS counter | Capture prototype |
| Day 4 | ROI cropping, grayscale/optional thresholding, template-matching experiment | ROI and preprocessing prototype |
| Day 5 | CPU/RAM/FPS/latency measurements and game baseline comparison | Performance report |
| Day 6 | JSON schemas, configuration loading, module interfaces | Configuration/database foundation |
| Day 7 | Integration, stability test, documentation, Week 2 backlog | Week 1 demo and review |

### Week 1 Definition of Done
- Python environment is reproducible.
- Capture backend obtains frames from intended Roblox configuration, or a documented blocker and fallback are recorded.
- Preview updates continuously.
- ROI can be configured and previewed.
- OpenCV preprocessing runs on ROI.
- Capture FPS and processing FPS are measured separately.
- CPU, RAM, and processing time are recorded.
- Capture stops cleanly.
- JSON configuration loads successfully.
- No injection, hooking, memory reading, or Roblox client modification is used.
- Technical notes and test results are committed.

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Capture backend cannot capture Roblox in selected mode | Test WGC and DXGI early; test windowed/borderless; document supported modes |
| Capture or processing latency is high | Reduce ROI, use latest-frame buffer, avoid unnecessary conversions |
| Processing queue becomes stale | Use bounded buffer and discard old frames |
| HUD changes position or scale | Manual ROI calibration in MVP |
| Visual effects obscure icons | Multi-template tests, temporal confirmation, manual fallback |
| False-positive event triggers | Debounce, confidence thresholds, state machine |
| Cooldown changes after balance updates | Keep values editable in local data |
| Overlay intercepts input | Dedicated click-through tests |
| Anti-cheat or platform policy conflict | Stop testing if conflict is indicated; do not bypass protections |

Screen capture and overlay behavior do not guarantee approval under Roblox or game-specific rules. Keep the project external and non-invasive.

## 10. Out of Scope
- Reading game process memory or internal variables.
- DLL injection, process hooking, executors, or client modification.
- Reading CDR buffs/modifiers through OCR in the initial MVP.
- Cloud synchronization and automatic cooldown updates.
- Guaranteed support for every killer/ability before the first path is validated.
- Guaranteed detection when the ability animation or indicator is not visible.
- Inferring hidden server-side cooldown state.

## 11. Future Milestones
- **Week 2:** PySide6 application panel, transparent overlay, circular timer, cooldown manager, manual controls, capture integration.
- **Week 3:** Gameplay recording, dataset extraction/annotation, baseline visual detector and temporal event recognition for The Hidden — Leap.
- **Week 4:** Integrate detection with cooldown manager, tune confidence/debounce, test false positives/negatives and performance.
- **Finalization:** Packaging, documentation, acceptance evaluation.

## 12. Acceptance Test Summary
The first end-to-end acceptance flow:
1. Start the application.
2. Select a supported Roblox capture source.
3. Start capture.
4. Calibrate the HUD ROI.
5. Play a supported test scenario.
6. Detect a visible ability-use event.
7. Confirm the event and start the configured timer.
8. Display the timer in the overlay.
9. Return the indicator to READY when the timer ends.

The first four steps are Week 1/2 foundation work. Automatic event detection and end-to-end cooldown behavior are later milestones.
