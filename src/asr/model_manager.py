"""Model lifecycle and cache management for Qwen3-ASR."""
from __future__ import annotations

import enum
import gc
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Standard model identifiers
MODEL_REGISTRY: dict[str, str] = {
    "0.6b": "Qwen/Qwen3-ASR-0.6B",
    "1.7b": "Qwen/Qwen3-ASR-1.7B",
}


class ModelStatus(str, enum.Enum):
    """Lifecycle status of the ASR model."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class ModelManagerError(Exception):
    """Base exception for model management operations."""
    pass


class ModelManager:
    """Manages downloading, caching, loading, and memory cleanup for Qwen3-ASR models."""

    def __init__(
        self,
        models_dir: Path | str = "./models",
        default_model: str = "0.6b",
        device: Optional[str] = None,
    ) -> None:
        self.models_dir = Path(models_dir).resolve()
        self.default_model_key = default_model.lower()
        self.device = device

        self._current_model_name: Optional[str] = None
        self._current_model_instance: Any = None
        self._status: ModelStatus = ModelStatus.UNLOADED
        self._last_error: Optional[str] = None

        # Ensure model cache directory exists and configure environment variables
        self._configure_cache_dir()

    def _configure_cache_dir(self) -> None:
        """Isolate HuggingFace and Torch download cache inside the project directory."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(self.models_dir / "huggingface")
        os.environ["TRANSFORMERS_CACHE"] = str(self.models_dir / "huggingface" / "hub")

    @property
    def status(self) -> ModelStatus:
        """Current status of the model."""
        return self._status

    @property
    def current_model_name(self) -> Optional[str]:
        """Name or key of the currently loaded model."""
        return self._current_model_name

    @property
    def current_model(self) -> Any:
        """The currently active model instance."""
        return self._current_model_instance

    @property
    def last_error(self) -> Optional[str]:
        """Last encountered error message, if any."""
        return self._last_error

    def resolve_model_id(self, model_identifier: str) -> str:
        """Resolve a model shortcut (e.g. '0.6b', '1.7b') or local path to a valid model ID."""
        key = model_identifier.lower().strip()
        if key in MODEL_REGISTRY:
            return MODEL_REGISTRY[key]
        # Allow passing full HuggingFace ID or local path directly
        return model_identifier

    def load_model(self, model_identifier: Optional[str] = None) -> Any:
        """Load a Qwen3-ASR model into memory.

        If a model is already loaded and differs from the requested one, the old model
        is automatically unloaded and its memory released first.
        """
        target_name = (model_identifier or self.default_model_key).lower().strip()
        model_id = self.resolve_model_id(target_name)

        if self._current_model_name == target_name and self._current_model_instance is not None:
            logger.info("Model '%s' is already loaded and ready.", target_name)
            return self._current_model_instance

        # Unload existing model before loading new one
        if self._current_model_instance is not None:
            self.unload_model()

        self._status = ModelStatus.LOADING
        self._last_error = None
        logger.info("Loading ASR model '%s' (ID: %s)...", target_name, model_id)

        try:
            # Import qwen_asr dynamically
            try:
                from qwen_asr import Qwen3ASRModel
            except ImportError as ie:
                raise ModelManagerError(
                    f"qwen-asr is not installed. Please install it with 'pip install qwen-asr'. Details: {ie}"
                ) from ie

            device = self.device
            if device is None:
                try:
                    import torch
                    if torch.cuda.is_available():
                        device = "cuda:0"
                    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                        device = "mps"
                    else:
                        device = "cpu"
                except ImportError:
                    device = "cpu"

            logger.info("Loading model on device: %s", device)
            model_instance = Qwen3ASRModel.from_pretrained(
                model_id,
                device_map=device if device != "cpu" else None,
                cache_dir=str(self.models_dir / "huggingface" / "hub"),
            )

            self._current_model_name = target_name
            self._current_model_instance = model_instance
            self._status = ModelStatus.READY
            logger.info("Model '%s' loaded successfully.", target_name)
            return self._current_model_instance

        except Exception as e:
            self._status = ModelStatus.ERROR
            self._last_error = str(e)
            self._current_model_name = None
            self._current_model_instance = None
            logger.error("Failed to load model '%s': %s", target_name, e)
            raise ModelManagerError(f"Failed to load model '{target_name}': {e}") from e

    def unload_model(self) -> None:
        """Release the currently loaded model and reclaim memory/VRAM."""
        if self._current_model_instance is not None:
            logger.info("Unloading model '%s'...", self._current_model_name)
            del self._current_model_instance
            self._current_model_instance = None
            self._current_model_name = None

            # Garbage collection & PyTorch cache flush
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                    torch.mps.empty_cache()
            except ImportError:
                pass

        self._status = ModelStatus.UNLOADED
        logger.info("Model unloaded successfully.")
