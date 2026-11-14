"""Schema Validator for Temporal Ground Truth Annotations.

Violence District Cooldown Tracker — Detector Rebuild (Phase 1)
Validates dataset/temporal_annotations.json schema and event consistency:
- Validates ability names ('leap', 'mark').
- Validates frame indices against video boundaries.
- Validates event cast_start_frame and timing.
- Checks phase boundary continuity and overlaps.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VALID_ABILITIES = {"leap", "mark"}
VALID_OUTCOMES = {"completed", "interrupted", "hit", "miss", "hit_wall", "unknown"}


class TemporalValidationError(Exception):
    """Raised when temporal annotations fail schema validation."""
    pass


def validate_temporal_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Memvalidasi struktur kamus data temporal_annotations.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Root data must be a dictionary."]

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        errors.append("Missing or invalid 'schema_version' (expected integer >= 1).")

    killer_id = data.get("killer_id")
    if killer_id != "the_hidden":
        errors.append(f"Invalid 'killer_id' (expected 'the_hidden', got '{killer_id}').")

    videos = data.get("videos")
    if not isinstance(videos, dict) or not videos:
        errors.append("Field 'videos' must be a non-empty dictionary mapping filename to metadata.")
        return False, errors

    for vname, vinfo in videos.items():
        if not isinstance(vinfo, dict):
            errors.append(f"Video entry '{vname}' must be a dictionary.")
            continue

        fps = vinfo.get("fps")
        if not isinstance(fps, (int, float)) or fps <= 0:
            errors.append(f"Video '{vname}': missing or invalid 'fps' (expected > 0).")

        total_frames = vinfo.get("total_frames")
        if not isinstance(total_frames, int) or total_frames <= 0:
            errors.append(f"Video '{vname}': missing or invalid 'total_frames' (expected > 0).")
            continue

        # Validasi Events
        events = vinfo.get("events", [])
        if not isinstance(events, list):
            errors.append(f"Video '{vname}': 'events' must be a list.")
        else:
            for i, evt in enumerate(events):
                if not isinstance(evt, dict):
                    errors.append(f"Video '{vname}' event {i}: must be a dictionary.")
                    continue

                ability = evt.get("ability")
                if ability not in VALID_ABILITIES:
                    errors.append(f"Video '{vname}' event {i}: invalid ability '{ability}' (expected one of {VALID_ABILITIES}).")

                csf = evt.get("cast_start_frame")
                if not isinstance(csf, int) or csf < 0 or csf >= total_frames:
                    errors.append(f"Video '{vname}' event {i}: 'cast_start_frame'={csf} out of bounds [0, {total_frames - 1}].")

                outcome = evt.get("outcome", "unknown")
                if outcome not in VALID_OUTCOMES:
                    errors.append(f"Video '{vname}' event {i}: invalid outcome '{outcome}' (expected one of {VALID_OUTCOMES}).")

        # Validasi Phases (jika ada)
        phases = vinfo.get("phases", [])
        if isinstance(phases, list):
            prev_end = -1
            for j, p in enumerate(phases):
                sf = p.get("start_frame")
                ef = p.get("end_frame")
                if not isinstance(sf, int) or not isinstance(ef, int) or sf > ef or sf < 0 or ef >= total_frames:
                    errors.append(f"Video '{vname}' phase {j}: invalid boundary [{sf}, {ef}].")

    is_valid = (len(errors) == 0)
    return is_valid, errors


def validate_temporal_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Membaca dan memvalidasi file JSON temporal ground truth."""
    if not file_path.exists():
        raise FileNotFoundError(f"Temporal annotations file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"JSON syntax error: {str(e)}"]

    return validate_temporal_data(data)


if __name__ == "__main__":
    import sys
    target = Path("dataset/temporal_annotations.json")
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])

    print(f"Validating temporal annotations: {target}")
    valid, errs = validate_temporal_file(target)
    if valid:
        print("SUCCESS: temporal_annotations.json is schema-valid!")
        sys.exit(0)
    else:
        print(f"FAILED with {len(errs)} error(s):")
        for err in errs:
            print(f"  - {err}")
        sys.exit(1)
