"""Global hotkey listening module using pynput."""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

try:
    from pynput import keyboard
except Exception:  # pragma: no cover
    keyboard = None  # type: ignore

logger = logging.getLogger(__name__)


class HotkeyError(Exception):
    """Base exception for hotkey operations."""
    pass


def normalize_hotkey_string(hotkey_str: str) -> str:
    """Normalize a hotkey string for pynput GlobalHotKeys format.

    Examples:
        'f8' -> '<f8>'
        '<f8>' -> '<f8>'
        'F8' -> '<f8>'
        'ctrl+alt+a' -> '<ctrl>+<alt>+a'
    """
    cleaned = hotkey_str.strip().lower()
    if not cleaned:
        return "<f8>"

    parts = cleaned.split("+")
    normalized_parts = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        if p.startswith("<") and p.endswith(">"):
            normalized_parts.append(p)
        elif p.startswith("f") and p[1:].isdigit():
            normalized_parts.append(f"<{p}>")
        elif p in ("ctrl", "alt", "cmd", "shift", "caps_lock", "space", "enter", "tab", "esc"):
            normalized_parts.append(f"<{p}>")
        else:
            normalized_parts.append(p)

    return "+".join(normalized_parts)


class HotkeyListener:
    """Listens for global keyboard shortcut triggers."""

    def __init__(
        self,
        hotkey: str = "f8",
        on_triggered: Optional[Callable[[], None]] = None,
    ) -> None:
        self.raw_hotkey = hotkey
        self.normalized_hotkey = normalize_hotkey_string(hotkey)
        self.on_triggered = on_triggered

        self._hotkey_listener: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()
        self._is_running = False

    @property
    def is_listening(self) -> bool:
        """Return True if the hotkey listener thread is running."""
        with self._lock:
            return self._is_running and (self._hotkey_listener is not None and self._hotkey_listener.is_alive())

    def _on_hotkey_press(self) -> None:
        """Internal callback invoked when the configured global hotkey is pressed."""
        logger.info("Global hotkey '%s' triggered.", self.normalized_hotkey)
        if self.on_triggered:
            try:
                self.on_triggered()
            except Exception as e:
                logger.error("Error executing hotkey callback: %s", e)

    def start(self) -> None:
        """Start listening for the global hotkey in a background thread."""
        if keyboard is None:
            raise HotkeyError("pynput keyboard library is not available.")

        with self._lock:
            if self._is_running:
                logger.warning("Hotkey listener is already running.")
                return

            try:
                hotkey_map = {self.normalized_hotkey: self._on_hotkey_press}
                self._hotkey_listener = keyboard.GlobalHotKeys(hotkey_map)
                self._hotkey_listener.daemon = True
                self._hotkey_listener.start()
                self._is_running = True
                logger.info("Started global hotkey listener for '%s'.", self.normalized_hotkey)
            except Exception as e:
                self._is_running = False
                self._hotkey_listener = None
                logger.error("Failed to start global hotkey listener: %s", e)
                raise HotkeyError(f"Failed to start hotkey listener: {e}") from e

    def stop(self) -> None:
        """Stop the background hotkey listener thread."""
        with self._lock:
            if not self._is_running or self._hotkey_listener is None:
                self._is_running = False
                return

            try:
                self._hotkey_listener.stop()
                logger.info("Stopped global hotkey listener.")
            except Exception as e:
                logger.warning("Error stopping hotkey listener: %s", e)
            finally:
                self._hotkey_listener = None
                self._is_running = False
