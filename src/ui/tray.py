"""System menu bar and tray interface using pystray."""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw

from src.app.state import AppState, StateManager

try:
    import pystray
    from pystray import Menu, MenuItem
except Exception:  # pragma: no cover
    pystray = None  # type: ignore
    Menu = None  # type: ignore
    MenuItem = None  # type: ignore

logger = logging.getLogger(__name__)


def find_app_icon_path() -> Optional[Path]:
    """Locate assets/icon.png in project directory or frozen bundle."""
    candidates = [
        Path("assets/icon.png"),
        Path(__file__).resolve().parent.parent.parent / "assets" / "icon.png",
        Path(sys.executable).parent / "assets" / "icon.png" if getattr(sys, "frozen", False) else None,
    ]
    for c in candidates:
        if c and c.is_file():
            return c
    return None


def create_status_icon(state: AppState, size: int = 64) -> Image.Image:
    """Generate a high-contrast tray icon representing the current application state.

    Uses assets/icon.png as base if available, with state badges overlaid.
    """
    icon_path = find_app_icon_path()
    if icon_path:
        try:
            base_img = Image.open(icon_path).convert("RGBA")
            image = base_img.resize((size, size), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)

            # Overlay status badge if in active non-ready state
            if state != AppState.READY and state != AppState.IDLE:
                badge_colors = {
                    AppState.RECORDING: "#D32F2F",    # Vivid Red
                    AppState.PROCESSING: "#F57C00",   # Amber/Orange
                    AppState.DOWNLOADING: "#7C4DFF",  # Vivid Purple
                    AppState.ERROR: "#757575",        # Neutral Gray
                }
                color = badge_colors.get(state, "#1976D2")
                badge_r = max(size // 5, 6)
                cx, cy = size - badge_r - 2, size - badge_r - 2
                draw.ellipse(
                    [(cx - badge_r, cy - badge_r), (cx + badge_r, cy + badge_r)],
                    fill=color,
                    outline="#FFFFFF",
                    width=2,
                )
            return image
        except Exception as e:
            logger.debug("Could not load app icon image: %s. Falling back to procedural.", e)

    # Procedural fallback icon
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Color palette based on state
    colors = {
        AppState.IDLE: "#2E7D32",         # Forest Green
        AppState.READY: "#1976D2",        # Deep Blue
        AppState.RECORDING: "#D32F2F",    # Vivid Red
        AppState.PROCESSING: "#F57C00",   # Amber/Orange
        AppState.DOWNLOADING: "#7C4DFF",  # Vivid Purple
        AppState.ERROR: "#757575",        # Neutral Gray
    }
    color = colors.get(state, "#1976D2")

    # Draw outer anti-aliased circular badge
    padding = 6
    draw.ellipse(
        [(padding, padding), (size - padding, size - padding)],
        fill=color,
        outline="#FFFFFF",
        width=2,
    )

    # Draw inner symbol / dot
    inner_pad = size // 3
    if state == AppState.RECORDING:
        draw.ellipse(
            [(inner_pad, inner_pad), (size - inner_pad, size - inner_pad)],
            fill="#FFFFFF",
        )
    elif state == AppState.PROCESSING:
        draw.rectangle(
            [(inner_pad, inner_pad), (size - inner_pad, size - inner_pad)],
            fill="#FFFFFF",
        )
    elif state == AppState.DOWNLOADING:
        mid_x = size // 2
        draw.line([(mid_x, inner_pad), (mid_x, size - inner_pad)], fill="#FFFFFF", width=3)
        draw.line([(inner_pad + 2, mid_x + 2), (mid_x, size - inner_pad)], fill="#FFFFFF", width=3)
        draw.line([(size - inner_pad - 2, mid_x + 2), (mid_x, size - inner_pad)], fill="#FFFFFF", width=3)
    elif state == AppState.ERROR:
        draw.line([(inner_pad, inner_pad), (size - inner_pad, size - inner_pad)], fill="#FFFFFF", width=3)
        draw.line([(inner_pad, size - inner_pad), (size - inner_pad, inner_pad)], fill="#FFFFFF", width=3)
    else:
        core_pad = size // 2 - 3
        draw.ellipse(
            [(core_pad, core_pad), (core_pad + 6, core_pad + 6)],
            fill="#FFFFFF",
        )

    return image


def open_file_in_system_editor(file_path: Path | str) -> bool:
    """Open a file with the system default application (cross-platform)."""
    target = Path(file_path).resolve()
    if not target.exists():
        logger.warning("Target file does not exist: %s", target)
        return False

    current_os = platform.system().lower()
    try:
        if "darwin" in current_os:
            subprocess.Popen(["open", str(target)])
        elif "windows" in current_os:
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(target)])
        logger.info("Opened '%s' in default system editor.", target)
        return True
    except Exception as e:
        logger.error("Failed to open file '%s': %s", target, e)
        return False


