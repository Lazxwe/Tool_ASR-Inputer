"""Unit tests for configuration loading and saving."""
import json
from pathlib import Path
from src.settings.config import AppConfig, load_config, save_config


def test_load_default_when_file_missing(tmp_path: Path):
    missing_file = tmp_path / "non_existent.json"
    config = load_config(missing_file)
    assert config.model == "0.6b"
    assert config.hotkey == "f8"
    assert config.model_dir == "./models"


def test_load_valid_config(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "1.7b", "hotkey": "f9", "model_dir": "./custom_models"}), encoding="utf-8")
    config = load_config(config_file)
    assert config.model == "1.7b"
    assert config.hotkey == "f9"
    assert config.model_dir == "./custom_models"


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
    original = AppConfig(model="1.7b", hotkey="f8", model_dir="./models")
    success = save_config(original, config_file)
    assert success is True
    assert config_file.is_file()

    reloaded = load_config(config_file)
    assert reloaded.model == "1.7b"
    assert reloaded.hotkey == "f8"
    assert reloaded.model_dir == "./models"
