"""Unit tests for dictionary loading and deterministic replacement."""
import json
from pathlib import Path
from src.settings.dictionary_loader import DictionaryData, DictionaryEntry, load_dictionary
from src.text.dictionary import DictionaryCorrector


def test_load_dictionary_when_missing(tmp_path: Path):
    missing_path = tmp_path / "not_found.json"
    dict_data = load_dictionary(missing_path)
    assert dict_data.version == 1
    assert len(dict_data.entries) == 0


def test_load_dictionary_valid(tmp_path: Path):
    dict_file = tmp_path / "dict.json"
    dict_file.write_text(json.dumps({
        "version": 1,
        "entries": [
            {"target": "程式", "variants": ["城市", "乘勢"]},
            {"target": "介面", "variants": ["接口"]}
        ]
    }), encoding="utf-8")

    dict_data = load_dictionary(dict_file)
    assert dict_data.version == 1
    assert len(dict_data.entries) == 2
    assert dict_data.entries[0].target == "程式"
    assert dict_data.entries[0].variants == ["城市", "乘勢"]
    assert dict_data.entries[1].target == "介面"
    assert dict_data.entries[1].variants == ["接口"]


def test_load_dictionary_corrupted_json(tmp_path: Path):
    dict_file = tmp_path / "broken.json"
    dict_file.write_text("{ broken json: [", encoding="utf-8")
    dict_data = load_dictionary(dict_file)
    assert len(dict_data.entries) == 0


def test_corrector_exact_replacement():
    entries = [
        DictionaryEntry(target="程式", variants=["城市"]),
        DictionaryEntry(target="介面", variants=["接口"]),
    ]
    corrector = DictionaryCorrector(entries)
    result = corrector.correct("我今天要修改城市的接口")
    assert result == "我今天要修改程式的介面"


def test_corrector_longest_match_precedence():
    entries = [
        DictionaryEntry(target="人工智慧", variants=["智慧"]),
        DictionaryEntry(target="生成式人工智慧", variants=["人工智慧"]),
    ]
    corrector = DictionaryCorrector(entries)
    # Longest variant matches properly without mangling
    result = corrector.correct("這是一個智慧系統")
    assert result == "這是一個人工智慧系統"


def test_corrector_no_match_preserves_text():
    entries = [DictionaryEntry(target="程式", variants=["城市"])]
    corrector = DictionaryCorrector(entries)
    original = "今天天氣非常好，沒有問題。"
    assert corrector.correct(original) == original


def test_load_dictionary_malformed_entries(tmp_path: Path):
    dict_file = tmp_path / "malformed.json"
    dict_file.write_text(json.dumps({
        "version": "not_int",
        "entries": [
            "not_a_dict",
            {"target": "", "variants": ["測試"]},
            {"target": "正常", "variants": "not_a_list"},
            {"target": "目標", "variants": ["  變體  ", 123, ""]}
        ]
    }), encoding="utf-8")

    dict_data = load_dictionary(dict_file)
    assert dict_data.version == 1
    assert len(dict_data.entries) == 2
    assert dict_data.entries[0].target == "正常"
    assert dict_data.entries[0].variants == []
    assert dict_data.entries[1].target == "目標"
    assert dict_data.entries[1].variants == ["變體"]


def test_load_dictionary_root_not_dict(tmp_path: Path):
    dict_file = tmp_path / "array_root.json"
    dict_file.write_text(json.dumps([{"target": "測試"}]), encoding="utf-8")
    dict_data = load_dictionary(dict_file)
    assert len(dict_data.entries) == 0


def test_load_dictionary_entries_not_list(tmp_path: Path):
    dict_file = tmp_path / "entries_obj.json"
    dict_file.write_text(json.dumps({"version": 1, "entries": "invalid"}), encoding="utf-8")
    dict_data = load_dictionary(dict_file)
    assert len(dict_data.entries) == 0

