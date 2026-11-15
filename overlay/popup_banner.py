"""Popup Banner Overlay Widget for Violence District Cooldown Tracker.

Displays stylized killer ability banners popping up smoothly from the left edge of the screen
with realistic physics-based bounce animations (matching 'OVERLAY UI/POP UP OVERLAY EXAMPLE.mov')
and large crisp digital countdown text in the designated black area (matching 'OVERLAY UI/example_countdown_time.png').
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from app.logger import get_logger
from cooldown.cooldown_state import CooldownSnapshot, CooldownState

logger = get_logger("overlay.banner")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OVERLAY_UI_DIR = PROJECT_ROOT / "OVERLAY UI"

# Explicit mapping from (killer_id, ability_id) to PNG filename in OVERLAY UI/
BANNER_FILE_MAP: Dict[Tuple[str, str], str] = {
    ("the_hidden", "leap"): "hidden_leap.png",
    ("the_hidden", "mark"): "hidden_mark.png",
    ("the_abysswalker", "dark_severance"): "abyss_darkseverance.png",
    ("the_abysswalker", "abyssal_burst"): "abyss_abyysalburst.png",
    ("the_butcher", "your_heart_is_mine"): "butcher_yourheartismine.png",
    ("the_slasher", "lake_mist"): "slasher_lakemist.png",
    ("the_slasher", "pursuit"): "jason_pursuit.png",
    ("the_stalker", "evils_grasp"): "myers_evilgrasp.png",
    ("veil", "through_the_veil"): "veil_throughtheveil.png",
    ("the_masked", "mask_duration"): "mask_maskup.png",
    ("the_masked", "mask_swap"): "mask_maskswap.png",
    ("the_killer", "frenzy"): "thekiller_frenzy.png",
}

# Keyword fallbacks for partial matching
KEYWORD_BANNER_FALLBACKS = [
    ("leap", "hidden_leap.png"),
    ("mark", "hidden_mark.png"),
    ("dark_severance", "abyss_darkseverance.png"),
    ("severance", "abyss_darkseverance.png"),
    ("abyssal_burst", "abyss_abyysalburst.png"),
    ("burst", "abyss_abyysalburst.png"),
    ("your_heart_is_mine", "butcher_yourheartismine.png"),
    ("heart", "butcher_yourheartismine.png"),
    ("hook", "butcher_yourheartismine.png"),
    ("lake_mist", "slasher_lakemist.png"),
    ("mist", "slasher_lakemist.png"),
    ("pursuit", "jason_pursuit.png"),
    ("jason", "jason_pursuit.png"),
    ("evils_grasp", "myers_evilgrasp.png"),
    ("grasp", "myers_evilgrasp.png"),
    ("myers", "myers_evilgrasp.png"),
    ("through_the_veil", "veil_throughtheveil.png"),
    ("veil", "veil_throughtheveil.png"),
    ("spear", "veil_throughtheveil.png"),
    ("mask_duration", "mask_maskup.png"),
    ("mask_up", "mask_maskup.png"),
    ("mask_swap", "mask_maskswap.png"),
    ("swap_mask", "mask_maskswap.png"),
    ("change_mask", "mask_maskswap.png"),
    ("mask", "mask_maskup.png"),
    ("frenzy", "thekiller_frenzy.png"),
    ("thekiller", "thekiller_frenzy.png"),
    ("jeff", "thekiller_frenzy.png"),
]


def resolve_banner_path(killer_id: str, ability_id: str) -> Optional[Path]:
    """Finds the matching banner image file path on disk."""
    k_norm = (killer_id or "").strip().lower()
    a_norm = (ability_id or "").strip().lower()

    # 1. Exact tuple lookup
    filename = BANNER_FILE_MAP.get((k_norm, a_norm))
    if filename:
        p = OVERLAY_UI_DIR / filename
        if p.exists():
            return p

    # 2. Keyword fallback lookup
    for kw, fname in KEYWORD_BANNER_FALLBACKS:
        if kw in a_norm or kw in k_norm:
            p = OVERLAY_UI_DIR / fname
            if p.exists():
                return p

    # 3. Direct filename match if ability_id matches filename
    for candidate in OVERLAY_UI_DIR.glob("*.png"):
        c_stem = candidate.stem.lower()
        if a_norm in c_stem or (k_norm and k_norm in c_stem):
            return candidate

    return None


class PopupBannerItem(QWidget):
    """Individual animated popup banner for a single ability cooldown.
    
    Slides in from the left with OutBack overshoot curve when active,
    and slides out to the left with InBack curve when finished or reset.
    """

    animation_completed = Signal(str, str)  # (ability_id, state)

    BANNER_WIDTH = 296
    BANNER_HEIGHT = 158

    def __init__(
        self,
        slot_index: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.slot_index = slot_index
        self._killer_id = ""
        self._ability_id = ""
        self._ability_name = ""
        self._banner_pixmap: Optional[QPixmap] = None
        self._snapshot: Optional[CooldownSnapshot] = None

        self._rest_x = 24
        self._hidden_x = -self.BANNER_WIDTH - 30
        self._rest_y = 10 + (slot_index * (self.BANNER_HEIGHT + 16))

        self.resize(self.BANNER_WIDTH, self.BANNER_HEIGHT)
        self.move(self._hidden_x, self._rest_y)

        # Property Animation for slide in / slide out
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.finished.connect(self._on_animation_finished)

        self._state = "HIDDEN"  # "HIDDEN", "SLIDING_IN", "ACTIVE", "SLIDING_OUT"
        self._calibration_mode = False

        # Visual color palette
        self.COLOR_COUNTDOWN_ACTIVE = QColor(255, 240, 245)    # Crisp Crimson-White
        self.COLOR_COUNTDOWN_WARN = QColor(251, 191, 36)        # Amber Yellow (< 5s)
        self.COLOR_COUNTDOWN_READY = QColor(52, 211, 153)       # Neon Emerald Green
        self.COLOR_COUNTDOWN_SHADOW = QColor(0, 0, 0, 230)      # Shadow for contrast
        self.COLOR_CALIB_BORDER = QColor(250, 204, 21, 220)     # Neon Gold Calibration Outline

        self.hide()

    @property
    def ability_id(self) -> str:
        return self._ability_id

    @property
    def killer_id(self) -> str:
        return self._killer_id

    @property
    def snapshot(self) -> Optional[CooldownSnapshot]:
        return self._snapshot

    def set_ability(self, killer_id: str, ability_id: str, ability_name: str) -> None:
        """Sets the ability and loads its corresponding banner asset."""
        if self._killer_id == killer_id and self._ability_id == ability_id:
            return

        self._killer_id = killer_id
        self._ability_id = ability_id
        self._ability_name = ability_name

        banner_path = resolve_banner_path(killer_id, ability_id)
        if banner_path and banner_path.exists():
            raw_pix = QPixmap(str(banner_path))
            if not raw_pix.isNull():
                self._banner_pixmap = raw_pix.scaled(
                    self.BANNER_WIDTH,
                    self.BANNER_HEIGHT,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation,
                )
                logger.debug("Loaded banner pixmap for %s/%s from %s", killer_id, ability_id, banner_path.name)
            else:
                self._banner_pixmap = None
        else:
            self._banner_pixmap = None
            logger.debug("No banner image found for %s/%s. Using procedural fallback.", killer_id, ability_id)

        self.update()

    def set_slot_index(self, slot_index: int) -> None:
        """Updates the vertical slot position."""
        self.slot_index = slot_index
        self._rest_y = 10 + (slot_index * (self.BANNER_HEIGHT + 16))
        if self._state == "ACTIVE" or self._calibration_mode:
            self.move(self._rest_x, self._rest_y)
        else:
            self.move(self._hidden_x, self._rest_y)

    def set_calibration_mode(self, enabled: bool) -> None:
        """Toggles calibration preview mode."""
        self._calibration_mode = enabled
        self._anim.stop()
        if enabled:
            self.show()
            self.move(self._rest_x, self._rest_y)
            self._state = "ACTIVE"
        else:
            # If not active cooldown, return to hidden position
            if self._snapshot is None or self._snapshot.state != CooldownState.COOLDOWN:
                self.move(self._hidden_x, self._rest_y)
                self.hide()
                self._state = "HIDDEN"
        self.update()

    def slide_in(self) -> None:
        """Plays slide-in animation from left to right with OutBack easing curve."""
        if self._calibration_mode:
            return

        self._anim.stop()
        self._state = "SLIDING_IN"
        self.show()

        start_pt = QPoint(self._hidden_x, self._rest_y)
        end_pt = QPoint(self._rest_x, self._rest_y)

        self._anim.setDuration(620)
        self._anim.setStartValue(start_pt)
        self._anim.setEndValue(end_pt)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.start()
        logger.debug("Slide-in animation started for %s (%s)", self._ability_name, self._ability_id)

    def slide_out(self) -> None:
        """Plays slide-out animation to the left with InBack anticipation curve."""
        if self._calibration_mode:
            return

        if self._state == "HIDDEN":
            return

        self._anim.stop()
        self._state = "SLIDING_OUT"

        start_pt = self.pos()
        end_pt = QPoint(self._hidden_x, self._rest_y)

        self._anim.setDuration(520)
        self._anim.setStartValue(start_pt)
        self._anim.setEndValue(end_pt)
        self._anim.setEasingCurve(QEasingCurve.Type.InBack)
        self._anim.start()
        logger.debug("Slide-out animation started for %s (%s)", self._ability_name, self._ability_id)

    def _on_animation_finished(self) -> None:
        """Callback when slide animation completes."""
        if self._state == "SLIDING_IN":
            self._state = "ACTIVE"
            self.move(self._rest_x, self._rest_y)
            self.animation_completed.emit(self._ability_id, "ACTIVE")
        elif self._state == "SLIDING_OUT":
            self._state = "HIDDEN"
            self.hide()
            self.move(self._hidden_x, self._rest_y)
            self.animation_completed.emit(self._ability_id, "HIDDEN")

    def update_snapshot(self, snapshot: CooldownSnapshot) -> None:
        """Updates cooldown snapshot and handles animation triggers."""
        old_state = self._snapshot.state if self._snapshot else CooldownState.READY
        self._snapshot = snapshot
        new_state = snapshot.state

        # Check transition to COOLDOWN -> Slide in!
        if old_state != CooldownState.COOLDOWN and new_state == CooldownState.COOLDOWN:
            self.slide_in()
        # Check transition from COOLDOWN -> READY (or reset) -> Slide out!
        elif old_state == CooldownState.COOLDOWN and new_state == CooldownState.READY:
            self.slide_out()

        self.update()

    def paintEvent(self, event) -> None:
        """Renders the banner template and the digital countdown in the black area."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # 1. Background Banner Image (or procedural fallback)
        if self._banner_pixmap is not None:
            painter.drawPixmap(0, 0, w, h, self._banner_pixmap)
        else:
            self._draw_procedural_banner(painter, w, h)

        # 2. Digital Countdown in Black Area (Right side)
        # Based on exact measurement of 'example_countdown_time.png':
        # Digit center: X = ~81.1%, Y = ~81.8% of banner dimensions
        box_w = int(w * 0.24)
        box_h = int(h * 0.28)
        target_x = int((w * 0.811) - (box_w / 2.0))
        target_y = int((h * 0.818) - (box_h / 2.0))
        target_rect = QRect(target_x, target_y, box_w, box_h)

        self._draw_countdown_text(painter, target_rect)

        # 3. Calibration Mode Border & Handle
        if self._calibration_mode:
            painter.setPen(QPen(self.COLOR_CALIB_BORDER, 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)

            # Slot indicator
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(self.COLOR_CALIB_BORDER)
            painter.drawText(
                QRect(8, 6, w - 16, 20),
                Qt.AlignLeft | Qt.AlignTop,
                f"⚙️ Slot {self.slot_index + 1}: {self._ability_name or 'Ability'}",
            )

        painter.end()

    def _draw_procedural_banner(self, painter: QPainter, w: int, h: int) -> None:
        """Draws a sleek procedural dark banner if no custom PNG is present."""
        rect = QRectF(0, 0, w, h)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(24, 24, 32, 245))
        grad.setColorAt(0.65, QColor(14, 14, 18, 250))
        grad.setColorAt(1.0, QColor(6, 6, 8, 255))
        painter.setBrush(grad)
        painter.setPen(QPen(QColor(60, 60, 75, 200), 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        # Decorative left accent bar
        painter.setBrush(QColor(220, 38, 38, 220))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(QRectF(4, 8, 6, h - 16), 3, 3)

        # Ability title
        painter.setFont(QFont("Segoe UI Black", 14, QFont.Bold))
        painter.setPen(QColor(248, 250, 252))
        painter.drawText(QRect(20, 20, int(w * 0.55), 30), Qt.AlignLeft | Qt.AlignVCenter, self._ability_name.upper())

        # Subtitle
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(QRect(20, 52, int(w * 0.55), 20), Qt.AlignLeft | Qt.AlignVCenter, f"[{self._killer_id.upper()}]")

    def _draw_countdown_text(self, painter: QPainter, target_rect: QRect) -> None:
        """Renders the countdown numbers inside the designated black area."""
        if self._calibration_mode:
            # Preview numbers during calibration
            rem = 25.0 if self.slot_index == 0 else 30.0
            display_str = f"{int(rem)}"
            text_color = self.COLOR_COUNTDOWN_ACTIVE
        elif self._snapshot is not None:
            state = self._snapshot.state
            rem = self._snapshot.remaining_seconds

            if state == CooldownState.COOLDOWN:
                if rem >= 10.0:
                    display_str = f"{int(rem)}"
                elif rem > 0.0:
                    display_str = f"{rem:.1f}"
                else:
                    display_str = "0"

                if rem <= 5.0:
                    text_color = self.COLOR_COUNTDOWN_WARN
                else:
                    text_color = self.COLOR_COUNTDOWN_ACTIVE
            elif state == CooldownState.READY:
                display_str = "READY"
                text_color = self.COLOR_COUNTDOWN_READY
            elif state == CooldownState.WAITING_FOR_RELEASE:
                display_str = "HOLD"
                text_color = self.COLOR_COUNTDOWN_WARN
            else:
                display_str = ""
                text_color = self.COLOR_COUNTDOWN_ACTIVE
        else:
            return

        if not display_str:
            return

        # Adaptive font sizing
        font_size = 28 if len(display_str) <= 2 else (22 if len(display_str) <= 4 else 15)
        font = QFont("Segoe UI Black", font_size, QFont.Bold)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)

        # Drop shadow for readability
        painter.setPen(self.COLOR_COUNTDOWN_SHADOW)
        painter.drawText(target_rect.translated(2, 2), Qt.AlignCenter, display_str)

        # Primary countdown number
        painter.setPen(text_color)
        painter.drawText(target_rect, Qt.AlignCenter, display_str)
