# 專案開發進度追蹤 (Project Progress)

本文件為 `Tool_ASR Inputer` 專案的狀態真相來源（Single Source of Truth）。每次新開啟對話時，請先檢視此文件了解最新進度。

---

## 總覽里程碑狀態 (Milestones Overview)

| Phase | 名稱 | 狀態 | 核心目標 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **基礎環境與文字核心** | ✅ 已完成 (Completed) | 建立隔離環境、OpenCC 繁中轉換、Custom Dictionary 替換、文字管線與單元測試 (20/20 通過, 93% 覆蓋率) |
| **Phase 2** | **音訊錄製與 ASR 整合** | ✅ 已完成 (Completed) | `sounddevice` 錄音、Qwen3-ASR (0.6B/1.7B) 本地模型載入與推論整合 (47/47 通過, 97% 覆蓋率) |
| **Phase 3** | **系統互動與常駐介面** | ✅ 已完成 (Completed) | F8 全域按鍵、系統剪貼簿寫入與模擬貼上 (Cmd+V/Ctrl+V)、pystray 常駐選單、應用程式背景調度 (94/94 通過, 95% 覆蓋率) |
| **Phase 4** | **錯誤防禦與打包分發** | ✅ 已完成 (Completed) | 純本機模型檢測與引導、異常防禦（麥克風/模型/詞庫）、一鍵系統診斷 (`--doctor`)、PyInstaller 分發打包與繁中部署手冊 (117/117 通過, 94% 覆蓋率) |
| **Phase 5** | **上下文感知同音詞校正** | 待開始 (Pending) | Level 2 Context-Aware Dictionary（前後文條件比對，如「寫+城市」->「寫+程式」，但「台北是一個城市」不誤替換）、自訂詞庫 v2 格式升級與單元測試 |

---

## 詳細任務清單 (Detailed Tasks)

### Phase 1: 基礎環境與文字核心 (Phase 1: Environment & Text Core)
- [x] 建立 `.gitignore`（隔離環境與模型快取排除）
- [x] 建立 `AGENTS.md`（上下文管理與主動換對話規範）
- [x] 建立 `PROGRESS.md`（進度追蹤表）
- [x] 建立 Python 虛擬隔離環境 (`.venv`)
- [x] 建立 `requirements.txt` / `pyproject.toml`
- [x] 實作 `src/settings/config.py`（設定檔管理）
- [x] 實作 `src/settings/dictionary_loader.py`（詞庫載入與校驗）
- [x] 實作 `src/text/traditional_chinese.py`（OpenCC 繁中保底轉換）
- [x] 實作 `src/text/dictionary.py`（Exact Variant 詞庫替換邏輯）
- [x] 實作 `src/text/pipeline.py`（整合文字處理管線）
- [x] 建立範例 `custom_dictionary.json`
- [x] 撰寫單元測試 `tests/test_config.py`, `tests/test_dictionary.py`, `tests/test_traditional_chinese.py`, `tests/test_pipeline.py`
- [x] 執行測試與型別檢查確認 100% 通過 (20 passed in 0.16s, 93% coverage)


### Phase 2: 音訊錄製與 ASR 整合 (Phase 2: Audio & ASR Integration)
- [x] 實作 `src/audio/recorder.py`（`sounddevice` + `numpy` 錄音管理）
- [x] 實作 `src/asr/model_manager.py`（模型下載路徑隔離至 `./models/`、0.6B/1.7B 載入與釋放）
- [x] 實作 `src/asr/qwen_asr.py`（Qwen3-ASR 本地推論介面與繁中 Prompt 配置）
- [x] 撰寫音訊與 ASR 介面測試 `tests/test_audio.py`, `tests/test_model_manager.py`, `tests/test_qwen_asr.py`
- [x] 執行測試與覆蓋率檢查確認 100% 通過 (47 passed in 0.49s, 97% coverage)

### Phase 3: 系統互動與常駐介面 (Phase 3: System Interactions & Tray)
- [x] 實作 `src/input/hotkey.py`（F8 全域按鍵監聽，支援 hold 與 toggle 雙模式）
- [x] 實作 `src/input/clipboard.py`（剪貼簿複製封裝）
- [x] 實作 `src/input/paste.py`（跨平台模擬貼上，macOS/Windows）
- [x] 實作 `src/app/state.py`（狀態機：Idle / Recording / Processing / Ready / Error）
- [x] 實作 `src/ui/tray.py`（pystray 選單：模型切換、開啟詞庫、重置設定檔、離開）
- [x] 實作 `src/app/application.py`（主應用程式調度與背景執行緒）
- [x] 實作 `src/main.py`（命令列與常駐程式進入點）
- [x] 撰寫單元與整合測試 `tests/test_clipboard.py`, `tests/test_paste.py`, `tests/test_hotkey.py`, `tests/test_state.py`, `tests/test_tray.py`, `tests/test_application.py`, `tests/test_main.py`
- [x] 執行測試與覆蓋率檢查確認 100% 通過 (94 passed in 4.82s, 95% coverage)

### Phase 4: 錯誤防禦與打包分發 (Phase 4: Error Handling & Packaging)
- [x] 實作純本機模型檢測與引導機制（優先檢測 `./models/0.6b/` 與 `./models/1.7b/`，缺失模型時提供清楚友善的繁中下載與放置指引）
- [x] 健全化異常防禦處理（麥克風缺失/串流失敗、模型權重缺失/損毀、自訂詞庫格式錯誤、剪貼簿與貼上容錯、設定檔自動備份重置）
- [x] 實作一鍵系統健康診斷工具 `src/diagnostics.py` 與 CLI 旗標 (`python -m src.main --doctor`)
- [x] 建立 PyInstaller 自動化打包腳本 `scripts/build.py`（執行檔、獨立 models/、config.json 與 custom_dictionary.json 外置分離）
- [x] 實機驗證 PyInstaller 二進位執行檔與系統診斷執行正常
- [x] 撰寫繁體中文純本機部署與操作使用說明書 `README.md`
- [x] 撰寫測試套件 `tests/test_diagnostics.py`，全專案通過測試 (117 passed in 4.97s, 94% coverage)

### Phase 5: 上下文感知同音詞校正 (Phase 5: Context-Aware Dictionary)
- [ ] 升級 `custom_dictionary.json` 格式支援 `version: 2`（支援 `context` 陣列或觸發條件，保持相容 v1 格式）
- [ ] 擴充 `src/text/dictionary.py` 實作 Level 2 Context Rule 比對演算法（基於前綴詞、後綴詞或視窗範圍條件觸發替換）
- [ ] 確保 Exact Replacement（無 context 條件時）與 Contextual Replacement（具備 context 條件時）並存且優先序正確
- [ ] 撰寫進階同音詞上下文測試案例 `tests/test_context_dictionary.py`（例如：「我正在寫城市」->「我正在寫程式」；「台北是一個城市」-> 保持「城市」不誤替換）
- [ ] 更新 `--doctor` 與設定載入器支援 v2 詞庫解析與詞條統計
