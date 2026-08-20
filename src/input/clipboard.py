"""System clipboard service module."""
from __future__ import annotations

import logging
from typing import Optional

try:
    import pyperclip
except Exception:  # pragma: no cover
    pyperclip = None  # type: ignore

logger = logging.getLogger(__name__)


class ClipboardError(Exception):
    """Base exception for clipboard operations."""
    pass


class ClipboardService:
    """Provides safe clipboard read and write operations."""

    def __init__(self) -> None:
        self._available = pyperclip is not None

    @property
    def is_available(self) -> bool:
        """Return True if clipboard backend is available."""
        return self._available

    def copy(self, text: str) -> bool:
        """Copy text to the system clipboard.

        Args:
            text: String to place on the clipboard.

        Returns:
            bool: True if copy succeeded, False otherwise.
        """
        if not self._available or pyperclip is None:
            logger.error("Clipboard backend (pyperclip) is not available.")
            return False

        try:
            pyperclip.copy(text)
            logger.debug("Successfully copied %d characters to clipboard.", len(text))
            return True
        except Exception as e:
            logger.error("Failed to copy text to clipboard: %s", e)
            return False

    def paste(self) -> Optional[str]:
        """Retrieve text from the system clipboard.

        Returns:
            Optional[str]: Clipboard text content, or None if failed.
        """
        if not self._available or pyperclip is None:
            logger.error("Clipboard backend (pyperclip) is not available.")
            return None

        try:
            content = pyperclip.paste()
            return content
        except Exception as e:
            logger.error("Failed to read from clipboard: %s", e)
            return None

    def clear(self) -> bool:
        """Clear the system clipboard content."""
        return self.copy("")
