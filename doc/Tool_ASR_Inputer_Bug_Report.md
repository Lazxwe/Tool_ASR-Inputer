# Tool_ASR_Inputer v0821 — PyInstaller 打包缺陷完整除錯報告

> **報告日期**：2026-08-21  
> **環境**：Windows 11, Python 3.12, PyInstaller 打包的 `.exe`  
> **結論**：打包時遺漏了關鍵的 `python3.dll` 以及多項執行期依賴，導致 `safetensors` 原生 Rust 模組無法載入，進而使整條 `qwen_asr → transformers → safetensors` 匯入鏈斷裂，最終以誤導性的「尚未安裝 qwen-asr」錯誤呈現給使用者。

---

## 一、問題現象

使用者解壓後雙擊 `Tool_ASR_Inputer.exe` 啟動，系統匣圖示正常出現。  
但按下 `F8` 觸發語音辨識時，**每次都會失敗**，日誌固定顯示：

```
[ERROR] [src.asr.model_manager] Failed to load model '0.6b': 
  尚未安裝 qwen-asr 推論套件 (pip install qwen-asr)。
  未偵測到本地模型 '0.6b'。
  【純離線部署】請將 Qwen/Qwen3-ASR-0.6B 模型檔案放置於：
    -> D:\AI\Tool_ASR_Inputer\models\0.6b
```

此錯誤訊息**極度誤導**——不論模型路徑是否正確、依賴是否已安裝，都會顯示完全相同的字串。

---

## 二、測試環境

| 項目 | 值 |
|---|---|
| 作業系統 | Windows 11 (非開發者模式、無 Symlink 權限) |
| 系統 Python | 3.12 (位於 `C:\Users\...\AppData\Local\Programs\Python\Python312`) |
| 打包方式 | PyInstaller (onedir 模式)，產出 `.exe` + `_internal/` 資料夾 |
| `.exe` 大小 | ~5 MB（極輕量，AI 推論引擎完全排除在打包範圍外） |
| `_internal/` | 包含基礎 Python 運行環境、部分標準庫，**不含** torch / transformers / qwen-asr 等 AI 套件 |

---

## 三、除錯時間線與試錯過程

### 階段 1：初步環境分析

**觀察**：`_internal/` 資料夾中完全沒有 `torch`、`transformers`、`qwen-asr` 等 AI 推論所需的套件。

**動作**：使用 `pip install --target D:\..\_internal` 將以下套件注入打包環境：
- `qwen-asr`
- `torch` (CPU 版)
- `transformers`
- `safetensors`
- `huggingface_hub`
- 以及上述套件的所有遞移依賴

**結果**：❌ 依然報錯「尚未安裝 qwen-asr」

---

### 階段 2：模型下載與路徑修正

**觀察**：錯誤訊息提示「未偵測到本地模型 '0.6b'」，懷疑是模型未下載。

**動作**：
1. 使用 `--download-model 0.6b` 指令下載模型至 `models/huggingface/hub/` 快取目錄
2. 過程中遭遇 Windows `WinError 1314` (symlink 權限不足)，透過設定環境變數 `HF_HUB_DISABLE_SYMLINKS=1` 解決
3. 將下載好的模型檔案手動複製到 `models/0.6b/` 目錄（離線部署路徑）

**結果**：❌ 模型路徑正確（10 個檔案皆存在，含 1.8GB 的 `model.safetensors`），但依然報同樣的錯

---

### 階段 3：標準庫補全

**觀察**：部分 pip 安裝的套件在匯入時觸發 `ModuleNotFoundError`，缺少 Python 標準庫模組（如 `timeit`、`http.cookies`、`unittest.mock`）。PyInstaller 的 tree-shaking 過度裁剪了標準庫。

**動作**：將系統 Python 3.12 的完整標準庫 (`Lib/`) 複製到 `_internal/` 目錄

**結果**：❌ 部分匯入錯誤修復，但核心問題不變

---

### 階段 4：DLL 搜尋路徑修正

**觀察**：懷疑 PyInstaller 執行檔無法找到深層的 `.dll` 檔案（如 `torch_cpu.dll`、`c10.dll` 等）

**動作**：
1. 將 `_internal/` 內所有 `.dll` 遞迴複製到 `.exe` 同層目錄
2. 將 Python `DLLs/` 資料夾的 `.pyd` 擴充模組複製到 `_internal/`

**結果**：❌ 問題持續

---

### 階段 5：植入偵錯程式碼（關鍵轉折點）🔑

**思路轉變**：既然所有外部修復都無效，必須深入到 `qwen-asr` 套件的**匯入過程**內部，捕捉最底層的真實例外。

**動作**：修改 `_internal/qwen_asr/__init__.py`，在匯入語句外包裹 `try-except`，將完整的 `traceback` 寫入 `debug.log`：

