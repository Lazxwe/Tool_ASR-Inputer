"""Unit tests for ClipboardService."""
from unittest.mock import patch

from src.input.clipboard import ClipboardService


def test_clipboard_copy_and_paste() -> None:
    service = ClipboardService()
    test_text = "測試剪貼簿文字 123"

    assert service.is_available is True
    success = service.copy(test_text)
    assert success is True

    retrieved = service.paste()
    assert retrieved == test_text


def test_clipboard_clear() -> None:
    service = ClipboardService()
    service.copy("something")
    cleared = service.clear()
    assert cleared is True
    assert service.paste() == ""


def test_clipboard_copy_exception_handled() -> None:
    service = ClipboardService()
    with patch("pyperclip.copy", side_effect=Exception("Simulated clipboard copy failure")):
        assert service.copy("test") is False


def test_clipboard_paste_exception_handled() -> None:
    service = ClipboardService()
    with patch("pyperclip.paste", side_effect=Exception("Simulated clipboard paste failure")):
        assert service.paste() is None


def test_clipboard_unavailable_handling() -> None:
    service = ClipboardService()
    service._available = False
    assert service.copy("test") is False
    assert service.paste() is None
