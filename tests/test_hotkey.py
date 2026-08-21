"""Unit tests for HotkeyListener."""
from unittest.mock import MagicMock, patch

import pytest

from src.input.hotkey import HotkeyError, HotkeyListener, normalize_hotkey_string


def test_normalize_hotkey_string() -> None:
    assert normalize_hotkey_string("f8") == "<f8>"
    assert normalize_hotkey_string("<f8>") == "<f8>"
    assert normalize_hotkey_string("F8") == "<f8>"
    assert normalize_hotkey_string("ctrl_r") == "<ctrl_r>"
    assert normalize_hotkey_string("ctrl_right") == "<ctrl_r>"
    assert normalize_hotkey_string("ctrl_l") == "<ctrl_l>"
    assert normalize_hotkey_string("alt_r") == "<alt_r>"
    assert normalize_hotkey_string("shift_r") == "<shift_r>"
    assert normalize_hotkey_string("cmd_r") == "<cmd_r>"
    assert normalize_hotkey_string("ctrl_r+space") == "<ctrl_r>+<space>"
    assert normalize_hotkey_string("ctrl+alt+a") == "<ctrl>+<alt>+a"
    assert normalize_hotkey_string("cmd+shift+f12") == "<cmd>+<shift>+<f12>"
    assert normalize_hotkey_string("") == "<ctrl_r>"


def test_hotkey_listener_start_and_stop() -> None:
    listener = HotkeyListener(hotkey="f8", mode="hold")

    with patch("pynput.keyboard.Listener") as mock_listener_cls, \
         patch("pynput.keyboard.HotKey.parse", return_value={"key"}):
        mock_instance = MagicMock()
        mock_listener_cls.return_value = mock_instance

        listener.start()
        assert listener._is_running is True
        assert mock_instance.start.called

        # Start again should be no-op
        listener.start()
        assert mock_instance.start.call_count == 1

        listener.stop()
        assert listener._is_running is False
        assert mock_instance.stop.called


def test_hotkey_listener_hold_mode_press_and_release() -> None:
    start_called = []
    stop_called = []

    listener = HotkeyListener(
        hotkey="f8",
        mode="hold",
        on_press_start=lambda: start_called.append(1),
        on_release_stop=lambda: stop_called.append(1),
    )

    # Mock hotkey object state
    mock_hotkey = MagicMock()
    mock_hotkey._keys = {"k1"}
    mock_hotkey._state = set()
    listener._hotkey_obj = mock_hotkey
    mock_listener = MagicMock()
    mock_listener.canonical.side_effect = lambda k: k
    listener._listener = mock_listener

    # Press key: _state now has "k1"
    mock_hotkey._state = {"k1"}
    listener._on_hotkey_press_event("k1")
    assert len(start_called) == 1
    assert listener._is_active is True

    # Press again while already active (should not trigger start again)
    listener._on_hotkey_press_event("k1")
    assert len(start_called) == 1

    # Release key: _state is now empty
    mock_hotkey._state = set()
    listener._on_hotkey_release_event("k1")
    assert len(stop_called) == 1
    assert listener._is_active is False


def test_hotkey_listener_toggle_mode() -> None:
    toggled = []
    listener = HotkeyListener(
        hotkey="f8",
        mode="toggle",
        on_triggered=lambda: toggled.append(1),
    )
    listener._on_toggle_activated()
    assert len(toggled) == 1


def test_hotkey_listener_callback_exception_handled() -> None:
    def bad_callback() -> None:
        raise ValueError("Error inside hotkey callback")

    listener = HotkeyListener(hotkey="f8", mode="toggle", on_triggered=bad_callback)
    # Should not raise exception
    listener._on_toggle_activated()


def test_hotkey_listener_start_failure() -> None:
    listener = HotkeyListener(hotkey="f8")
    with patch("pynput.keyboard.Listener", side_effect=Exception("Failed to bind hotkey")):
        with pytest.raises(HotkeyError):
            listener.start()


def test_hotkey_listener_unavailable() -> None:
    listener = HotkeyListener(hotkey="f8")
    with patch("src.input.hotkey.keyboard", None):
        with pytest.raises(HotkeyError):
            listener.start()


def test_hotkey_listener_resolve_matching_key() -> None:
    listener = HotkeyListener(hotkey="ctrl_r")
    assert listener._resolve_matching_key("dummy") == "dummy"

    mock_hotkey = MagicMock()
    mock_hotkey._keys = {"key_r_vk"}
    listener._hotkey_obj = mock_hotkey

    mock_listener = MagicMock()
    mock_listener.canonical.return_value = "canonical_ctrl"
    listener._listener = mock_listener

    # Simulated raw key with .value
    raw_key = MagicMock()
    raw_key.value = "key_r_vk"

    # Should match candidates ("key_r_vk") instead of falling back to "canonical_ctrl"
    with patch("src.input.hotkey.keyboard.KeyCode", str):
        matched = listener._resolve_matching_key(raw_key)
        assert matched == "key_r_vk"
