"""Unit tests for configuration loading and saving."""
import json
from pathlib import Path
from src.settings.config import AppConfig, load_config, save_config


def test_load_default_when_file_missing(tmp_path: Path):
    missing_file = tmp_path / "non_existent.json"
    config = load_config(missing_file)
    assert config.model == "0.6b"
    assert config.hotkey == "f8"
    assert config.hotkey_mode == "hold"
    assert config.model_dir == "./models"
    assert config.sample_rate == 16000
    assert config.language == "Chinese"


def test_load_valid_config(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "model": "1.7b",
            "hotkey": "f9",
            "hotkey_mode": "toggle",
            "model_dir": "./custom_models",
            "sample_rate": 8000,
            "language": "zh",
        }),
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.model == "1.7b"
    assert config.hotkey == "f9"
    assert config.hotkey_mode == "toggle"
    assert config.model_dir == "./custom_models"
    assert config.sample_rate == 8000
    assert config.language == "zh"


def test_load_invalid_model_fallback(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "invalid_model_size"}), encoding="utf-8")
    config = load_config(config_file)
    assert config.model == "0.6b"


def test_load_config_root_not_dict(tmp_path: Path):
    config_file = tmp_path / "array_config.json"
    config_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    config = load_config(config_file)
    assert config.model == "0.6b"


def test_load_config_corrupted_json(tmp_path: Path):
    config_file = tmp_path / "corrupted.json"
    config_file.write_text("{ corrupt", encoding="utf-8")
    config = load_config(config_file)
    assert config.model == "0.6b"


def test_save_and_reload_config(tmp_path: Path):
    config_file = tmp_path / "saved_config.json"
    original = AppConfig(
        model="1.7b",
        hotkey="f8",
        model_dir="./models",
        sample_rate=16000,
        language="Chinese",
    )
    success = save_config(original, config_file)
    assert success is True
    assert config_file.is_file()

    reloaded = load_config(config_file)
    assert reloaded.model == "1.7b"
    assert reloaded.hotkey == "f8"
    assert reloaded.model_dir == "./models"
    assert reloaded.sample_rate == 16000
    assert reloaded.language == "Chinese"


def test_reset_config_with_backup(tmp_path: Path):
    from src.settings.config import reset_config

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "1.7b", "hotkey": "f12"}), encoding="utf-8")

    success, backup_path = reset_config(config_file, backup_old=True)
    assert success is True
    assert backup_path is not None
    assert backup_path.is_file()
    assert "f12" in backup_path.read_text(encoding="utf-8")

    reloaded = load_config(config_file)
    assert reloaded.model == "0.6b"
    assert reloaded.hotkey == "f8"
    assert reloaded.hotkey_mode == "hold"


def test_reset_config_non_existent_file(tmp_path: Path):
    from src.settings.config import reset_config

    config_file = tmp_path / "missing.json"
    success, backup_path = reset_config(config_file, backup_old=True)
    assert success is True
    assert backup_path is None
    assert config_file.is_file()
