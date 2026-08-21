"""Unit tests for NotificationService across platforms."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ui.notification import NotificationService, _escape_applescript_string


def test_escape_applescript_string() -> None:
    """Test escaping of quotes, backslashes, and newlines for AppleScript."""
    raw = 'Hello "World" \\ Path\nLine 2'
    escaped = _escape_applescript_string(raw)
    assert '\\"' in escaped
    assert "\\\\" in escaped
    assert "\n" not in escaped
    assert "Line 2" in escaped


def test_send_macos() -> None:
    """Test macOS notification dispatch via osascript."""
    service = NotificationService()
    service._os_type = "darwin"

    with patch("subprocess.Popen") as mock_popen:
        success = service.send(
            message='Test "Quote" Message',
            title="Test App",
            subtitle="Subtitle",
            sound=True,
        )
        assert success is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "osascript"
        assert cmd[1] == "-e"
        assert "display notification" in cmd[2]
        assert "Test App" in cmd[2]
        assert "sound name" in cmd[2]


def test_send_macos_without_sound_and_subtitle() -> None:
    """Test macOS notification without sound and subtitle."""
    service = NotificationService()
    service._os_type = "darwin"

    with patch("subprocess.Popen") as mock_popen:
        success = service.send(message="Simple Message", sound=False)
        assert success is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "sound name" not in cmd[2]
        assert "subtitle" not in cmd[2]


def test_send_windows_with_pystray() -> None:
    """Test Windows notification using pystray icon."""
    mock_icon = MagicMock()
    service = NotificationService(tray_icon=mock_icon)
    service._os_type = "windows"

    success = service.send(message="Windows Toast", title="Title")
    assert success is True
    mock_icon.notify.assert_called_once_with("Windows Toast", "Title")


def test_send_windows_powershell_fallback() -> None:
    """Test Windows notification using PowerShell fallback when tray icon is None."""
    service = NotificationService()
    service._os_type = "windows"

    with patch("subprocess.Popen") as mock_popen:
        success = service.send(message="Windows PS Toast", title="App")
        assert success is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "powershell"
        assert "ToastNotification" in cmd[5]


def test_send_windows_pystray_exception_falls_back_to_powershell() -> None:
    """Test fallback to PowerShell if pystray notify raises an error."""
    mock_icon = MagicMock()
    mock_icon.notify.side_effect = RuntimeError("pystray failure")
    service = NotificationService(tray_icon=mock_icon)
    service._os_type = "windows"

    with patch("subprocess.Popen") as mock_popen:
        success = service.send(message="Fallback Toast", title="App")
        assert success is True
        mock_popen.assert_called_once()


def test_send_linux() -> None:
    """Test Linux notification via notify-send."""
    service = NotificationService()
    service._os_type = "linux"

    with patch("subprocess.Popen") as mock_popen:
        success = service.send(message="Linux Body", title="Linux Title")
        assert success is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert cmd == ["notify-send", "Linux Title", "Linux Body"]


def test_send_other_platform_logging() -> None:
    """Test unknown platform gracefully logs and returns True."""
    service = NotificationService()
    service._os_type = "freebsd"

    success = service.send(message="Other OS Message")
    assert success is True


def test_send_error_suppression() -> None:
    """Test that unexpected system exceptions are suppressed and return False."""
    service = NotificationService()
    service._os_type = "darwin"

    with patch("subprocess.Popen", side_effect=OSError("OS command failed")):
        success = service.send(message="Error Test")
        assert success is False


def test_set_tray_icon() -> None:
    """Test dynamically binding tray icon."""
    service = NotificationService()
    assert service.tray_icon is None
    mock_icon = MagicMock()
    service.set_tray_icon(mock_icon)
    assert service.tray_icon is mock_icon
