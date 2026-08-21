"""Automated post-build verification script for Tool_ASR Inputer."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist" / "Tool_ASR_Inputer"


def verify_dist() -> bool:
    print("=" * 60)
    print("Verifying Tool_ASR Inputer packaged distribution...")
    print(f"Target directory: {DIST_DIR}")
    print("=" * 60)

    if not DIST_DIR.exists():
        print(f"❌ Error: Distribution folder does not exist at {DIST_DIR}")
        return False

    is_windows = platform.system().lower() == "windows"
    exe_name = "Tool_ASR_Inputer.exe" if is_windows else "Tool_ASR_Inputer"
    exe_path = DIST_DIR / exe_name

    # 1. Check Executable Exists
    if not exe_path.exists():
        print(f"❌ Error: Executable not found at {exe_path}")
        return False
    print(f"✓ Found executable: {exe_path.name}")

    # 2. Check Configuration & Assets
    required_files = ["config.json", "custom_dictionary.json"]
    for rf in required_files:
        fpath = DIST_DIR / rf
        if not fpath.exists():
            print(f"❌ Error: Missing required file '{rf}' in dist root")
            return False
        print(f"✓ Found asset file: {rf}")

    # 3. Check Windows-specific requirements (python3.dll)
    if is_windows:
        has_python3_dll = (
            (DIST_DIR / "python3.dll").exists()
            or (DIST_DIR / "_internal" / "python3.dll").exists()
        )
        if not has_python3_dll:
            print("❌ WARNING: 'python3.dll' was NOT found in dist or _internal/!")
            print("  This may cause 'safetensors' (Rust Stable ABI) to fail with 'DLL load failed'.")
            return False
        print("✓ Verified 'python3.dll' (Python Stable ABI forwarding layer) is present.")

    # 4. Smoke Test: Run --doctor or --help
    print("\nExecuting CLI smoke test...")
    try:
        res = subprocess.run(
            [str(exe_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(DIST_DIR),
        )
        if res.returncode != 0:
            print(f"❌ Executable failed CLI smoke test (Return code {res.returncode})")
            print(f"STDERR:\n{res.stderr}")
            return False
        print("✓ CLI smoke test passed (--help executed successfully).")
    except Exception as e:
        print(f"❌ Execution failed during smoke test: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 All package verification checks passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = verify_dist()
    sys.exit(0 if success else 1)
