"""Card Picker Carousel Overlay for Violence District Cooldown Tracker.

Displays a full-screen or top-centered transparent album slide / character select
carousel triggered via the 'Insert' global hotkey.
Allows fast killer selection without Alt-Tabbing using Left/Right arrows or mouse,
and confirms via Enter or click.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    Property,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QWidget

from app.logger import get_logger
from capture.window_helper import set_window_capture_invisible
from database.database_manager import DatabaseManager, KillerConfig

logger = get_logger("overlay.card_picker")

# Path to card assets folder
CARD_ASSET_DIR = Path("OVERLAY UI/CARD PICK SYSTEM")

# Mapping of killer_id to card filename
CARD_FILE_MAP: Dict[str, str] = {
    "the_hidden": "HIDDEN CARD.png",
    "veil": "VEIL CARD.png",
    "the_abysswalker": "ABYSS CARD.png",
    "the_slasher": "SLASHER CARD.png",
    "the_butcher": "BUTCHER CARD.png",
    "the_stalker": "MYERS CARD.png",
    "the_masked": "MASK CARD.png",
}


class CardPickerOverlay(QWidget):
    """Transparent overlay window displaying a carousel of killer cards at top-center."""

    killer_selected = Signal(str)  # Emits chosen killer_id
    picker_closed = Signal()

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.db_manager = db_manager or DatabaseManager()
        self._killers: List[KillerConfig] = (
            list(self.db_manager.database.killers)
            if (self.db_manager and self.db_manager.database)
            else []
        )
        self._current_index: int = 0
        self._target_index: int = 0

        # Animation states
        self._slide_offset: float = 0.0
        self._anim_slide = QPropertyAnimation(self, b"slideOffset", self)
        self._anim_slide.finished.connect(self._on_slide_finished)

        self._anim_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_pos.finished.connect(self._on_pos_anim_finished)
        self._is_dismissing = False

        # Cache of loaded card pixmaps
        self._card_pixmaps: Dict[str, QPixmap] = {}
        self._load_all_card_assets()

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Dimensions: 1040 x 290 (Pure floating cards, zero background, zero bottom text)
        self.resize(1040, 290)

        # Hover states for arrows
        self._hover_arrow: Optional[str] = None  # "left" or "right"
        self.setMouseTracking(True)

        self.hide()
        logger.info("CardPickerOverlay initialized with %d killers.", len(self._killers))

    # =========================================================================
    # Properties for Qt Animations
    # =========================================================================

    def get_slide_offset(self) -> float:
        return self._slide_offset

    def set_slide_offset(self, val: float) -> None:
        self._slide_offset = float(val)
        self.update()

    slideOffset = Property(float, get_slide_offset, set_slide_offset)

    # =========================================================================
    # Asset Management
    # =========================================================================

    def _load_all_card_assets(self) -> None:
        """Pre-loads card images into QPixmap cache."""
        for killer in self._killers:
            kid = killer.id
            filename = CARD_FILE_MAP.get(kid)
            if filename:
                card_path = CARD_ASSET_DIR / filename
                if card_path.exists():
                    pix = QPixmap(str(card_path))
                    if not pix.isNull():
                        self._card_pixmaps[kid] = pix
                        continue
            # If not found or failed, will render procedurally
            logger.debug("Card asset for killer '%s' will be procedurally rendered.", kid)

    def set_active_killer(self, killer_id: str) -> None:
        """Sets the initially focused killer in the carousel."""
        for idx, k in enumerate(self._killers):
            if k.id == killer_id:
                self._current_index = idx
                self._target_index = idx
                self._slide_offset = 0.0
                self.update()
                break

    # =========================================================================
    # Navigation & Carousel Logic
    # =========================================================================

    def select_prev(self) -> None:
        """Slides carousel to the previous killer."""
        if not self._killers:
            return
        if self._anim_slide.state() == QPropertyAnimation.State.Running:
            self._anim_slide.stop()
            self._current_index = self._target_index

        self._target_index = (self._current_index - 1) % len(self._killers)

        self._anim_slide.stop()
        self._anim_slide.setDuration(240)
        self._anim_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_slide.setStartValue(1.0)
        self._anim_slide.setEndValue(0.0)
        self._anim_slide.start()

    def select_next(self) -> None:
        """Slides carousel to the next killer."""
        if not self._killers:
            return
        if self._anim_slide.state() == QPropertyAnimation.State.Running:
            self._anim_slide.stop()
            self._current_index = self._target_index

        self._target_index = (self._current_index + 1) % len(self._killers)

        self._anim_slide.stop()
        self._anim_slide.setDuration(240)
        self._anim_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_slide.setStartValue(-1.0)
        self._anim_slide.setEndValue(0.0)
        self._anim_slide.start()

    def _on_slide_finished(self) -> None:
        self._current_index = self._target_index
        self._slide_offset = 0.0
        self.update()

    def confirm_selection(self) -> None:
        """Confirms the currently focused killer and closes overlay."""
        if not self._killers:
            self.slide_out_and_hide()
            return

        chosen_killer = self._killers[self._current_index]
        logger.info("CardPickerOverlay selected killer: '%s' (%s)", chosen_killer.name, chosen_killer.id)
        self.killer_selected.emit(chosen_killer.id)
        self.slide_out_and_hide()

    # =========================================================================
    # Show & Hide Animations (Slide Down / Up)
    # =========================================================================

    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        set_window_capture_invisible(hwnd, invisible=False)

    def slide_in_and_show(self) -> None:
        """Opens the overlay with a smooth slide-down spring bounce."""
        self._is_dismissing = False
        screen = QApplication.primaryScreen()
        screen_geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)

        # Center horizontally at top
        target_x = max(0, (screen_geo.width() - self.width()) // 2)
        target_y = 28  # Resting position below screen top edge

        start_pos = QPoint(target_x, -self.height() - 20)
        end_pos = QPoint(target_x, target_y)

        self.move(start_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        self._anim_pos.stop()
        self._anim_pos.setDuration(480)
        self._anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim_pos.setStartValue(start_pos)
        self._anim_pos.setEndValue(end_pos)
        self._anim_pos.start()
        logger.debug("CardPickerOverlay sliding in.")

    def slide_out_and_hide(self) -> None:
        """Closes the overlay with a smooth slide-up exit."""
        if not self.isVisible() or self._is_dismissing:
            return

        self._is_dismissing = True
        curr_x = self.x()
        start_pos = self.pos()
        end_pos = QPoint(curr_x, -self.height() - 30)

        self._anim_pos.stop()
        self._anim_pos.setDuration(360)
        self._anim_pos.setEasingCurve(QEasingCurve.Type.InBack)
        self._anim_pos.setStartValue(start_pos)
        self._anim_pos.setEndValue(end_pos)
        self._anim_pos.start()
        logger.debug("CardPickerOverlay sliding out.")

    def _on_pos_anim_finished(self) -> None:
        if self._is_dismissing:
            self.hide()
            self._is_dismissing = False
            self.picker_closed.emit()

    def toggle_picker(self) -> None:
        """Toggles between open and closed state."""
        if self.isVisible() and not self._is_dismissing:
            self.slide_out_and_hide()
        else:
            self.slide_in_and_show()

    # =========================================================================
    # Keyboard & Mouse Event Handlers
    # =========================================================================

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.select_prev()
            event.accept()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.select_next()
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.confirm_selection()
            event.accept()
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_Insert):
            self.slide_out_and_hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        old_hover = self._hover_arrow

        # Check left arrow rect
        if QRect(40, 100, 60, 80).contains(int(pos.x()), int(pos.y())):
            self._hover_arrow = "left"
        elif QRect(self.width() - 100, 100, 60, 80).contains(int(pos.x()), int(pos.y())):
            self._hover_arrow = "right"
        else:
            self._hover_arrow = None

        if old_hover != self._hover_arrow:
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            px, py = int(pos.x()), int(pos.y())
            cx = self.width() // 2

            # 1. Left Arrow click
            if QRect(30, 90, 80, 100).contains(px, py):
                self.select_prev()
                return

            # 2. Right Arrow click
            if QRect(self.width() - 110, 90, 80, 100).contains(px, py):
                self.select_next()
                return

            # 3. Center card click -> Select & Confirm
            center_rect = QRect(cx - 125, 15, 250, 270)
            if center_rect.contains(px, py):
                self.confirm_selection()
                return

            # 4. Left card click -> Slide to it
            left_rect = QRect(cx - 370, 40, 210, 230)
            if left_rect.contains(px, py):
                self.select_prev()
                return

            # 5. Right card click -> Slide to it
            right_rect = QRect(cx + 160, 40, 210, 230)
            if right_rect.contains(px, py):
                self.select_next()
                return

        super().mousePressEvent(event)

    # =========================================================================
    # Painting & Visual Rendering
    # =========================================================================

    def paintEvent(self, event) -> None:
        if not self._killers:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        cx = w // 2

        # Draw Cards in Carousel (Pure floating cards, zero background)
        # Relative slots: -2, -1, 0, 1, 2
        active_idx = self._target_index if self._anim_slide.state() == QPropertyAnimation.State.Running else self._current_index
        n = len(self._killers)

        # Draw relative slots in order of depth: outer first, center last
        draw_order = [-2, 2, -1, 1, 0]
        for rel_slot in draw_order:
            k_idx = (active_idx + rel_slot) % n
            killer = self._killers[k_idx]

            # Calculate horizontal position with animated slide offset
            slot_effective = rel_slot + self._slide_offset
            card_x = cx + (slot_effective * 280.0)

            # Scale and opacity based on distance from center
            dist = abs(slot_effective)
            if dist > 2.4:
                continue  # Too far off-screen

            scale = max(0.55, 1.0 - (dist * 0.22))
            opacity = max(0.15, 1.0 - (dist * 0.42))

            card_w = int(245.0 * scale)
            card_h = int(260.0 * scale)
            card_y = int(14.0 + (dist * 20.0))

            rect = QRect(int(card_x - (card_w / 2.0)), card_y, card_w, card_h)
            is_center = (rel_slot == 0 and abs(self._slide_offset) < 0.35)

            self._draw_single_card(painter, killer, rect, opacity, is_center)

        # Draw Left and Right Navigation Arrows
        self._draw_nav_arrow(painter, "left", QRect(36, 105, 48, 64))
        self._draw_nav_arrow(painter, "right", QRect(w - 84, 105, 48, 64))

        painter.end()

    def _draw_single_card(
        self,
        painter: QPainter,
        killer: KillerConfig,
        rect: QRect,
        opacity: float,
        is_center: bool,
    ) -> None:
        """Renders one killer card with drop shadow and gold highlight if center."""
        painter.save()
        painter.setOpacity(opacity)

        # 1. Glow highlight for center card
        if is_center:
            glow_rect = rect.adjusted(-6, -6, 6, 6)
            glow_grad = QRadialGradient(
                glow_rect.center().x(),
                glow_rect.center().y(),
                max(rect.width(), rect.height()) * 0.65,
            )
            glow_grad.setColorAt(0.0, QColor(234, 179, 8, 90))     # Amber gold glow
            glow_grad.setColorAt(0.7, QColor(220, 38, 38, 40))     # Crimson
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(glow_grad)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(glow_rect, 16, 16)

        # 2. Draw Pixmap or Procedural Card
        pix = self._card_pixmaps.get(killer.id)
        if pix and not pix.isNull():
            # Render card image scaled smoothly
            painter.drawPixmap(rect, pix)
        else:
            self._draw_procedural_card(painter, killer, rect)

        # 3. Border Outline
        if is_center:
            painter.setPen(QPen(QColor(250, 204, 21, 230), 2.5))  # Gold border
        else:
            painter.setPen(QPen(QColor(60, 60, 75, 140), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)

        painter.restore()

    def _draw_procedural_card(self, painter: QPainter, killer: KillerConfig, rect: QRect) -> None:
        """Draws a clean procedural card for killers without a dedicated PNG asset."""
        # Dark gradient card background
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(28, 28, 38, 255))
        grad.setColorAt(1.0, QColor(14, 14, 18, 255))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        # Red banner header
        header_h = max(24, int(rect.height() * 0.22))
        header_rect = QRect(rect.x(), rect.y(), rect.width(), header_h)
        painter.setBrush(QColor(153, 27, 27, 230))
        painter.drawRoundedRect(header_rect, 10, 10)

        # Title in header
        painter.setFont(QFont("Segoe UI Black", max(9, int(rect.height() * 0.06)), QFont.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(header_rect, Qt.AlignCenter, killer.name.upper())

        # Subtitle in center
        painter.setFont(QFont("Segoe UI", max(8, int(rect.height() * 0.045))))
        painter.setPen(QColor(148, 163, 184))
        content_rect = QRect(rect.x() + 8, rect.y() + header_h + 8, rect.width() - 16, rect.height() - header_h - 16)
        painter.drawText(content_rect, Qt.AlignCenter | Qt.TextWordWrap, killer.description or "No description")

    def _draw_nav_arrow(self, painter: QPainter, direction: str, rect: QRect) -> None:
        """Renders stylized Left (<) and Right (>) navigation arrow buttons."""
        is_hovered = (self._hover_arrow == direction)
        bg_color = QColor(40, 40, 55, 220) if is_hovered else QColor(22, 22, 30, 180)
        border_color = QColor(250, 204, 21, 220) if is_hovered else QColor(70, 70, 90, 160)
        arrow_color = QColor(255, 255, 255) if is_hovered else QColor(200, 205, 215)

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        # Arrow symbol
        symbol = "‹" if direction == "left" else "›"
        painter.setFont(QFont("Segoe UI", 26, QFont.Bold))
        painter.setPen(arrow_color)
        # Vertical adjustment for visual centering of unicode chevron
        adj_rect = rect.translated(0, -3)
        painter.drawText(adj_rect, Qt.AlignCenter, symbol)
