"""Windows On-Demand CUDA Addon Manager.

Handles checking, downloading, extracting, and dynamic DLL registration
for NVIDIA GPU acceleration on Windows.
"""
from __future__ import annotations

import logging
import os
import platform
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_CUDA_ADDON_DIR = Path("cuda_addon")
DEFAULT_CUDA_ADDON_URL = (
    "https://github.com/Lazxwe/Tool_ASR-Inputer/releases/download/v0.3/cuda121_win64_addon.zip"
)


class CUDAManager:
    """Manages the lifecycle of optional CUDA runtime libraries on Windows."""

    def __init__(
        self,
        addon_dir: Path | str = DEFAULT_CUDA_ADDON_DIR,
        download_url: str = "",
    ) -> None:
        self.addon_dir = Path(addon_dir)
        self.download_url = download_url.strip() or DEFAULT_CUDA_ADDON_URL
        self._dll_handle: Optional[object] = None

    def is_supported_platform(self) -> bool:
        """Only Windows requires separate CUDA DLL dynamic addon loading."""
        return platform.system().lower() == "windows"

    def is_addon_installed(self) -> bool:
        """Check if CUDA addon directory exists and is validly installed."""
        if not self.addon_dir.is_dir():
            return False
        # Check marker file or presence of key DLLs
        marker = self.addon_dir / ".installed"
        if marker.is_file():
            return True
        dlls = list(self.addon_dir.glob("*.dll"))
        return len(dlls) > 0

    def register_addon_dlls(self) -> bool:
        """Add addon directory to Windows dynamic library search path."""
        if not self.is_supported_platform():
            return True

        if not self.is_addon_installed():
            logger.debug("CUDA addon is not installed at %s", self.addon_dir)
            return False

        resolved_path = self.addon_dir.resolve()
        try:
            # Python 3.8+ on Windows uses os.add_dll_directory
            if hasattr(os, "add_dll_directory"):
                self._dll_handle = os.add_dll_directory(str(resolved_path))
                logger.info("Registered CUDA DLL directory: %s", resolved_path)

            # Also prepend to system PATH as compatibility fallback
            curr_path = os.environ.get("PATH", "")
            if str(resolved_path) not in curr_path:
                os.environ["PATH"] = f"{resolved_path};{curr_path}"

            return True
        except Exception as e:
            logger.error("Failed to register CUDA DLL directory %s: %s", resolved_path, e)
            return False

    def download_and_install(
        self,
        url: Optional[str] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        chunk_size: int = 1024 * 1024,  # 1MB
    ) -> bool:
        """Download and extract CUDA addon package.

        Args:
            url: Optional custom URL; defaults to self.download_url.
            progress_callback: Callable accepting (percent: float, downloaded_bytes: int, total_bytes: int).
            chunk_size: Streaming chunk size in bytes.

        Returns:
            bool: True if installation succeeded, False otherwise.
        """
        target_url = url or self.download_url
        self.addon_dir.mkdir(parents=True, exist_ok=True)
        temp_zip = self.addon_dir / "cuda_addon_download.tmp.zip"

        logger.info("Starting CUDA addon download from: %s", target_url)
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Tool_ASR_Inputer_CUDAManager"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(temp_zip, "wb") as f_out:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            pct = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                            progress_callback(pct, downloaded, total_size)

            logger.info("Download completed (%d bytes). Extracting to %s...", downloaded, self.addon_dir)

            # Unpack zip archive
            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                zip_ref.extractall(self.addon_dir)

            # Create completion marker
            marker = self.addon_dir / ".installed"
            marker.write_text(f"installed_from={target_url}\n", encoding="utf-8")

            # Cleanup temporary archive
            if temp_zip.is_file():
                temp_zip.unlink()

            # Register DLLs immediately
            self.register_addon_dlls()
            logger.info("CUDA addon successfully installed and registered!")
            return True

        except Exception as e:
            logger.error("CUDA addon installation failed: %s", e)
            if temp_zip.is_file():
                try:
                    temp_zip.unlink()
                except Exception:
                    pass
            return False

    def remove_addon(self) -> bool:
        """Remove the installed CUDA addon directory to reclaim disk space."""
        try:
            if self.addon_dir.exists():
                shutil.rmtree(self.addon_dir)
                logger.info("CUDA addon removed from %s", self.addon_dir)
            return True
        except Exception as e:
            logger.error("Failed to remove CUDA addon: %s", e)
            return False
