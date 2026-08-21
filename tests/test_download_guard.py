"""Unit and integration tests for Model Download Notification & Hotkey Guard (Phase 6)."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.app.application import VoiceInputApp
from src.app.state import AppState, StateManager
from src.asr.model_manager import ModelManager, ModelStatus, _HFDownloadProgressBar
from src.ui.notification import NotificationService
from src.ui.tray import TrayUI, create_status_icon


def test_app_state_downloading_properties() -> None:
    """Test StateManager DOWNLOADING state and progress tracking."""
    sm = StateManager(initial_state=AppState.READY)
    assert not sm.is_downloading
    assert sm.download_percent == 0.0
    assert sm.download_message is None

    # Update download progress
    events = []
    sm.subscribe(lambda st, msg: events.append((st, msg)))

    sm.set_download_progress(45.5, "下載權重中...")
    assert sm.is_downloading
    assert sm.state == AppState.DOWNLOADING
    assert sm.download_percent == 45.5
    assert sm.download_message == "下載權重中..."
    assert len(events) == 1
    assert events[0] == (AppState.DOWNLOADING, "下載權重中...")

    # Transition to READY clears download progress
    sm.set_state(AppState.READY)
    assert not sm.is_downloading
    assert sm.download_percent == 0.0
    assert sm.download_message is None


def test_app_state_downloading_clamping() -> None:
    """Test progress percentage is clamped within 0.0 - 100.0."""
    sm = StateManager()
    sm.set_download_progress(-10)
    assert sm.download_percent == 0.0

    sm.set_download_progress(150.0)
    assert sm.download_percent == 100.0


def test_hf_download_progress_bar() -> None:
    """Test _HFDownloadProgressBar calculates percentage and calls active callback."""
    reported = []
    def callback(pct: float, desc: str) -> None:
        reported.append((pct, desc))

    _HFDownloadProgressBar._active_callback = callback
    try:
        with _HFDownloadProgressBar(total=1000, desc="Downloading") as pbar:
            pbar.update(250)
            pbar.update(250)

        assert len(reported) >= 2
        assert reported[-1][0] == 50.0
        assert "Downloading" in reported[-1][1]
    finally:
        _HFDownloadProgressBar._active_callback = None


def test_hotkey_toggle_guard_when_downloading(tmp_path: Path) -> None:
    """Test F8 toggle is intercepted and sends warning notification when downloading."""
    cfg_file = tmp_path / "config.json"
    dict_file = tmp_path / "custom_dictionary.json"
    cfg_file.write_text('{"model": "0.6b"}')
    dict_file.write_text('{"version": 2, "entries": []}')

    mock_notifier = MagicMock(spec=NotificationService)
    app = VoiceInputApp(
        config_path=cfg_file,
        dictionary_path=dict_file,
        enable_tray=False,
        enable_hotkey=False,
        notifier=mock_notifier,
    )

    # Set app to DOWNLOADING
    app.state_manager.set_download_progress(35.0, "下載中")

    with patch.object(app.recorder, "start") as mock_rec_start:
        app.toggle_recording()

        # Recorder should NOT start
        mock_rec_start.assert_not_called()
        # Notifier should be triggered with warning
        mock_notifier.send.assert_called_once()
        sent_msg = mock_notifier.send.call_args[0][0]
        assert "正在下載模型中" in sent_msg
        assert "35%" in sent_msg


def test_hotkey_hold_guard_when_downloading(tmp_path: Path) -> None:
    """Test F8 hold press is intercepted and sends warning notification when downloading."""
    cfg_file = tmp_path / "config.json"
    dict_file = tmp_path / "custom_dictionary.json"
    cfg_file.write_text('{"model": "0.6b"}')
    dict_file.write_text('{"version": 2, "entries": []}')

    mock_notifier = MagicMock(spec=NotificationService)
    app = VoiceInputApp(
        config_path=cfg_file,
        dictionary_path=dict_file,
        enable_tray=False,
        enable_hotkey=False,
        notifier=mock_notifier,
    )

    # Set app to DOWNLOADING
    app.state_manager.set_download_progress(0.0, "準備下載")

    with patch.object(app.recorder, "start") as mock_rec_start:
        app._on_press_start()

        # Recorder should NOT start
        mock_rec_start.assert_not_called()
        # Notifier should be triggered with warning
        mock_notifier.send.assert_called_once()
        sent_msg = mock_notifier.send.call_args[0][0]
        assert "正在下載模型中" in sent_msg


def test_model_manager_download_with_callback(tmp_path: Path) -> None:
    """Test ModelManager.download_model passes progress callback properly."""
    mgr = ModelManager(models_dir=tmp_path)
    progress_updates = []

    def on_progress(pct: float, msg: str) -> None:
        progress_updates.append((pct, msg))

    mock_hf_module = MagicMock()
    mock_hf_module.snapshot_download.return_value = str(tmp_path / "hf_snapshot")

    with patch.dict(sys.modules, {"huggingface_hub": mock_hf_module}):
        res = mgr.download_model("0.6b", progress_callback=on_progress)

        assert res == str(tmp_path / "hf_snapshot")
        mock_hf_module.snapshot_download.assert_called_once()
        assert len(progress_updates) >= 2
        assert progress_updates[0][0] == 0.0
        assert progress_updates[-1][0] == 100.0


def test_model_manager_load_model_triggers_download_if_missing(tmp_path: Path) -> None:
    """Test load_model detects missing local weights and calls download_model first."""
    mgr = ModelManager(models_dir=tmp_path)
    progress_calls = []

    mock_qwen_module = MagicMock()
    mock_model_cls = MagicMock()
    mock_instance = MagicMock()
    mock_model_cls.from_pretrained.return_value = mock_instance
    mock_qwen_module.Qwen3ASRModel = mock_model_cls

    with patch.dict(sys.modules, {"qwen_asr": mock_qwen_module}):
        with patch.object(mgr, "check_local_model_availability", return_value={"available": False}):
            with patch.object(mgr, "download_model") as mock_dl:
                model = mgr.load_model("0.6b", on_download_progress=lambda p, m: progress_calls.append(p))

                mock_dl.assert_called_once()
                assert mgr.status == ModelStatus.READY
                assert model is mock_instance



def test_switch_model_with_download_notifications(tmp_path: Path) -> None:
    """Test switch_model dispatches download notification when switching to missing model."""
    cfg_file = tmp_path / "config.json"
    dict_file = tmp_path / "custom_dictionary.json"
    cfg_file.write_text('{"model": "0.6b"}')
    dict_file.write_text('{"version": 2, "entries": []}')

    mock_notifier = MagicMock(spec=NotificationService)
    app = VoiceInputApp(
        config_path=cfg_file,
        dictionary_path=dict_file,
        enable_tray=False,
        enable_hotkey=False,
        notifier=mock_notifier,
    )

    with patch.object(app.model_manager, "check_local_model_availability", return_value={"available": False}):
        with patch.object(app.model_manager, "load_model") as mock_load:
            app.switch_model("1.7b")
            time.sleep(0.1)  # wait for thread

            mock_load.assert_called_once()
            # Verify notifications were sent
            sent_messages = [call[0][0] for call in mock_notifier.send.call_args_list]
            assert any("開始下載 ASR 模型" in m for m in sent_messages)
            assert any("已成功切換至 ASR 模型" in m for m in sent_messages)


def test_tray_icon_and_menu_during_downloading() -> None:
    """Test tray icon creation and menu status text during DOWNLOADING state."""
    # Icon creation
    img = create_status_icon(AppState.DOWNLOADING, size=64)
    assert img.size == (64, 64)

    # Tray menu rendering
    sm = StateManager()
    sm.set_download_progress(78.0, "下載進度")

    tray = TrayUI(
        state_manager=sm,
        current_model_getter=lambda: "0.6b",
    )
    menu = tray._build_menu()
    menu_items = list(menu.items)
    status_item_text = menu_items[1].text
    assert "下載模型中 (78%)" in status_item_text
