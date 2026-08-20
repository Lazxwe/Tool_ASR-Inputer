# 專案開發進度追蹤 (Project Progress)

本文件為 `Tool_ASR Inputer` 專案的狀態真相來源（Single Source of Truth）。每次新開啟對話時，請先檢視此文件了解最新進度。

---

## 總覽里程碑狀態 (Milestones Overview)

| Phase | 名稱 | 狀態 | 核心目標 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **基礎環境與文字核心** | ✅ 已完成 (Completed) | 建立隔離環境、OpenCC 繁中轉換、Custom Dictionary 替換、文字管線與單元測試 (20/20 通過, 93% 覆蓋率) |
| **Phase 2** | **音訊錄製與 ASR 整合** | ✅ 已完成 (Completed) | `sounddevice` 錄音、Qwen3-ASR (0.6B/1.7B) 本地模型載入與推論整合 (47/47 通過, 97% 覆蓋率) |
| **Phase 3** | **系統互動與常駐介面** | 待開始 (Pending) | F8 全域按鍵、系統剪貼簿寫入與模擬貼上 (Cmd+V/Ctrl+V)、pystray 常駐選單 |
| **Phase 4** | **錯誤防禦與打包分發** | 待開始 (Pending) | 麥克風與模型異常處理、跨平台驗證、PyInstaller 打包驗證 |

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
- [ ] 實作 `src/input/hotkey.py`（F8 全域按鍵監聽）
- [ ] 實作 `src/input/clipboard.py`（剪貼簿複製封裝）
- [ ] 實作 `src/input/paste.py`（跨平台模擬貼上，macOS/Windows）
- [ ] 實作 `src/app/state.py`（狀態機：Idle / Recording / Processing / Error）
- [ ] 實作 `src/ui/tray.py`（pystray 選單：模型切換、開啟詞庫、離開）
- [ ] 實作 `src/app/application.py`（主應用程式調度與背景執行緒）

### Phase 4: 錯誤防禦與打包分發 (Phase 4: Error Handling & Packaging)
- [ ] 健全化異常處理（麥克風缺失/權限、模型載入失敗、JSON 損毀）
- [ ] 跨平台相容性測試（macOS / Windows）
- [ ] PyInstaller 打包腳本與獨立執行檔測試
- [ ] 完成驗收測試清單
