"""
Tests for the ASR (Automatic Speech Recognition) engine.
Tests MiMo API integration and Whisper fallback logic.

Session 42: Added tests for confidence scoring, detailed transcription,
and enhanced status reporting.
"""

import pytest
import tempfile
import wave
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from asr.engine import ASREngine, get_asr_engine


def _create_test_wav(path: str, duration_s: float = 1.0, sample_rate: int = 16000):
    """Create a simple WAV file for testing."""
    samples = int(sample_rate * duration_s)
    audio = np.random.randint(-1000, 1000, samples, dtype=np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


class TestASREngine:
    """Test ASR engine initialization and behavior."""

    def test_init(self):
        """Test ASR engine initialization."""
        client = MagicMock()
        engine = ASREngine(client, whisper_model="tiny")
        assert engine.client is client
        assert engine.whisper_model_name == "tiny"
        assert engine._whisper is None
        assert engine._whisper_loaded is False
        assert engine._api_available is True

    def test_transcribe_file_not_found(self):
        """Test transcription of non-existent file."""
        client = MagicMock()
        engine = ASREngine(client)
        result = engine.transcribe("/nonexistent/file.wav")
        assert result == ""

    def test_transcribe_api_success(self):
        """Test successful API transcription."""
        client = MagicMock()
        client.asr.return_value = "Hola, soy Luna"
        engine = ASREngine(client)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            result = engine.transcribe(f.name)

        assert result == "Hola, soy Luna"
        client.asr.assert_called_once()

    def test_transcribe_api_failure_whisper_fallback(self):
        """Test fallback to Whisper when API fails."""
        client = MagicMock()
        client.asr.side_effect = Exception("API error")
        engine = ASREngine(client)

        # Mock Whisper
        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = {"text": "whisper result"}
        engine._whisper = mock_whisper
        engine._whisper_loaded = True

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            result = engine.transcribe(f.name)

        assert result == "whisper result"
        assert engine._api_available is False

    def test_transcribe_api_empty_fallback(self):
        """Test fallback to Whisper when API returns empty."""
        client = MagicMock()
        client.asr.return_value = ""
        engine = ASREngine(client)

        # Mock Whisper
        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = {"text": "whisper fallback"}
        engine._whisper = mock_whisper
        engine._whisper_loaded = True

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            result = engine.transcribe(f.name)

        assert result == "whisper fallback"

    def test_transcribe_bytes(self):
        """Test transcription from audio bytes."""
        client = MagicMock()
        client.asr.return_value = "test transcription"
        engine = ASREngine(client)

        # Create WAV bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            with open(f.name, "rb") as rf:
                audio_bytes = rf.read()

        result = engine.transcribe_bytes(audio_bytes, format="wav")
        assert result == "test transcription"

    def test_transcribe_with_asr_respelling(self):
        """Test that ASR respelling is applied to transcriptions."""
        client = MagicMock()
        client.asr.return_value = "hola dekov, soy luna jarvis"
        engine = ASREngine(client)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            result = engine.transcribe(f.name)

        assert "Dekov" in result
        assert "Luna JARVIS" in result

    def test_get_status_api_available(self):
        """Test status when API is available."""
        client = MagicMock()
        engine = ASREngine(client)
        status = engine.get_status()
        assert status["api_available"] is True
        assert status["backend"] == "mimo-asr"

    def test_get_status_api_unavailable_whisper_loaded(self):
        """Test status when API is down but Whisper is loaded."""
        client = MagicMock()
        engine = ASREngine(client)
        engine._api_available = False
        engine._whisper = MagicMock()
        engine._whisper_loaded = True
        status = engine.get_status()
        assert status["api_available"] is False
        assert status["whisper_loaded"] is True
        assert status["backend"] == "whisper"

    def test_get_status_no_backend(self):
        """Test status when no backend is available."""
        client = MagicMock()
        engine = ASREngine(client)
        engine._api_available = False
        engine._whisper_loaded = True  # loaded but None
        engine._whisper = None
        status = engine.get_status()
        assert status["backend"] == "none"

    # ── Session 42: Confidence scoring tests ─────────────────────

    def test_transcribe_with_confidence_api(self):
        """Test confidence scoring from API transcription."""
        client = MagicMock()
        client.asr.return_value = "hola dekov, soy luna"
        engine = ASREngine(client)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            result = engine.transcribe_with_confidence(f.name)

        assert result["text"] == "hola Dekov, soy luna"
        assert result["confidence"] == 0.85  # API estimate
        assert result["backend"] == "mimo-asr"
        assert result["language"] == "es"
        assert result["error"] is None

    def test_transcribe_with_confidence_file_not_found(self):
        """Test confidence scoring with missing file."""
        client = MagicMock()
        engine = ASREngine(client)

        result = engine.transcribe_with_confidence("/nonexistent.wav")
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert result["backend"] == "none"
        assert result["error"] == "file_not_found"

    def test_transcribe_count_tracking(self):
        """Test that transcribe count is tracked."""
        client = MagicMock()
        client.asr.return_value = "test"
        engine = ASREngine(client)

        assert engine._transcribe_count == 0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name)
            engine.transcribe(f.name)
            engine.transcribe(f.name)

        assert engine._transcribe_count == 2
        assert engine._api_success_count == 2

    def test_status_includes_counts(self):
        """Test that status includes usage counts."""
        client = MagicMock()
        engine = ASREngine(client)
        status = engine.get_status()
        assert "transcribe_count" in status
        assert "error_count" in status
        assert "api_success_count" in status
        assert "whisper_success_count" in status
        assert "success_rate" in status


class TestASREngineSingleton:
    """Test the singleton getter."""

    def test_get_asr_engine_creates_instance(self):
        """Test that get_asr_engine creates a singleton."""
        # Reset singleton
        import asr.engine
        asr.engine._asr_engine = None

        client = MagicMock()
        engine = get_asr_engine(client, whisper_model="tiny")
        assert engine is not None
        assert engine.whisper_model_name == "tiny"

        # Same instance on second call
        engine2 = get_asr_engine()
        assert engine2 is engine

        # Reset for other tests
        asr.engine._asr_engine = None

    def test_get_asr_engine_requires_client_on_first_call(self):
        """Test that first call requires mimo_client."""
        import asr.engine
        asr.engine._asr_engine = None

        with pytest.raises(ValueError, match="mimo_client"):
            get_asr_engine()

        asr.engine._asr_engine = None
