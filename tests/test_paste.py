"""Unit tests for PasteService."""
from unittest.mock import MagicMock, patch

from src.input.paste import PasteService


def test_paste_service_platform_detection() -> None:
    mac_service = PasteService(os_platform="darwin")
    assert mac_service.is_macos is True

    win_service = PasteService(os_platform="windows")
    assert win_service.is_macos is False


def test_paste_service_pynput_success_macos() -> None:
    service = PasteService(os_platform="darwin", default_delay=0.0)
    mock_controller = MagicMock()
    service._controller = mock_controller

    success = service.simulate_paste()
    assert success is True
    assert mock_controller.pressed.called
    mock_controller.press.assert_called_with('v')


def test_paste_service_pynput_success_windows() -> None:
    service = PasteService(os_platform="windows", default_delay=0.0)
    mock_controller = MagicMock()
    service._controller = mock_controller

    success = service.simulate_paste()
    assert success is True
    assert mock_controller.pressed.called


def test_paste_service_pynput_fallback_macos_osascript() -> None:
    service = PasteService(os_platform="darwin", default_delay=0.0)
    service._controller = MagicMock()
    service._controller.pressed.side_effect = Exception("Pynput error")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success = service.simulate_paste()
        assert success is True
        assert mock_run.called


def test_paste_service_osascript_failure() -> None:
    service = PasteService(os_platform="darwin", default_delay=0.0)
    service._controller = None

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="osascript permission denied")
        success = service.simulate_paste()
        assert success is False


def test_paste_service_no_mechanism_windows() -> None:
    service = PasteService(os_platform="windows", default_delay=0.0)
    service._controller = None
    assert service.simulate_paste() is False


def test_paste_service_osascript_exception() -> None:
    service = PasteService(os_platform="darwin", default_delay=0.0)
    service._controller = None
    with patch("subprocess.run", side_effect=Exception("Subprocess failed")):
        assert service.simulate_paste() is False
