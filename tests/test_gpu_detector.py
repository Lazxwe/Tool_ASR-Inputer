"""Unit tests for GPU and hardware accelerator detection."""
from unittest.mock import MagicMock, patch

import pytest

from src.hardware.gpu_detector import (
    NvidiaGpuInfo,
    detect_nvidia_gpu,
    is_apple_silicon,
    is_torch_cuda_ready,
    should_show_device_menu,
)


def test_nvidia_gpu_info_str():
    info1 = NvidiaGpuInfo(name="NVIDIA GeForce RTX 4070", total_memory_mb=12288)
    assert "RTX 4070" in str(info1)
    assert "12288 MB VRAM" in str(info1)

    info2 = NvidiaGpuInfo(name="NVIDIA Device")
    assert str(info2) == "NVIDIA Device"


def test_is_apple_silicon():
    with patch("platform.system", return_value="Darwin"):
        with patch("platform.machine", return_value="arm64"):
            assert is_apple_silicon() is True

    with patch("platform.system", return_value="Windows"):
        assert is_apple_silicon() is False


def test_is_torch_cuda_ready():
    with patch("torch.cuda.is_available", return_value=True):
        assert is_torch_cuda_ready() is True

    with patch("torch.cuda.is_available", return_value=False):
        assert is_torch_cuda_ready() is False


def test_should_show_device_menu_mac():
    with patch("platform.system", return_value="Darwin"):
        # On macOS, device menu must ALWAYS be hidden (Metal/MPS is native)
        assert should_show_device_menu() is False


def test_should_show_device_menu_windows_no_gpu():
    with patch("platform.system", return_value="Windows"):
        with patch("src.hardware.gpu_detector.detect_nvidia_gpu", return_value=None):
            # On Windows without NVIDIA GPU, device menu must be hidden
            assert should_show_device_menu() is False


def test_should_show_device_menu_windows_with_gpu():
    with patch("platform.system", return_value="Windows"):
        with patch("src.hardware.gpu_detector.detect_nvidia_gpu", return_value=NvidiaGpuInfo("RTX 3060")):
            # On Windows with NVIDIA GPU, device menu must be shown
            assert should_show_device_menu() is True


def test_detect_nvidia_gpu_via_nvidia_smi():
    with patch("torch.cuda.is_available", return_value=False):
        with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = "NVIDIA GeForce RTX 3080, 10240\n"
            with patch("subprocess.run", return_value=mock_proc):
                gpu = detect_nvidia_gpu()
                assert gpu is not None
                assert "RTX 3080" in gpu.name
                assert gpu.total_memory_mb == 10240