class TrayUI:
    """System tray / menu bar integration providing status indicator and settings menu."""

    def __init__(
        self,
        state_manager: StateManager,
        current_model_getter: Callable[[], str],
        current_device_getter: Optional[Callable[[], str]] = None,
        on_select_model: Optional[Callable[[str], None]] = None,
        on_select_device: Optional[Callable[[str], None]] = None,
        on_reload_dictionary: Optional[Callable[[], None]] = None,
        on_reset_config: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        dictionary_path: Path | str = "custom_dictionary.json",
    ) -> None:
        self.state_manager = state_manager
        self.current_model_getter = current_model_getter
        self.current_device_getter = current_device_getter or (lambda: "auto")
        self.on_select_model = on_select_model
        self.on_select_device = on_select_device
        self.on_reload_dictionary = on_reload_dictionary
        self.on_reset_config = on_reset_config
        self.on_quit = on_quit
        self.dictionary_path = Path(dictionary_path)

        self._icon: Optional[pystray.Icon] = None
        self._unsubscribe_state: Optional[Callable[[], None]] = None

    def _build_menu(self) -> Menu:
        """Construct the pystray menu items matching the project specification."""
        current_state = self.state_manager.state
        current_model = self.current_model_getter().lower()
        current_device = self.current_device_getter().lower()

        # Status text
        if current_state == AppState.DOWNLOADING:
            pct = self.state_manager.download_percent
            status_text = f"狀態: 下載模型中 ({pct:.0f}%)"
        elif current_state == AppState.ERROR and self.state_manager.last_error:
            error_preview = self.state_manager.last_error[:30]
            status_text = f"錯誤: {error_preview}..."
        else:
            status_text = f"狀態: {current_state.display_name}"

        # Model selection submenu
        def is_06b_selected(item: MenuItem) -> bool:
            return "0.6b" in self.current_model_getter().lower()

        def is_17b_selected(item: MenuItem) -> bool:
            return "1.7b" in self.current_model_getter().lower()

        def set_model_06b(icon: pystray.Icon, item: MenuItem) -> None:
            if self.on_select_model:
                self.on_select_model("0.6b")
            self.refresh()

        def set_model_17b(icon: pystray.Icon, item: MenuItem) -> None:
            if self.on_select_model:
                self.on_select_model("1.7b")
            self.refresh()

        model_submenu = Menu(
            MenuItem(
                "Qwen3-ASR-0.6B",
                set_model_06b,
                checked=is_06b_selected,
                radio=True,
            ),
            MenuItem(
                "Qwen3-ASR-1.7B",
                set_model_17b,
                checked=is_17b_selected,
                radio=True,
            ),
        )

        # Device selection submenu (Only displayed on Windows with NVIDIA GPU)
        device_submenu = None
        from src.hardware.gpu_detector import should_show_device_menu
        if should_show_device_menu():
            def is_auto_selected(item: MenuItem) -> bool:
                return self.current_device_getter().lower() == "auto"

            def is_cpu_selected(item: MenuItem) -> bool:
                return self.current_device_getter().lower() == "cpu"

            def is_gpu_selected(item: MenuItem) -> bool:
                return self.current_device_getter().lower() in ("cuda", "cuda:0")

            def set_device_auto(icon: pystray.Icon, item: MenuItem) -> None:
                if self.on_select_device:
                    self.on_select_device("auto")
                self.refresh()

            def set_device_cpu(icon: pystray.Icon, item: MenuItem) -> None:
                if self.on_select_device:
                    self.on_select_device("cpu")
                self.refresh()

            def set_device_gpu(icon: pystray.Icon, item: MenuItem) -> None:
                if self.on_select_device:
                    self.on_select_device("cuda")
                self.refresh()

            device_submenu = Menu(
                MenuItem(
                    "自動偵測 (Auto)",
                    set_device_auto,
                    checked=is_auto_selected,
                    radio=True,
                ),
                MenuItem(
                    "一般記憶體 (CPU / RAM)",
                    set_device_cpu,
                    checked=is_cpu_selected,
                    radio=True,
                ),
                MenuItem(
                    "顯示卡顯存 (NVIDIA GPU / VRAM)",
                    set_device_gpu,
                    checked=is_gpu_selected,
                    radio=True,
                ),
            )

        def handle_open_dict(icon: pystray.Icon, item: MenuItem) -> None:
            open_file_in_system_editor(self.dictionary_path)

        def handle_reload_dict(icon: pystray.Icon, item: MenuItem) -> None:
            if self.on_reload_dictionary:
                self.on_reload_dictionary()

        def handle_reset_cfg(icon: pystray.Icon, item: MenuItem) -> None:
            if self.on_reset_config:
                self.on_reset_config()

        def handle_quit(icon: pystray.Icon, item: MenuItem) -> None:
            if self.on_quit:
                self.on_quit()
            self.stop()

        items = [
            MenuItem(f"語音輸入 (Tool_ASR Inputer)", None, enabled=False),
            MenuItem(status_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("模型選擇 (Model)", model_submenu),
        ]

        if device_submenu is not None:
            items.append(MenuItem("運算裝置 (Device)", device_submenu))

        items.extend([
            MenuItem("開啟詞庫 (Open Dictionary)", handle_open_dict),
            MenuItem("重新載入詞庫 (Reload Dictionary)", handle_reload_dict),
            MenuItem("重置設定檔 (Reset Config)", handle_reset_cfg),
            Menu.SEPARATOR,
            MenuItem("結束 (Quit)", handle_quit),
        ])

        return Menu(*items)

    def _on_state_changed(self, state: AppState, error_msg: Optional[str]) -> None:
        """Invoked when StateManager notifies of a state change."""
        self.refresh()

    def refresh(self) -> None:
        """Update icon image and menu items in place."""
        if self._icon is not None:
            try:
                new_image = create_status_icon(self.state_manager.state)
                self._icon.icon = new_image
                if self.state_manager.state == AppState.DOWNLOADING:
                    pct = self.state_manager.download_percent
                    self._icon.title = f"Tool_ASR Inputer (下載中 {pct:.0f}%)"
                else:
                    self._icon.title = f"Tool_ASR Inputer ({self.state_manager.state.display_name})"
                self._icon.menu = self._build_menu()
                if hasattr(self._icon, "update_menu"):
                    self._icon.update_menu()
            except Exception as e:
                logger.warning("Error refreshing tray icon: %s", e)

    def start(self, detached: bool = True) -> None:
        """Start the system tray icon.

        Args:
            detached: If True, runs asynchronously in a background thread.
        """
        if pystray is None:
            logger.warning("pystray library is not available. Tray UI disabled.")
            return

        icon_image = create_status_icon(self.state_manager.state)
        self._icon = pystray.Icon(
            name="Tool_ASR_Inputer",
            icon=icon_image,
            title="Tool_ASR Inputer",
            menu=self._build_menu(),
        )

        self._unsubscribe_state = self.state_manager.subscribe(self._on_state_changed)

        if detached:
            self._icon.run_detached()
            logger.info("System tray initialized in detached background mode.")
        else:
            logger.info("System tray starting in blocking mode.")
            self._icon.run()

    def stop(self) -> None:
        """Stop and dismantle the system tray icon."""
        if self._unsubscribe_state:
            self._unsubscribe_state()
            self._unsubscribe_state = None

        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as e:
                logger.warning("Error stopping tray icon: %s", e)
            finally:
                self._icon = None
                logger.info("System tray icon stopped.")
