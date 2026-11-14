import json
from pathlib import Path

temporal_path = Path("dataset/temporal_annotations.json")
with open(temporal_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Known event annotations for existing 18 videos
events_map = {
    "hidden1_basic_hit.mp4": {"fps": 60.0, "total_frames": 164, "events": []},
    "hidden1_basic_hit_survivor.mp4": {"fps": 60.0, "total_frames": 338, "events": []},
    "hidden1_basic_hit_wall.mp4": {"fps": 30.0, "total_frames": 133, "events": []},
    "hidden1_leap_skill.mp4": {
        "fps": 30.0, "total_frames": 167,
        "events": [{"ability": "leap", "cast_start_frame": 75, "cast_start_seconds": 2.5, "outcome": "completed"}]
    },
    "hidden1_leap_skill_ref2.mp4": {
        "fps": 30.0, "total_frames": 129,
        "events": [{"ability": "leap", "cast_start_frame": 30, "cast_start_seconds": 1.0, "outcome": "completed"}]
    },
    "hidden1_mark_skill_hitsurvivor.mp4": {
        "fps": 30.0, "total_frames": 143,
        "events": [{"ability": "mark", "cast_start_frame": 40, "cast_start_seconds": 1.33, "outcome": "hit"}]
    },
    "hidden1_mark_skill_nohitsurvivor.mp4": {
        "fps": 30.0, "total_frames": 139,
        "events": [{"ability": "mark", "cast_start_frame": 35, "cast_start_seconds": 1.17, "outcome": "miss"}]
    },
    "hidden2_leap_skill.mp4": {
        "fps": 30.0, "total_frames": 157,
        "events": [{"ability": "leap", "cast_start_frame": 40, "cast_start_seconds": 1.33, "outcome": "completed"}]
    },
    "hidden2_mark_skill.mp4": {
        "fps": 30.0, "total_frames": 134,
        "events": [{"ability": "mark", "cast_start_frame": 40, "cast_start_seconds": 1.33, "outcome": "completed"}]
    },
    "hidden3_leap_skill.mp4": {
        "fps": 30.0, "total_frames": 408,
        "events": [{"ability": "leap", "cast_start_frame": 110, "cast_start_seconds": 3.67, "outcome": "completed"}]
    },
    "hidden3_leap_skills.mp4": {
        "fps": 30.0, "total_frames": 77,
        "events": [{"ability": "leap", "cast_start_frame": 15, "cast_start_seconds": 0.5, "outcome": "completed"}]
    },
    "hidden_chasing+mark_skill.mp4": {
        "fps": 30.0, "total_frames": 225,
        "events": [{"ability": "mark", "cast_start_frame": 120, "cast_start_seconds": 4.0, "outcome": "completed"}]
    },
    "hidden_chasing2_skill.mp4": {"fps": 30.0, "total_frames": 1418, "events": []},
    "hidden_chasing_skill.mp4": {"fps": 30.0, "total_frames": 1006, "events": []},
    "hidden_leap+mark_comboskill.mp4": {
        "fps": 30.0, "total_frames": 258,
        "events": [
            {"ability": "leap", "cast_start_frame": 35, "cast_start_seconds": 1.17, "outcome": "completed"},
            {"ability": "mark", "cast_start_frame": 140, "cast_start_seconds": 4.67, "outcome": "completed"}
        ]
    },
    "hidden_mark_skill_ref2.mp4": {
        "fps": 30.0, "total_frames": 126,
        "events": [{"ability": "mark", "cast_start_frame": 35, "cast_start_seconds": 1.17, "outcome": "completed"}]
    },
    "hidden_movement_chasing.mp4": {"fps": 30.0, "total_frames": 304, "events": []},
    "hidden_movement_chasing2.mp4": {"fps": 30.0, "total_frames": 142, "events": []},
}

for vname, vmeta in events_map.items():
    if vname not in data["videos"]:
        data["videos"][vname] = {
            "fps": vmeta["fps"],
            "total_frames": vmeta["total_frames"],
            "duration_seconds": round(vmeta["total_frames"] / vmeta["fps"], 2),
            "events": vmeta["events"]
        }
    else:
        data["videos"][vname]["events"] = vmeta["events"]

with open(temporal_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Updated temporal_annotations.json with ground-truth events across all 18 videos!")
