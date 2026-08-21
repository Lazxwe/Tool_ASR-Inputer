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


SPECIAL_KEY_ALIASES: dict[str, str] = {
    # Specific left/right modifiers (e.g. right Control, right Alt)
    "ctrl_r": "<ctrl_r>",
    "ctrl_right": "<ctrl_r>",
    "r_ctrl": "<ctrl_r>",
    "rctrl": "<ctrl_r>",
    "ctrl_l": "<ctrl_l>",
    "ctrl_left": "<ctrl_l>",
    "l_ctrl": "<ctrl_l>",
    "lctrl": "<ctrl_l>",
    "alt_r": "<alt_r>",
    "alt_right": "<alt_r>",
    "r_alt": "<alt_r>",
    "ralt": "<alt_r>",
    "alt_l": "<alt_l>",
    "alt_left": "<alt_l>",
    "l_alt": "<alt_l>",
    "lalt": "<alt_l>",
    "shift_r": "<shift_r>",
    "shift_right": "<shift_r>",
    "r_shift": "<shift_r>",
    "rshift": "<shift_r>",
    "shift_l": "<shift_l>",
    "shift_left": "<shift_l>",
    "l_shift": "<shift_l>",
    "lshift": "<shift_l>",
    "cmd_r": "<cmd_r>",
    "cmd_right": "<cmd_r>",
    "r_cmd": "<cmd_r>",
    "rcmd": "<cmd_r>",
    "cmd_l": "<cmd_l>",
    "cmd_left": "<cmd_l>",
    "l_cmd": "<cmd_l>",
    "lcmd": "<cmd_l>",
    # Generic modifiers (triggers on either side)
    "ctrl": "<ctrl>",
    "alt": "<alt>",
    "cmd": "<cmd>",
    "shift": "<shift>",
    # Other special keys
    "capslock": "<caps_lock>",
    "caps_lock": "<caps_lock>",
    "space": "<space>",
    "enter": "<enter>",
    "tab": "<tab>",
    "esc": "<esc>",
    "escape": "<esc>",
}


def normalize_hotkey_string(hotkey_str: str) -> str:
    """Normalize a hotkey string for pynput GlobalHotKeys format.

    Supports distinguishing left and right modifier keys (e.g. 'ctrl_r', 'ctrl_l').

    Examples:
        'ctrl_r' -> '<ctrl_r>'
        'ctrl_l' -> '<ctrl_l>'
        'f8' -> '<f8>'
        '<f8>' -> '<f8>'
        'ctrl+alt+a' -> '<ctrl>+<alt>+a'
    """
    cleaned = hotkey_str.strip().lower()
    if not cleaned:
        return "<ctrl_r>"

    parts = cleaned.split("+")
    normalized_parts = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        if p.startswith("<") and p.endswith(">"):
            normalized_parts.append(p)
        elif p in SPECIAL_KEY_ALIASES:
            normalized_parts.append(SPECIAL_KEY_ALIASES[p])
        elif p.startswith("f") and p[1:].isdigit():
            normalized_parts.append(f"<{p}>")
        else:
            normalized_parts.append(p)

    return "+".join(normalized_parts)


class HotkeyListener:
    """Listens for global keyboard shortcut triggers in hold or toggle mode."""

    def __init__(
        self,
        hotkey: str = "ctrl_r",
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

    def _resolve_matching_key(self, key: object) -> object:
        """Resolve raw key event to match specific side modifiers or canonical modifiers."""
        if self._hotkey_obj is None or self._listener is None:
            return key
        try:
            canonical_key = self._listener.canonical(key)  # type: ignore[arg-type]
        except Exception:
            canonical_key = key

        candidates = [canonical_key, key]
        if hasattr(key, "value") and keyboard is not None and isinstance(getattr(key, "value"), keyboard.KeyCode):
            candidates.append(getattr(key, "value"))

        for c in candidates:
            if c in self._hotkey_obj._keys:
                return c
        return canonical_key

    def _on_hotkey_press_event(self, key: object) -> None:
        """Handle raw key press event."""
        if self._hotkey_obj is None or self._listener is None:
            return
        try:
            matching_key = self._resolve_matching_key(key)
            self._hotkey_obj.press(matching_key)

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
            matching_key = self._resolve_matching_key(key)
            was_active = self._is_active
            self._hotkey_obj.release(matching_key)

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
