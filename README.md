# Tool_ASR Inputer (本地端繁體中文 AI 語音打字工具)

> **極簡、純本地端、跨平台、繁體中文優先的 AI 語音打字與自動貼上工具。**

`Tool_ASR Inputer` 專注於將語音以極低延遲辨識為台灣繁體中文，並一鍵自動貼上至目前系統游標所在處。所有 ASR 推論與文字處理完全在本機端執行，不依賴任何雲端 API，保障個人隱私與資料安全。

---

## 🌟 核心特色

1. **純本機端執行 (Local First)**：
   - 使用 Qwen3-ASR (`0.6B` / `1.7B`) 本地推論模型，無需連網亦可進行語音打字。
   - 模型與快取隔離於專案目錄（`./models/`），不污染使用者全域空間。
2. **繁體中文與台灣用語優先 (Traditional Chinese First)**：
   - ASR 繁中 Prompt 引導 + OpenCC 台灣常用字詞保底轉換。
   - 專屬自訂詞庫 (`custom_dictionary.json`)，支援同音詞、近音詞與專有名詞精準替換（例如：`城市` → `程式`、`視頻` → `影片`）。
3. **極簡操作體驗 (Minimalist UX)**：
   - 無複雜的主視窗干擾，僅常駐於系統托盤 / 選單列 (System Tray / Menu Bar)。
   - 全域快捷鍵 **`F8`**：按一下開始錄音，再按一下停止並自動辨識貼上。
4. **一鍵系統健康診斷 (`--doctor`)**：
   - 內建診斷工具，一鍵檢測麥克風設備、模型權重、詞庫格式、依賴套件與作業系統權限。
5. **獨立發布架構 (Packaging Ready)**：
   - 提供 PyInstaller 自動化打包腳本，執行檔、詞庫與模型資料夾結構乾淨分離。

---

## 🛠️ 系統需求

- **作業系統**：macOS (Apple Silicon / Intel) 或 Windows 10/11
- **Python 版本**：Python 3.11 或 3.12
- **硬體建議**：
  - **0.6B 模型**：Apple Silicon (MPS) 或 一般 CPU 即可流暢執行（記憶體需求約 2GB）。
  - **1.7B 模型**：建議配備 NVIDIA GPU (CUDA) 或 Apple Silicon 統一記憶體（建議 8GB RAM 以上）。

---

## 🚀 快速開始

### 1. 建立虛擬環境並安裝依賴

```bash
# 建立虛擬環境
python3 -m venv .venv

# 啟用虛擬環境
# macOS / Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 安裝相依套件
pip install -r requirements.txt
```

### 2. 執行系統健康檢測

在首次啟動前，建議執行系統診斷工具以確認環境就緒：

```bash
python -m src.main --doctor
```

### 3. 啟動語音打字工具

```bash
python -m src.main
```

啟動後，系統托盤將出現圓形圖示（藍色表示 Ready 就緒）。

---

## 🧠 Qwen3-ASR 模型配置指南

支援兩種模型配置方式：

### 方式 A：純離線模式（手動放置權重）
適合無網際網路連線或內部網路環境。請將下載好的模型資料夾放置於專案根目錄的 `models/` 下：
- **0.6B 模型**：`models/0.6b/`
- **1.7B 模型**：`models/1.7b/`

當目錄內包含模型權重檔（如 `config.json`, `model.safetensors`）時，系統將自動優先載入本機目錄。

### 方式 B：自動下載快取模式（具備網路連線）
在有網路連線的環境下，若本機目錄無模型，系統會在首次使用時自動從 Hugging Face 下載至 `./models/huggingface/hub/` 專案隔離快取中。

---

## 📖 自訂詞庫配置 (`custom_dictionary.json`)

使用者可隨時編輯專案目錄下的 `custom_dictionary.json` 進行近音字與專有名詞校正：

```json
{
  "version": 1,
  "entries": [
    {
      "target": "程式",
      "variants": ["城市", "成式"]
    },
    {
      "target": "介面",
      "variants": ["接口", "界面"]
    },
    {
      "target": "影片",
      "variants": ["視頻", "視訊"]
    },
    {
      "target": "軟體",
      "variants": ["軟件"]
    },
    {
      "target": "伺服器",
      "variants": ["服務器"]
    }
  ]
}
```

- **`target`**：您希望最終輸出的標準詞。
- **`variants`**：語音辨識可能產生的同音詞、簡體習慣詞或異用字清單。
- 編輯完成後，可於托盤選單點擊 **「重新載入詞庫」**，無需重啟程式。

---

## ⚙️ 設定檔詳解 (`config.json`)

本專案採用極簡純文字設定檔，使用者可直接修改 `config.json`：

```json
{
  "model": "0.6b",
  "hotkey": "f8",
  "hotkey_mode": "hold",
  "model_dir": "./models",
  "sample_rate": 16000,
  "language": "Chinese"
}
```

### 各欄位意義與說明

| 參數名稱 | 預設值 | 可選值 | 說明 |
| :--- | :--- | :--- | :--- |
| **`hotkey_mode`** | `"hold"` | `"hold"` / `"toggle"` | **觸發模式**：<br>• `"hold"`（推薦）：**按住不放錄音，鬆開自動結束並貼上**。<br>• `"toggle"`：**按一下開始錄音，再按一下停止並貼上**。 |
| **`hotkey`** | `"f8"` | 字串（見下方範例） | **語音熱鍵名稱**，跨 macOS 與 Windows 通用。 |
| **`model`** | `"0.6b"` | `"0.6b"` / `"1.7b"` | **預設載入模型**。<br>💡 *注意：軟體啟動後，直接點擊右上角工作列/選單列圖示即可即時熱切換模型，無需手動改檔。* |
| **`sample_rate`**| `16000` | 數字 (Hz) | 錄音取樣率（Qwen3-ASR 最佳辨識頻率為 16000）。 |
| **`language`** | `"Chinese"`| `"Chinese"` / `"English"` | 預設 ASR 辨識語言。 |
| **`model_dir`** | `"./models"`| 路徑字串 | 本機模型與 HuggingFace 快取儲存目錄。 |

