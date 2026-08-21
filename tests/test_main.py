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


def test_main_cli_doctor() -> None:
    test_args = ["main.py", "--doctor"]

    with patch.object(sys, "argv", test_args), \
         patch("src.diagnostics.SystemDoctor.run_all_diagnostics") as mock_diag, \
         patch("builtins.print") as mock_print:

        mock_report = MagicMock()
        mock_report.render_cli.return_value = "DIAGNOSTIC_OUTPUT"
        mock_diag.return_value = mock_report

        exit_code = main()
        assert exit_code == 0
        mock_print.assert_called_with("DIAGNOSTIC_OUTPUT")


def test_main_cli_reset_config_success(tmp_path) -> None:
    cfg = tmp_path / "config.json"
    test_args = ["main.py", "--reset-config", "-c", str(cfg)]

    with patch.object(sys, "argv", test_args), \
         patch("src.settings.config.reset_config", return_value=(True, tmp_path / "config.json.bak")), \
         patch("builtins.print") as mock_print:
        exit_code = main()
        assert exit_code == 0
        assert any("成功將設定檔" in str(c) for c in mock_print.call_args_list)


def test_main_cli_reset_config_failure(tmp_path) -> None:
    cfg = tmp_path / "config.json"
    test_args = ["main.py", "--reset-config", "-c", str(cfg)]

    with patch.object(sys, "argv", test_args), \
         patch("src.settings.config.reset_config", return_value=(False, None)), \
         patch("builtins.print") as mock_print:
        exit_code = main()
        assert exit_code == 1
