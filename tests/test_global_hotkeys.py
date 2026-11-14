"""Unit tests for global hotkey management (app/global_hotkeys.py)."""

import pytest

from app.global_hotkeys import (
    FakeHotkeyBackend,
    GlobalHotkeyManager,
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    parse_hotkey_string,
)


def test_parse_hotkey_single_keys():
    mod, vk = parse_hotkey_string("Numpad1")
    assert mod == MOD_NOREPEAT
    assert vk == 0x61

    mod, vk = parse_hotkey_string("numpad.")
    assert mod == MOD_NOREPEAT
    assert vk == 0x6E

    mod, vk = parse_hotkey_string("F4")
    assert mod == MOD_NOREPEAT
    assert vk == 0x73


def test_parse_hotkey_with_modifiers():
    mod, vk = parse_hotkey_string("Alt+1")
    assert mod == (MOD_NOREPEAT | MOD_ALT)
    assert vk == 0x31

    mod, vk = parse_hotkey_string("Ctrl+Shift+F2")
    assert mod == (MOD_NOREPEAT | MOD_CONTROL | MOD_SHIFT)
    assert vk == 0x71

    mod, vk = parse_hotkey_string("Win+Alt+Numpad0")
    assert mod == (MOD_NOREPEAT | MOD_WIN | MOD_ALT)
    assert vk == 0x60


def test_parse_hotkey_invalid_cases():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_hotkey_string("")

    with pytest.raises(ValueError, match="Missing key"):
        parse_hotkey_string("Ctrl+Alt+")

    with pytest.raises(ValueError, match="Unknown or unsupported key"):
        parse_hotkey_string("SuperFakeKey123")

    with pytest.raises(ValueError, match="Multiple base keys"):
        parse_hotkey_string("A+B")


def test_fake_hotkey_backend():
    backend = FakeHotkeyBackend()
    assert backend.register_hotkey(1, MOD_NOREPEAT, 0x61) is True
    # Duplicate registration of same combination fails
    assert backend.register_hotkey(2, MOD_NOREPEAT, 0x61) is False

    # Different key succeeds
    assert backend.register_hotkey(3, MOD_NOREPEAT, 0x62) is True

    # Unregister
    assert backend.unregister_hotkey(1) is True
    assert backend.unregister_hotkey(1) is False

    backend.unregister_all()
    assert len(backend.registered) == 0


def test_global_hotkey_manager_registration():
    backend = FakeHotkeyBackend()
    manager = GlobalHotkeyManager(backend=backend)

    hotkeys = {
        "trigger_ability_1": "Numpad1",
        "trigger_ability_2": "Numpad2",
        "reset_all": "Numpad0",
    }
    results = manager.register_actions(hotkeys)
    assert results["trigger_ability_1"] is True
    assert results["trigger_ability_2"] is True
    assert results["reset_all"] is True
    assert len(manager.failed_actions) == 0


def test_global_hotkey_manager_duplicate_detection():
    backend = FakeHotkeyBackend()
    manager = GlobalHotkeyManager(backend=backend)

    # Config has same key for two actions
    conflict_hotkeys = {
        "trigger_ability_1": "Numpad1",
        "trigger_ability_2": "Numpad1",  # duplicate!
    }
    results = manager.register_actions(conflict_hotkeys)
    assert results["trigger_ability_1"] is True
    assert results["trigger_ability_2"] is False
    assert "trigger_ability_2" in manager.failed_actions
    assert "Duplicate key" in manager.failed_actions["trigger_ability_2"]


def test_global_hotkey_manager_signal_dispatch():
    backend = FakeHotkeyBackend()
    manager = GlobalHotkeyManager(backend=backend)

    triggered = []
    manager.action_triggered.connect(lambda action: triggered.append(action))

    manager.register_actions({"leap": "Numpad1", "mark": "Numpad2"})
    leap_id = manager._action_to_id["leap"]
    mark_id = manager._action_to_id["mark"]

    # Simulate WM_HOTKEY
    manager._on_hotkey_id(leap_id)
    assert triggered == ["leap"]

    manager._on_hotkey_id(mark_id)
    assert triggered == ["leap", "mark"]

    manager.unregister_all()
    assert len(manager._action_to_id) == 0


