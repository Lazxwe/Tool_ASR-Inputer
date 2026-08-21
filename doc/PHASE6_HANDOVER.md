# Phase 6 開發交接文件：模型下載進度感知與原生系統通知 (Model Download Notification & Guard)

<!-- 
[說明] 本文件為 Phase 6 開發啟動的專屬交接指引。
供新對話中的 AI Agent 立即獲取專案最新架構現狀、技術決策與 Phase 6 開發規格。
-->

## 1. 專案最新現狀 (Current Project State)

本專案 `Tool_ASR Inputer` 目前已順利完成 **Phase 1 至 Phase 5** 的全部核心功能與實機驗收：
- **ASR 本機推論**：已實機驗證 `Qwen/Qwen3-ASR-0.6B` 與 `1.7B` 本機推論，支援 Apple Silicon MPS 加速與無網路純離線部署。
- **全域熱鍵系統**：基於 `pynput` 實作跨平台自然按鍵解析，支援 **`hold`（按住說話，放開自動貼上）** 與 **`toggle`（按一下開始/再按一下結束）** 雙模式。
- **系統常駐托盤 (pystray)**：支援模型即時熱切換、開啟詞庫、重新載入詞庫、一鍵安全重置設定檔（自動備份 `.bak`）。
- **異常防禦與診斷**：內建 `python -m src.main --doctor` 全方位診斷工具，自動檢測音訊設備、模型權重、詞庫與 macOS 輔助使用權限。
- **Level 2 同音詞上下文校正**：實作滑動視窗與子句感知比對（如「我正在寫城市 ➡️ 寫程式 ✅」，「台北是一個城市 ➡️ 保持城市 ✅」），支援 `custom_dictionary.json` v2。
- **打包與測試覆蓋率**：PyInstaller 獨立打包架構，全專案 **126 / 126** 項單元測試全數通過（覆蓋率 92%）。

---

## 2. Phase 6 開發目標與規格 (Phase 6 Specification)

在無重型 UI（純系統托盤常駐）的極簡架構下，實現**模型下載即時通知、下載中操作攔截與防禦**：

### 2.1 欲解決的核心痛點
1. **無下載反饋**：首次執行或切換未下載之模型時，背景下載權重若無任何提示，使用者無法得知系統當前狀態。
2. **下載中誤觸發**：若使用者在模型下載期間按下 `F8`，會引發空錄音、無效推論或程式掛起（Hanging）。
3. **無重型 UI 原則**：不引進複雜 GUI 視窗，必須使用系統原生推播與托盤提示。

### 2.2 核心架構與設計原則

```text
模型開始下載 ───► [原生系統通知：開始下載模型...]
      │
      ├── (使用者按 F8) ───► [狀態機攔截：DOWNLOADING 狀態]
      │                         │
      │                         └──► [原生通知：⚠️ 正在下載模型中 (XX%)，請稍候...]
      │                         └──► (立即中斷，拒絕錄音與 ASR 執行)
      │
模型下載完成 ───► [原生系統通知：🎉 模型下載完成，已就緒！] ───► 轉為 READY
```

1. **跨平台原生系統通知 (`src/ui/notification.py`)**：
   - **macOS**：透過 `osascript -e 'display notification ... with title "Tool_ASR Inputer"'` 調用原生 Notification Center（右上角浮動橫幅與提示聲），零肥大依賴。
   - **Windows**：透過 `pystray.Icon.notify()` 或 PowerShell 系統快顯通知 (Toast)。
2. **狀態機防禦 (`AppState.DOWNLOADING`)**：
   - 在 `AppState` 新增 `DOWNLOADING = "downloading"`。
   - 記錄即時下載百分比與下載階段描述。
3. **下載進度捕捉 (Progress Tracking)**：
   - 在 `ModelManager` 中掛載下載進度回調（支援 HuggingFace Hub 下載進度捕捉）。
4. **按鍵攔截防禦 (`VoiceInputApp`)**：
   - 當處於 `AppState.DOWNLOADING` 狀態時，`toggle_recording()` 與 `_on_press_start()` 立即攔截並發送「⚠️ 模型下載中」原生通知，終止所有後續錄音與貼上行為。

---

## 3. Phase 6 詳細待辦清單 (Phase 6 Task Breakdown)

1. **實作原生通知模組** ([`src/ui/notification.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/ui/notification.py))：
   - 封裝 `NotificationService`，支援 macOS（osascript）、Windows（pystray/PowerShell）與後備 log 模式。
2. **擴充狀態機與進度管理** ([`src/app/state.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/app/state.py))：
   - 新增 `AppState.DOWNLOADING`，提供 `set_download_progress(percent: float, message: str)`。
3. **模型下載回調與通知串接** ([`src/asr/model_manager.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/asr/model_manager.py))：
   - 擴充 `download_model` 與 `load_model`，在開始、進度更新、完成與失敗時發送通知與狀態轉移。
4. **應用層下載中攔截防禦** ([`src/app/application.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/app/application.py))：
   - 在熱鍵觸發點檢查 `DOWNLOADING` 狀態，觸發提醒通知並直接返回。
5. **托盤狀態與提示同步** ([`src/ui/tray.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/ui/tray.py))：
   - 下載時更新托盤圖示與懸停文字為「下載模型中 (XX%)」。
6. **單元與防禦測試套件** ([`tests/test_notification.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/tests/test_notification.py), [`tests/test_download_guard.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/tests/test_download_guard.py))：
   - 驗證各平台通知派發、下載中按鍵攔截、狀態機轉移與極限邊界。

---

## 4. 新對話啟動提示詞 (Prompt for New Chat Session)

開啟新對話後，您可以直接貼上以下提示詞給 AI Agent：

```text
請依據 PROGRESS.md、doc/PHASE6_HANDOVER.md 與 doc/開發規格.md，開始進行 Phase 6：模型下載進度感知與原生系統通知 (Model Download Notification & Guard) 的開發工作。
```
