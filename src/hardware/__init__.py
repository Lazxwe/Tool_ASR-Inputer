"""Hardware acceleration and device management package."""
from src.hardware.gpu_detector import (
    NvidiaGpuInfo,
    detect_nvidia_gpu,
    is_apple_silicon,
    is_torch_cuda_ready,
    should_show_device_menu,
)

__all__ = [
    "NvidiaGpuInfo",
    "detect_nvidia_gpu",
    "is_apple_silicon",
    "is_torch_cuda_ready",
    "should_show_device_menu",
]