```python
# 原始程式碼：
from .inference.qwen3_asr import Qwen3ASRModel
from .inference.qwen3_forced_aligner import Qwen3ForcedAligner

# 修改為：
try:
    from .inference.qwen3_asr import Qwen3ASRModel
    from .inference.qwen3_forced_aligner import Qwen3ForcedAligner
except Exception as e:
    import traceback
    with open("debug.log", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    raise e
```

**結果**：✅ `debug.log` 成功生成，**揭露了真正的根因！**

---

## 四、根因分析

### `debug.log` 完整錯誤堆疊

```
Traceback (most recent call last):
  File "..\_internal\qwen_asr\__init__.py", line 21, in <module>
    from .inference.qwen3_asr import Qwen3ASRModel
  File "..\_internal\qwen_asr\inference\qwen3_asr.py", line 21, in <module>
    from qwen_asr.core.transformers_backend import (
  File "..\_internal\qwen_asr\core\transformers_backend\__init__.py", line 16, in <module>
    from .configuration_qwen3_asr import Qwen3ASRConfig
  File "..\_internal\qwen_asr\core\transformers_backend\configuration_qwen3_asr.py", line 15, in <module>
    from transformers.configuration_utils import PretrainedConfig
  File "..\_internal\transformers\__init__.py", line 27, in <module>
    from . import dependency_versions_check
  File "..\_internal\transformers\dependency_versions_check.py", line 16, in <module>
    from .utils.versions import require_version, require_version_core
  File "..\_internal\transformers\utils\__init__.py", line 24, in <module>
    from .auto_docstring import (
  File "..\_internal\transformers\utils\auto_docstring.py", line 30, in <module>
    from .generic import ModelOutput
  File "..\_internal\transformers\utils\generic.py", line 53, in <module>
    from ..model_debugging_utils import model_addition_debugger_context
  File "..\_internal\transformers\model_debugging_utils.py", line 30, in <module>
    from safetensors.torch import save_file
  File "..\_internal\safetensors\__init__.py", line 2, in <module>
    from ._safetensors_rust import (  # noqa: F401
ImportError: DLL load failed while importing _safetensors_rust: 找不到指定的模組。
```

### 匯入鏈斷裂流程圖

```
qwen_asr
  └─→ qwen3_asr.py
        └─→ transformers_backend
              └─→ configuration_qwen3_asr.py
                    └─→ transformers.configuration_utils
                          └─→ transformers.__init__
                                └─→ dependency_versions_check
                                      └─→ transformers.utils
                                            └─→ auto_docstring
                                                  └─→ generic.py
                                                        └─→ model_debugging_utils
                                                              └─→ safetensors.torch
                                                                    └─→ safetensors.__init__
                                                                          └─→ _safetensors_rust.pyd
                                                                                ❌ DLL load failed!
```

### 為什麼 `_safetensors_rust.pyd` 會載入失敗？

使用 `pefile` 分析 `_safetensors_rust.pyd` 的 DLL 依賴清單：

```
bcryptprimitives.dll    ← Windows 系統自帶 ✅
kernel32.dll            ← Windows 系統自帶 ✅
VCRUNTIME140.dll        ← 打包中已包含 ✅
api-ms-win-crt-*.dll    ← 打包中已包含 ✅
python3.dll             ← ❌❌❌ 打包中完全遺漏！
python312.dll           ← (未直接依賴，但存在)
```

**`python3.dll` 是 Python 的 Stable ABI 轉發層 DLL**。它是一個極小的轉發用 DLL，負責將 Stable ABI 呼叫轉發到版本特定的 `python312.dll`。  

所有使用 Stable ABI (即 `Py_LIMITED_API`) 編譯的 `.pyd` 原生擴充模組（包含 Rust 透過 PyO3 編譯的 `_safetensors_rust.pyd`）都會依賴 `python3.dll` 而非 `python312.dll`。

**PyInstaller 在打包時遺漏了這個 DLL，導致所有 Stable ABI 的原生模組全部無法載入。**

---

## 五、修復方式

### 最終有效修復（僅需 1 個檔案）

將系統 Python 安裝目錄中的 `python3.dll` 複製到打包目錄的根目錄和 `_internal/` 目錄：

```powershell
# 從系統 Python 複製 python3.dll
Copy-Item "C:\Users\...\Python\Python312\python3.dll" -Destination ".\Tool_ASR_Inputer-0821\"
Copy-Item "C:\Users\...\Python\Python312\python3.dll" -Destination ".\Tool_ASR_Inputer-0821\_internal\"
```

> **注意**：`python3.dll` 大小約 57 KB，對打包體積幾乎沒有影響。

---

## 六、給開發者的版本修正建議

### 建議 1：PyInstaller `.spec` 檔增加 `python3.dll`

在 PyInstaller 的 `.spec` 檔案或 `build` 腳本中，**明確將 `python3.dll` 加入 binaries 清單**：

