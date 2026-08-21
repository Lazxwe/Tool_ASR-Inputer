"""Cross-platform native system notification service."""
from __future__ import annotations

import logging
import platform
import subprocess
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _escape_applescript_string(text: str) -> str:
    """Escape backslashes and double quotes for AppleScript string literals."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class NotificationService:
    """Dispatches native desktop notifications across macOS, Windows, and Linux."""

    def __init__(self, app_title: str = "Tool_ASR Inputer", tray_icon: Optional[Any] = None) -> None:
        self.app_title = app_title
        self.tray_icon = tray_icon
        self._os_type = platform.system().lower()

    def set_tray_icon(self, tray_icon: Any) -> None:
        """Bind a pystray Icon instance for Windows tray balloon notifications."""
        self.tray_icon = tray_icon

    def send(
        self,
        message: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        sound: bool = True,
    ) -> bool:
        """Send a native OS notification.

        Args:
            message: Body text of the notification.
            title: Title of the notification (defaults to self.app_title).
            subtitle: Optional subtitle (macOS only).
            sound: Whether to play a system notification alert sound.

        Returns:
            bool: True if notification command was dispatched without error, False otherwise.
        """
        resolved_title = title or self.app_title

        try:
            if "darwin" in self._os_type:
                return self._send_macos(message, resolved_title, subtitle, sound)
            elif "windows" in self._os_type:
                return self._send_windows(message, resolved_title)
            elif "linux" in self._os_type:
                return self._send_linux(message, resolved_title)
            else:
                logger.info("[NOTIFICATION][%s] %s", resolved_title, message)
                return True
        except Exception as e:
            logger.warning("Failed to send system notification: %s", e)
            return False

    def _send_macos(
        self,
        message: str,
        title: str,
        subtitle: Optional[str],
        sound: bool,
    ) -> bool:
        """Send notification via macOS osascript."""
        esc_title = _escape_applescript_string(title)
        esc_msg = _escape_applescript_string(message)
        
        script_parts = [f'display notification "{esc_msg}" with title "{esc_title}"']
        if subtitle:
            esc_sub = _escape_applescript_string(subtitle)
            script_parts.append(f'subtitle "{esc_sub}"')
        if sound:
            script_parts.append('sound name "default"')

        script = " ".join(script_parts)
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.debug("Dispatched macOS notification: %s", message)
        return True

    def _send_windows(self, message: str, title: str) -> bool:
        """Send notification via pystray Icon.notify or PowerShell Toast on Windows."""
        # 1. Try pystray Icon notify if available
        if self.tray_icon is not None and hasattr(self.tray_icon, "notify"):
            try:
                self.tray_icon.notify(message, title)
                logger.debug("Dispatched Windows pystray notification: %s", message)
                return True
            except Exception as e:
                logger.debug("pystray notify failed, falling back to PowerShell: %s", e)

        # 2. PowerShell Toast notification fallback
        ps_script = (
            f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; '
            f'$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); '
            f'$textNodes = $template.GetElementsByTagName("text"); '
            f'$textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null; '
            f'$textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null; '
            f'$toast = [Windows.UI.Notifications.ToastNotification]::new($template); '
            f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{title}").Show($toast);'
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.debug("Dispatched Windows PowerShell notification: %s", message)
            return True
        except Exception as e:
            logger.warning("PowerShell toast notification failed: %s", e)
            logger.info("[NOTIFICATION][%s] %s", title, message)
            return False

    def _send_linux(self, message: str, title: str) -> bool:
        """Send notification via notify-send on Linux."""
        try:
            subprocess.Popen(
                ["notify-send", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.debug("Dispatched Linux notify-send: %s", message)
            return True
        except Exception as e:
            logger.warning("notify-send failed: %s", e)
            logger.info("[NOTIFICATION][%s] %s", title, message)
            return False
