"""Unit tests for TrayUI and icon generation."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.app.state import AppState, StateManager
from src.ui.tray import TrayUI, create_status_icon, open_file_in_system_editor


def test_create_status_icon_all_states() -> None:
    for state in AppState:
        img = create_status_icon(state, size=32)
        assert img is not None
        assert img.size == (32, 32)
        assert img.mode == "RGBA"


def test_open_file_in_system_editor(tmp_path: Path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    # Non-existent file
    assert open_file_in_system_editor(tmp_path / "non_existent.json") is False

    with patch("subprocess.Popen") as mock_popen:
        assert open_file_in_system_editor(test_file) is True
        assert mock_popen.called


def test_open_file_in_system_editor_failure(tmp_path: Path) -> None:
    test_file = tmp_path / "test.json"
    test_file.write_text("{}", encoding="utf-8")

    with patch("subprocess.Popen", side_effect=Exception("Failed to spawn process")):
        assert open_file_in_system_editor(test_file) is False


def test_tray_ui_build_menu_and_callbacks(tmp_path: Path) -> None:
    sm = StateManager(initial_state=AppState.READY)
    selected_models = []
    reloaded_dict = []
    quitted = []
    dict_file = tmp_path / "custom_dictionary.json"
    dict_file.write_text("{}", encoding="utf-8")

    current_model = "0.6b"

    def get_model() -> str:
        return current_model

    tray = TrayUI(
        state_manager=sm,
        current_model_getter=get_model,
        on_select_model=lambda m: selected_models.append(m),
        on_reload_dictionary=lambda: reloaded_dict.append(True),
        on_quit=lambda: quitted.append(True),
        dictionary_path=dict_file,
    )

    menu = tray._build_menu()
    assert menu is not None

    # Test error state menu title formatting
    sm.set_state(AppState.ERROR, "Long error message testing description")
    error_menu = tray._build_menu()
    assert error_menu is not None

    # Simulate clicking menu items
    # Item 3 is Model submenu
    model_submenu = menu.items[3].submenu
    # 0.6B item
    model_submenu.items[0]._action(tray._icon, model_submenu.items[0])
    assert "0.6b" in selected_models

    # 1.7B item
    model_submenu.items[1]._action(tray._icon, model_submenu.items[1])
    assert "1.7b" in selected_models

    # Open dict item
    with patch("src.ui.tray.open_file_in_system_editor") as mock_open:
        menu.items[4]._action(tray._icon, menu.items[4])
        assert mock_open.called

    # Reload dict item
    menu.items[5]._action(tray._icon, menu.items[5])
    assert len(reloaded_dict) == 1

    # Reset config item
    reset_called = []
    tray.on_reset_config = lambda: reset_called.append(True)
    menu.items[6]._action(tray._icon, menu.items[6])
    assert len(reset_called) == 1

    # Quit item
    menu.items[8]._action(tray._icon, menu.items[8])
    assert len(quitted) == 1


def test_tray_ui_start_and_stop() -> None:
    sm = StateManager()
    tray = TrayUI(
        state_manager=sm,
        current_model_getter=lambda: "0.6b",
    )

    with patch("pystray.Icon") as mock_icon_cls:
        mock_icon = MagicMock()
        mock_icon_cls.return_value = mock_icon

        tray.start(detached=True)
        assert tray._icon is not None
        assert mock_icon.run_detached.called

        # Test refresh
        tray.refresh()
        assert mock_icon.update_menu.called

        tray.stop()
        assert tray._icon is None
        assert mock_icon.stop.called


def test_tray_ui_unavailable() -> None:
    sm = StateManager()
    tray = TrayUI(
        state_manager=sm,
        current_model_getter=lambda: "0.6b",
    )
    with patch("src.ui.tray.pystray", None):
        # Should not raise exception
        tray.start(detached=True)
        tray.stop()