```python
# 在 .spec 檔中：
import sys
import os

python_dir = os.path.dirname(sys.executable)
python3_dll = os.path.join(python_dir, 'python3.dll')

a = Analysis(
    ...
    binaries=[
        (python3_dll, '.'),  # 將 python3.dll 放到打包根目錄
    ],
    ...
)
```

或者，如果使用命令列打包：

```bash
pyinstaller --add-binary "C:/path/to/Python312/python3.dll;." your_script.py
```

### 建議 2：在 `model_manager` 的錯誤處理中加入更詳細的匯入診斷

目前 `model_manager` 捕捉到匯入失敗後，只顯示固定的「尚未安裝 qwen-asr / 未偵測到模型」字串，**完全掩蓋了真實的底層錯誤**。建議改為：

```python
# 改善前（推測的現有邏輯）：
try:
    import qwen_asr
except ImportError:
    raise ModelNotFoundError(
        "尚未安裝 qwen-asr 推論套件 (pip install qwen-asr)。\n"
        "未偵測到本地模型..."
    )

# 改善後：
try:
    import qwen_asr
except ImportError as e:
    import traceback
    detailed_error = traceback.format_exc()
    raise ModelNotFoundError(
        f"qwen-asr 匯入失敗。\n"
        f"底層錯誤：{e}\n"
        f"完整堆疊：\n{detailed_error}\n\n"
        f"常見原因：\n"
        f"  1. 尚未安裝 qwen-asr (pip install qwen-asr)\n"
        f"  2. 打包環境缺少 python3.dll (Stable ABI 依賴)\n"
        f"  3. 原生模組的 DLL 依賴遺失\n"
    )
```

### 建議 3：新增打包後自動驗證腳本

在 CI/CD 或手動發布流程中，新增一個驗證步驟，在**乾淨的 Windows 環境**（不含 Python）上測試打包結果：

```python
# verify_package.py — 放在打包目錄中作為發布前驗證
import subprocess, sys, os

exe_path = os.path.join(os.path.dirname(__file__), 'Tool_ASR_Inputer.exe')

# 測試 1：基本啟動
result = subprocess.run([exe_path, '--version'], capture_output=True, text=True, timeout=30)
assert result.returncode == 0, f"啟動失敗：{result.stderr}"

# 測試 2：模型載入（需先放置模型）
result = subprocess.run([exe_path, '--dry-run'], capture_output=True, text=True, timeout=60)
assert 'ImportError' not in result.stderr, f"匯入錯誤：{result.stderr}"
assert 'DLL load failed' not in result.stderr, f"DLL 載入失敗：{result.stderr}"

print("✅ 打包驗證通過")
```

### 建議 4：處理 Windows Symlink 權限問題

許多 Windows 使用者沒有建立 Symlink 的權限，導致 Hugging Face Hub 的快取系統產生警告或失敗。建議：

```python
# 在應用程式啟動時自動設定
import os
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')

# 或在 config.json 中提供選項讓使用者控制
```

---

## 七、額外發現的次要問題

以下問題在本次除錯過程中也被發現，雖非根因，但可能影響部分使用者：

| # | 問題 | 影響 | 建議修復 |
|---|---|---|---|
| 1 | `_internal/` 中缺少部分 Python 標準庫模組（`timeit`、`http.cookies`、`unittest.mock` 等） | 某些依賴套件匯入時會觸發 `ModuleNotFoundError` | 在 `.spec` 中使用 `hiddenimports` 明確列出所需的標準庫模組 |
| 2 | Windows 上 `HF_HUB_DISABLE_SYMLINKS` 未預設啟用 | 非開發者模式的 Windows 使用者下載模型時觸發 `WinError 1314` | 程式啟動時自動偵測並設定此環境變數 |
| 3 | 錯誤日誌含有 `cp950` 編碼問題 | 繁體中文 Windows 上日誌訊息輸出到 console 時可能觸發 `UnicodeEncodeError` | 設定 `PYTHONIOENCODING=utf-8` 或在 logger 中處理編碼 |

---

## 八、總結

| 項目 | 內容 |
|---|---|
| **根因** | PyInstaller 打包時遺漏 `python3.dll`（Python Stable ABI 轉發層） |
| **影響範圍** | 所有透過 Stable ABI (PyO3/Rust) 編譯的 `.pyd` 模組，包含 `safetensors`、可能還有 `tokenizers` 等 |
| **修復成本** | 極低——僅需在打包配置中增加 1 個約 57KB 的 DLL 檔案 |
| **誤導性** | 極高——錯誤訊息將底層 DLL 載入失敗偽裝成「套件未安裝 / 模型未下載」，大幅增加使用者排障難度 |
| **驗證方法** | 在 `qwen_asr/__init__.py` 匯入處加入 `try-except` + `traceback` 寫入 `debug.log`，即可直接看到真實錯誤 |
