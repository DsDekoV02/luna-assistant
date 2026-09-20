"""
Luna JARVIS - Tests for Audio Streaming Handler
Tests AudioStreamProcessor, TTSStreamer, and StreamingVoiceHandler.
"""

import pytest
import sys
import base64
import struct
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.streaming import (
    AudioStreamProcessor, TTSStreamer, StreamingVoiceHandler,
    get_streaming_handler,
)


# ── Helpers ──────────────────────────────────────────────────────

def make_wav_chunk(num_samples=1600, sample_rate=16000, amplitude=1000):
    """Create a WAV audio chunk with given amplitude."""
    import wave
    import io
    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    # Generate sine-ish wave
    import math
    samples = []
    for i in range(num_samples):
        val = int(amplitude * math.sin(2 * math.pi * 440 * i / sample_rate))
        samples.append(max(-32768, min(32767, val)))
    wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    wf.close()
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def make_silence_chunk(num_samples=1600, sample_rate=16000):
    """Create a silent WAV chunk."""
    return make_wav_chunk(num_samples, sample_rate, amplitude=0)


# ── AudioStreamProcessor ────────────────────────────────────────

class TestAudioStreamProcessor:
    def test_init(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        assert proc.sample_rate == 16000
        assert proc.is_recording is False
        assert len(proc.audio_buffer) == 0

    def test_process_chunk_speech_detected(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        proc.silence_threshold = 100  # Low threshold

        chunk = make_wav_chunk(amplitude=5000)
        result = proc.process_chunk(chunk, format="wav")
        assert result["status"] == "recording"
        assert result["speech"] is True

    def test_process_chunk_silence(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        # The chunk is a full WAV file; header bytes may have high values.
        # Send multiple silence chunks so silence_counter accumulates.
        proc.silence_threshold = 10000  # Very high threshold
        proc._speech_detected = True  # Simulate prior speech

        chunk = make_silence_chunk()
        result = proc.process_chunk(chunk, format="wav")
        assert result["status"] == "recording"
        assert result["speech"] is False

    def test_reset(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        proc.audio_buffer.extend(b"test data")
        proc._speech_detected = True
        proc._silence_counter = 5.0

        proc.reset()
        assert len(proc.audio_buffer) == 0
        assert proc._speech_detected is False
        assert proc._silence_counter == 0.0

    def test_force_finalize_empty(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        result = proc.force_finalize()
        assert result["status"] == "error"

    def test_non_wav_format(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        proc = AudioStreamProcessor(mock_client, mock_tts, mock_stt)
        chunk = base64.b64encode(b"\x00" * 100).decode()
        result = proc.process_chunk(chunk, format="webm")
        assert result["status"] == "buffering"


# ── TTSStreamer ──────────────────────────────────────────────────

class TestTTSStreamer:
    def test_init(self):
        mock_tts = MagicMock()
        streamer = TTSStreamer(mock_tts)
        assert streamer.tts is mock_tts

    def test_stream_tts_no_audio(self):
        mock_tts = MagicMock()
        mock_tts.speak.return_value = b""
        streamer = TTSStreamer(mock_tts)
        callback = AsyncMock()

        asyncio.run(streamer.stream_tts("test", callback))
        callback.assert_called()
        # Should send audio_error
        call_args = callback.call_args[0][0]
        assert call_args["type"] == "audio_error"

    def test_stream_tts_with_audio(self, sample_wav_bytes):
        mock_tts = MagicMock()
        mock_tts.speak.return_value = sample_wav_bytes
        streamer = TTSStreamer(mock_tts)
        callback = AsyncMock()

        asyncio.run(streamer.stream_tts("hola", callback))
        assert callback.call_count >= 2  # At least chunks + final


# ── StreamingVoiceHandler ───────────────────────────────────────

class TestStreamingVoiceHandler:
    def test_init(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        handler = StreamingVoiceHandler(mock_client, mock_tts, mock_stt)
        assert handler.audio_processor is not None
        assert handler.tts_streamer is not None

    def test_handle_audio_start(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        handler = StreamingVoiceHandler(mock_client, mock_tts, mock_stt)
        callback = AsyncMock()

        asyncio.run(handler.handle_audio_start(callback))
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["type"] == "status"
        assert call_args["state"] == "listening"

    def test_handle_audio_stop_empty(self):
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        handler = StreamingVoiceHandler(mock_client, mock_tts, mock_stt)
        callback = AsyncMock()

        asyncio.run(handler.handle_audio_stop(callback))
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["type"] == "error"

    def test_speak_response(self, sample_wav_bytes):
        mock_client = MagicMock()
        mock_tts = AsyncMock()
        mock_tts.speak.return_value = sample_wav_bytes
        mock_stt = MagicMock()
        handler = StreamingVoiceHandler(mock_client, mock_tts, mock_stt)
        callback = AsyncMock()

        asyncio.run(handler.speak_response("hola mundo", callback))
        # Should send status updates
        calls = [c[0][0] for c in callback.call_args_list]
        types = [c["type"] for c in calls]
        assert "status" in types
        assert "speaking" in [c.get("state") for c in calls]
        assert "ready" in [c.get("state") for c in calls]


# ── Singleton ────────────────────────────────────────────────────

class TestStreamingSingleton:
    def test_get_handler_requires_deps(self):
        import voice.streaming
        voice.streaming._streaming_handler = None
        with pytest.raises(ValueError):
            get_streaming_handler()

    def test_get_handler_returns_instance(self):
        import voice.streaming
        voice.streaming._streaming_handler = None
        mock_client = MagicMock()
        mock_tts = MagicMock()
        mock_stt = MagicMock()
        handler = get_streaming_handler(mock_client, mock_tts, mock_stt)
        assert isinstance(handler, StreamingVoiceHandler)
        voice.streaming._streaming_handler = None
