"""Unit tests for HotkeyListener."""
from unittest.mock import MagicMock, patch

import pytest

from src.input.hotkey import HotkeyError, HotkeyListener, normalize_hotkey_string


def test_normalize_hotkey_string() -> None:
    assert normalize_hotkey_string("f8") == "<f8>"
    assert normalize_hotkey_string("<f8>") == "<f8>"
    assert normalize_hotkey_string("F8") == "<f8>"
    assert normalize_hotkey_string("ctrl+alt+a") == "<ctrl>+<alt>+a"
    assert normalize_hotkey_string("cmd+shift+f12") == "<cmd>+<shift>+<f12>"
    assert normalize_hotkey_string("") == "<f8>"


def test_hotkey_listener_start_and_stop() -> None:
    triggered = []

    def callback() -> None:
        triggered.append(True)

    listener = HotkeyListener(hotkey="f8", on_triggered=callback)

    with patch("pynput.keyboard.GlobalHotKeys") as mock_ghk:
        mock_instance = MagicMock()
        mock_ghk.return_value = mock_instance

        listener.start()
        assert listener._is_running is True
        assert mock_instance.start.called

        # Start again should be no-op
        listener.start()
        assert mock_instance.start.call_count == 1

        listener.stop()
        assert listener._is_running is False
        assert mock_instance.stop.called


def test_hotkey_listener_trigger_callback() -> None:
    called = []
    listener = HotkeyListener(hotkey="f8", on_triggered=lambda: called.append(1))
    listener._on_hotkey_press()
    assert len(called) == 1


def test_hotkey_listener_callback_exception_handled() -> None:
    def bad_callback() -> None:
        raise ValueError("Error inside hotkey callback")

    listener = HotkeyListener(hotkey="f8", on_triggered=bad_callback)
    # Should not raise exception
    listener._on_hotkey_press()


def test_hotkey_listener_start_failure() -> None:
    listener = HotkeyListener(hotkey="f8")
    with patch("pynput.keyboard.GlobalHotKeys", side_effect=Exception("Failed to bind hotkey")):
        with pytest.raises(HotkeyError):
            listener.start()


def test_hotkey_listener_unavailable() -> None:
    listener = HotkeyListener(hotkey="f8")
    with patch("src.input.hotkey.keyboard", None):
        with pytest.raises(HotkeyError):
            listener.start()
