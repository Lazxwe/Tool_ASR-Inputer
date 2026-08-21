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
    """Listens for global keyboard shortcut triggers in hold or toggle mode."""

    def __init__(
        self,
        hotkey: str = "f8",
        mode: str = "hold",
        on_triggered: Optional[Callable[[], None]] = None,
        on_press_start: Optional[Callable[[], None]] = None,
        on_release_stop: Optional[Callable[[], None]] = None,
    ) -> None:
        self.raw_hotkey = hotkey
        self.mode = mode.lower().strip() if mode else "hold"
        self.normalized_hotkey = normalize_hotkey_string(hotkey)
        self.on_triggered = on_triggered
        self.on_press_start = on_press_start
        self.on_release_stop = on_release_stop

        self._hotkey_obj: Optional[keyboard.HotKey] = None
        self._listener: Optional[keyboard.Listener] = None
        self._is_active = False
        self._lock = threading.Lock()
        self._is_running = False

    @property
    def is_listening(self) -> bool:
        """Return True if the hotkey listener thread is running."""
        with self._lock:
            return self._is_running and (self._listener is not None and self._listener.is_alive())

    def _on_hotkey_press_event(self, key: object) -> None:
        """Handle raw key press event."""
        if self._hotkey_obj is None or self._listener is None:
            return
        try:
            canonical_key = self._listener.canonical(key)  # type: ignore[arg-type]
            self._hotkey_obj.press(canonical_key)

            if self.mode == "hold":
                if len(self._hotkey_obj._state) == len(self._hotkey_obj._keys):
                    if not self._is_active:
                        self._is_active = True
                        logger.info("Global hotkey '%s' pressed (Hold mode start).", self.normalized_hotkey)
                        if self.on_press_start:
                            self.on_press_start()
        except Exception as e:
            logger.error("Error in hotkey press handler: %s", e)

    def _on_hotkey_release_event(self, key: object) -> None:
        """Handle raw key release event."""
        if self._hotkey_obj is None or self._listener is None:
            return
        try:
            canonical_key = self._listener.canonical(key)  # type: ignore[arg-type]
            was_active = self._is_active
            self._hotkey_obj.release(canonical_key)

            if self.mode == "hold" and was_active:
                if len(self._hotkey_obj._state) < len(self._hotkey_obj._keys):
                    self._is_active = False
                    logger.info("Global hotkey '%s' released (Hold mode stop).", self.normalized_hotkey)
                    if self.on_release_stop:
                        self.on_release_stop()
        except Exception as e:
            logger.error("Error in hotkey release handler: %s", e)

    def _on_toggle_activated(self) -> None:
        """Invoked when hotkey is fully triggered in toggle mode."""
        if self.mode == "toggle":
            logger.info("Global hotkey '%s' triggered (Toggle mode).", self.normalized_hotkey)
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
                parsed_keys = keyboard.HotKey.parse(self.normalized_hotkey)
                self._hotkey_obj = keyboard.HotKey(parsed_keys, self._on_toggle_activated)
                self._listener = keyboard.Listener(
                    on_press=self._on_hotkey_press_event,
                    on_release=self._on_hotkey_release_event,
                )
                self._listener.daemon = True
                self._listener.start()
                self._is_running = True
                logger.info("Started global hotkey listener for '%s' (Mode: %s).", self.normalized_hotkey, self.mode)
            except Exception as e:
                self._is_running = False
                self._listener = None
                self._hotkey_obj = None
                logger.error("Failed to start global hotkey listener: %s", e)
                raise HotkeyError(f"Failed to start hotkey listener: {e}") from e

    def stop(self) -> None:
        """Stop the background hotkey listener thread."""
        with self._lock:
            if not self._is_running or self._listener is None:
                self._is_running = False
                return

            try:
                self._listener.stop()
                logger.info("Stopped global hotkey listener.")
            except Exception as e:
                logger.warning("Error stopping hotkey listener: %s", e)
            finally:
                self._listener = None
                self._hotkey_obj = None
                self._is_active = False
                self._is_running = False
