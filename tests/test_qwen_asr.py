"""Unit tests for QwenASREngine and pipeline integration."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import numpy as np
import pytest

from src.asr.model_manager import ModelManager, ModelManagerError, ModelStatus
from src.asr.qwen_asr import ASRInferenceError, QwenASREngine
from src.text.pipeline import TextPipeline


def test_transcribe_empty_audio():
    engine = QwenASREngine()

    # Empty 1D numpy array
    assert engine.transcribe(np.empty(0, dtype=np.float32)) == ""
    # Empty tuple audio
    assert engine.transcribe((np.empty(0, dtype=np.float32), 16000)) == ""
    # Empty string
    assert engine.transcribe("   ") == ""


def test_transcribe_unsupported_audio_type():
    engine = QwenASREngine()
    with pytest.raises(ValueError, match="Unsupported audio input type"):
        engine.transcribe(12345)  # type: ignore


def test_transcribe_success_with_various_return_types():
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_manager.current_model = mock_model

    engine = QwenASREngine(model_manager=mock_manager, default_language="Chinese")

    audio = np.ones(1600, dtype=np.float32)

    # 1. Return object with .text attribute
    mock_model.transcribe.return_value = [SimpleNamespace(text="測試辨識文字")]
    res1 = engine.transcribe(audio, language="zh", prompt="台灣繁體")
    assert res1 == "測試辨識文字"
    mock_model.transcribe.assert_called_with(audio=(audio, 16000), language="zh", prompt="台灣繁體")

    # 2. Return dict with 'text'
    mock_model.transcribe.return_value = [{"text": "字典回傳文字"}]
    res2 = engine.transcribe(audio)
    assert res2 == "字典回傳文字"

    # 3. Return string directly
    mock_model.transcribe.return_value = "字串回傳文字"
    res3 = engine.transcribe(audio)
    assert res3 == "字串回傳文字"

    # 4. Return empty list
    mock_model.transcribe.return_value = []
    res4 = engine.transcribe(audio)
    assert res4 == ""


def test_transcribe_auto_load_model():
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_manager.current_model = None
    mock_manager.load_model.return_value = mock_model
    mock_model.transcribe.return_value = "載入成功"

    engine = QwenASREngine(model_manager=mock_manager)
    res = engine.transcribe(np.ones(100, dtype=np.float32))

    assert res == "載入成功"
    mock_manager.load_model.assert_called_once()


def test_transcribe_model_load_failure():
    mock_manager = MagicMock(spec=ModelManager)
    mock_manager.current_model = None
    mock_manager.load_model.side_effect = ModelManagerError("Model file missing")

    engine = QwenASREngine(model_manager=mock_manager)
    with pytest.raises(ASRInferenceError, match="Cannot perform inference"):
        engine.transcribe(np.ones(100, dtype=np.float32))


def test_transcribe_inference_runtime_error():
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("CUDA device error")
    mock_manager.current_model = mock_model

    engine = QwenASREngine(model_manager=mock_manager)
    with pytest.raises(ASRInferenceError, match="Inference error"):
        engine.transcribe(np.ones(100, dtype=np.float32))


def test_transcribe_and_process_integration(tmp_path):
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_manager.current_model = mock_model

    # Simulated ASR returns simplified Chinese with variant: "我今天要修改城市的接口"
    mock_model.transcribe.return_value = [SimpleNamespace(text="我今天要修改城市的接口")]

    # Build real TextPipeline with temp dictionary
    import json
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text(
        json.dumps({
            "version": 1,
            "entries": [
                {"target": "程式", "variants": ["城市"]},
                {"target": "介面", "variants": ["接口"]},
            ],
        }),
        encoding="utf-8",
    )
    pipeline = TextPipeline(dict_path=dict_file)

    engine = QwenASREngine(model_manager=mock_manager, text_pipeline=pipeline)

    audio = np.ones(16000, dtype=np.float32)
    final_text = engine.transcribe_and_process(audio)

    # "接口" becomes "介面" via OpenCC/Dictionary, "城市" becomes "程式" via Dictionary
    assert final_text == "我今天要修改程式的介面"


def test_transcribe_and_process_without_pipeline():
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_manager.current_model = mock_model
    mock_model.transcribe.return_value = "純文字"

    engine = QwenASREngine(model_manager=mock_manager, text_pipeline=None)
    assert engine.transcribe_and_process(np.ones(100, dtype=np.float32)) == "純文字"


def test_transcribe_audio_tuple_and_file_path():
    mock_manager = MagicMock(spec=ModelManager)
    mock_model = MagicMock()
    mock_manager.current_model = mock_model
    mock_model.transcribe.return_value = "辨識音訊檔"

    engine = QwenASREngine(model_manager=mock_manager)

    # Valid tuple input
    tuple_audio = (np.ones(800, dtype=np.float32), 16000)
    assert engine.transcribe(tuple_audio) == "辨識音訊檔"

    # Valid file path input
    assert engine.transcribe("sample_audio.wav") == "辨識音訊檔"


def test_extract_text_edge_cases():
    assert QwenASREngine._extract_text(None) == ""
    assert QwenASREngine._extract_text(12345) == "12345"
