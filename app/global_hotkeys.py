"""Global Hotkey Manager via Win32 ctypes.

Violence District Cooldown Tracker — Manual Trigger Milestone (Phase M3)
Registers system-wide hotkeys using user32.RegisterHotKey with MOD_NOREPEAT.
Intercepts WM_HOTKEY (0x0312) directly on the Qt main event loop via QAbstractNativeEventFilter.
Zero third-party keyboard hook dependencies.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
from typing import Callable, Dict, Optional, Set, Tuple

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

from app.logger import get_logger

logger = get_logger("global_hotkeys")

# Win32 Constants
WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual Key Mapping
VK_MAPPING: Dict[str, int] = {
    # Numpad
    "numpad0": 0x60,
    "num0": 0x60,
    "numpad1": 0x61,
    "num1": 0x61,
    "numpad2": 0x62,
    "num2": 0x62,
    "numpad3": 0x63,
    "num3": 0x63,
    "numpad4": 0x64,
    "num4": 0x64,
    "numpad5": 0x65,
    "num5": 0x65,
    "numpad6": 0x66,
    "num6": 0x66,
    "numpad7": 0x67,
    "num7": 0x67,
    "numpad8": 0x68,
    "num8": 0x68,
    "numpad9": 0x69,
    "num9": 0x69,
    "numpad.": 0x6E,
    "numpad_dot": 0x6E,
    "decimal": 0x6E,
    "numpad+": 0x6B,
    "numpadadd": 0x6B,
    "numpad-": 0x6D,
    "numpadsub": 0x6D,
    "numpad*": 0x6A,
    "numpadmul": 0x6A,
    "numpad/": 0x6F,
    "numpaddiv": 0x6F,
    # Function Keys
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    # Navigation / Editing
    "space": 0x20,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "insert": 0x2D,
    "delete": 0x2E,
    "del": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pgup": 0x21,
    "pagedown": 0x22,
    "pgdn": 0x22,
    # Symbols
    ".": 0xBE,
    "period": 0xBE,
    ",": 0xBC,
    "comma": 0xBC,
    "-": 0xBD,
    "minus": 0xBD,
    "=": 0xBB,
    "plus": 0xBB,
}

# Add standard numbers '0'-'9' (0x30 - 0x39)
for digit in range(10):
    VK_MAPPING[str(digit)] = 0x30 + digit

# Add standard letters 'a'-'z' (0x41 - 0x5A)
for i in range(26):
    char = chr(ord("a") + i)
    VK_MAPPING[char] = 0x41 + i


def parse_hotkey_string(hotkey_str: str) -> Tuple[int, int]:
    """Parses a hotkey string like 'Numpad1', 'Alt+1', 'Ctrl+Shift+F1'.
    
    Returns:
        Tuple[int, int]: (modifiers, vk_code). Always includes MOD_NOREPEAT.
        
    Raises:
        ValueError: If key string is invalid or cannot be parsed.
    """
    cleaned = hotkey_str.strip()
    if not cleaned:
        raise ValueError("Hotkey string cannot be empty.")

    # Split by '+' while handling special single '+' character
    parts = [p.strip().lower() for p in cleaned.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"Invalid hotkey combination: '{hotkey_str}'")

    modifiers = MOD_NOREPEAT
    key_part = ""

    for part in parts:
        if part in ("alt", "menu"):
            modifiers |= MOD_ALT
        elif part in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif part in ("shift",):
            modifiers |= MOD_SHIFT
        elif part in ("win", "windows", "super", "meta"):
            modifiers |= MOD_WIN
        else:
            if key_part:
                raise ValueError(f"Multiple base keys specified in '{hotkey_str}': '{key_part}' and '{part}'")
            key_part = part

    if not key_part:
        raise ValueError(f"Missing key in hotkey combination '{hotkey_str}' (only modifiers given).")

    vk_code = VK_MAPPING.get(key_part)
    if vk_code is None:
        raise ValueError(f"Unknown or unsupported key '{key_part}' in hotkey '{hotkey_str}'.")

    return modifiers, vk_code


class HotkeyBackend:
    """Abstract interface for hotkey registration backend."""

    def register_hotkey(self, hotkey_id: int, modifiers: int, vk: int) -> bool:
        raise NotImplementedError

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        raise NotImplementedError

    def unregister_all(self) -> None:
        raise NotImplementedError


class Win32HotkeyBackend(HotkeyBackend):
    """Concrete backend using Win32 user32.RegisterHotKey via ctypes."""

    def __init__(self, hwnd: int = 0) -> None:
        self.hwnd = hwnd
        self._registered_ids: Set[int] = set()
        self._user32 = ctypes.windll.user32

    def register_hotkey(self, hotkey_id: int, modifiers: int, vk: int) -> bool:
        res = self._user32.RegisterHotKey(self.hwnd, hotkey_id, modifiers, vk)
        if res != 0:
            self._registered_ids.add(hotkey_id)
            logger.debug("Win32 RegisterHotKey success: id=%d, mod=0x%04x, vk=0x%02x", hotkey_id, modifiers, vk)
            return True

        err = ctypes.windll.kernel32.GetLastError()
        logger.warning(
            "Win32 RegisterHotKey failed: id=%d, mod=0x%04x, vk=0x%02x (GetLastError=%d)",
            hotkey_id,
            modifiers,
            vk,
            err,
        )
        return False

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        if hotkey_id in self._registered_ids:
            res = self._user32.UnregisterHotKey(self.hwnd, hotkey_id)
            self._registered_ids.discard(hotkey_id)
            return bool(res)
        return False

    def unregister_all(self) -> None:
        for hid in list(self._registered_ids):
            self.unregister_hotkey(hid)


class FakeHotkeyBackend(HotkeyBackend):
    """In-memory mock backend for headless automated unit testing."""

    def __init__(self) -> None:
        self.registered: Dict[int, Tuple[int, int]] = {}
        self.fail_ids: Set[int] = set()

    def register_hotkey(self, hotkey_id: int, modifiers: int, vk: int) -> bool:
        if hotkey_id in self.fail_ids:
            return False
        # Check duplicate VK registration
        for hid, (m, k) in self.registered.items():
            if m == modifiers and k == vk:
                return False  # Already registered
        self.registered[hotkey_id] = (modifiers, vk)
        return True

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        if hotkey_id in self.registered:
            del self.registered[hotkey_id]
            return True
        return False

    def unregister_all(self) -> None:
        self.registered.clear()


class HotkeyNativeEventFilter(QAbstractNativeEventFilter, QObject):
    """Qt native event filter to intercept WM_HOTKEY directly in the Qt event loop."""

    hotkey_received = Signal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)

    def nativeEventFilter(self, event_type: bytes, message: int) -> Tuple[bool, int]:
        try:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hotkey_id = int(msg.wParam)
                self.hotkey_received.emit(hotkey_id)
                # Return True, 0 to consume the event
                return True, 0
        except Exception as exc:
            logger.debug("nativeEventFilter parse ignored: %s", exc)
        return False, 0


class GlobalHotkeyManager(QObject):
    """High-level manager binding configurable action names to global system hotkeys."""

    action_triggered = Signal(str)  # Emits action_name (e.g. 'trigger_ability_1', 'reset_all')

    def __init__(
        self,
        backend: Optional[HotkeyBackend] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.backend = backend or (Win32HotkeyBackend() if sys.platform == "win32" else FakeHotkeyBackend())

        self._id_counter: int = 1000
        self._action_to_id: Dict[str, int] = {}
        self._id_to_action: Dict[int, str] = {}
        self._failed_actions: Dict[str, str] = {}

        self._native_filter: Optional[HotkeyNativeEventFilter] = None

    @property
    def failed_actions(self) -> Dict[str, str]:
        """Returns mapping of actions that failed registration and the error reason."""
        return dict(self._failed_actions)

    def install_event_filter(self) -> None:
        """Installs the native event filter into the QCoreApplication instance."""
        app = QCoreApplication.instance()
        if app is not None and self._native_filter is None:
            self._native_filter = HotkeyNativeEventFilter(self)
            self._native_filter.hotkey_received.connect(self._on_hotkey_id)
            app.installNativeEventFilter(self._native_filter)
            logger.info("Installed HotkeyNativeEventFilter into Qt application.")

    def remove_event_filter(self) -> None:
        """Removes the native event filter from the QCoreApplication instance."""
        app = QCoreApplication.instance()
        if app is not None and self._native_filter is not None:
            app.removeNativeEventFilter(self._native_filter)
            self._native_filter = None
            logger.info("Removed HotkeyNativeEventFilter from Qt application.")

    def register_actions(self, hotkeys_config: Dict[str, str]) -> Dict[str, bool]:
        """Registers a full map of actions to hotkey strings (e.g. settings.manual.hotkeys).
        
        Returns:
            Dict[str, bool]: Success status per action.
        """
        self.unregister_all()
        self._failed_actions.clear()
        results: Dict[str, bool] = {}

        # 1. Check for duplicates in configuration
        seen_keys: Dict[str, str] = {}
        for action, key_str in hotkeys_config.items():
            norm_key = key_str.strip().lower()
            if norm_key in seen_keys:
                err_msg = f"Duplicate key '{key_str}' conflicts with action '{seen_keys[norm_key]}'"
                self._failed_actions[action] = err_msg
                results[action] = False
                logger.warning("Hotkey config error: %s", err_msg)
                continue
            seen_keys[norm_key] = action

            # 2. Parse key string
            try:
                mod, vk = parse_hotkey_string(key_str)
            except ValueError as val_err:
                self._failed_actions[action] = str(val_err)
                results[action] = False
                logger.warning("Failed to parse hotkey for '%s': %s", action, val_err)
                continue

            # 3. Register hotkey with OS backend
            hid = self._id_counter
            self._id_counter += 1

            success = self.backend.register_hotkey(hid, mod, vk)
            if success:
                self._action_to_id[action] = hid
                self._id_to_action[hid] = action
                results[action] = True
                logger.info("Registered global hotkey '%s' -> '%s' (id=%d)", action, key_str, hid)
            else:
                err_msg = f"System registration failed for '{key_str}' (possibly in use by another app)"
                self._failed_actions[action] = err_msg
                results[action] = False
                logger.warning("Global hotkey registration failed for '%s' -> '%s'", action, key_str)

        return results

    def unregister_all(self) -> None:
        """Unregisters all active hotkeys cleanly from the OS."""
        self.backend.unregister_all()
        self._action_to_id.clear()
        self._id_to_action.clear()
        logger.info("Unregistered all global hotkeys.")

    def trigger_action(self, action: str) -> None:
        """Directly triggers an action (useful for tests or fallback buttons)."""
        logger.info("Triggered action: %s", action)
        self.action_triggered.emit(action)

    def _on_hotkey_id(self, hotkey_id: int) -> None:
        """Handler called when WM_HOTKEY is received for hotkey_id."""
        action = self._id_to_action.get(hotkey_id)
        if action:
            self.trigger_action(action)
        else:
            logger.debug("Received unmapped hotkey id: %d", hotkey_id)
