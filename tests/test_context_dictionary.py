"""Unit tests for Level 2 Context-Aware Dictionary correction engine."""
from pathlib import Path
from src.settings.dictionary_loader import DictionaryData, DictionaryEntry, load_dictionary
from src.text.dictionary import DictionaryCorrector


def test_contextual_triggered_when_keyword_present():
    entry = DictionaryEntry(
        target="程式",
        variants=["城市", "成式"],
        context=["寫", "修改", "開發", "執行", "編譯", "專案"]
    )
    corrector = DictionaryCorrector([entry])

    assert corrector.correct("我正在寫城市") == "我正在寫程式"
    assert corrector.correct("幫我修改這個成式碼") == "幫我修改這個程式碼"
    assert corrector.correct("專案開發時出現城市錯誤") == "專案開發時出現程式錯誤"
    assert corrector.correct("執行城市") == "執行程式"


def test_contextual_not_triggered_when_keyword_absent():
    entry = DictionaryEntry(
        target="程式",
        variants=["城市", "成式"],
        context=["寫", "修改", "開發", "執行", "編譯", "專案"]
    )
    corrector = DictionaryCorrector([entry])

    # Unrelated geographical sentences should remain untouched
    assert corrector.correct("台北是一個城市") == "台北是一個城市"
    assert corrector.correct("這座城市有很多綠地與公園") == "這座城市有很多綠地與公園"
    assert corrector.correct("基隆是靠海的雨都城市") == "基隆是靠海的雨都城市"


def test_mixed_clauses_in_single_sentence():
    entry = DictionaryEntry(
        target="程式",
        variants=["城市"],
        context=["寫", "開發"]
    )
    corrector = DictionaryCorrector([entry])

    # First clause has no context, second clause has "寫"
    input_text = "台北是一個城市，但我現在在寫城市"
    expected = "台北是一個城市，但我現在在寫程式"
    assert corrector.correct(input_text) == expected


def test_multiple_occurrences_in_different_clauses():
    entry = DictionaryEntry(
        target="程式",
        variants=["城市"],
        context=["寫", "修改"]
    )
    corrector = DictionaryCorrector([entry])

    input_text = "這座美麗的城市！我在寫城市，你在修改城市。"
    expected = "這座美麗的城市！我在寫程式，你在修改程式。"
    assert corrector.correct(input_text) == expected


def test_hybrid_exact_and_contextual_rules():
    entries = [
        DictionaryEntry(
            target="程式",
            variants=["城市"],
            context=["寫", "修改"]
        ),
        DictionaryEntry(
            target="介面",
            variants=["接口"],
            context=[]  # Exact unconditional
        ),
        DictionaryEntry(
            target="影片",
            variants=["視頻"],
            context=[]  # Exact unconditional
        ),
    ]
    corrector = DictionaryCorrector(entries)

    input_text = "我想看這個視頻的接口設計，但這個城市很安靜，我正在寫城市。"
    expected = "我想看這個影片的介面設計，但這個城市很安靜，我正在寫程式。"
    assert corrector.correct(input_text) == expected


def test_window_size_limitation():
    entry = DictionaryEntry(
        target="程式",
        variants=["城市"],
        context=["寫"]
    )
    # Window radius = 5 chars, without clause bounding
    corrector = DictionaryCorrector([entry], window_size=5, clause_aware=False)

    # "寫" is 10 characters away from "城市" -> window size 5 won't reach it
    far_text = "寫了一整天到了晚上看著這個城市"
    assert corrector.correct(far_text) == far_text

    # "寫" is 2 characters away -> within window
    close_text = "正在寫這個城市"
    assert corrector.correct(close_text) == "正在寫這個程式"


def test_longest_match_priority_with_context():
    entries = [
        DictionaryEntry(target="前端程式", variants=["前端城市"], context=["寫", "開發"]),
        DictionaryEntry(target="程式", variants=["城市"], context=["寫", "開發"]),
    ]
    corrector = DictionaryCorrector(entries)

    input_text = "我正在開發前端城市"
    # Longest variant "前端城市" takes precedence over "城市"
    assert corrector.correct(input_text) == "我正在開發前端程式"


def test_real_world_custom_dictionary_v2_file():
    dict_data = load_dictionary("custom_dictionary.json")
    corrector = DictionaryCorrector(dict_data)

    assert corrector.correct("我正在寫城市") == "我正在寫程式"
    assert corrector.correct("台北是一個繁華的城市") == "台北是一個繁華的城市"
    assert corrector.correct("請提供使用者接口") == "請提供使用者介面"
    assert corrector.correct("觀看教學視頻") == "觀看教學影片"
    assert corrector.correct("後端服務器崩潰") == "後端伺服器崩潰"
