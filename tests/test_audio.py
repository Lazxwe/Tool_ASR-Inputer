"""Unit tests for the audio recording module."""
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from src.audio.recorder import AudioRecorder, AudioRecorderError, MicrophoneUnavailableError


def test_audio_recorder_init():
    recorder = AudioRecorder(sample_rate=16000, channels=1, dtype="float32")
    assert recorder.sample_rate == 16000
    assert recorder.channels == 1
    assert recorder.dtype == "float32"
    assert not recorder.is_recording


@patch("src.audio.recorder.sd")
def test_audio_recorder_start_and_stop(mock_sd):
    mock_sd.query_devices.return_value = {"name": "Test Built-in Microphone", "max_input_channels": 2}
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream

    recorder = AudioRecorder(sample_rate=16000, channels=1)
    recorder.start()

    assert recorder.is_recording
    mock_sd.query_devices.assert_called_once_with(None, kind="input")
    mock_sd.InputStream.assert_called_once()
    mock_stream.start.assert_called_once()

    # Simulate audio callback
    chunk1 = np.ones((800, 1), dtype=np.float32) * 0.5
    chunk2 = np.ones((800, 1), dtype=np.float32) * 0.2
    recorder._audio_callback(chunk1, 800, {}, None)
    recorder._audio_callback(chunk2, 800, {}, "input_overflow")

    audio = recorder.stop()

    assert not recorder.is_recording
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
    assert isinstance(audio, np.ndarray)
    assert audio.ndim == 1
    assert len(audio) == 1600
    assert audio.dtype == np.float32


@patch("src.audio.recorder.sd")
def test_audio_recorder_multi_channel_to_mono(mock_sd):
    mock_sd.query_devices.return_value = {"name": "Stereo Mic", "max_input_channels": 2}
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream

    recorder = AudioRecorder(sample_rate=16000, channels=2)
    recorder.start()

    # Stereo chunk: channel 1 = 1.0, channel 2 = 0.0 -> average should be 0.5
    stereo_chunk = np.zeros((100, 2), dtype=np.float32)
    stereo_chunk[:, 0] = 1.0
    recorder._audio_callback(stereo_chunk, 100, {}, None)

    audio = recorder.stop()
    assert audio.shape == (100,)
    assert np.allclose(audio, 0.5)


def test_audio_recorder_stop_without_start():
    recorder = AudioRecorder()
    audio = recorder.stop()
    assert isinstance(audio, np.ndarray)
    assert len(audio) == 0


@patch("src.audio.recorder.sd")
def test_audio_recorder_start_already_recording(mock_sd):
    mock_sd.query_devices.return_value = {"name": "Mic"}
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream

    recorder = AudioRecorder()
    recorder.start()
    assert recorder.is_recording

    # Calling start again should be a no-op
    recorder.start()
    assert mock_sd.InputStream.call_count == 1
    recorder.stop()


@patch("src.audio.recorder.sd")
def test_audio_recorder_query_device_failure(mock_sd):
    mock_sd.query_devices.side_effect = Exception("No input device available")

    recorder = AudioRecorder()
    with pytest.raises(MicrophoneUnavailableError, match="No available microphone found"):
        recorder.start()
    assert not recorder.is_recording


@patch("src.audio.recorder.sd")
def test_audio_recorder_stream_open_failure(mock_sd):
    mock_sd.query_devices.return_value = {"name": "Mic"}
    mock_sd.InputStream.side_effect = Exception("PortAudio error")

    recorder = AudioRecorder()
    with pytest.raises(AudioRecorderError, match="Could not open audio stream"):
        recorder.start()
    assert not recorder.is_recording


@patch("src.audio.recorder.sd", None)
def test_audio_recorder_sd_is_none():
    recorder = AudioRecorder()
    with pytest.raises(MicrophoneUnavailableError, match="sounddevice library is not available"):
        recorder.start()


@patch("src.audio.recorder.sd")
def test_audio_recorder_stream_close_exception_handled(mock_sd):
    mock_sd.query_devices.return_value = {"name": "Mic"}
    mock_stream = MagicMock()
    mock_stream.close.side_effect = Exception("Error closing")
    mock_sd.InputStream.return_value = mock_stream

    recorder = AudioRecorder()
    recorder.start()
    recorder._audio_callback(np.ones((100, 1), dtype=np.float32), 100, {}, None)
    # Should not raise exception
    audio = recorder.stop()
    assert len(audio) == 100