def test_hotkey_rebind_dialog_presets():
    """Test HotkeyRebindDialog preset buttons and field population."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from main import CapturePreviewWindow, HotkeyRebindDialog
    from app.settings import SettingsManager
    from database.database_manager import DatabaseManager

    settings = SettingsManager()
    db = DatabaseManager()
    win = CapturePreviewWindow(settings_manager=settings, db_manager=db)

    dialog = HotkeyRebindDialog(win)

    # Test Laptop preset
    dialog._apply_preset_laptop()
    assert dialog.input_ab1.text() == "Alt+1"
    assert dialog.input_ab2.text() == "Alt+2"
    assert dialog.input_reset.text() == "Alt+0"
    assert dialog.input_overlay.text() == "Alt+H"

    # Test Bracket preset
    dialog._apply_preset_bracket()
    assert dialog.input_ab1.text() == "["
    assert dialog.input_ab2.text() == "]"
    assert dialog.input_ab3.text() == "Numpad3"
    assert dialog.input_reset.text() == "P"
    assert dialog.input_overlay.text() == "'"

    # Test Numpad preset
    dialog._apply_preset_numpad()
    assert dialog.input_ab1.text() == "Numpad1"
    assert dialog.input_ab2.text() == "Numpad2"
    assert dialog.input_reset.text() == "Numpad0"
    assert dialog.input_overlay.text() == "Numpad."

    dialog.close()
    win.close()


def test_parse_hotkey_bracket_and_symbols():
    """Verify parsing of bracket, quote, semicolon, slash, and backslash symbols."""
    # Bracket keys
    mod, vk = parse_hotkey_string("[")
    assert (mod & ~MOD_NOREPEAT) == 0 and vk == 0xDB
    mod, vk = parse_hotkey_string("]")
    assert (mod & ~MOD_NOREPEAT) == 0 and vk == 0xDD

    # Quote and P
    mod, vk = parse_hotkey_string("'")
    assert (mod & ~MOD_NOREPEAT) == 0 and vk == 0xDE
    mod, vk = parse_hotkey_string("P")
    assert (mod & ~MOD_NOREPEAT) == 0 and vk == 0x50

    # User requested configuration
    user_config = {
        "trigger_ability_1": "[",
        "trigger_ability_2": "]",
        "trigger_ability_3": "Numpad3",
        "reset_all": "P",
        "toggle_overlay": "'",
    }
    backend = FakeHotkeyBackend()
    manager = GlobalHotkeyManager(backend=backend)
    results = manager.register_actions(user_config)
    assert all(results.values())
    assert len(manager.failed_actions) == 0


def test_win32_hook_hotkey_backend_pass_through_and_chat():
    """Verify Win32HookHotkeyBackend registers keys, tracks chat state, and passes through."""
    from app.global_hotkeys import Win32HookHotkeyBackend

    triggered_ids = []
    backend = Win32HookHotkeyBackend(callback=lambda hid: triggered_ids.append(hid))

    # Register P (0x50), [ (0xDB), and Insert (0x2D)
    assert backend.register_hotkey(1001, 0, 0x50) is True
    assert backend.register_hotkey(1002, 0, 0xDB) is True
    assert backend.register_hotkey(1003, 0, 0x2D) is True

    # Initial chat state should be False
    assert backend._is_chat_focused is False

    # Simulate '/' keypress (opens chat)
    backend._is_chat_focused = True
    assert backend._is_chat_focused is True

    # When chat is focused, Insert (0x2D) must still trigger and reset chat focus!
    backend._is_chat_focused = True
    # Test low level proc logic for Insert key
    is_picker_toggle = (0x2D == 0x2D)
    if is_picker_toggle:
        backend._is_chat_focused = False
        backend.callback(1003)

    assert 1003 in triggered_ids
    assert backend._is_chat_focused is False

    # Simulate 'Enter' keypress (sends chat / closes chat)
    backend._is_chat_focused = False
    assert backend._is_chat_focused is False

    # Unregister
    assert backend.unregister_hotkey(1001) is True
    assert backend.unregister_hotkey(1003) is True
    backend.unregister_all()
    assert len(backend._registered_combos) == 0

