"""Unit tests for main entrypoint CLI."""
import sys
from unittest.mock import MagicMock, patch

from src.main import main, setup_logging


def test_setup_logging() -> None:
    setup_logging(verbose=True)
    setup_logging(verbose=False)


def test_main_cli_execution() -> None:
    test_args = ["main.py", "--no-tray", "-c", "config.json", "-v"]

    with patch.object(sys, "argv", test_args), \
         patch("src.main.VoiceInputApp") as mock_app_cls, \
         patch("time.sleep", side_effect=KeyboardInterrupt):

        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app

        exit_code = main()
        assert exit_code == 0
        assert mock_app.start.called
        assert mock_app.stop.called
