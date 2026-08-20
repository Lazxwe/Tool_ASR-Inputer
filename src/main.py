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
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

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
