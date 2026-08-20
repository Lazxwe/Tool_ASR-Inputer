"""Unit tests for ModelManager."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.asr.model_manager import ModelManager, ModelManagerError, ModelStatus


def test_model_manager_init(tmp_path: Path):
    models_dir = tmp_path / "models"
    manager = ModelManager(models_dir=models_dir, default_model="0.6b")

    assert manager.status == ModelStatus.UNLOADED
    assert manager.current_model_name is None
    assert manager.current_model is None
    assert manager.last_error is None
    assert models_dir.is_dir()
    assert os.environ.get("HF_HOME") == str(models_dir / "huggingface")


def test_resolve_model_id(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)
    assert manager.resolve_model_id("0.6b") == "Qwen/Qwen3-ASR-0.6B"
    assert manager.resolve_model_id("1.7B") == "Qwen/Qwen3-ASR-1.7B"
    assert manager.resolve_model_id("custom/path/model") == "custom/path/model"


def test_load_model_success(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path, default_model="0.6b")

    mock_qwen_module = MagicMock()
    mock_model_cls = MagicMock()
    mock_model_instance = MagicMock()
    mock_model_cls.from_pretrained.return_value = mock_model_instance
    mock_qwen_module.Qwen3ASRModel = mock_model_cls

    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module}):
        model = manager.load_model("0.6b")

        assert model is mock_model_instance
        assert manager.status == ModelStatus.READY
        assert manager.current_model_name == "0.6b"
        assert manager.current_model is mock_model_instance
        mock_model_cls.from_pretrained.assert_called_once()

        # Loading the same model again should return cached instance
        model_again = manager.load_model("0.6b")
        assert model_again is mock_model_instance
        assert mock_model_cls.from_pretrained.call_count == 1


def test_load_model_switch_unloads_previous(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)

    mock_qwen_module = MagicMock()
    mock_model_cls = MagicMock()
    mock_instance_1 = MagicMock()
    mock_instance_2 = MagicMock()
    mock_model_cls.from_pretrained.side_effect = [mock_instance_1, mock_instance_2]
    mock_qwen_module.Qwen3ASRModel = mock_model_cls

    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module}):
        manager.load_model("0.6b")
        assert manager.current_model_name == "0.6b"

        # Switch to 1.7b
        manager.load_model("1.7b")
        assert manager.current_model_name == "1.7b"
        assert manager.current_model is mock_instance_2
        assert mock_model_cls.from_pretrained.call_count == 2


def test_load_model_qwen_not_installed(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)

    with patch.dict(sys.modules, {"qwen_asr": None}):
        with pytest.raises(ModelManagerError, match="尚未安裝 qwen-asr"):
            manager.load_model("0.6b")
        assert manager.status == ModelStatus.ERROR
        assert manager.last_error is not None


def test_load_model_exception_handled(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)

    mock_qwen_module = MagicMock()
    mock_model_cls = MagicMock()
    mock_model_cls.from_pretrained.side_effect = RuntimeError("Out of memory")
    mock_qwen_module.Qwen3ASRModel = mock_model_cls

    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module}):
        with pytest.raises(ModelManagerError, match="模型載入失敗"):
            manager.load_model("1.7b")

        assert manager.status == ModelStatus.ERROR
        assert "Out of memory" in str(manager.last_error)


def test_load_model_torch_cuda_and_mps_device(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)

    mock_qwen_module = MagicMock()
    mock_model_cls = MagicMock()
    mock_qwen_module.Qwen3ASRModel = mock_model_cls

    # Test CUDA detection
    mock_torch_cuda = MagicMock()
    mock_torch_cuda.cuda.is_available.return_value = True
    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module, "torch": mock_torch_cuda}):
        manager.load_model("0.6b")
        mock_model_cls.from_pretrained.assert_called_with(
            "Qwen/Qwen3-ASR-0.6B",
            device_map="cuda:0",
            cache_dir=str(tmp_path / "huggingface" / "hub"),
        )

    # Test MPS detection
    manager.unload_model()
    mock_torch_mps = MagicMock()
    mock_torch_mps.cuda.is_available.return_value = False
    mock_torch_mps.backends.mps.is_available.return_value = True
    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module, "torch": mock_torch_mps}):
        manager.load_model("1.7b")
        mock_model_cls.from_pretrained.assert_called_with(
            "Qwen/Qwen3-ASR-1.7B",
            device_map="mps",
            cache_dir=str(tmp_path / "huggingface" / "hub"),
        )


def test_unload_model_with_torch_cache_cleaning(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)
    manager._current_model_instance = MagicMock()
    manager._current_model_name = "0.6b"
    manager._status = ModelStatus.READY

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.mps.empty_cache = MagicMock()

    with patch.dict(sys.modules, {"torch": mock_torch}):
        manager.unload_model()

    assert manager.status == ModelStatus.UNLOADED
    mock_torch.cuda.empty_cache.assert_called_once()
    mock_torch.mps.empty_cache.assert_called_once()


def test_local_model_directory_precedence(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)
    local_06b_dir = tmp_path / "0.6b"
    local_06b_dir.mkdir(parents=True)
    (local_06b_dir / "config.json").write_text("{}", encoding="utf-8")

    resolved = manager.resolve_model_id("0.6b")
    assert resolved == str(local_06b_dir)

    status = manager.check_local_model_availability("0.6b")
    assert status["available"] is True
    assert status["source"] == "local_dir"
    assert status["path"] == str(local_06b_dir)


def test_hf_cache_model_availability(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)
    hf_snapshot_dir = tmp_path / "huggingface" / "hub" / "models--Qwen--Qwen3-ASR-0.6B" / "snapshots" / "abc123"
    hf_snapshot_dir.mkdir(parents=True)
    (hf_snapshot_dir / "model.safetensors").write_text("fake", encoding="utf-8")

    status = manager.check_local_model_availability("0.6b")
    assert status["available"] is True
    assert status["source"] == "hf_cache"


def test_offline_guidance_message(tmp_path: Path):
    manager = ModelManager(models_dir=tmp_path)
    status = manager.check_local_model_availability("1.7b")
    assert status["available"] is False
    assert status["source"] == "remote_hub"
    assert "純離線部署" in status["guidance"]
