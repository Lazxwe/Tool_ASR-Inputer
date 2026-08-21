"""System health check and diagnostic utilities for Tool_ASR Inputer."""
from __future__ import annotations

import logging
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from src.asr.model_manager import MODEL_REGISTRY, ModelManager
from src.settings.config import load_config
from src.settings.dictionary_loader import load_custom_dictionary

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticItem:
    """Individual diagnostic check result."""
    category: str
    name: str
    passed: bool
    details: str
    guidance: Optional[str] = None


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic result report."""
    system_info: dict[str, str] = field(default_factory=dict)
    items: List[DiagnosticItem] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Return True if all diagnostic checks passed."""
        return all(item.passed for item in self.items)

    def render_cli(self) -> str:
        """Render diagnostic report into human-readable Traditional Chinese console format."""
        lines: list[str] = []
        lines.append("=" * 65)
        lines.append("   Tool_ASR Inputer 系統診斷報告 (System Diagnostic Report)")
        lines.append("=" * 65)

        # System info
        lines.append("\n[系統環境資訊]")
        for k, v in self.system_info.items():
            lines.append(f"  • {k:<18}: {v}")

        # Diagnostic results by category
        categories: dict[str, list[DiagnosticItem]] = {}
        for item in self.items:
            categories.setdefault(item.category, []).append(item)

        for cat_name, cat_items in categories.items():
            lines.append(f"\n[{cat_name}]")
            for item in cat_items:
                icon = "✓ 通過" if item.passed else "✗ 警告/待處理"
                lines.append(f"  {icon} - {item.name}: {item.details}")
                if item.guidance and not item.passed:
                    guidance_lines = item.guidance.strip().split("\n")
                    for g_line in guidance_lines:
                        lines.append(f"       ↳ {g_line}")

        lines.append("\n" + "=" * 65)
        if self.all_passed:
            lines.append("  總結: 所有核心檢查均正常，系統已就緒可直接使用！")
        else:
            lines.append("  總結: 部分檢查有待處理事項，請參閱上方指引進行調整。")
        lines.append("=" * 65)

        return "\n".join(lines)


