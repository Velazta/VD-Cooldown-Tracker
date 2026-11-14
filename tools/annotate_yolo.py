"""Interactive YOLO Bounding Box Annotator & Reviewer.

Violence District Cooldown Tracker — Rebuild Phase 2 (Task 2.2)
Zero-dependency desktop annotator using OpenCV HighGUI.
Allows human annotators to draw, correct, and verify bounding boxes for:
- Class 0: 'hidden' (Green box)
- Class 1: 'survivor' (Blue box)

Controls:
  Mouse Drag     : Draw bounding box on current image
  [0] / [H]      : Switch active class to 0 (Hidden)
  [1] / [V]      : Switch active class to 1 (Survivor)
  [A] / [Left]   : Save & Go to Previous Image
  [D] / [Right]  : Save & Go to Next Image
  [Z]            : Undo last bounding box
  [C]            : Clear all bounding boxes on current image
  [S]            : Force save current annotations
  [Q] / [Esc]    : Save & Quit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

CLASS_NAMES = {0: "hidden", 1: "survivor"}
CLASS_COLORS = {
    0: (0, 255, 0),    # Green for Hidden
    1: (255, 128, 0),  # Blue/Cyan for Survivor
}


class YoloAnnotatorGUI:
    def __init__(self, dataset_dir: Path = Path("dataset/yolo"), split: str = "train") -> None:
        self.dataset_dir = Path(dataset_dir)
        self.split = split
        self.img_dir = self.dataset_dir / "images" / split
        self.lbl_dir = self.dataset_dir / "labels" / split

        if not self.img_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {self.img_dir}")
        self.lbl_dir.mkdir(parents=True, exist_ok=True)

        self.image_paths = sorted(list(self.img_dir.glob("*.jpg")) + list(self.img_dir.glob("*.png")))
        if not self.image_paths:
            raise FileNotFoundError(f"No images found in: {self.img_dir}")

        self.current_idx = 0
        self.active_class = 0  # 0: hidden, 1: survivor

        # Mouse state
        self.drawing = False
        self.start_pt: Optional[Tuple[int, int]] = None
        self.current_pt: Optional[Tuple[int, int]] = None

        # Boxes for current image: List of (class_id, xc, yc, w, h) normalized
        self.boxes: List[Tuple[int, float, float, float, float]] = []
        self.window_name = f"YOLO Annotator [{self.split.upper()}] - VD Cooldown Tracker"

        self._load_current_image_and_labels()

    def _load_current_image_and_labels(self) -> None:
        self.current_img_path = self.image_paths[self.current_idx]
        self.current_img = cv2.imread(str(self.current_img_path))
        if self.current_img is None:
            raise RuntimeError(f"Failed to read image: {self.current_img_path}")

        self.h, self.w = self.current_img.shape[:2]
        self.lbl_path = self.lbl_dir / f"{self.current_img_path.stem}.txt"

        self.boxes = []
        if self.lbl_path.exists():
            content = self.lbl_path.read_text(encoding="utf-8").strip()
            if content:
                for line in content.splitlines():
                    tokens = line.strip().split()
                    if len(tokens) == 5:
                        try:
                            cid = int(tokens[0])
                            xc, yc, bw, bh = map(float, tokens[1:])
                            if cid in (0, 1) and (0 <= xc <= 1) and (0 <= yc <= 1):
                                self.boxes.append((cid, xc, yc, bw, bh))
                        except ValueError:
                            pass

    def _save_current_labels(self) -> None:
        lines = []
        for cid, xc, yc, bw, bh in self.boxes:
            lines.append(f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        self.lbl_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param: Any) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_pt = (x, y)
            self.current_pt = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            self.current_pt = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and self.drawing:
            self.drawing = False
            if self.start_pt and self.current_pt:
                x1, y1 = self.start_pt
                x2, y2 = x, y
                xmin, xmax = min(x1, x2), max(x1, x2)
                ymin, ymax = min(y1, y2), max(y1, y2)
                box_w = xmax - xmin
                box_h = ymax - ymin

                # Minimum size threshold (at least 6x6 pixels)
                if box_w >= 6 and box_h >= 6:
                    xc = (xmin + box_w / 2.0) / self.w
                    yc = (ymin + box_h / 2.0) / self.h
                    norm_w = box_w / self.w
                    norm_h = box_h / self.h
                    self.boxes.append((self.active_class, xc, yc, norm_w, norm_h))
            self.start_pt = None
            self.current_pt = None

    def render(self) -> np.ndarray:
        display = self.current_img.copy()

        # Draw existing boxes
        for cid, xc, yc, bw, bh in self.boxes:
            color = CLASS_COLORS.get(cid, (0, 255, 0))
            name = CLASS_NAMES.get(cid, str(cid))
            px_w = int(bw * self.w)
            px_h = int(bh * self.h)
            px_x1 = int((xc * self.w) - (px_w / 2.0))
            px_y1 = int((yc * self.h) - (px_h / 2.0))
            px_x2 = px_x1 + px_w
            px_y2 = px_y1 + px_h

            cv2.rectangle(display, (px_x1, px_y1), (px_x2, px_y2), color, 2)
            cv2.putText(
                display,
                f"{cid}:{name}",
                (px_x1, max(15, px_y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
                cv2.LINE_AA,
            )

        # Draw ongoing box drag
        if self.drawing and self.start_pt and self.current_pt:
            color = CLASS_COLORS.get(self.active_class, (0, 255, 0))
            cv2.rectangle(display, self.start_pt, self.current_pt, color, 1)

        # Draw HUD overlay
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, 42), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, display, 0.25, 0, display)

        title = f"[{self.current_idx + 1}/{len(self.image_paths)}] {self.current_img_path.name}"
        cv2.putText(display, title, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        active_str = f"Active: [{self.active_class}] {CLASS_NAMES[self.active_class].upper()}"
        act_col = CLASS_COLORS[self.active_class]
        cv2.putText(display, active_str, (self.w - 280, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, act_col, 2)

        # Bottom help bar
        help_bar = display.copy()
        cv2.rectangle(help_bar, (0, self.h - 30), (self.w, self.h), (20, 20, 20), -1)
        cv2.addWeighted(help_bar, 0.75, display, 0.25, 0, display)

        help_text = "[0] Hidden  [1] Survivor  |  [A/D] Prev/Next  |  [Z] Undo  [C] Clear  [S] Save  [Q] Quit"
        cv2.putText(display, help_text, (10, self.h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return display

    def run(self) -> None:
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        print(f"Launching YOLO Annotator for split '{self.split}'...")
        print("Controls: Mouse drag to box, [0]=Hidden, [1]=Survivor, [A]/[D]=Nav, [Z]=Undo, [C]=Clear, [Q]=Quit")

        while True:
            display = self.render()
            cv2.imshow(self.window_name, display)

            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                self._save_current_labels()
                break
            elif key in (ord("0"), ord("h"), ord("H")):
                self.active_class = 0
            elif key in (ord("1"), ord("v"), ord("V"), ord("s"), ord("S")) and key not in (ord("s"), ord("S")):
                self.active_class = 1
            elif key in (ord("d"), ord("D"), 83):  # D or Right Arrow
                self._save_current_labels()
                if self.current_idx < len(self.image_paths) - 1:
                    self.current_idx += 1
                    self._load_current_image_and_labels()
            elif key in (ord("a"), ord("A"), 81):  # A or Left Arrow
                self._save_current_labels()
                if self.current_idx > 0:
                    self.current_idx -= 1
                    self._load_current_image_and_labels()
            elif key in (ord("z"), ord("Z")):
                if self.boxes:
                    self.boxes.pop()
            elif key in (ord("c"), ord("C")):
                self.boxes.clear()
            elif key in (ord("s"), ord("S")):
                self._save_current_labels()
                print(f"Saved: {self.lbl_path.name} ({len(self.boxes)} boxes)")

        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive YOLO Bounding Box Annotator.")
    parser.add_argument("--dataset", default="dataset/yolo", help="Path to YOLO dataset directory")
    parser.add_argument("--split", default="train", choices=["train", "val", "test"], help="Dataset split to annotate")
    args = parser.parse_args()

    gui = YoloAnnotatorGUI(dataset_dir=Path(args.dataset), split=args.split)
    gui.run()


if __name__ == "__main__":
    main()
