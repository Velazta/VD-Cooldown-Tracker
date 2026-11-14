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

    # Test Numpad preset
    dialog._apply_preset_numpad()
    assert dialog.input_ab1.text() == "Numpad1"
    assert dialog.input_ab2.text() == "Numpad2"
    assert dialog.input_reset.text() == "Numpad0"
    assert dialog.input_overlay.text() == "Numpad."

    dialog.close()
    win.close()

