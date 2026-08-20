"""Audio recording management module using sounddevice and numpy."""
from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
except Exception as _e:  # pragma: no cover
    sd = None  # type: ignore

logger = logging.getLogger(__name__)


class AudioRecorderError(Exception):
    """Base exception for audio recording errors."""
    pass


class MicrophoneUnavailableError(AudioRecorderError):
    """Raised when no input audio device is available or accessible."""
    pass


class AudioRecorder:
    """Thread-safe audio recorder capturing mono audio at a target sample rate."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
        device: Optional[int | str] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device = device

        self._stream: Optional[sd.InputStream] = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Return True if recording is currently active."""
        with self._lock:
            return self._is_recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Internal callback invoked by sounddevice for each audio block."""
        if status:
            logger.warning("Audio callback status: %s", status)
        with self._lock:
            if self._is_recording:
                self._frames.append(indata.copy())

    def start(self) -> None:
        """Start capturing audio from the input device.

        Raises:
            MicrophoneUnavailableError: If sounddevice or input device is not available.
            AudioRecorderError: If the stream fails to open or is already active.
        """
        if sd is None:
            raise MicrophoneUnavailableError("sounddevice library is not available or failed to load.")

        with self._lock:
            if self._is_recording:
                logger.warning("Recording is already in progress.")
                return

            try:
                # Query input device to ensure it exists
                device_info = sd.query_devices(self.device, kind="input")
                logger.info("Using input device: %s", device_info.get("name", "Unknown"))
            except Exception as e:
                logger.error("Failed to query input audio device: %s", e)
                raise MicrophoneUnavailableError(f"No available microphone found: {e}") from e

            self._frames = []
            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    device=self.device,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._is_recording = True
                logger.info("Audio recording started (SR=%d, Channels=%d).", self.sample_rate, self.channels)
            except Exception as e:
                self._stream = None
                self._is_recording = False
                logger.error("Failed to start audio input stream: %s", e)
                raise AudioRecorderError(f"Could not open audio stream: {e}") from e

    def stop(self) -> np.ndarray:
        """Stop capturing audio and return the concatenated audio data as a 1D float32 numpy array.

        Returns:
            np.ndarray: 1D numpy array with float32 audio samples.
        """
        with self._lock:
            if not self._is_recording:
                logger.warning("Stop called while not recording.")
                if not self._frames:
                    return np.empty(0, dtype=np.float32)

            self._is_recording = False
            stream = self._stream
            self._stream = None

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logger.warning("Error closing audio stream: %s", e)

        with self._lock:
            if not self._frames:
                logger.info("No audio frames were recorded.")
                return np.empty(0, dtype=np.float32)

            # Concatenate all 2D chunks (frames, channels) and flatten to 1D
            audio_array = np.concatenate(self._frames, axis=0)
            self._frames = []

        # Flatten if mono
        if audio_array.ndim > 1:
            if audio_array.shape[1] == 1:
                audio_array = audio_array.squeeze(axis=1)
            else:
                # Average multi-channel to mono
                audio_array = np.mean(audio_array, axis=1)

        audio_array = audio_array.astype(np.float32)
        logger.info("Audio recording stopped. Captured %d samples (%.2f seconds).",
                    len(audio_array), len(audio_array) / self.sample_rate)
        return audio_array