### 鍵盤熱鍵名稱組合範例（macOS / Windows 通用）

| 按鍵類型 | 設定檔範例 | 說明 |
| :--- | :--- | :--- |
| **單一功能鍵** | `"f8"`, `"f9"`, `"f2"`, `"f12"` | 單鍵觸發（最推薦，不易與其他程式衝突） |
| **控制鍵 + 字母** | `"ctrl+alt+v"`, `"alt+a"`, `"ctrl+shift+a"` | 標準組合鍵 |
| **控制鍵 + 特殊鍵**| `"ctrl+space"`, `"alt+space"` | 快速鍵呼叫 |
| **Mac 專屬鍵** | `"cmd+shift+v"`, `"cmd+space"` | Command 鍵 (macOS) |
| **其他特殊鍵** | `"caps_lock"`, `"esc"`, `"enter"`, `"tab"` | 特殊按鍵 |

---

## 🎮 使用與操作指南

### 語音打字操作流程

#### 模式一：按住錄音 (Hold 模式，預設推薦)
1. 將游標移動至任何文字編輯區（瀏覽器、記事本、Word、Slack、VS Code 等）。
2. **按住鍵盤 `F8` 不放**：選單列圖示轉為 **紅色**，代表正在錄音。
3. 對著麥克風說話。
4. **手指鬆開 `F8`**：選單列圖示轉為 **橘色**（進行 ASR 與繁中後處理）。
5. 辨識完成後，文字自動貼上至目前游標處，圖示回復為 **藍色**。

#### 模式二：按鍵切換 (Toggle 模式)
- 按一下 `F8` 開始錄音（圖示變紅），說完後再按一下 `F8` 停止並貼上。

### 工作列 / 選單列托盤功能
- **模型選擇 (Model)**：直接點擊選單列圖示，即可在 `Qwen3-ASR-0.6B` 與 `Qwen3-ASR-1.7B` 之間**即時熱切換**（不需重啟程式或改設定檔）。
- **開啟詞庫 (Open Dictionary)**：以系統預設文字編輯器開啟 `custom_dictionary.json`。
- **重新載入詞庫 (Reload Dictionary)**：即時重載自訂詞庫。
- **重置設定檔 (Reset Config)**：將 `config.json` 恢復成原廠預設值（舊檔會自動備份為 `config.json.bak`）。
- **結束 (Quit)**：安全釋放音訊串流與記憶體並關閉程式。

---

## 📦 PyInstaller 分發打包

本專案提供一鍵打包腳本：

```bash
python scripts/build.py
```

打包完成後將生成 `dist/Tool_ASR_Inputer/` 分發資料夾，其目錄結構如下：

```text
dist/Tool_ASR_Inputer/
├── Tool_ASR_Inputer         # 獨立執行檔 (macOS / Windows 可執行程式)
├── _internal/               # Python 執行階段動態函式庫與依賴
├── config.json              # 執行階段設定檔
├── custom_dictionary.json   # 外部自訂詞庫 (可隨時手動編輯)
├── models/                  # 本地模型放置目錄 (可自由放入 0.6b 或 1.7b)
│   ├── 0.6b/
│   └── 1.7b/
└── README.md
```

使用者無需安裝 Python 環境，只需解壓縮資料夾並執行 `Tool_ASR_Inputer` 即可使用。

---

## 🔒 系統權限與故障排除

### macOS 系統權限設定
在 macOS 上執行語音輸入與自動貼上需要以下系統權限：
1. **麥克風權限 (Microphone)**：
   - 路徑：「系統設定」->「隱私權與安全性」->「麥克風」
   - 請確認已允許執行中的終端機或 `Tool_ASR_Inputer` 取用麥克風。
2. **輔助使用與輸入監控權限 (Accessibility / Input Monitoring)**：
   - 路徑：「系統設定」->「隱私權與安全性」->「輔助使用」及「輸入監控」
   - 用於全域監聽 `F8` 熱鍵與發送 `Command + V` 貼上指令。

### 常見問題
- **Q: 按下 F8 無反應？**
  - 請檢查終端機日誌或執行 `--doctor`，確認熱鍵監聽權限已授予。
- **Q: 辨識結果未自動貼上？**
  - 文字仍會安全保存在系統剪貼簿中，您可以手動按 `Cmd+V` / `Ctrl+V` 貼上，並檢查系統輔助使用權限。
- **Q: 手動修改 config.json 格式跑掉壞了怎麼辦？**
  - 您可以點擊工作列圖示選擇 **「重置設定檔 (Reset Config)」**，或在終端機執行：
    ```bash
    python -m src.main --reset-config
    ```
    系統會自動將舊設定檔備份至 `config.json.bak` 並恢復為原廠標準設定！
- **Q: 想要更換自訂熱鍵？**
  - 可編輯 `config.json` 中的 `"hotkey": "f8"` 為其他按鍵名稱（如 `"f9"` 或 `"ctrl+alt+v"`）。

---

## 🧪 單元與整合測試

```bash
# 執行所有測試並輸出覆蓋率報告
pytest --cov=src -v
```
