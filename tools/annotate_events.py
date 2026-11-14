"""Interactive OpenCV Video Scrubber & Event Annotator.

Violence District Cooldown Tracker — Detector Rebuild (Phase 1)
Allows human annotators to scrub video footage frame-by-frame and tag
ground-truth 'cast_start_frame' for Leap and Mark abilities.

Controls:
  [A] / [D]      : Step backward / forward 1 frame
  [W] / [S]      : Step backward / forward 10 frames
  [Space]        : Toggle Play / Pause
  [L]            : Tag current frame as LEAP cast start
  [M]            : Tag current frame as MARK cast start
  [O]            : Toggle event outcome (completed -> hit -> miss -> hit_wall)
  [C]            : Clear events for this video
  [Enter]        : Save events to dataset/temporal_annotations.json
  [Q] / [Esc]    : Quit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPORAL_PATH = PROJECT_ROOT / "dataset" / "temporal_annotations.json"
OUTCOMES = ["completed", "hit", "miss", "hit_wall", "interrupted"]


class VideoEventAnnotator:
    """Anotator event interaktif OpenCV dengan visual HUD dan trackbar slider."""

    def __init__(
        self,
        video_path: Path,
        annotations_json: Path = DEFAULT_TEMPORAL_PATH,
    ) -> None:
        self.video_path = Path(video_path).resolve()
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.annotations_json = Path(annotations_json).resolve()
        self.cap = cv2.VideoCapture(str(self.video_path))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.current_frame_idx = 0
        self.is_playing = False
        self.current_outcome_idx = 0
        self.events: List[Dict[str, Any]] = []

        self._load_existing_events()

    def _load_existing_events(self) -> None:
        if self.annotations_json.exists():
            try:
                with open(self.annotations_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                v_entry = data.get("videos", {}).get(self.video_path.name, {})
                self.events = list(v_entry.get("events", []))
            except Exception:
                self.events = []

    def save_events(self) -> None:
        """Menyimpan events ke dataset/temporal_annotations.json."""
        self.annotations_json.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {"schema_version": 1, "killer_id": "the_hidden", "videos": {}}
        if self.annotations_json.exists():
            try:
                with open(self.annotations_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if "videos" not in data:
            data["videos"] = {}

        vname = self.video_path.name
        if vname not in data["videos"]:
            data["videos"][vname] = {
                "fps": float(self.fps),
                "total_frames": int(self.total_frames),
                "duration_seconds": round(self.total_frames / self.fps, 2),
                "events": [],
            }

        data["videos"][vname]["events"] = self.events
        with open(self.annotations_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n[SAVED] Successfully saved {len(self.events)} event(s) for '{vname}' to {self.annotations_json}")

    def run(self) -> None:
        """Menjalankan loop interaktif window OpenCV."""
        win_name = f"VD Event Scrubber - {self.video_path.name}"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 1280, 720)

        def on_trackbar(val: int) -> None:
            self.current_frame_idx = max(0, min(val, self.total_frames - 1))

        cv2.createTrackbar("Frame", win_name, 0, max(1, self.total_frames - 1), on_trackbar)

        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
            ret, frame = self.cap.read()
            if not ret:
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

            display = frame.copy()
            h, w = display.shape[:2]

            # Top HUD bar
            cv2.rectangle(display, (0, 0), (w, 50), (20, 20, 20), -1)
            sec = self.current_frame_idx / self.fps
            hud_txt = f"{self.video_path.name} | Frame: {self.current_frame_idx}/{self.total_frames - 1} ({sec:.2f}s) | FPS: {self.fps:.1f}"
            cv2.putText(display, hud_txt, (15, 32), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1)

            # Marked events indicator
            outcome_curr = OUTCOMES[self.current_outcome_idx]
            status_txt = f"Active Outcome: [{outcome_curr}] | Marked Events: {len(self.events)}"
            cv2.putText(display, status_txt, (w - 450, 32), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 255), 1)

            # Bottom instructions bar
            cv2.rectangle(display, (0, h - 36), (w, h), (15, 15, 15), -1)
            inst_txt = "[L] Mark Leap | [M] Mark Mark | [O] Toggle Outcome | [Space] Play/Pause | [Enter] Save | [Q] Quit"
            cv2.putText(display, inst_txt, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)

            # Render marked events on screen
            for ev in self.events:
                cf = ev["cast_start_frame"]
                ab = ev["ability"].upper()
                out = ev.get("outcome", "")
                if abs(self.current_frame_idx - cf) <= 5:
                    tag = f">> TRIGGER {ab} (Frame {cf}, {out}) <<"
                    cv2.putText(display, tag, (w // 2 - 180, 100), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 255), 2)

            cv2.imshow(win_name, display)
            cv2.setTrackbarPos("Frame", win_name, self.current_frame_idx)

            key = cv2.waitKey(30 if self.is_playing else 15) & 0xFF
            if key in [ord("q"), ord("Q"), 27]:  # Esc or Q
                break
            elif key == ord(" "):
                self.is_playing = not self.is_playing
            elif key in [ord("d"), ord("D")]:
                self.current_frame_idx = min(self.total_frames - 1, self.current_frame_idx + 1)
            elif key in [ord("a"), ord("A")]:
                self.current_frame_idx = max(0, self.current_frame_idx - 1)
            elif key in [ord("w"), ord("W")]:
                self.current_frame_idx = min(self.total_frames - 1, self.current_frame_idx + 10)
            elif key in [ord("s"), ord("S")]:
                self.current_frame_idx = max(0, self.current_frame_idx - 10)
            elif key in [ord("l"), ord("L")]:
                self._add_event("leap")
            elif key in [ord("m"), ord("M")]:
                self._add_event("mark")
            elif key in [ord("o"), ord("O")]:
                self.current_outcome_idx = (self.current_outcome_idx + 1) % len(OUTCOMES)
            elif key in [ord("c"), ord("C")]:
                self.events.clear()
                print("\n[CLEARED] Cleared all events for current video.")
            elif key in [10, 13]:  # Enter
                self.save_events()

            if self.is_playing:
                self.current_frame_idx += 1
                if self.current_frame_idx >= self.total_frames:
                    self.current_frame_idx = 0
                    self.is_playing = False

        self.cap.release()
        cv2.destroyAllWindows()

    def _add_event(self, ability: str) -> None:
        outcome = OUTCOMES[self.current_outcome_idx]
        sec = round(self.current_frame_idx / self.fps, 3)
        evt = {
            "ability": ability,
            "cast_start_frame": int(self.current_frame_idx),
            "cast_start_seconds": sec,
            "outcome": outcome,
        }
        self.events.append(evt)
        print(f"\n[EVENT ADDED] {ability.upper()} @ Frame {self.current_frame_idx} ({sec:.2f}s) | Outcome: {outcome}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive OpenCV Video Event Scrubber")
    parser.add_argument("video", nargs="?", default="", help="Path ke file video MP4")
    args = parser.parse_args()

    vpath = Path(args.video) if args.video else Path("database/dataset/HIDDEN/MP4/SURVIVOR CAM/hidden1_leap_skill.mp4")
    if not vpath.exists():
        print(f"File video tidak ditemukan: {vpath}")
        sys.exit(1)

    annotator = VideoEventAnnotator(vpath)
    annotator.run()
