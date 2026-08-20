"""PyInstaller automated build script for Tool_ASR Inputer."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ENTRY_POINT = SRC_DIR / "main.py"


def find_opencc_data_dir() -> Path:
    """Locate opencc assets directory in python environment."""
    import opencc
    opencc_root = Path(opencc.__file__).resolve().parent
    return opencc_root


def run_pyinstaller() -> None:
    """Execute PyInstaller with custom specifications."""
    print("=" * 60)
    print("Building Tool_ASR Inputer executable via PyInstaller...")
    print("=" * 60)

    # 1. Locate opencc data directory
    opencc_dir = find_opencc_data_dir()
    print(f"OpenCC module path: {opencc_dir}")

    # Separator for PyInstaller --add-data (';' on Windows, ':' on Unix)
    sep = ";" if platform.system().lower() == "windows" else ":"
    opencc_add_data = f"{opencc_dir}{sep}opencc"

    # 2. Base PyInstaller arguments
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=Tool_ASR_Inputer",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--add-data={opencc_add_data}",
        "--hidden-import=opencc",
        "--hidden-import=numpy",
        "--hidden-import=sounddevice",
        "--hidden-import=pyperclip",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=pynput",
        "--hidden-import=pynput.keyboard",
        "--hidden-import=pynput.mouse",
    ]

    # Platform-specific hidden imports
    current_os = platform.system().lower()
    if "darwin" in current_os:
        cmd.extend([
            "--hidden-import=pynput.keyboard._darwin",
            "--hidden-import=pynput.mouse._darwin",
            "--hidden-import=pystray._darwin",
        ])
    elif "windows" in current_os:
        cmd.extend([
            "--hidden-import=pynput.keyboard._win32",
            "--hidden-import=pynput.mouse._win32",
            "--hidden-import=pystray._win32",
        ])
    else:
        cmd.extend([
            "--hidden-import=pynput.keyboard._xorg",
            "--hidden-import=pynput.mouse._xorg",
            "--hidden-import=pystray._xorg",
        ])

    cmd.append(str(ENTRY_POINT))

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with return code {result.returncode}")

    print("PyInstaller build finished successfully.")


def package_distribution() -> None:
    """Assemble external configuration, dictionaries, and model directories into dist."""
    target_dist_dir = DIST_DIR / "Tool_ASR_Inputer"
    if not target_dist_dir.exists():
        print(f"Warning: Expected dist directory not found at {target_dist_dir}")
        return

    print("Copying external configuration files to dist...")

    # Copy config.json and custom_dictionary.json
    for filename in ("config.json", "custom_dictionary.json", "README.md"):
        src_file = PROJECT_ROOT / filename
        if src_file.exists():
            shutil.copy2(src_file, target_dist_dir / filename)
            print(f"  -> Copied {filename}")

    # Prepare models directory structure in distribution
    dist_models_dir = target_dist_dir / "models"
    (dist_models_dir / "0.6b").mkdir(parents=True, exist_ok=True)
    (dist_models_dir / "1.7b").mkdir(parents=True, exist_ok=True)

    model_readme = dist_models_dir / "README.txt"
    model_readme.write_text(
        "【純離線模型放置說明】\n"
        "若要在無網路連線環境下使用，請將 Qwen3-ASR 模型檔案分別放置於此目錄下的子資料夾：\n"
        "  - 0.6B 模型: ./models/0.6b/\n"
        "  - 1.7B 模型: ./models/1.7b/\n"
        "若具備網路連線，系統將於首次執行時自動快取下載。\n",
        encoding="utf-8",
    )
    print(f"  -> Initialized models directory structure at {dist_models_dir}")

    print("=" * 60)
    print("Distribution assembly complete!")
    print(f"Output folder: {target_dist_dir}")
    print("=" * 60)


def main() -> int:
    """Main build runner."""
    try:
        run_pyinstaller()
        package_distribution()
        return 0
    except Exception as e:
        print(f"Build failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
