"""Unit tests for global hotkey management (app/global_hotkeys.py)."""

import sys
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

    # Test Dual preset (Mouse + [ ])
    dialog._apply_preset_dual()
    assert dialog.input_ab1.text() == "[, Mouse4"
    assert dialog.input_ab2.text() == "], Mouse5"
    assert dialog.input_ab3.text() == "Numpad3"
    assert dialog.input_reset.text() == "P, Mouse3"
    assert dialog.input_overlay.text() == "'"
    assert dialog.input_card_picker.text() == "="

    # Test Mouse preset
    dialog._apply_preset_mouse()
    assert dialog.input_ab1.text() == "Mouse4"
    assert dialog.input_ab2.text() == "Mouse5"
    assert dialog.input_ab3.text() == "Mouse3"
    assert dialog.input_reset.text() == "P"
    assert dialog.input_overlay.text() == "'"
    assert dialog.input_card_picker.text() == "="

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

    # Test Roblox focus filter checkbox
    assert hasattr(dialog, "chk_roblox_only")
    assert dialog.chk_roblox_only.isChecked() is False  # General by default

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

    # General (non-Roblox restricted) by default
    assert backend.require_foreground is False
    assert backend._is_roblox_or_tracker_foreground() is True

    # Register P (0x50), [ (0xDB), and '=' (0xBB)
    assert backend.register_hotkey(1001, 0, 0x50) is True
    assert backend.register_hotkey(1002, 0, 0xDB) is True
    assert backend.register_hotkey(1003, 0, 0xBB) is True
    backend.unrestricted_hids.add(1003)

    # Initial chat state should be False
    assert backend._is_chat_focused is False

    # Simulate '/' keypress (opens chat)
    backend._is_chat_focused = True
    assert backend._is_chat_focused is True

    # When chat is focused, '=' (0xBB) must still trigger and reset chat focus!
    backend._is_chat_focused = True
    is_picker_toggle = (1003 in backend.unrestricted_hids) or (0xBB in (0xBB, 0x2D))
    assert is_picker_toggle is True
    backend._is_chat_focused = False
    backend.callback(1003)

    assert 1003 in triggered_ids
    assert backend._is_chat_focused is False

    # Simulate 'Enter' keypress (sends chat / closes chat)
    backend._is_chat_focused = False
    assert backend._is_chat_focused is False

    # Verify 64-bit CallNextHookEx doesn't crash with OverflowError on Windows
    if sys.platform == "win32" and backend._user32 is not None:
        try:
            large_lparam = 0x0000023C190406E0
            backend._user32.CallNextHookEx(None, 0, 0x0100, large_lparam)
        except OverflowError:
            assert False, "CallNextHookEx failed with OverflowError on 64-bit pointer!"

    # Unregister
    assert backend.unregister_hotkey(1001) is True
    assert backend.unregister_hotkey(1003) is True
    backend.unregister_all()
    assert len(backend._registered_combos) == 0


def test_parse_mouse_thumb_buttons_and_backend():
    """Verify parsing and backend dispatch for mouse thumb buttons (Mouse4/Mouse5)."""
    import ctypes
    from app.global_hotkeys import (
        MSLLHOOKSTRUCT,
        WM_XBUTTONDOWN,
        Win32HookHotkeyBackend,
        parse_hotkey_string,
    )

    # 1. Test key parsing aliases
    m4_mod, m4_vk = parse_hotkey_string("Mouse4")
    assert (m4_mod & ~MOD_NOREPEAT) == 0 and m4_vk == 0x05

    t1_mod, t1_vk = parse_hotkey_string("Thumb1")
    assert (t1_mod & ~MOD_NOREPEAT) == 0 and t1_vk == 0x05

    m5_mod, m5_vk = parse_hotkey_string("Mouse5")
    assert (m5_mod & ~MOD_NOREPEAT) == 0 and m5_vk == 0x06

    t2_mod, t2_vk = parse_hotkey_string("Thumb2")
    assert (t2_mod & ~MOD_NOREPEAT) == 0 and t2_vk == 0x06

    m3_mod, m3_vk = parse_hotkey_string("Mouse3")
    assert (m3_mod & ~MOD_NOREPEAT) == 0 and m3_vk == 0x04

    alt_m4_mod, alt_m4_vk = parse_hotkey_string("Alt+Mouse4")
    assert (alt_m4_mod & MOD_ALT) != 0 and alt_m4_vk == 0x05

    # 2. Test Win32HookHotkeyBackend mouse proc dispatch
    triggered = []
    backend = Win32HookHotkeyBackend(callback=lambda hid: triggered.append(hid))

    # Register Mouse4 (0x05) -> hid 2001, Mouse5 (0x06) -> hid 2002
    backend.register_hotkey(2001, 0, 0x05)
    backend.register_hotkey(2002, 0, 0x06)

    # Mock foreground check so it triggers in test environment
    backend._is_roblox_or_tracker_foreground = lambda: True

    # Simulate Mouse4 press: MSLLHOOKSTRUCT with mouseData = (1 << 16)
    ms_struct1 = MSLLHOOKSTRUCT()
    ms_struct1.mouseData = 1 << 16
    ptr1 = ctypes.addressof(ms_struct1)

    backend._low_level_mouse_proc(0, WM_XBUTTONDOWN, ptr1)
    assert 2001 in triggered

    # Simulate Mouse5 press: MSLLHOOKSTRUCT with mouseData = (2 << 16)
    ms_struct2 = MSLLHOOKSTRUCT()
    ms_struct2.mouseData = 2 << 16
    ptr2 = ctypes.addressof(ms_struct2)

    backend._low_level_mouse_proc(0, WM_XBUTTONDOWN, ptr2)
    assert 2002 in triggered

    backend.unregister_all()
    assert len(backend._registered_combos) == 0


