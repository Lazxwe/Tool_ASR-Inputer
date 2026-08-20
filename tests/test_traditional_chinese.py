"""Unit tests for TraditionalChineseConverter."""
from src.text.traditional_chinese import TraditionalChineseConverter


def test_converter_basic():
    converter = TraditionalChineseConverter()
    assert converter.convert("内存") == "記憶體"
    assert converter.convert("软件") == "軟體"
    assert converter.convert("") == ""


def test_converter_error_fallback():
    converter = TraditionalChineseConverter(config_name="non_existent_config_12345")
    # Graceful fallback when initialization failed
    assert converter.convert("任意文字") == "任意文字"
