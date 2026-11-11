# Development Workflow — Violence District Cooldown Tracker

## 1. Purpose
This document defines how the user and coding agents plan, implement, test, and review changes in this repository. Development should remain incremental, reproducible, and aligned with the active milestone.

## 2. Start-of-Session Procedure
At the beginning of a development session:
1. Read `AGENTS.md`.
2. Read relevant sections of `PRD.md`.
3. Read `ARCHITECTURE.md` before changing module boundaries or data flow.
4. Read `TODO.md` to identify the active milestone and unfinished work.
5. Inspect existing code before proposing replacements.
6. Identify the smallest next task that advances the active milestone.

Do not assume the repository matches the documentation. Verify actual files and runtime state.

## 3. Task Selection
Choose tasks in this order:
1. Unblock the current milestone.
2. Fix reproducible defects in implemented work.
3. Complete the smallest unfinished acceptance criterion.
4. Add tests and observability.
5. Improve performance based on measurements.
6. Add optional enhancements only after core acceptance criteria pass.

Do not start future-week AI features while Week 1 capture feasibility is unproven.

## 4. Before Implementation
For each task, write a short implementation plan containing:
- Objective.
- Current behavior.
- Expected behavior.
- Files/modules likely to change.
- Dependencies, if any.
- Risks and assumptions.
- How success will be tested.

If a task requires an architectural change, explain alternatives and trade-offs before coding.

## 5. Implementation Rules
- Make the smallest change that solves the task.
- Preserve working code and existing public interfaces where practical.
- Do not rewrite unrelated modules.
- Keep UI code out of capture and detection modules.
- Keep CV work out of the UI thread.
- Use bounded frame buffers.
- Use timestamps and monotonic clocks for elapsed-time calculations.
- Handle invalid configuration and capture failures explicitly.
- Add dependencies only when justified.
- Keep secrets, account data, and personal gameplay recordings out of Git.
- Do not introduce prohibited Roblox interaction methods.

## 6. Testing Workflow

### 6.1 Unit Tests
Test isolated behavior such as:
- ROI coordinate validation.
- ROI cropping.
- JSON parsing and validation.
- Cooldown duration calculations.
- Event debounce logic when implemented.

### 6.2 Integration Tests
Test connected components such as:
- Capture backend → frame buffer.
- Frame buffer → ROI processor.
- ROI processor → preview.
- Database → detection configuration.
- Detection event → cooldown manager → overlay.

### 6.3 Manual Tests
For Windows capture and overlay behavior, maintain reproducible manual test steps. Record:
- Windows version.
- Python version.
- Display resolution and scaling.
- Roblox display mode.
- Capture backend.
- Test duration.
- Observed FPS and latency.
- Errors or visual artifacts.

### 6.4 Performance Tests
Measure separately:
- Capture FPS.
- Processing FPS.
- Processing duration.
- Application CPU usage.
- Application RAM usage.
- Game FPS baseline and application-enabled FPS.

Do not compare measurements taken under materially different gameplay conditions without noting the difference.

## 7. Git Workflow
Recommended branch pattern:
- `main` — stable, tested state.
- `develop` — integration branch if needed.
- `feature/<short-name>` — new functionality.
- `fix/<short-name>` — bug fixes.
- `docs/<short-name>` — documentation-only changes.

Suggested commit format:

```text
feat(capture): add frame preview
fix(roi): validate crop boundaries
test(database): cover invalid JSON
docs(architecture): record capture backend decision
```

Keep commits focused. Do not commit virtual environments, generated caches, credentials, large raw recordings, or temporary benchmark dumps unless explicitly intended.

## 8. Definition of Done for Each Task
A task is complete only when:
- Implementation matches the stated objective.
- Relevant automated or manual tests pass.
- Failure behavior has been considered.
- No prohibited game interaction was introduced.
- Documentation is updated when behavior or architecture changes.
- `TODO.md` reflects the verified state.
- The agent reports tests run and known limitations.

Code being present is not sufficient evidence that a task is complete.

## 9. Documentation Maintenance
Update:
- `PRD.md` when product scope or requirements change.
- `ARCHITECTURE.md` when module responsibilities, data flow, or technical decisions change.
- `AGENTS.md` only when durable instructions for future coding agents change.
- `TODO.md` when task status changes.
- `WORKFLOW.md` when the development process changes.

Avoid duplicating long technical explanations across all files. Refer to the authoritative document instead.

## 10. Agent Response Format
After completing a task, report in Indonesian using this structure:

### Ringkasan
What was implemented.

### File yang Berubah
List modified/created files and why.

### Pengujian
Commands or manual scenarios executed, with pass/fail results.

### Catatan Teknis
Important decisions, assumptions, and limitations.

### TODO
Items completed, remaining, or blocked.

Never fabricate test output. If code could not be executed, state that clearly.

## 11. Week 1 Execution Order
Follow this sequence unless test evidence requires a change:
1. Environment and dependency smoke tests.
2. WGC/DXGI capture feasibility.
3. Capture prototype and preview.
4. ROI cropping and preprocessing.
5. Performance measurements.
6. JSON configuration foundation.
7. Integration, documentation, and review.

A capture backend decision must be based on actual Roblox test evidence, not documentation alone.

## 12. Change Approval
Ask the user before:
- Changing primary language or desktop framework.
- Introducing cloud processing or external data upload.
- Adding broad game support that expands MVP scope.
- Replacing JSON with a database system.
- Adding any capability that interacts with Roblox internals.
- Making a breaking change to configuration format.

When a small implementation detail is unspecified, choose the simplest reversible option and document it.