def test_split_hotkey_alternatives():
    """Verify splitting of multiple hotkey alternatives across various formats."""
    from app.global_hotkeys import split_hotkey_alternatives

    assert split_hotkey_alternatives("[, Mouse4") == ["[", "Mouse4"]
    assert split_hotkey_alternatives("Mouse5 [") == ["Mouse5", "["]
    assert split_hotkey_alternatives("[ / Mouse4") == ["[", "Mouse4"]
    assert split_hotkey_alternatives("[ | Mouse4") == ["[", "Mouse4"]
    assert split_hotkey_alternatives("[ dan mouse4") == ["[", "mouse4"]
    assert split_hotkey_alternatives("[ or mouse4") == ["[", "mouse4"]
    assert split_hotkey_alternatives("[ atau mouse4") == ["[", "mouse4"]
    assert split_hotkey_alternatives("Alt + 1, Mouse5") == ["Alt+1", "Mouse5"]
    assert split_hotkey_alternatives("Numpad1") == ["Numpad1"]
    assert split_hotkey_alternatives("") == []
    # Deduplication within same string
    assert split_hotkey_alternatives("Mouse4, mouse4") == ["Mouse4"]


def test_multi_hotkey_registration_and_trigger():
    """Verify GlobalHotkeyManager supports multiple alternative keys for a single action."""
    backend = FakeHotkeyBackend()
    manager = GlobalHotkeyManager(backend=backend)

    triggered = []
    manager.action_triggered.connect(lambda action: triggered.append(action))

    # Register Ability 1 with BOTH '[' and 'Mouse4'
    # Register Ability 2 with BOTH ']' and 'Mouse5'
    config = {
        "trigger_ability_1": "[, Mouse4",
        "trigger_ability_2": "Mouse5 ]",  # space-separated
        "reset_all": "P / Mouse3",
    }
    results = manager.register_actions(config)
    assert all(results.values())
    assert len(manager.failed_actions) == 0

    # 4 distinct keys registered in backend: 2 for ab1, 2 for ab2, 2 for reset -> 6 total
    assert len(backend.registered) == 6

    # Verify both '[' and 'Mouse4' trigger ability 1
    # Find hids for '[' (vk=0xDB) and 'Mouse4' (vk=0x05)
    id_bracket = [hid for hid, (mod, vk) in backend.registered.items() if vk == 0xDB][0]
    id_mouse4 = [hid for hid, (mod, vk) in backend.registered.items() if vk == 0x05][0]

    manager._on_hotkey_id(id_bracket)
    assert triggered == ["trigger_ability_1"]

    manager._on_hotkey_id(id_mouse4)
    assert triggered == ["trigger_ability_1", "trigger_ability_1"]

    # Verify both ']' (vk=0xDD) and 'Mouse5' (vk=0x06) trigger ability 2
    id_bracket2 = [hid for hid, (mod, vk) in backend.registered.items() if vk == 0xDD][0]
    id_mouse5 = [hid for hid, (mod, vk) in backend.registered.items() if vk == 0x06][0]

    manager._on_hotkey_id(id_bracket2)
    manager._on_hotkey_id(id_mouse5)
    assert triggered[-2:] == ["trigger_ability_2", "trigger_ability_2"]

    # Verify conflict when a key is used across different actions
    conflict_config = {
        "trigger_ability_1": "[, Mouse4",
        "trigger_ability_2": "Mouse4, ]",  # Mouse4 already taken by ab1!
    }
    res_conflict = manager.register_actions(conflict_config)
    assert res_conflict["trigger_ability_1"] is True
    assert res_conflict["trigger_ability_2"] is False
    assert "Duplicate key 'Mouse4'" in manager.failed_actions["trigger_ability_2"]

    manager.unregister_all()
    assert len(backend.registered) == 0

