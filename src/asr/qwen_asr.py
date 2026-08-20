"""Qwen3-ASR inference engine with Traditional Chinese post-processing pipeline."""
from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

from src.asr.model_manager import ModelManager, ModelManagerError
from src.text.pipeline import TextPipeline

logger = logging.getLogger(__name__)


class ASRInferenceError(Exception):
    """Exception raised when ASR inference fails."""
    pass


class QwenASREngine:
    """High-level ASR inference engine integrating Qwen3-ASR with text normalization."""

    def __init__(
        self,
        model_manager: Optional[ModelManager] = None,
        text_pipeline: Optional[TextPipeline] = None,
        default_language: str = "Chinese",
        sample_rate: int = 16000,
    ) -> None:
        self.model_manager = model_manager or ModelManager()
        self.text_pipeline = text_pipeline
        self.default_language = default_language
        self.sample_rate = sample_rate

    def transcribe(
        self,
        audio: np.ndarray | str | tuple[np.ndarray, int],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """Transcribe audio data or file path to raw text.

        Args:
            audio: 1D float32 numpy array, audio file path, or (ndarray, sample_rate) tuple.
            language: Target language or None for auto-detect (defaults to self.default_language).
            prompt: Optional context prompt to bias speech recognition.

        Returns:
            str: Raw transcribed text from the model.
        """
        # Guard: Check for empty numpy array
        if isinstance(audio, np.ndarray):
            if audio.size == 0:
                logger.info("Audio array is empty, returning empty transcription.")
                return ""
            audio_input: Any = (audio, self.sample_rate)
        elif isinstance(audio, tuple):
            if isinstance(audio[0], np.ndarray) and audio[0].size == 0:
                return ""
            audio_input = audio
        elif isinstance(audio, str):
            if not audio.strip():
                return ""
            audio_input = audio
        else:
            raise ValueError(f"Unsupported audio input type: {type(audio)}")

        # Ensure model is ready
        try:
            model = self.model_manager.current_model
            if model is None:
                model = self.model_manager.load_model()
        except ModelManagerError as me:
            raise ASRInferenceError(f"Cannot perform inference because model failed to load: {me}") from me

        target_lang = language if language is not None else self.default_language

        try:
            logger.info("Running Qwen3-ASR transcription (language=%s)...", target_lang)
            kwargs: dict[str, Any] = {}
            if target_lang:
                kwargs["language"] = target_lang
            if prompt:
                kwargs["prompt"] = prompt

            results = model.transcribe(audio=audio_input, **kwargs)

            # Parse results from Qwen3-ASR return structure
            raw_text = self._extract_text(results)
            logger.info("ASR transcription result: '%s'", raw_text)
            return raw_text

        except Exception as e:
            logger.error("ASR inference failed: %s", e)
            raise ASRInferenceError(f"Inference error: {e}") from e

    def transcribe_and_process(
        self,
        audio: np.ndarray | str | tuple[np.ndarray, int],
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> str:
        """Transcribe audio and apply Traditional Chinese pipeline post-processing.

        Returns:
            str: Processed Traditional Chinese text with Custom Dictionary replacements.
        """
        raw_text = self.transcribe(audio, language=language, prompt=prompt)
        if not raw_text:
            return ""

        if self.text_pipeline is not None:
            processed_text = self.text_pipeline.process(raw_text)
            logger.info("Text pipeline post-processed: '%s' -> '%s'", raw_text, processed_text)
            return processed_text

        return raw_text

    @staticmethod
    def _extract_text(results: Any) -> str:
        """Extract plain string text from diverse model return formats."""
        if results is None:
            return ""

        # If list of results (standard qwen-asr returns list of TranscriptionResult objects or dicts)
        if isinstance(results, list):
            if not results:
                return ""
            item = results[0]
        else:
            item = results

        if isinstance(item, str):
            return item.strip()
        if hasattr(item, "text"):
            return str(item.text).strip()
        if isinstance(item, dict):
            return str(item.get("text", "")).strip()

        return str(item).strip()
