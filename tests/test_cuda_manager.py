"""Unit tests for Windows CUDA Manager."""
import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.asr.cuda_manager import CUDAManager


def test_cuda_manager_is_supported_platform():
    mgr = CUDAManager()
    with patch("platform.system", return_value="Windows"):
        assert mgr.is_supported_platform() is True
    with patch("platform.system", return_value="Darwin"):
        assert mgr.is_supported_platform() is False


def test_cuda_manager_is_addon_installed(tmp_path: Path):
    addon_dir = tmp_path / "cuda_addon"
    mgr = CUDAManager(addon_dir=addon_dir)

    assert mgr.is_addon_installed() is False

    # Create dummy dll
    addon_dir.mkdir(parents=True)
    (addon_dir / "test.dll").write_bytes(b"dummy dll")
    assert mgr.is_addon_installed() is True

    # Or marker file
    (addon_dir / "test.dll").unlink()
    (addon_dir / ".installed").write_text("installed=true")
    assert mgr.is_addon_installed() is True


def test_cuda_manager_download_and_install(tmp_path: Path):
    addon_dir = tmp_path / "cuda_addon"
    mgr = CUDAManager(addon_dir=addon_dir)

    # Create a mock zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("cublas64_12.dll", "mock dll content")
    zip_bytes = zip_buffer.getvalue()

    mock_resp = MagicMock()
    mock_resp.headers = {"content-length": str(len(zip_bytes))}
    mock_resp.read.side_effect = [zip_bytes, b""]
    mock_resp.__enter__.return_value = mock_resp

    progress_calls = []
    def on_progress(pct, downloaded, total):
        progress_calls.append((pct, downloaded, total))

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with patch("platform.system", return_value="Windows"):
            success = mgr.download_and_install(progress_callback=on_progress)
            assert success is True
            assert mgr.is_addon_installed() is True
            assert (addon_dir / "cublas64_12.dll").exists()
            assert len(progress_calls) > 0
            assert progress_calls[-1][0] == 100.0


def test_cuda_manager_remove_addon(tmp_path: Path):
    addon_dir = tmp_path / "cuda_addon"
    addon_dir.mkdir()
    (addon_dir / "dummy.dll").write_text("content")

    mgr = CUDAManager(addon_dir=addon_dir)
    assert mgr.remove_addon() is True
    assert not addon_dir.exists()
