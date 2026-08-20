"""Application state machine and observer management."""
from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AppState(str, enum.Enum):
    """Lifecycle states of the voice input tool."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

    @property
    def display_name(self) -> str:
        """Traditional Chinese localized display label."""
        labels = {
            AppState.IDLE: "閒置 (Idle)",
            AppState.RECORDING: "錄音中 (Recording)",
            AppState.PROCESSING: "辨識處理中 (Processing)",
            AppState.READY: "就緒 (Ready)",
            AppState.ERROR: "發生錯誤 (Error)",
        }
        return labels.get(self, self.value)


StateCallback = Callable[[AppState, Optional[str]], None]


class StateManager:
    """Thread-safe state manager with observer pattern subscription."""

    def __init__(self, initial_state: AppState = AppState.READY) -> None:
        self._state = initial_state
        self._last_error: Optional[str] = None
        self._last_state_change: float = time.time()
        self._subscribers: list[StateCallback] = []
        self._lock = threading.Lock()

    @property
    def state(self) -> AppState:
        """Current application state."""
        with self._lock:
            return self._state

    @property
    def last_error(self) -> Optional[str]:
        """Last recorded error message."""
        with self._lock:
            return self._last_error

    @property
    def last_state_change(self) -> float:
        """Timestamp of the most recent state change."""
        with self._lock:
            return self._last_state_change

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self.state == AppState.RECORDING

    @property
    def is_processing(self) -> bool:
        """Return True if currently processing ASR / text."""
        return self.state == AppState.PROCESSING

    @property
    def is_idle_or_ready(self) -> bool:
        """Return True if ready to accept a new recording trigger."""
        return self.state in (AppState.IDLE, AppState.READY)

    def set_state(self, new_state: AppState, error_msg: Optional[str] = None) -> None:
        """Transition to a new application state and notify all subscribers.

        Args:
            new_state: Target AppState.
            error_msg: Optional error description if transitioning to or from ERROR.
        """
        with self._lock:
            old_state = self._state
            self._state = new_state
            self._last_state_change = time.time()
            if error_msg is not None:
                self._last_error = error_msg
            elif new_state in (AppState.READY, AppState.IDLE):
                self._last_error = None

            logger.info("State transition: %s -> %s %s",
                        old_state.value, new_state.value,
                        f"(Error: {error_msg})" if error_msg else "")
            callbacks = list(self._subscribers)

        # Notify subscribers outside the lock to prevent deadlocks
        for callback in callbacks:
            try:
                callback(new_state, error_msg)
            except Exception as e:
                logger.error("Error in state change subscriber callback: %s", e)

    def subscribe(self, callback: StateCallback) -> Callable[[], None]:
        """Register a callback for state change events.

        Returns:
            Callable[[], None]: Unsubscribe callable.
        """
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def reset_to_ready(self) -> None:
        """Helper to safely reset state back to READY."""
        self.set_state(AppState.READY)
