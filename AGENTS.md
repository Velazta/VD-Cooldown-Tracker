# AGENTS.md — Project Instructions for Coding Agents

## 1. Project Identity
You are contributing to **Violence District Cooldown Tracker**, an external Windows desktop companion application built primarily with Python.

It observes visible game output through screen capture, analyzes selected HUD/UI regions, and displays configurable cooldown timers in a transparent overlay.

The first MVP path is **The Hidden → Leap**. Keep the architecture extensible, but do not expand the first milestone unnecessarily.

## 2. Read Before Making Changes
Read these files in order:
1. `PRD.md` — product goals, scope, requirements, acceptance criteria.
2. `ARCHITECTURE.md` — module boundaries, data flow, technical decisions.
3. `TODO.md` — current milestone and task status.
4. `WORKFLOW.md` — implementation, testing, and change process.

If documents conflict, do not silently choose one. Report the conflict and recommend a resolution. PRD defines product intent; Architecture defines technical boundaries; TODO defines execution status.

## 3. Language and Communication
- Explain plans, findings, and implementation summaries in Indonesian unless the user requests otherwise.
- Keep code identifiers, filenames, comments, and technical terminology in English.
- Distinguish verified behavior from assumptions.
- Do not claim a feature works until it has been executed or tested.
- When blocked, explain the evidence and the smallest useful next experiment.

## 4. Technology Baseline
Use this stack unless the user explicitly approves a change:
- Python 64-bit as primary language.
- PySide6 for desktop UI and overlay window management.
- OpenCV for image processing and template matching.
- NumPy for image-array operations.
- Windows.Graphics.Capture or DXGI Desktop Duplication as candidate Windows capture backends.
- JSON for initial local configuration and skill data.
- PyTorch only when a learned model is justified.
- YOLO only when object detection is actually needed.
- Git for version control.

Do not introduce C#, Electron, Rust, a web backend, cloud services, or a second application stack without explaining the trade-off and receiving approval.

## 5. Non-Negotiable Safety and Platform Boundaries
The application must remain an external, non-invasive companion tool.

**Never implement or recommend:**
- DLL injection or process injection.
- Hooking into Roblox or Violence District processes.
- Reading Roblox process memory or internal game variables.
- Roblox executors or exploit APIs.
- Modifying Roblox client files or executable behavior.
- Bypassing anti-cheat or platform protections.
- Automated gameplay input or macros.

Use visible screen capture only. Screen capture does not guarantee that the game or platform permits the application. Do not claim policy approval or account safety without authoritative evidence.

Do not use `SetWindowDisplayAffinity` as an anti-cheat bypass. It is not a method for hiding the application from anti-cheat systems.

## 6. Engineering Principles
- Prefer small, reviewable changes.
- Preserve existing working code.
- Do not rewrite unrelated modules to fix a localized issue.
- Separate capture, processing, detection, cooldown, overlay, database, and monitoring responsibilities.
- Keep interfaces replaceable; do not hard-wire capture backend or detection algorithm throughout the codebase.
- Use type hints for public functions and important data structures.
- Use clear names and short functions.
- Handle errors explicitly.
- Use bounded queues/buffers for frames.
- Avoid unnecessary copies and color conversions.
- Do not block the UI thread with capture or inference work.
- Ensure threads/tasks stop cleanly.
- Do not add dependencies without explaining why they are needed.

## 7. Computer Vision Rules
- Start with OpenCV and a reproducible baseline.
- Use ROI cropping before expensive processing.
- Measure capture FPS separately from processing FPS.
- Prefer latest-frame processing over an unbounded backlog of stale frames.
- Use template matching for stable, fixed-position HUD icons as the initial baseline.
- `TM_CCOEFF_NORMED` may be evaluated, but thresholds must be measured on actual gameplay footage.
- Grayscale, thresholding, and edge detection are optional experiments; do not assume they always improve recognition.
- YOLO detects objects; it does not automatically recognize a temporal ability-use action.
- For animation/event recognition, evaluate temporal consistency, state machines, optical flow, or sequence models.
- A detection must not trigger repeated timers on every frame. Add event confirmation and duplicate-event suppression.
- Provide manual fallback where practical.
- Never claim 100% accuracy or infer an ability use that is not visually observable.

## 8. Performance Targets
Treat these as targets to measure, not guarantees:
- CV processing rate: 15–30 FPS.
- Detection latency target: below 150 ms.
- Stretch goal: below 100 ms under controlled conditions.
- Overlay appearance acceptance target: below 200 ms after confirmed visual change.
- CPU target: below 5% on a standard quad-core reference system.
- RAM target: below 250 MB.
- Game performance target: relative degradation below 3%; also report absolute FPS change.
- Stability: one-hour test without application/game crash.

Always record hardware, resolution, capture mode, test duration, and measurement method. If a target is missed, report it honestly.

## 9. Data and Configuration Rules
- Keep cooldown values in configuration, not hard-coded in detection logic.
- Use stable IDs for killers and abilities.
- Store cooldown durations as numeric seconds.
- Validate JSON on load.
- Provide useful errors for missing or invalid fields.
- Never assume a community-reported cooldown is authoritative or permanently current.
- Do not overwrite user data without preserving existing values.

## 10. Testing Expectations
For every meaningful change:
- Run the smallest relevant test.
- Add/update tests when behavior changes.
- Test normal and failure paths.
- Check clean shutdown for background threads.
- Check UI responsiveness.
- Record performance changes if capture or image processing is affected.

Do not mark a TODO complete merely because code was written. It is complete only when the acceptance condition has been tested or the limitation is documented.

## 11. Change Management
Before coding:
1. State intended change briefly.
2. Identify affected files/modules.
3. Identify assumptions and risks.
4. Check current TODO status.

After coding:
1. Summarize files changed.
2. Explain key implementation choices.
3. List tests executed and outcomes.
4. State known limitations.
5. Update `TODO.md` only for work actually completed.
6. Update `ARCHITECTURE.md` if a lasting architectural decision changes.

Do not silently expand scope. Ask before breaking architecture or dependency changes.

## 12. Current Milestone Guardrail
Current milestone: **Week 1 — Foundation & Technical Feasibility**.

Prioritize:
- Python environment.
- Windows capture feasibility.
- Capture prototype.
- Frame preview and metrics.
- ROI cropping.
- OpenCV preprocessing experiment.
- JSON schema foundation.
- Performance/stability report.

Do not start YOLO training, full automatic killer detection, complete overlay design, or all-killer support unless the user explicitly changes the milestone.

## 13. Definition of Done
A task is done only when:
- Requested behavior is implemented.
- Relevant tests or reproducible manual test pass.
- Errors and limitations are documented.
- No prohibited game interaction has been introduced.
- Related documentation and TODO status are updated.
