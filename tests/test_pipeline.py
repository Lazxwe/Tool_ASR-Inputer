"""Unit tests for full TextPipeline."""
import json
from pathlib import Path
from src.text.pipeline import TextPipeline


def test_text_pipeline_full_conversion(tmp_path: Path):
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"target": "程式", "variants": ["城市"]},
            {"target": "影片", "variants": ["視頻"]}
        ]
    }), encoding="utf-8")

    pipeline = TextPipeline(dict_path=dict_file)

    # Simplified Chinese text with OpenCC target + dictionary target
    # 软件 -> 軟體 (via OpenCC s2twp)
    # 城市 -> 程式 (via Custom Dictionary)
    # 视频 -> 影片 (via Custom Dictionary / OpenCC)
    raw_asr_output = "我今天要修改城市的接口软件和视频"
    result = pipeline.process(raw_asr_output)

    assert "程式" in result
    assert "城市" not in result
    assert "介面" in result or "接口" not in result
    assert "軟體" in result
    assert "影片" in result


def test_text_pipeline_reload_dictionary(tmp_path: Path):
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"target": "程式", "variants": ["城市"]}
        ]
    }), encoding="utf-8")

    pipeline = TextPipeline(dict_path=dict_file)
    assert pipeline.process("修改城市") == "修改程式"

    # Update dictionary file
    dict_file.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"target": "專案", "variants": ["項目"]}
        ]
    }), encoding="utf-8")

    pipeline.reload_dictionary()
    assert pipeline.process("修改項目") == "修改專案"


def test_text_pipeline_empty_and_spaces():
    pipeline = TextPipeline()
    assert pipeline.process("") == ""
    assert pipeline.process("   \n\t  ") == ""
