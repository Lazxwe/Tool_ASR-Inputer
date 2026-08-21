"""Application main entrypoint."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from src.app.application import VoiceInputApp


def setup_logging(verbose: bool = False) -> None:
    """Configure console logging format and level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Main entrypoint for Tool_ASR Inputer."""
    parser = argparse.ArgumentParser(
        description="Tool_ASR Inputer: Minimalist Local Traditional Chinese AI Voice Typing Tool"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.json",
        help="Path to configuration JSON file (default: config.json)",
    )
    parser.add_argument(
        "-d", "--dictionary",
        type=str,
        default="custom_dictionary.json",
        help="Path to custom dictionary JSON file (default: custom_dictionary.json)",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable system tray / menu bar UI",
    )
    parser.add_argument(
        "--doctor", "--check",
        action="store_true",
        dest="doctor",
        help="Run system diagnostic health check and exit",
    )
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Reset config.json to factory defaults (with backup) and exit",
    )
    parser.add_argument(
        "--download-model", "--download",
        type=str,
        default=None,
        metavar="MODEL",
        help="Download specified ASR model (e.g. '0.6b' or '1.7b') with progress bar and exit",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

    # Handle --download-model request
    if args.download_model:
        from src.asr.model_manager import ModelManager
        manager = ModelManager(models_dir=Path(args.config).parent / "models")
        try:
            print(f"正在連線 Hugging Face 下載模型 '{args.download_model}' (請稍候)...")
            path = manager.download_model(args.download_model)
            print(f"✓ 模型 '{args.download_model}' 下載完成！本地存放路徑:\n  {path}")
            return 0
        except Exception as e:
            print(f"✗ 模型下載失敗: {e}")
            return 1

    # Handle --reset-config request
    if args.reset_config:
        from src.settings.config import reset_config
        cfg_path = Path(args.config)
        success, backup_path = reset_config(cfg_path, backup_old=True)
        if success:
            msg = f"✓ 已成功將設定檔 ({cfg_path}) 重置為原廠預設值！"
            if backup_path:
                msg += f"\n  舊設定檔已自動備份至: {backup_path}"
            print(msg)
            return 0
        else:
            print(f"✗ 重置設定檔 ({cfg_path}) 失敗，請檢查檔案權限。")
            return 1

    # Run system diagnosis if --doctor is requested
    if args.doctor:
        from src.diagnostics import SystemDoctor
        doctor = SystemDoctor(
            config_path=Path(args.config),
            dictionary_path=Path(args.dictionary),
        )
        report = doctor.run_all_diagnostics()
        print(report.render_cli())
        return 0

    logger.info("Initializing Tool_ASR Inputer...")
    app = VoiceInputApp(
        config_path=Path(args.config),
        dictionary_path=Path(args.dictionary),
        enable_tray=not args.no_tray,
        enable_hotkey=True,
    )

    # Signal handlers for clean shutdown
    def handle_signal(sig: int, frame: object) -> None:
        logger.info("Received signal %d. Shutting down...", sig)
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    app.start()

    # Keep main thread alive if tray is in detached mode
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Stopping...")
        app.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
