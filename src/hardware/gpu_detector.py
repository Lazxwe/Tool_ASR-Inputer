"""Hardware acceleration and GPU detection utilities."""
from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NvidiaGpuInfo:
    """NVIDIA GPU hardware details."""
    name: str
    total_memory_mb: Optional[int] = None

    def __str__(self) -> str:
        if self.total_memory_mb:
            return f"{self.name} ({self.total_memory_mb} MB VRAM)"
        return self.name


def is_apple_silicon() -> bool:
    """Check if the current host is macOS running on Apple Silicon (M1/M2/M3/M4...)."""
    if platform.system().lower() != "darwin":
        return False
    # Check arm64 or MPS backend
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return True
    except Exception:
        pass
    return platform.machine().lower() in ("arm64", "aarch64")


def is_torch_cuda_ready() -> bool:
    """Check if the active PyTorch environment has working CUDA runtime."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def detect_nvidia_gpu() -> Optional[NvidiaGpuInfo]:
    """Detect physical NVIDIA GPU on Windows / Linux hosts.

    First checks PyTorch CUDA runtime, then falls back to nvidia-smi if torch is CPU-only.
    """
    # 1. Check if PyTorch already sees the CUDA GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            mem_bytes = torch.cuda.get_device_properties(0).total_memory
            mem_mb = int(mem_bytes / (1024 * 1024))
            return NvidiaGpuInfo(name=gpu_name, total_memory_mb=mem_mb)
    except Exception as e:
        logger.debug("PyTorch CUDA check raised: %s", e)

    # 2. Fallback: Query nvidia-smi command if installed in system path
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi and platform.system().lower() == "windows":
        # Check standard Windows NVIDIA System32 / Program Files paths
        import os
        candidates = [
            os.path.expandvars(r"%SystemRoot%\System32\nvidia-smi.exe"),
            os.path.expandvars(r"%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                nvidia_smi = c
                break

    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
                if lines:
                    parts = [p.strip() for p in lines[0].split(",")]
                    gpu_name = parts[0]
                    mem_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                    logger.info("Detected NVIDIA GPU via nvidia-smi: %s (%s MB)", gpu_name, mem_mb)
                    return NvidiaGpuInfo(name=gpu_name, total_memory_mb=mem_mb)
        except Exception as ex:
            logger.debug("nvidia-smi query failed: %s", ex)

    # 3. Fallback on Windows: Check nvcuda.dll via ctypes
    if platform.system().lower() == "windows":
        try:
            import ctypes
            # Loading nvcuda.dll verifies the presence of NVIDIA Display Driver
            cuda_lib = ctypes.windll.LoadLibrary("nvcuda.dll")
            if cuda_lib:
                logger.info("Detected NVIDIA driver via nvcuda.dll")
                return NvidiaGpuInfo(name="NVIDIA Graphics Device")
        except Exception:
            pass

    return None


def should_show_device_menu() -> bool:
    """Determine whether the 'Device' menu should be displayed in Tray UI.

    Rule:
    - macOS: Hide (always MPS/Unified Memory)
    - Windows without NVIDIA GPU: Hide (always CPU)
    - Windows with NVIDIA GPU: Show (user chooses between RAM and VRAM)
    """
    sys_os = platform.system().lower()
    if "darwin" in sys_os:
        return False
    if "windows" in sys_os:
        return detect_nvidia_gpu() is not None
    # Linux: Show if NVIDIA GPU is present
    return detect_nvidia_gpu() is not None
