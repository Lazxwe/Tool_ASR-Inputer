"""Cross-platform paste keystroke simulation service."""
from __future__ import annotations

import logging
import platform
import subprocess
import time
from typing import Optional

try:
    from pynput.keyboard import Controller, Key
except Exception:  # pragma: no cover
    Controller = None  # type: ignore
    Key = None  # type: ignore

logger = logging.getLogger(__name__)


class PasteError(Exception):
    """Base exception for paste simulation operations."""
    pass


class PasteService:
    """Simulates system paste shortcut (Cmd+V on macOS, Ctrl+V on Windows/Linux)."""

    def __init__(
        self,
        os_platform: Optional[str] = None,
        default_delay: float = 0.05,
    ) -> None:
        self.os_platform = (os_platform or platform.system()).lower()
        self.default_delay = default_delay
        self._controller: Optional[Controller] = None
        if Controller is not None:
            try:
                self._controller = Controller()
            except Exception as e:  # pragma: no cover
                logger.warning("Failed to initialize pynput keyboard controller: %s", e)

    @property
    def is_macos(self) -> bool:
        return "darwin" in self.os_platform or "mac" in self.os_platform

    def simulate_paste(self, delay: Optional[float] = None) -> bool:
        """Simulate pasting clipboard contents into the currently focused window.

        Args:
            delay: Pre/post keystroke pause in seconds. Defaults to self.default_delay.

        Returns:
            bool: True if paste simulation was dispatched successfully.
        """
        sleep_duration = delay if delay is not None else self.default_delay
        if sleep_duration > 0:
            time.sleep(sleep_duration)

        # 1. Primary method: pynput controller
        if self._controller is not None and Key is not None:
            try:
                modifier = Key.cmd if self.is_macos else Key.ctrl
                with self._controller.pressed(modifier):
                    self._controller.press('v')
                    self._controller.release('v')

                if sleep_duration > 0:
                    time.sleep(sleep_duration)

                logger.debug("Simulated paste key combination successfully via pynput.")
                return True
            except Exception as e:
                logger.warning("pynput paste simulation failed: %s. Attempting fallback if available.", e)

        # 2. Fallback for macOS via osascript
        if self.is_macos:
            return self._simulate_paste_macos_osascript(sleep_duration)

        logger.error("No available paste mechanism could be executed.")
        return False

    def _simulate_paste_macos_osascript(self, sleep_duration: float) -> bool:
        """Fallback paste simulation using macOS AppleScript (osascript)."""
        try:
            cmd = ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down']
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                logger.debug("Simulated paste via macOS osascript.")
                return True
            logger.error("osascript paste failed: %s", result.stderr.strip())
            return False
        except Exception as e:
            logger.error("Failed to execute osascript paste fallback: %s", e)
            return False
