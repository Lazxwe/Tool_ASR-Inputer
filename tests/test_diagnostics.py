"""Unit tests for SystemDoctor and diagnostic utilities."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.diagnostics import DiagnosticItem, DiagnosticReport, SystemDoctor


def test_diagnostic_report_all_passed():
    report = DiagnosticReport(
        system_info={"OS": "Darwin"},
        items=[
            DiagnosticItem(category="Cat1", name="Item1", passed=True, details="OK"),
            DiagnosticItem(category="Cat2", name="Item2", passed=True, details="OK"),
        ],
    )
    assert report.all_passed is True
    rendered = report.render_cli()
    assert "所有核心檢查均正常" in rendered
    assert "Item1: OK" in rendered


def test_diagnostic_report_with_failures():
    report = DiagnosticReport(
        system_info={"OS": "Darwin"},
        items=[
            DiagnosticItem(category="Cat1", name="Item1", passed=True, details="OK"),
            DiagnosticItem(
                category="Cat2",
                name="Item2",
                passed=False,
                details="Failed",
                guidance="Please fix this",
            ),
        ],
    )
    assert report.all_passed is False
    rendered = report.render_cli()
    assert "部分檢查有待處理事項" in rendered
    assert "Please fix this" in rendered


def test_doctor_collect_system_info():
    doctor = SystemDoctor()
    info = doctor.collect_system_info()
    assert "作業系統 (OS)" in info
    assert "Python 版本" in info
    assert "執行檔路徑" in info
    assert "運算加速裝置" in info


def test_doctor_check_packages_all_present():
    doctor = SystemDoctor()
    items = doctor.check_packages()
    assert len(items) >= 7
    # All our installed packages should pass
    assert all(item.passed for item in items)


def test_doctor_check_packages_missing():
    doctor = SystemDoctor()
    with patch("builtins.__import__", side_effect=ImportError("No module")):
        items = doctor.check_packages()
        assert all(not item.passed for item in items)


def test_doctor_check_audio_devices_success():
    doctor = SystemDoctor()
    mock_sd = MagicMock()
    mock_sd.query_devices.side_effect = [
        [{"name": "Mic", "max_input_channels": 2}],  # devices list
        {"name": "Default Mic", "max_input_channels": 2},  # kind="input"
    ]
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream
    mock_stream.__enter__.return_value = mock_stream

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        items = doctor.check_audio_devices()
        assert len(items) == 2
        assert items[0].passed is True
        assert items[1].passed is True


def test_doctor_check_audio_devices_no_input_device():
    doctor = SystemDoctor()
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [{"name": "Speaker", "max_input_channels": 0}]

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        items = doctor.check_audio_devices()
        assert len(items) == 1
        assert items[0].passed is False
        assert "未偵測到任何可用的音訊輸入設備" in items[0].details


def test_doctor_check_audio_devices_stream_failure():
    doctor = SystemDoctor()
    mock_sd = MagicMock()
    mock_sd.query_devices.side_effect = [
        [{"name": "Mic", "max_input_channels": 1}],
        {"name": "Default Mic", "max_input_channels": 1},
    ]
    mock_sd.InputStream.side_effect = RuntimeError("Permission denied")

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        items = doctor.check_audio_devices()
        assert len(items) == 2
        assert items[0].passed is True
        assert items[1].passed is False
        assert "Permission denied" in items[1].details


def test_doctor_check_models(tmp_path: Path):
    doctor = SystemDoctor(models_dir=tmp_path)
    # Create 0.6b local dir
    local_06b = tmp_path / "0.6b"
    local_06b.mkdir()
    (local_06b / "config.json").write_text("{}", encoding="utf-8")

    items = doctor.check_models()
    assert len(items) == 2
    # 0.6b passes because local dir exists
    item_06b = next(it for it in items if "0.6B" in it.name)
    assert item_06b.passed is True

    # 1.7b is not downloaded
    item_17b = next(it for it in items if "1.7B" in it.name)
    assert item_17b.passed is False


def test_doctor_check_custom_dictionary(tmp_path: Path):
    dict_file = tmp_path / "custom_dictionary.json"
    doctor = SystemDoctor(dictionary_path=dict_file)

    # 1. Missing dictionary
    items = doctor.check_custom_dictionary()
    assert items[0].passed is False

    # 2. Valid dictionary
    dict_file.write_text('{"version": 1, "entries": [{"target": "程式", "variants": ["城市"]}]}', encoding="utf-8")
    items = doctor.check_custom_dictionary()
    assert items[0].passed is True
    assert "有效詞條 1 組" in items[0].details

    # 3. Empty dictionary
    dict_file.write_text('{"version": 1, "entries": []}', encoding="utf-8")
    items = doctor.check_custom_dictionary()
    assert items[0].passed is True
    assert "詞庫為空" in items[0].details


def test_doctor_check_config(tmp_path: Path):
    config_file = tmp_path / "config.json"
    doctor = SystemDoctor(config_path=config_file)

    # 1. Missing config (passes with defaults)
    items = doctor.check_config()
    assert items[0].passed is True
    assert "預設參數運作" in items[0].details

    # 2. Existing config
    config_file.write_text('{"model": "1.7b", "hotkey": "f8"}', encoding="utf-8")
    items = doctor.check_config()
    assert items[0].passed is True
    assert "預設模型: 1.7b" in items[0].details


def test_doctor_run_all_diagnostics(tmp_path: Path):
    doctor = SystemDoctor(
        config_path=tmp_path / "config.json",
        dictionary_path=tmp_path / "custom_dictionary.json",
        models_dir=tmp_path / "models",
    )
    report = doctor.run_all_diagnostics()
    assert isinstance(report, DiagnosticReport)
    assert len(report.items) > 0
    assert len(report.system_info) > 0
