"""Model lifecycle and cache management for Qwen3-ASR."""
from __future__ import annotations

import enum
import gc
import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Standard model identifiers
MODEL_REGISTRY: dict[str, str] = {
    "0.6b": "Qwen/Qwen3-ASR-0.6B",
    "1.7b": "Qwen/Qwen3-ASR-1.7B",
}


class ModelStatus(str, enum.Enum):
    """Lifecycle status of the ASR model."""
    UNLOADED = "unloaded"
    DOWNLOADING = "downloading"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class _HFDownloadProgressBar:
    """Lightweight tqdm wrapper to capture HuggingFace download progress."""
    _active_callback: Optional[Callable[[float, str], None]] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.total: float = float(kwargs.get("total") or 0)
        self.n: float = float(kwargs.get("initial") or 0)
        self.desc: str = str(kwargs.get("desc") or "模型下載中")
        self._report()

    def update(self, n: float = 1) -> None:
        self.n += n
        self._report()

    def _report(self) -> None:
        cb = _HFDownloadProgressBar._active_callback
        if cb and self.total > 0:
            pct = min(100.0, max(0.0, (self.n / self.total) * 100.0))
            try:
                cb(pct, f"{self.desc} ({pct:.1f}%)")
            except Exception as e:
                logger.debug("Error in download progress callback: %s", e)

    def close(self) -> None:
        pass

    def __enter__(self) -> _HFDownloadProgressBar:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()



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

    def get_local_directory(self, model_key: str) -> Path:
        """Return the expected offline local model folder path (e.g. ./models/0.6b)."""
        key = model_key.lower().strip()
        return self.models_dir / key

    def get_hf_cache_directory(self) -> Path:
        """Return the isolated HuggingFace hub cache directory."""
        return self.models_dir / "huggingface" / "hub"

    def check_local_model_availability(self, model_identifier: str) -> dict[str, Any]:
        """Check if the specified model is present locally (offline folder or HF cache).

        Returns:
            dict containing availability flag, source type, path or repo ID, and guidance notes.
        """
        key = model_identifier.lower().strip()
        local_dir = self.get_local_directory(key)

        # 1. Check dedicated offline directory (e.g. ./models/0.6b)
        if local_dir.is_dir() and any(local_dir.iterdir()):
            return {
                "available": True,
                "source": "local_dir",
                "path": str(local_dir),
                "description": f"已於本機目錄找到模型權重 ({local_dir})",
                "guidance": "純離線模式已就緒",
            }

        # 2. Check HuggingFace hub snapshot cache
        repo_id = MODEL_REGISTRY.get(key, model_identifier)
        hf_cache_dir = self.get_hf_cache_directory()
        repo_folder_name = f"models--{repo_id.replace('/', '--')}"
        repo_cache_path = hf_cache_dir / repo_folder_name / "snapshots"

        if repo_cache_path.is_dir() and any(repo_cache_path.iterdir()):
            return {
                "available": True,
                "source": "hf_cache",
                "path": str(repo_cache_path),
                "description": f"已於 HuggingFace 快取找到模型 ({repo_cache_path})",
                "guidance": "本地快取已就緒",
            }

        # 3. Not found locally
        return {
            "available": False,
            "source": "remote_hub",
            "path": repo_id,
            "description": f"本機尚未下載模型 '{key}'",
            "guidance": self.get_offline_guidance(key),
        }

    def get_offline_guidance(self, model_key: str) -> str:
        """Generate friendly Traditional Chinese guidance for placing offline model weights."""
        key = model_key.lower().strip()
        repo_id = MODEL_REGISTRY.get(key, f"Qwen/Qwen3-ASR-{key.upper()}")
        target_dir = self.get_local_directory(key)
        return (
            f"未偵測到本地模型 '{key}'。\n"
            f"【純離線部署】請將 {repo_id} 模型檔案放置於：\n"
            f"  -> {target_dir}\n"
            f"【在線自動下載】若具備網路連線，系統推論時將自動下載至專案快取目錄：\n"
            f"  -> {self.get_hf_cache_directory()}\n"
            f"或執行指令預先下載：python -m src.main --download-model {key}"
        )

    def download_model(
        self,
        model_identifier: str = "0.6b",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Explicitly download model weights with real-time progress bar displayed in console or via callback."""
        target_name = model_identifier.lower().strip()
        repo_id = MODEL_REGISTRY.get(target_name, model_identifier)
        logger.info("Starting download for model '%s' (HuggingFace Repo: %s)...", target_name, repo_id)

        if progress_callback is not None:
            _HFDownloadProgressBar._active_callback = progress_callback
            try:
                progress_callback(0.0, f"開始下載模型 {target_name}...")
            except Exception as e:
                logger.debug("Error in download start callback: %s", e)

        try:
            from huggingface_hub import snapshot_download
            cache_dir = self.get_hf_cache_directory()
            kwargs: dict[str, Any] = {
                "repo_id": repo_id,
                "cache_dir": str(cache_dir),
                "resume_download": True,
            }
            if progress_callback is not None:
                kwargs["tqdm_class"] = _HFDownloadProgressBar

            local_path = snapshot_download(**kwargs)
            logger.info("Model '%s' successfully downloaded to %s", target_name, local_path)
            if progress_callback is not None:
                try:
                    progress_callback(100.0, f"模型 {target_name} 下載完成")
                except Exception as e:
                    logger.debug("Error in download finish callback: %s", e)
            return str(local_path)
        except ImportError:
            # Fallback via qwen_asr
            try:
                from qwen_asr import Qwen3ASRModel
                model_instance = Qwen3ASRModel.from_pretrained(
                    repo_id,
                    cache_dir=str(self.get_hf_cache_directory()),
                )
                if progress_callback is not None:
                    try:
                        progress_callback(100.0, f"模型 {target_name} 下載完成")
                    except Exception as e:
                        logger.debug("Error in fallback callback: %s", e)
                return str(self.get_hf_cache_directory())
            except ImportError as ie:
                raise ModelManagerError(
                    "請先安裝 huggingface_hub 或 qwen-asr: pip install huggingface_hub qwen-asr"
                ) from ie
        finally:
            _HFDownloadProgressBar._active_callback = None

    def resolve_model_id(self, model_identifier: str) -> str:
        """Resolve a model shortcut or local path to a valid model ID or directory.

        Precedence:
        1. Local dedicated directory (e.g. ./models/0.6b/) if exists and non-empty.
        2. Known shortcut in MODEL_REGISTRY (e.g. '0.6b' -> 'Qwen/Qwen3-ASR-0.6B').
        3. Raw model identifier string.
        """
        key = model_identifier.lower().strip()
        local_dir = self.get_local_directory(key)
        if local_dir.is_dir() and any(local_dir.iterdir()):
            logger.info("Using offline local model directory: %s", local_dir)
            return str(local_dir)

        if key in MODEL_REGISTRY:
            return MODEL_REGISTRY[key]
        # Allow passing full HuggingFace ID or explicit local path directly
        return model_identifier

    def load_model(
        self,
        model_identifier: Optional[str] = None,
        on_download_progress: Optional[Callable[[float, str], None]] = None,
    ) -> Any:
        """Load a Qwen3-ASR model into memory.

        If a model is already loaded and differs from the requested one, the old model
        is automatically unloaded and its memory released first.
        If the model is not present locally, it will be downloaded first with progress notifications.
        """
        target_name = (model_identifier or self.default_model_key).lower().strip()
        model_id = self.resolve_model_id(target_name)

        if self._current_model_name == target_name and self._current_model_instance is not None:
            logger.info("Model '%s' is already loaded and ready.", target_name)
            return self._current_model_instance

        # Unload existing model before loading new one
        if self._current_model_instance is not None:
            self.unload_model()

        # If progress tracking callback is provided and model is not yet local, download explicitly
        if on_download_progress is not None:
            avail_info = self.check_local_model_availability(target_name)
            if not avail_info.get("available", False):
                self._status = ModelStatus.DOWNLOADING
                logger.info("Model '%s' not found locally. Initiating download with progress callback...", target_name)
                self.download_model(target_name, progress_callback=on_download_progress)

        self._status = ModelStatus.LOADING
        self._last_error = None
        logger.info("Loading ASR model '%s' (Resolved ID/Path: %s)...", target_name, model_id)

        try:
            # Import qwen_asr dynamically
            try:
                from qwen_asr import Qwen3ASRModel
            except ImportError as ie:
                guidance = self.get_offline_guidance(target_name)
                raise ModelManagerError(
                    f"尚未安裝 qwen-asr 推論套件 (pip install qwen-asr)。\n{guidance}"
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
                cache_dir=str(self.get_hf_cache_directory()),
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
            guidance = self.get_offline_guidance(target_name)
            logger.error("Failed to load model '%s': %s", target_name, e)
            raise ModelManagerError(f"模型載入失敗 '{target_name}': {e}\n{guidance}") from e

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
