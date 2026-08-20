"""Unit tests for AppState and StateManager."""
from src.app.state import AppState, StateManager


def test_app_state_display_names() -> None:
    assert "閒置" in AppState.IDLE.display_name
    assert "錄音中" in AppState.RECORDING.display_name
    assert "辨識處理中" in AppState.PROCESSING.display_name
    assert "就緒" in AppState.READY.display_name
    assert "發生錯誤" in AppState.ERROR.display_name


def test_state_manager_initial_state() -> None:
    sm = StateManager()
    assert sm.state == AppState.READY
    assert sm.is_idle_or_ready is True
    assert sm.is_recording is False
    assert sm.is_processing is False
    assert sm.last_error is None


def test_state_manager_transitions() -> None:
    sm = StateManager()

    sm.set_state(AppState.RECORDING)
    assert sm.state == AppState.RECORDING
    assert sm.is_recording is True
    assert sm.is_idle_or_ready is False

    sm.set_state(AppState.PROCESSING)
    assert sm.state == AppState.PROCESSING
    assert sm.is_processing is True

    sm.set_state(AppState.ERROR, error_msg="Something went wrong")
    assert sm.state == AppState.ERROR
    assert sm.last_error == "Something went wrong"

    sm.reset_to_ready()
    assert sm.state == AppState.READY
    assert sm.last_error is None


def test_state_manager_subscription() -> None:
    sm = StateManager()
    history = []

    def observer(new_state: AppState, err: str | None) -> None:
        history.append((new_state, err))

    unsubscribe = sm.subscribe(observer)

    sm.set_state(AppState.RECORDING)
    sm.set_state(AppState.ERROR, "test error")

    assert len(history) == 2
    assert history[0] == (AppState.RECORDING, None)
    assert history[1] == (AppState.ERROR, "test error")

    # Unsubscribe
    unsubscribe()
    sm.set_state(AppState.READY)
    assert len(history) == 2


def test_state_manager_subscriber_exception_handled() -> None:
    sm = StateManager()

    def bad_subscriber(state: AppState, err: str | None) -> None:
        raise RuntimeError("Subscriber crashed")

    sm.subscribe(bad_subscriber)
    # Should not raise exception
    sm.set_state(AppState.RECORDING)
    assert sm.state == AppState.RECORDING
