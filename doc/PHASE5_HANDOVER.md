# Phase 5 開發交接文件：上下文感知同音詞校正 (Context-Aware Dictionary)

<!-- 
[說明] 本文件為 Phase 5 開發啟動的專屬交接指引。
供新對話中的 AI Agent 立即獲取專案最新架構現狀、技術決策與 Phase 5 開發規格。
-->

## 1. 專案最新現狀 (Current Project State)

本專案 `Tool_ASR Inputer` 目前已順利完成 **Phase 1 至 Phase 4** 的全部核心功能與實機驗收：
- **ASR 本機推論**：已實機驗證 `Qwen/Qwen3-ASR-0.6B` 與 `1.7B` 本機推論，支援 Apple Silicon MPS 加速與無網路純離線部署。
- **全域熱鍵系統**：基於 `pynput` 實作跨平台自然按鍵解析，支援 **`hold`（按住說話，放開自動貼上）** 與 **`toggle`（按一下開始/再按一下結束）** 雙模式。
- **系統常駐托盤 (pystray)**：支援模型即時熱切換、開啟詞庫、重新載入詞庫、一鍵安全重置設定檔（自動備份 `.bak`）。
- **異常防禦與診斷**：內建 `python -m src.main --doctor` 全方位診斷工具，自動檢測音訊設備、模型權重、詞庫與 macOS 輔助使用權限。
- **打包與測試覆蓋率**：PyInstaller 獨立打包架構（模型與詞庫外置分離），全專案 **117 / 117** 項單元測試全數通過（覆蓋率 94%）。
- **Git 乾淨排除**：`.gitignore` 已嚴格排除所有 `models/` 目錄、`*.safetensors`、`*.bin`、`*.pt`、`*.onnx` 及 HuggingFace 快取檔案。

---

## 2. Phase 5 開發目標與規格依據 (Phase 5 Specification)

依據 [`doc/開發規格.md`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/doc/%E9%96%8B%E7%99%BC%E8%A6%8F%E6%A0%BC.md) 第 21 節與第 22 節規範，Phase 5 的核心任務是將詞庫比對引擎由 **Level 1（Exact Variant 無條件替換）** 升級為 **Level 2（Context-Aware Dictionary 上下文感知條件校正）**。

### 2.1 欲解決的核心痛點
在 MVP 的無條件替換中：
```text
城市 → 程式
```
會導致正常語句被誤殺：
- 「我正在寫城市」 ➡️ 成功校正為「我正在寫程式」✅
- 「台北是一個城市」 ➡️ **被誤替換為**「台北是一個程式」❌

### 2.2 升級後的詞庫格式 (`custom_dictionary.json` v2)
```json
{
  "version": 2,
  "entries": [
    {
      "target": "程式",
      "variants": ["城市", "成式"],
      "context": ["寫", "修改", "開發", "執行", "編譯", "代碼", "軟體", "專案"]
    },
    {
      "target": "介面",
      "variants": ["接口"],
      "context": []  // 空陣列或未提供 context 時，代表無條件全域替換 (相容 v1 行為)
    }
  ]
}
```

### 2.3 比對演算法原則
1. **向下相容**：當詞條無 `context` 或為空時，維持原本 Exact Replacement 邏輯。
2. **上下文視窗比對**：當詞條定義了 `context` 關鍵字時，僅當 ASR 辨識文字在目標詞前後特定視窗範圍內（或同一子句中）包含 `context` 陣列中的任一關鍵字時，才觸發替換。
3. **最長匹配與優先序保證**：長詞規則優先於短詞規則。

---

## 3. Phase 5 詳細待辦清單 (Phase 5 Task Breakdown)

1. **詞庫資料結構升級** ([`src/settings/dictionary_loader.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/settings/dictionary_loader.py))：
   - 擴充 `DictionaryEntry` 支援 `context: list[str] = field(default_factory=list)` 欄位。
   - 支援解析 `version: 2`，並對 `version: 1` 保持 100% 向下相容。
2. **上下文感知替換引擎** ([`src/text/dictionary.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/text/dictionary.py))：
   - 實作 `ContextAwareDictionaryCorrector`，支援基於上下文關鍵字與滑動視窗的比對演算法。
3. **文字管線串接** ([`src/text/pipeline.py`](file:///Users/lazxwe/Documents/GitHub/Tool_ASR%20Inputer/src/text/pipeline.py))：
   - 無縫整合上下文替換引擎。
4. **診斷工具與預設詞庫更新**：
   - 更新 `custom_dictionary.json` 升級為 v2 格式並附帶 context 範例。
   - 更新 `src/diagnostics.py` 支援 v2 詞庫統計展示。
5. **單元與邊界測試套件**：
   - 撰寫 `tests/test_dictionary.py` 增強測試，全面驗證「有上下文觸發」、「無上下文保持原樣」、「v1/v2 混合模式」等邊界情況。

---

## 4. 新對話啟動提示詞 (Prompt for New Chat Session)

開啟新對話後，您可以直接貼上以下提示詞給 AI Agent：

```text
請依據 PROGRESS.md、doc/PHASE5_HANDOVER.md 與 doc/開發規格.md，開始進行 Phase 5：上下文感知同音詞校正 (Context-Aware Dictionary) 的開發工作。
```
