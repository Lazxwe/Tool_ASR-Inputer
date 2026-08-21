"""Unit and integration tests for VoiceInputApp application coordinator."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from src.app.application import VoiceInputApp
from src.app.state import AppState


def create_mock_app(tmp_path: Path) -> VoiceInputApp:
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "0.6b", "hotkey": "f8", "sample_rate": 16000}), encoding="utf-8")

    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text(
        json.dumps({
            "version": 1,
            "entries": [{"target": "程式", "variants": ["城市"]}]
        }),
        encoding="utf-8",
    )

    app = VoiceInputApp(
        config_path=config_file,
        dictionary_path=dict_file,
        enable_tray=False,
        enable_hotkey=False,
        auto_load_model=False,
    )
    return app


def test_app_initialization(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    assert app.state_manager.state == AppState.READY
    assert app.config.model == "0.6b"
    assert "城市" in app.pipeline._corrector._replacement_map


def test_app_toggle_recording_lifecycle(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)

    # 1. Start recording
    with patch.object(app.recorder, "start") as mock_start:
        app.toggle_recording()
        assert app.state_manager.state == AppState.RECORDING
        assert mock_start.called

    # 2. Stop recording and process
    mock_audio = np.ones(16000, dtype=np.float32)
    with patch.object(app.recorder, "stop", return_value=mock_audio) as mock_stop, \
         patch.object(app, "_process_audio_worker") as mock_worker:
        app.toggle_recording()
        assert app.state_manager.state == AppState.PROCESSING
        assert mock_stop.called

    # 3. Toggle during processing is ignored
    with patch.object(app, "_start_recording_locked") as mock_start2:
        app.toggle_recording()
        assert not mock_start2.called


def test_app_hold_mode_lifecycle(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)

    # Press start
    with patch.object(app.recorder, "start") as mock_start:
        app._on_press_start()
        assert app.state_manager.state == AppState.RECORDING
        assert mock_start.called

    # Release stop
    mock_audio = np.ones(16000, dtype=np.float32)
    with patch.object(app.recorder, "stop", return_value=mock_audio) as mock_stop, \
         patch.object(app, "_process_audio_worker"):
        app._on_release_stop()
        assert app.state_manager.state == AppState.PROCESSING
        assert mock_stop.called


def test_app_toggle_recording_start_failure(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    with patch.object(app.recorder, "start", side_effect=RuntimeError("Mic busy")):
        app.toggle_recording()
        assert app.state_manager.state == AppState.ERROR
        assert "錄音失敗" in (app.state_manager.last_error or "")


def test_app_process_audio_worker_success(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    audio = np.ones(16000, dtype=np.float32)  # 1 second of audio

    with patch.object(app.asr_engine, "transcribe", return_value="我今天寫城市軟件") as mock_asr, \
         patch.object(app.clipboard, "copy", return_value=True) as mock_copy, \
         patch.object(app.paste_service, "simulate_paste", return_value=True) as mock_paste:

        app._process_audio_worker(audio)

        assert mock_asr.called
        # "城市" -> "程式", "軟件" -> "軟體" (via OpenCC + custom dict)
        mock_copy.assert_called_once_with("我今天寫程式軟體")
        assert mock_paste.called
        assert app.state_manager.state == AppState.READY


def test_app_process_audio_worker_silent_or_short(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    short_audio = np.zeros(100, dtype=np.float32)

    with patch.object(app.asr_engine, "transcribe") as mock_asr:
        app._process_audio_worker(short_audio)
        assert not mock_asr.called
        assert app.state_manager.state == AppState.READY


def test_app_process_audio_worker_empty_transcription(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    audio = np.ones(16000, dtype=np.float32)

    with patch.object(app.asr_engine, "transcribe", return_value="   "):
        app._process_audio_worker(audio)
        assert app.state_manager.state == AppState.READY


def test_app_process_audio_worker_error_recovery(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    audio = np.ones(16000, dtype=np.float32)

    with patch.object(app.asr_engine, "transcribe", side_effect=RuntimeError("CUDA Out of memory")):
        app._process_audio_worker(audio)
        assert app.state_manager.state == AppState.ERROR
        assert "CUDA Out of memory" in (app.state_manager.last_error or "")


def test_app_switch_model(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)

    # Unsupported key ignored
    app.switch_model("unknown_model")
    assert app.config.model == "0.6b"

    with patch.object(app.model_manager, "load_model") as mock_load:
        app.switch_model("1.7b")
        assert app.config.model == "1.7b"


def test_app_reload_dictionary(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)

    # Write new entry
    new_dict = {
        "version": 1,
        "entries": [
            {"target": "介面", "variants": ["接口"]},
            {"target": "伺服器", "variants": ["服務器"]},
        ]
    }
    app.dictionary_path.write_text(json.dumps(new_dict), encoding="utf-8")

    app.reload_dictionary()
    assert "接口" in app.pipeline._corrector._replacement_map
    assert "服務器" in app.pipeline._corrector._replacement_map


def test_app_auto_load_model(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "0.6b"}), encoding="utf-8")
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text("{}", encoding="utf-8")

    with patch("src.asr.model_manager.ModelManager.load_model") as mock_load:
        app = VoiceInputApp(
            config_path=config_file,
            dictionary_path=dict_file,
            enable_tray=False,
            enable_hotkey=False,
            auto_load_model=True,
        )
        assert app is not None


def test_app_auto_load_model_exception(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"model": "0.6b"}), encoding="utf-8")
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text("{}", encoding="utf-8")

    with patch("src.asr.model_manager.ModelManager.load_model", side_effect=Exception("Pre-load failed")):
        app = VoiceInputApp(
            config_path=config_file,
            dictionary_path=dict_file,
            enable_tray=False,
            enable_hotkey=False,
            auto_load_model=True,
        )
        assert app is not None


def test_app_process_audio_worker_copy_failure(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    audio = np.ones(16000, dtype=np.float32)

    with patch.object(app.asr_engine, "transcribe", return_value="你好世界"), \
         patch.object(app.clipboard, "copy", return_value=False):
        app._process_audio_worker(audio)
        assert app.state_manager.state == AppState.ERROR


def test_app_switch_model_worker_execution(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)

    # Success case
    with patch.object(app.model_manager, "load_model") as mock_load:
        app.switch_model("1.7b")
        assert app.config.model == "1.7b"

    # Error case in worker
    with patch.object(app.model_manager, "load_model", side_effect=RuntimeError("Load error")):
        app.switch_model("0.6b")
        assert app.config.model == "0.6b"


def test_app_start_hotkey_failure(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    app.hotkey_listener = MagicMock()
    app.hotkey_listener.start.side_effect = Exception("Hotkey failed")
    app.start()
    assert app._is_running is True


def test_app_stop_while_recording(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    app.recorder._is_recording = True
    with patch.object(app.recorder, "stop") as mock_stop:
        app.stop()
        assert mock_stop.called


def test_app_start_and_stop(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    app.hotkey_listener = MagicMock()
    app.tray_ui = MagicMock()

    app.start()
    assert app.hotkey_listener.start.called
    assert app.tray_ui.start.called

    app.stop()
    assert app.hotkey_listener.stop.called
    assert app.tray_ui.stop.called
    assert app.state_manager.state == AppState.IDLE


def test_app_reset_configuration(tmp_path: Path) -> None:
    app = create_mock_app(tmp_path)
    app._is_running = True
    app.hotkey_listener = MagicMock()

    app.reset_configuration()
    assert app.config.model == "0.6b"
    assert app.config.hotkey == "ctrl_r"
    assert app.hotkey_listener is not None
