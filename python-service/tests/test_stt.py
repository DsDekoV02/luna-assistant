"""
Luna JARVIS - Tests for STT Engine
Tests speech-to-text transcription.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.stt import STTEngine


@pytest.fixture
def mock_client():
    c = MagicMock()
    c.asr.return_value = "hola mundo de prueba"
    return c


@pytest.fixture
def stt_engine(mock_client):
    return STTEngine(mock_client, sample_rate=16000)


# ── Initialization ────────────────────────────────────────────────

class TestSTTEngineInit:
    def test_default_sample_rate(self, mock_client):
        engine = STTEngine(mock_client)
        assert engine.sample_rate == 16000

    def test_custom_sample_rate(self, mock_client):
        engine = STTEngine(mock_client, sample_rate=44100)
        assert engine.sample_rate == 44100

    def test_initial_state(self, stt_engine):
        assert stt_engine.is_listening is False


# ── Transcribe File ──────────────────────────────────────────────

class TestTranscribeFile:
    def test_transcribes_file(self, stt_engine, mock_client, sample_wav_file):
        result = stt_engine.transcribe_file(sample_wav_file)
        assert result == "hola mundo de prueba"
        mock_client.asr.assert_called_once_with(sample_wav_file)

    def test_nonexistent_file(self, stt_engine):
        result = stt_engine.transcribe_file("/nonexistent/file.wav")
        assert result == ""

    def test_strips_whitespace(self, stt_engine, mock_client, sample_wav_file):
        mock_client.asr.return_value = "  hola mundo  "
        result = stt_engine.transcribe_file(sample_wav_file)
        assert result == "hola mundo"

    def test_api_error_returns_empty(self, stt_engine, mock_client, sample_wav_file):
        mock_client.asr.side_effect = Exception("API error")
        result = stt_engine.transcribe_file(sample_wav_file)
        assert result == ""


# ── Transcribe Bytes ─────────────────────────────────────────────

class TestTranscribeBytes:
    def test_transcribes_bytes(self, stt_engine, mock_client, sample_wav_bytes):
        result = stt_engine.transcribe_bytes(sample_wav_bytes, format="wav")
        assert result == "hola mundo de prueba"

    def test_creates_temp_file(self, stt_engine, mock_client, sample_wav_bytes):
        """Should create a temp file and clean it up."""
        stt_engine.transcribe_bytes(sample_wav_bytes)
        # The temp file should be cleaned up after
        mock_client.asr.assert_called_once()

    def test_empty_bytes(self, stt_engine, mock_client):
        mock_client.asr.return_value = ""
        result = stt_engine.transcribe_bytes(b"")
        assert result == ""


# ── Stop Listening ────────────────────────────────────────────────

class TestStopListening:
    def test_stop_sets_flag(self, stt_engine):
        stt_engine.is_listening = True
        stt_engine.stop_listening()
        assert stt_engine.is_listening is False
