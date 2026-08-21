"""Application configuration management."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class AppConfig:
    """Application configuration schema."""
    model: str = "0.6b"
    hotkey: str = "ctrl_r"
    hotkey_mode: str = "hold"  # 'hold' (按住錄音/鬆開送出) 或 'toggle' (按一下開始/再按一下結束)
    model_dir: str = "./models"
    sample_rate: int = 16000
    language: str = "Chinese"

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load application configuration from a JSON file.

    Falls back to default config if file is missing or invalid.
    """
    path = Path(config_path)
    if not path.is_file():
        logger.info("Config file not found at %s. Using default configuration.", path)
        return AppConfig()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Config root is not an object. Using defaults.")
            return AppConfig()

        model = str(data.get("model", "0.6b")).lower().strip()
        if model not in ("0.6b", "1.7b"):
            logger.warning("Invalid model '%s' in config. Falling back to '0.6b'.", model)
            model = "0.6b"

        hotkey = str(data.get("hotkey", "ctrl_r")).lower().strip()
        hotkey_mode = str(data.get("hotkey_mode", "hold")).lower().strip()
        if hotkey_mode not in ("hold", "toggle"):
            logger.warning("Invalid hotkey_mode '%s' in config. Defaulting to 'hold'.", hotkey_mode)
            hotkey_mode = "hold"

        model_dir = str(data.get("model_dir", "./models"))
        sample_rate = int(data.get("sample_rate", 16000))
        language = str(data.get("language", "Chinese"))

        return AppConfig(
            model=model,
            hotkey=hotkey,
            hotkey_mode=hotkey_mode,
            model_dir=model_dir,
            sample_rate=sample_rate,
            language=language,
        )

    except json.JSONDecodeError as jde:
        logger.error(
            "Config JSON syntax error at %s (Line %d, Col %d): %s. Run with --reset-config to restore defaults.",
            path, jde.lineno, jde.colno, jde.msg
        )
        return AppConfig()
    except Exception as e:
        logger.warning("Failed to parse config file at %s: %s. Using defaults.", path, e)
        return AppConfig()


def save_config(config: AppConfig, config_path: Path | str = DEFAULT_CONFIG_PATH) -> bool:
    """Save application configuration to a JSON file."""
    path = Path(config_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("Failed to write config file to %s: %s", path, e)
        return False


def reset_config(
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    backup_old: bool = True,
) -> tuple[bool, Optional[Path]]:
    """Reset configuration file to factory defaults, optionally backing up the old file.

    Returns:
        tuple of (success: bool, backup_path: Optional[Path])
    """
    path = Path(config_path)
    backup_path: Optional[Path] = None

    try:
        if path.is_file() and backup_old:
            backup_path = path.with_suffix(path.suffix + ".bak")
            try:
                import shutil
                shutil.copy2(path, backup_path)
                logger.info("Backed up existing config from %s to %s", path, backup_path)
            except Exception as b_err:
                logger.warning("Could not create config backup: %s", b_err)

        default_config = AppConfig()
        saved = save_config(default_config, path)
        if saved:
            logger.info("Successfully reset %s to factory defaults.", path)
            return True, backup_path
        return False, None

    except Exception as e:
        logger.error("Failed to reset config file %s: %s", path, e)
        return False, None
