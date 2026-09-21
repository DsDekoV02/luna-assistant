"""
Luna JARVIS - Tests for TTS Engine
Tests text-to-speech with caching and voice clone.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.tts import TTSEngine, AudioPlayer


@pytest.fixture
def mock_client():
    c = MagicMock()
    c.tts.return_value = b"RIFF" + b"\x00" * 200
    c.voice_clone.return_value = b"RIFF" + b"\x00" * 200
    return c


@pytest.fixture
def mock_cache():
    c = MagicMock()
    c.get.return_value = None  # Cache miss by default
    c.set.return_value = None
    return c


@pytest.fixture
def tts_engine(mock_client, mock_cache, sample_wav_file):
    return TTSEngine(mock_client, cache=mock_cache, voice_ref_path=sample_wav_file)


# ── Initialization ────────────────────────────────────────────────

class TestTTSEngineInit:
    def test_loads_voice_ref(self, tts_engine, sample_wav_file):
        assert tts_engine.voice_ref_b64 is not None
        assert len(tts_engine.voice_ref_b64) > 0

    def test_no_voice_ref(self, mock_client, mock_cache):
        engine = TTSEngine(mock_client, cache=mock_cache, voice_ref_path=None)
        assert engine.voice_ref_b64 is None

    def test_nonexistent_voice_ref(self, mock_client, mock_cache):
        engine = TTSEngine(mock_client, cache=mock_cache, voice_ref_path="/nonexistent/file.wav")
        assert engine.voice_ref_b64 is None


# ── Speak ─────────────────────────────────────────────────────────

class TestSpeak:
    def test_basic_speak(self, tts_engine, mock_client):
        result = tts_engine.speak("Hola mundo", use_clone=False, use_edge=False)
        assert result == b"RIFF" + b"\x00" * 200
        mock_client.tts.assert_called_once()

    def test_clone_speak(self, tts_engine, mock_client):
        result = tts_engine.speak("Hola mundo", use_clone=True, use_edge=False)
        assert result is not None
        mock_client.voice_clone.assert_called_once()

    def test_cache_miss_then_set(self, tts_engine, mock_cache, mock_client):
        mock_cache.get.return_value = None
        tts_engine.speak("Test", use_clone=False, use_edge=False)
        mock_cache.set.assert_called_once()

    def test_cache_hit(self, tts_engine, mock_cache, mock_client):
        cached_audio = b"CACHED_AUDIO"
        mock_cache.get.return_value = cached_audio
        result = tts_engine.speak("Test", use_clone=False, use_edge=False)
        assert result == cached_audio
        mock_client.tts.assert_not_called()

    def test_clone_fallback_to_standard(self, mock_client, mock_cache, sample_wav_file):
        mock_client.voice_clone.side_effect = Exception("Clone failed")
        mock_client.tts.return_value = b"FALLBACK_AUDIO"

        engine = TTSEngine(mock_client, cache=mock_cache, voice_ref_path=sample_wav_file)
        result = engine.speak("Test", use_clone=True, use_edge=False)
        assert result == b"FALLBACK_AUDIO"

    def test_cache_key_differs_by_mode(self, tts_engine):
        key1 = tts_engine._cache_key("hello", True)
        key2 = tts_engine._cache_key("hello", False)
        assert key1 != key2

    def test_cache_key_same_for_same_input(self, tts_engine):
        key1 = tts_engine._cache_key("hello", True)
        key2 = tts_engine._cache_key("hello", True)
        assert key1 == key2


# ── Audio Player ─────────────────────────────────────────────────

class TestAudioPlayer:
    def test_save_wav(self, tmp_dir, sample_wav_bytes):
        path = str(tmp_dir / "output.wav")
        AudioPlayer.save_wav(sample_wav_bytes, path)
        assert Path(path).exists()
        assert Path(path).read_bytes() == sample_wav_bytes

    def test_save_creates_parent_dirs(self, tmp_dir, sample_wav_bytes):
        path = str(tmp_dir / "subdir" / "deep" / "output.wav")
        AudioPlayer.save_wav(sample_wav_bytes, path)
        assert Path(path).exists()
