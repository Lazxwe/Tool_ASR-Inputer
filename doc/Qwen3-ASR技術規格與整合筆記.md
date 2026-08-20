# Qwen3-ASR 技術規格與整合速查筆記

<!-- 
[說明] 本文件記錄 Qwen3-ASR 官方規格、Python API 介面、參數定義與專案整合實踐。
所有 AI Agent 在開發 ASR 相關模組時請優先查閱本文件，無需重複上網搜尋。
-->

## 1. 核心模型資訊 (Model Registry)

| 規格代碼 | Hugging Face Model ID | 參數量 | 適用情境 | 建議推論裝置 |
| :--- | :--- | :--- | :--- | :--- |
| **`0.6b`** | `Qwen/Qwen3-ASR-0.6B` | ~600M | 低延遲打字、CPU/Apple Silicon 輕量執行 | `mps` / `cuda` / `cpu` |
| **`1.7b`** | `Qwen/Qwen3-ASR-1.7B` | ~1.7B | 高精準度語音辨識、多語言/方言混合 | `cuda` / `mps` |

---

## 2. 官方推論套件與 API 規格 (`qwen-asr`)

### 2.1 套件安裝
```bash
pip install -U qwen-asr
```

### 2.2 模型載入 API (`Qwen3ASRModel.from_pretrained`)
```python
import torch
from qwen_asr import Qwen3ASRModel

model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-0.6B",          # 模型 ID 或本地路徑
    device_map="mps",                # 'mps' (macOS), 'cuda:0' (NVIDIA), 或 'cpu'
    cache_dir="./models/huggingface/hub" # 專案本地隔離快取路徑
)
```

### 2.3 辨識推論 API (`model.transcribe`)
```python
results = model.transcribe(
    audio=audio_input,              # 支援: (np.ndarray, 16000), 檔案路徑, 或 base64
    language="Chinese",             # "Chinese", "English", "zh", "en" 或 None (自動偵測)
    prompt="繁體中文，台灣習慣用語"     # Context/System Prompt 引導輸出格式
)
```

#### 音訊輸入格式說明：
* **記憶體直傳**：`(audio_array, sample_rate)` 元組（音訊為 1D `np.float32`，建議取樣率 `16000` Hz，單聲道）。
* **檔案路徑**：傳入 `.wav` / `.mp3` 檔案字串路徑。
* **回傳結構**：回傳 list，每個元素具備 `.text` 屬性（或 dict / str）。

---

## 3. 本專案整合架構與注意事項 (Developer Notes)

1. **路徑隔離原則**：
   - 模型下載時必須透過環境變數 `HF_HOME="./models/huggingface"` 與 `cache_dir` 限制在專案目錄內，避免佔用全域快取空間。
2. **記憶體釋放與熱切換**：
   - 切換模型（如 0.6B 切換至 1.7B）時，需呼叫 `del model_instance`、`gc.collect()` 並清除 PyTorch 快取（`torch.cuda.empty_cache()` 或 `torch.mps.empty_cache()`）。
3. **繁中文字後處理串接**：
   - ASR 原始文字輸出後，依序通過 `OpenCC`（保底繁化）與 `Custom Dictionary`（Exact Variant 近音詞精確替換），再進入剪貼簿。
