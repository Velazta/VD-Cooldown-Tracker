"""Multi-Ability Cooldown Indicator & Popup Banner Widget for Transparent Overlay.

Violence District Cooldown Tracker — Week 2 / Manual Milestone (Phase M4)
Features:
- Individual popup banners with realistic physics-based bounce animations (OutBack appear, InBack dismiss)
- High-resolution killer ability banner templates loaded from 'OVERLAY UI/'
- Precise digital countdown timer rendered in the designated black area
- Per-ability independent popups (only appears when triggered; disappears on expiry/reset)
- Calibration mode with interactive drag-and-drop repositioning
"""

from __future__ import annotations

import sys
import time
from typing import Dict, List, Optional, Union

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.logger import get_logger
from cooldown.cooldown_state import CooldownSnapshot, CooldownState
from overlay.popup_banner import PopupBannerItem

logger = get_logger("overlay.widget")

try:
    import winsound
except ImportError:
    winsound = None


class CooldownWidget(QWidget):
    """Custom PySide6 Widget for multi-ability popup banner cooldown display."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._snapshots: List[CooldownSnapshot] = []
        self._prev_states: Dict[str, CooldownState] = {}
        self._blink_until: Dict[str, float] = {}
        self.sound_on_ready: bool = False
        self._calibration_mode: bool = False
        self.use_popup_banners: bool = True

        self._banner_items: Dict[str, PopupBannerItem] = {}

        self.setMinimumSize(120, 120)

        # Visual Palette (Legacy fallback)
        self.COLOR_BG = QColor(14, 14, 18, 210)
        self.COLOR_BORDER = QColor(46, 46, 56, 180)
        self.COLOR_TRACK = QColor(36, 36, 46, 180)
        self.COLOR_READY = QColor(16, 185, 129, 255)
        self.COLOR_COOLDOWN = QColor(239, 68, 68, 255)
        self.COLOR_WARNING = QColor(245, 158, 11, 255)
        self.COLOR_AIMING = QColor(245, 158, 11, 240)
        self.COLOR_DISABLED = QColor(100, 116, 139, 180)
        self.COLOR_TEXT_MAIN = QColor(248, 250, 252, 255)
        self.COLOR_TEXT_SUB = QColor(148, 163, 184, 230)
        self.COLOR_BADGE_BG = QColor(30, 30, 40, 220)

    def set_sound_on_ready(self, enabled: bool) -> None:
        """Enables or disables audio notification when an ability becomes ready."""
        self.sound_on_ready = bool(enabled)

    def set_calibration_mode(self, enabled: bool) -> None:
        """Toggles calibration mode for all child banner items."""
        self._calibration_mode = enabled
        for item in self._banner_items.values():
            item.set_calibration_mode(enabled)
        self.update()

    def update_snapshot(self, snapshot: CooldownSnapshot) -> None:
        """Backward-compatible single snapshot updater."""
        self.update_snapshots([snapshot])

    def update_snapshots(
        self,
        snapshots: Union[Dict[str, CooldownSnapshot], List[CooldownSnapshot]],
    ) -> None:
        """Updates multiple ability snapshots and handles state transition triggers."""
        if isinstance(snapshots, dict):
            new_list = list(snapshots.values())
        else:
            new_list = list(snapshots)

        now = time.monotonic()
        active_ids = {snap.ability_id for snap in new_list}

        # Remove banner items that no longer exist for the current killer
        for ab_id in list(self._banner_items.keys()):
            if ab_id not in active_ids:
                item = self._banner_items.pop(ab_id)
                item.setParent(None)
                item.deleteLater()

        # Update or create banner items for each active ability
        for idx, snap in enumerate(new_list):
            ab_id = snap.ability_id
            old_state = self._prev_states.get(ab_id)

            if ab_id not in self._banner_items:
                item = PopupBannerItem(slot_index=idx, parent=self)
                item.set_calibration_mode(self._calibration_mode)
                self._banner_items[ab_id] = item

            item = self._banner_items[ab_id]
            item.set_slot_index(idx)
            item.set_ability(snap.killer_id, snap.ability_id, snap.ability_name)
            item.update_snapshot(snap)

            # Check transition from COOLDOWN -> READY
            if old_state == CooldownState.COOLDOWN and snap.state == CooldownState.READY:
                self._blink_until[ab_id] = now + 0.4
                if self.sound_on_ready:
                    self._play_ready_sound()

            self._prev_states[ab_id] = snap.state

        self._snapshots = new_list

        # Notify parent OverlayWindow to adjust size if slot count changed
        parent_win = self.parent()
        if parent_win is not None and hasattr(parent_win, "set_slot_count"):
            parent_win.set_slot_count(max(1, len(new_list)))

        self.update()

    def reset_banners(self) -> None:
        """Slides out all currently active popup banners immediately."""
        for item in self._banner_items.values():
            item.slide_out()

    def _play_ready_sound(self) -> None:
        """Plays a gentle ready notification beep without external dependencies."""
        try:
            if winsound is not None and sys.platform == "win32":
                winsound.Beep(1200, 120)  # 1200 Hz for 120 ms
            else:
                from PySide6.QtWidgets import QApplication
                QApplication.beep()
        except Exception as exc:
            logger.debug("Failed to play sound: %s", exc)

    @property
    def snapshot(self) -> Optional[CooldownSnapshot]:
        """Backward-compatible single snapshot property."""
        return self._snapshots[0] if self._snapshots else None

    @property
    def snapshots(self) -> List[CooldownSnapshot]:
        return list(self._snapshots)

    def paintEvent(self, event) -> None:
        """Background drawing for the container widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # If not using popup banners, draw legacy rows (for backwards compatibility)
        if not self.use_popup_banners:
            card_rect = QRectF(2.0, 2.0, w - 4.0, h - 4.0)
            painter.setPen(QPen(self.COLOR_BORDER, 1.2))
            painter.setBrush(self.COLOR_BG)
            painter.drawRoundedRect(card_rect, 10.0, 10.0)

            if not self._snapshots:
                painter.setPen(self.COLOR_TEXT_SUB)
                painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
                painter.drawText(card_rect, Qt.AlignCenter, "NO ACTIVE ABILITIES")
                painter.end()
                return

            now = time.monotonic()
            count = len(self._snapshots)
            row_h = (h - 16.0) / float(count)
            for i, snap in enumerate(self._snapshots):
                row_y = 8.0 + (i * row_h)
                self._draw_legacy_ability_row(painter, snap, row_y, row_h, w, now)
        else:
            # When using popup banners, the child PopupBannerItem widgets paint themselves.
            # In calibration mode, draw a subtle container guide
            if self._calibration_mode:
                calib_rect = QRectF(2.0, 2.0, w - 4.0, h - 4.0)
                painter.setPen(QPen(QColor(250, 204, 21, 140), 1.5, Qt.DashLine))
                painter.setBrush(QColor(10, 10, 15, 80))
                painter.drawRoundedRect(calib_rect, 8.0, 8.0)

        painter.end()

    def _draw_legacy_ability_row(
        self,
        painter: QPainter,
        snap: CooldownSnapshot,
        row_y: float,
        row_h: float,
        width: float,
        now: float,
    ) -> None:
        """Renders one row in legacy mode."""
        margin_x = 14.0
        content_w = width - (margin_x * 2.0)
        state = snap.state
        rem = snap.remaining_seconds
        total = snap.total_cooldown_seconds
        is_blinking = (now < self._blink_until.get(snap.ability_id, 0.0))

        if state == CooldownState.READY:
            accent_color = QColor(255, 255, 255) if is_blinking else self.COLOR_READY
            time_text = "READY"
        elif state == CooldownState.WAITING_FOR_RELEASE:
            accent_color = self.COLOR_AIMING
            time_text = "HOLD"
        elif state == CooldownState.DISABLED:
            accent_color = self.COLOR_DISABLED
            time_text = "OFF"
        else:
            accent_color = self.COLOR_WARNING if rem <= 5.0 else self.COLOR_COOLDOWN
            time_text = f"{rem:.1f}s"

        title_font_size = max(8, int(row_h * 0.22))
        time_font_size = max(11, int(row_h * 0.32))
        text_top_y = row_y + (row_h * 0.08)
        text_h = row_h * 0.45

        painter.setFont(QFont("Segoe UI", title_font_size, QFont.Bold))
        painter.setPen(self.COLOR_TEXT_MAIN)
        name_str = snap.ability_name.upper()
        if snap.interact_input:
            name_str = f"[{snap.interact_input}] {name_str}"
        name_rect = QRectF(margin_x, text_top_y, content_w * 0.60, text_h)
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, name_str)

        painter.setFont(QFont("Segoe UI", time_font_size, QFont.Bold))
        painter.setPen(accent_color)
        time_rect = QRectF(margin_x + (content_w * 0.50), text_top_y, content_w * 0.50, text_h)
        painter.drawText(time_rect, Qt.AlignRight | Qt.AlignVCenter, time_text)

        bar_y = row_y + (row_h * 0.65)
        bar_h = max(4.0, row_h * 0.16)
        bar_rect = QRectF(margin_x, bar_y, content_w, bar_h)

        painter.setPen(Qt.NoPen)
        painter.setBrush(self.COLOR_TRACK)
        painter.drawRoundedRect(bar_rect, bar_h / 2.0, bar_h / 2.0)

        if state == CooldownState.READY or state == CooldownState.WAITING_FOR_RELEASE:
            fill_w = content_w
        elif state == CooldownState.COOLDOWN:
            fraction = min(1.0, max(0.0, rem / total)) if total > 0 else 0.0
            fill_w = content_w * fraction
        else:
            fill_w = 0.0

        if fill_w > 0:
            fill_rect = QRectF(margin_x, bar_y, fill_w, bar_h)
            painter.setBrush(accent_color)
            painter.drawRoundedRect(fill_rect, bar_h / 2.0, bar_h / 2.0)
