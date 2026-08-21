"""Main application coordinator for Tool_ASR Inputer."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from src.app.state import AppState, StateManager
from src.asr.model_manager import ModelManager
from src.asr.qwen_asr import QwenASREngine
from src.audio.recorder import AudioRecorder
from src.input.clipboard import ClipboardService
from src.input.hotkey import HotkeyListener
from src.input.paste import PasteService
from src.settings.config import AppConfig, load_config, save_config
from src.text.pipeline import TextPipeline
from src.ui.notification import NotificationService
from src.ui.tray import TrayUI

logger = logging.getLogger(__name__)


class VoiceInputApp:
    """Coordinates hotkey, audio recording, ASR inference, text processing, clipboard, and tray UI."""

    def __init__(
        self,
        config_path: Path | str = "config.json",
        dictionary_path: Path | str = "custom_dictionary.json",
        enable_tray: bool = True,
        enable_hotkey: bool = True,
        auto_load_model: bool = False,
        notifier: Optional[NotificationService] = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.dictionary_path = Path(dictionary_path)
        self.enable_tray = enable_tray
        self.enable_hotkey = enable_hotkey

        # 1. Settings & Text Pipeline
        self.config: AppConfig = load_config(self.config_path)
        self.pipeline = TextPipeline(dict_path=self.dictionary_path)

        # 2. Notification Service
        self.notifier = notifier or NotificationService()

        # 3. Audio & State
        self.recorder = AudioRecorder(sample_rate=self.config.sample_rate)
        self.state_manager = StateManager(initial_state=AppState.READY)

        # 4. Model & ASR Engine
        self.model_manager = ModelManager(
            models_dir=self.config.model_dir,
            default_model=self.config.model,
        )
        self.asr_engine = QwenASREngine(model_manager=self.model_manager)

        # 5. Input Services (Clipboard & Paste)
        self.clipboard = ClipboardService()
        self.paste_service = PasteService()

        # 6. Global Hotkey Listener
        self.hotkey_listener: Optional[HotkeyListener] = None
        if self.enable_hotkey:
            self.hotkey_listener = HotkeyListener(
                hotkey=self.config.hotkey,
                mode=self.config.hotkey_mode,
                on_triggered=self.toggle_recording,
                on_press_start=self._on_press_start,
                on_release_stop=self._on_release_stop,
            )

        # 7. Tray UI
        self.tray_ui: Optional[TrayUI] = None
        if self.enable_tray:
            self.tray_ui = TrayUI(
                state_manager=self.state_manager,
                current_model_getter=lambda: self.config.model,
                on_select_model=self.switch_model,
                on_reload_dictionary=self.reload_dictionary,
                on_reset_config=self.reset_configuration,
                on_quit=self.stop,
                dictionary_path=self.dictionary_path,
            )
            # Bind tray icon to notification service if available
            if hasattr(self.tray_ui, "_icon"):
                self.notifier.set_tray_icon(self.tray_ui._icon)

        self._processing_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._lock = threading.Lock()

        if auto_load_model:
            self._lazy_load_model()

    def _lazy_load_model(self) -> None:
        """Asynchronously pre-load ASR model in background if requested."""
        def loader() -> None:
            target = self.config.model
            avail = self.model_manager.check_local_model_availability(target)
            if not avail.get("available", False):
                self.notifier.send(f"開始下載 ASR 模型 '{target}'，請稍候...")

            def on_progress(pct: float, msg: str) -> None:
                self.state_manager.set_download_progress(pct, msg)

            try:
                self.model_manager.load_model(target, on_download_progress=on_progress)
                self.state_manager.set_state(AppState.READY)
                if not avail.get("available", False):
                    self.notifier.send(f"🎉 ASR 模型 '{target}' 下載完成，已就緒！")
            except Exception as e:
                logger.warning("Could not pre-load model '%s': %s", target, e)
                self.state_manager.set_state(AppState.ERROR, f"載入模型失敗: {e}")
                self.notifier.send(f"❌ 載入模型 '{target}' 失敗: {e}")

        thread = threading.Thread(target=loader, daemon=True)
        thread.start()

    def toggle_recording(self) -> None:
        """Toggle recording state when hotkey is triggered in toggle mode."""
        with self._lock:
            current_state = self.state_manager.state

            # Intercept hotkey if model is currently downloading
            if current_state == AppState.DOWNLOADING or self.state_manager.is_downloading:
                pct = self.state_manager.download_percent
                msg = f"⚠️ 正在下載模型中 ({pct:.0f}%)，請稍候..." if pct > 0 else "⚠️ 正在下載模型中，請稍候..."
                logger.warning("Hotkey triggered while model is downloading (%.1f%%). Intercepted.", pct)
                self.notifier.send(msg)
                return

            if current_state in (AppState.IDLE, AppState.READY, AppState.ERROR):
                self._start_recording_locked()
            elif current_state == AppState.RECORDING:
                self._stop_recording_and_process_locked()
            elif current_state == AppState.PROCESSING:
                logger.info("ASR processing is in progress. Ignoring hotkey toggle.")

    def _on_press_start(self) -> None:
        """Triggered on hotkey press in hold mode."""
        with self._lock:
            current_state = self.state_manager.state

            # Intercept hotkey if model is currently downloading
            if current_state == AppState.DOWNLOADING or self.state_manager.is_downloading:
                pct = self.state_manager.download_percent
                msg = f"⚠️ 正在下載模型中 ({pct:.0f}%)，請稍候..." if pct > 0 else "⚠️ 正在下載模型中，請稍候..."
                logger.warning("Hotkey pressed while model is downloading (%.1f%%). Intercepted.", pct)
                self.notifier.send(msg)
                return

            if current_state in (AppState.IDLE, AppState.READY, AppState.ERROR):
                self._start_recording_locked()


    def _on_release_stop(self) -> None:
        """Triggered on hotkey release in hold mode."""
        with self._lock:
            if self.state_manager.state == AppState.RECORDING:
                self._stop_recording_and_process_locked()

    def _start_recording_locked(self) -> None:
        """Internal helper to start audio capture (must be called with self._lock)."""
        try:
            self.state_manager.set_state(AppState.RECORDING)
            self.recorder.start()
            logger.info("Recording started via hotkey.")
        except Exception as e:
            logger.error("Failed to start audio recording: %s", e)
            self.state_manager.set_state(AppState.ERROR, f"錄音失敗: {e}")

    def _stop_recording_and_process_locked(self) -> None:
        """Internal helper to stop recording and trigger background ASR pipeline (must be called with self._lock)."""
        try:
            self.state_manager.set_state(AppState.PROCESSING)
            audio_data = self.recorder.stop()
            logger.info("Recording stopped. Audio samples: %d", len(audio_data))

            # Dispatch ASR & paste in non-blocking worker thread
            self._processing_thread = threading.Thread(
                target=self._process_audio_worker,
                args=(audio_data,),
                daemon=True,
            )
            self._processing_thread.start()
        except Exception as e:
            logger.error("Failed to stop recording or launch worker: %s", e)
            self.state_manager.set_state(AppState.ERROR, f"停止錄音失敗: {e}")

    def _process_audio_worker(self, audio_data: np.ndarray) -> None:
        """Worker executing ASR inference, text processing, clipboard copy, and paste."""
        try:
            # 1. Skip if empty or too short (< 0.2s of audio)
            min_samples = int(self.config.sample_rate * 0.2)
            if len(audio_data) < min_samples or np.max(np.abs(audio_data)) < 1e-4:
                logger.info("Audio too short or silent (samples: %d). Skipping ASR.", len(audio_data))
                self.state_manager.set_state(AppState.READY)
                return

            # 2. Transcribe via Qwen3-ASR
            logger.info("Starting ASR inference with model '%s'...", self.config.model)
            raw_text = self.asr_engine.transcribe(
                audio=audio_data,
                language=self.config.language,
            )

            raw_text = raw_text.strip()
            logger.info("ASR raw output: '%s'", raw_text)
            if not raw_text:
                logger.info("No speech recognized.")
                self.state_manager.set_state(AppState.READY)
                return

            # 3. Post-process via OpenCC and Custom Dictionary
            final_text = self.pipeline.process(raw_text)
            logger.info("Post-processed final text: '%s'", final_text)

            # 4. Copy to Clipboard
            copied = self.clipboard.copy(final_text)
            if not copied:
                raise RuntimeError("Failed to copy final text to clipboard.")

            # 5. Simulate Paste
            pasted = self.paste_service.simulate_paste()
            if not pasted:
                logger.warning("Simulate paste returned False. Text remains in clipboard.")

            self.state_manager.set_state(AppState.READY)

        except Exception as e:
            logger.error("Error during ASR pipeline execution: %s", e)
            self.state_manager.set_state(AppState.ERROR, str(e))

    def switch_model(self, model_key: str) -> None:
        """Switch active ASR model and persist in configuration."""
        target = model_key.lower().strip()
        if target not in ("0.6b", "1.7b"):
            logger.warning("Unsupported model key '%s'.", target)
            return

        logger.info("Switching ASR model to '%s'...", target)
        self.config.model = target
        save_config(self.config, self.config_path)

        def worker() -> None:
            avail = self.model_manager.check_local_model_availability(target)
            if not avail.get("available", False):
                self.notifier.send(f"開始下載 ASR 模型 '{target}'，請稍候...")

            def on_progress(pct: float, msg: str) -> None:
                self.state_manager.set_download_progress(pct, msg)

            try:
                self.state_manager.set_state(AppState.PROCESSING)
                self.model_manager.load_model(target, on_download_progress=on_progress)
                self.state_manager.set_state(AppState.READY)
                logger.info("Successfully switched model to '%s'.", target)
                self.notifier.send(f"🎉 已成功切換至 ASR 模型 '{target}'！")
            except Exception as e:
                logger.error("Failed to load switched model '%s': %s", target, e)
                self.state_manager.set_state(AppState.ERROR, f"切換模型失敗: {e}")
                self.notifier.send(f"❌ 切換模型 '{target}' 失敗: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def reload_dictionary(self) -> None:
        """Reload custom dictionary file and update text processing pipeline."""
        logger.info("Reloading custom dictionary from %s...", self.dictionary_path)
        self.pipeline.reload_dictionary(self.dictionary_path)
        logger.info("Dictionary reloaded successfully.")

    def reset_configuration(self) -> None:
        """Reset configuration file to factory defaults and rebind services."""
        logger.info("Resetting configuration to factory defaults...")
        from src.settings.config import reset_config
        success, backup_path = reset_config(self.config_path, backup_old=True)
        if success:
            self.config = load_config(self.config_path)
            logger.info("Config reset complete. New settings: %s (Backup: %s)", self.config, backup_path)
            if self.hotkey_listener is not None:
                self.hotkey_listener.stop()
                self.hotkey_listener = HotkeyListener(
                    hotkey=self.config.hotkey,
                    mode=self.config.hotkey_mode,
                    on_triggered=self.toggle_recording,
                    on_press_start=self._on_press_start,
                    on_release_stop=self._on_release_stop,
                )
                if self._is_running:
                    try:
                        self.hotkey_listener.start()
                    except Exception as e:
                        logger.warning("Could not restart hotkey listener after reset: %s", e)

    def start(self) -> None:
        """Start all services (hotkey listener and tray UI)."""
        self._is_running = True
        logger.info("Starting Tool_ASR Inputer application...")

        if self.hotkey_listener is not None:
            try:
                self.hotkey_listener.start()
            except Exception as e:
                logger.warning("Could not start hotkey listener: %s", e)

        if self.tray_ui is not None:
            self.tray_ui.start(detached=True)

        logger.info("Tool_ASR Inputer is ready and running.")

    def stop(self) -> None:
        """Stop all services and cleanly dismantle background threads."""
        logger.info("Stopping Tool_ASR Inputer application...")
        self._is_running = False

        if self.recorder.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass

        if self.hotkey_listener is not None:
            self.hotkey_listener.stop()

        if self.tray_ui is not None:
            self.tray_ui.stop()

        self.state_manager.set_state(AppState.IDLE)
        logger.info("Tool_ASR Inputer stopped.")
