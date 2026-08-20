"""Settings and configuration management."""
from .config import AppConfig, load_config, save_config
from .dictionary_loader import DictionaryData, DictionaryEntry, load_dictionary

__all__ = [
    "AppConfig",
    "load_config",
    "save_config",
    "DictionaryData",
    "DictionaryEntry",
    "load_dictionary",
]