class SystemDoctor:
    """Performs end-to-end environment, device, model, and configuration diagnosis."""

    def __init__(
        self,
        config_path: Path | str = "config.json",
        dictionary_path: Path | str = "custom_dictionary.json",
        models_dir: Path | str = "./models",
    ) -> None:
        self.config_path = Path(config_path)
        self.dictionary_path = Path(dictionary_path)
        self.models_dir = Path(models_dir)
        self.model_manager = ModelManager(models_dir=self.models_dir)

    def collect_system_info(self) -> dict[str, str]:
        """Gather host platform and Python runtime details."""
        info: dict[str, str] = {
            "作業系統 (OS)": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "Python 版本": f"{platform.python_version()}",
            "執行檔路徑": sys.executable,
        }

        # Check torch acceleration
        try:
            import torch
            if torch.cuda.is_available():
                info["運算加速裝置"] = f"NVIDIA CUDA ({torch.cuda.get_device_name(0)})"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                info["運算加速裝置"] = "Apple Silicon MPS (GPU 加速)"
            else:
                info["運算加速裝置"] = "CPU (標準處理器模式)"
        except ImportError:
            info["運算加速裝置"] = "未偵測到 PyTorch"

        return info

    def check_audio_devices(self) -> list[DiagnosticItem]:
        """Verify microphone device availability and input stream capabilities."""
        results: list[DiagnosticItem] = []

        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]

            if not input_devices:
                results.append(DiagnosticItem(
                    category="音訊與麥克風",
                    name="麥克風輸入設備",
                    passed=False,
                    details="未偵測到任何可用的音訊輸入設備",
                    guidance="請連接麥克風並確認系統設定中已啟用音訊輸入權限。",
                ))
            else:
                default_in = sd.query_devices(kind="input")
                device_name = default_in.get("name", "預設麥克風")
                channels = default_in.get("max_input_channels", 1)
                results.append(DiagnosticItem(
                    category="音訊與麥克風",
                    name="預設麥克風",
                    passed=True,
                    details=f"偵測到: {device_name} (輸入聲道數: {channels})",
                ))

                # Test stream opening (sample rate 16000)
                try:
                    with sd.InputStream(samplerate=16000, channels=1, dtype="float32"):
                        pass
                    results.append(DiagnosticItem(
                        category="音訊與麥克風",
                        name="16kHz 取樣率串流",
                        passed=True,
                        details="16000Hz 單聲道音訊串流開啟成功",
                    ))
                except Exception as stream_err:
                    results.append(DiagnosticItem(
                        category="音訊與麥克風",
                        name="16kHz 取樣率串流",
                        passed=False,
                        details=f"無法建立 16000Hz 串流: {stream_err}",
                        guidance="若在 macOS 上，請至「系統設定 -> 隱私權與安全性 -> 麥克風」確認授予權限。",
                    ))

        except Exception as e:
            results.append(DiagnosticItem(
                category="音訊與麥克風",
                name="sounddevice 驅動",
                passed=False,
                details=f"音訊子系統檢查失敗: {e}",
                guidance="請確認系統音訊驅動程式運作正常，或執行 'pip install sounddevice'。",
            ))

        return results

    def check_models(self) -> list[DiagnosticItem]:
        """Check local availability and cache state for ASR models."""
        results: list[DiagnosticItem] = []

        for model_key in MODEL_REGISTRY:
            status = self.model_manager.check_local_model_availability(model_key)
            if status["available"]:
                results.append(DiagnosticItem(
                    category="Qwen3-ASR 模型檢測",
                    name=f"模型 {model_key.upper()}",
                    passed=True,
                    details=f"{status['description']} [{status['guidance']}]",
                ))
            else:
                results.append(DiagnosticItem(
                    category="Qwen3-ASR 模型檢測",
                    name=f"模型 {model_key.upper()}",
                    passed=False,
                    details=status["description"],
                    guidance=status["guidance"],
                ))

        return results

    def check_custom_dictionary(self) -> list[DiagnosticItem]:
        """Verify custom dictionary existence, JSON schema, and entry counts."""
        results: list[DiagnosticItem] = []

        if not self.dictionary_path.exists():
            results.append(DiagnosticItem(
                category="自訂詞庫 (Custom Dictionary)",
                name="詞庫檔案存在性",
                passed=False,
                details=f"未找到詞庫檔案: {self.dictionary_path}",
                guidance=f"系統將於首次執行時自動生成預設詞庫，或手動建立 {self.dictionary_path}。",
            ))
            return results

        dict_obj = load_custom_dictionary(self.dictionary_path)
        if dict_obj.entries:
            total_variants = sum(len(e.variants) for e in dict_obj.entries)
            context_entries = sum(1 for e in dict_obj.entries if e.context)
            exact_entries = len(dict_obj.entries) - context_entries
            
            if context_entries > 0:
                breakdown = f"（無條件替換: {exact_entries} 組, 上下文感知: {context_entries} 組）"
            else:
                breakdown = ""
                
            results.append(DiagnosticItem(
                category="自訂詞庫 (Custom Dictionary)",
                name="詞庫結構與解析",
                passed=True,
                details=f"有效詞條 {len(dict_obj.entries)} 組{breakdown}，共計 {total_variants} 個替換詞（版本: v{dict_obj.version}）",
            ))
        else:
            results.append(DiagnosticItem(
                category="自訂詞庫 (Custom Dictionary)",
                name="詞庫結構與解析",
                passed=True,
                details="詞庫為空或無有效詞條，將使用標準繁體中文轉換",
                guidance="可於 custom_dictionary.json 中新增 target 與 variants 項目。",
            ))

        return results

    def check_config(self) -> list[DiagnosticItem]:
        """Verify configuration file integrity."""
        results: list[DiagnosticItem] = []

        if not self.config_path.exists():
            results.append(DiagnosticItem(
                category="設定檔 (Config)",
                name="設定檔存在性",
                passed=True,
                details=f"未找到 {self.config_path}，程式將以預設參數運作 (0.6B, F8, 16kHz)",
            ))
        else:
            config = load_config(self.config_path)
            results.append(DiagnosticItem(
                category="設定檔 (Config)",
                name="設定檔載入",
                passed=True,
                details=f"預設模型: {config.model}, 熱鍵: {config.hotkey}, 取樣率: {config.sample_rate}Hz",
            ))

        return results

    def check_packages(self) -> list[DiagnosticItem]:
        """Verify essential library imports."""
        results: list[DiagnosticItem] = []
        required_pkgs = [
            ("opencc", "OpenCC 繁簡轉換引擎"),
            ("numpy", "NumPy 陣列運算庫"),
            ("sounddevice", "sounddevice 錄音介面"),
            ("pyperclip", "pyperclip 剪貼簿控制"),
            ("pystray", "pystray 系統托盤選單"),
            ("PIL", "Pillow 托盤圖示生成"),
            ("pynput", "pynput 熱鍵與模擬輸入"),
        ]

        for mod_name, desc in required_pkgs:
            try:
                __import__(mod_name)
                results.append(DiagnosticItem(
                    category="核心套件依賴",
                    name=desc,
                    passed=True,
                    details=f"套件 '{mod_name}' 已就緒",
                ))
            except ImportError as ie:
                results.append(DiagnosticItem(
                    category="核心套件依賴",
                    name=desc,
                    passed=False,
                    details=f"套件 '{mod_name}' 缺失: {ie}",
                    guidance=f"請執行 'pip install {mod_name}' 安裝相依套件。",
                ))

        return results

    def run_all_diagnostics(self) -> DiagnosticReport:
        """Run all diagnostic checks and construct a DiagnosticReport."""
        report = DiagnosticReport()
        report.system_info = self.collect_system_info()

        report.items.extend(self.check_packages())
        report.items.extend(self.check_audio_devices())
        report.items.extend(self.check_models())
        report.items.extend(self.check_custom_dictionary())
        report.items.extend(self.check_config())

        return report
