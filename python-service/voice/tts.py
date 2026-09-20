"""
Luna JARVIS - TTS Module
Text-to-Speech using MiMo TTS API with caching support.
"""

import io
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable
from voice.text_processor import optimize_for_voice_clone

logger = logging.getLogger("luna.voice.tts")


class TTSEngine:
    """Handles text-to-speech conversion using MiMo TTS.
    
    Voice Clone Quality Optimizer Settings (tested 2026-09-20):
    - Best reference: session23_voice_test_1.wav (4.5s clean clone)
    - Optimal text length: 9-19 words
    - Best punctuation: natural pauses with '...'
    - Best style: conversational/mixed
    """

    # Reference audio priority (best quality first)
    REFERENCE_PRIORITY = [
        "session23_voice_test_1.wav",  # Best quality (clean clone)
        "luna_voz_v5b_kohana_fina.wav",  # Original reference
        "luna_clone_v6_test1.wav",  # V6 test
    ]

    def __init__(self, mimo_client, cache=None, voice_ref_path: Optional[str] = None):
        self.client = mimo_client
        self.cache = cache
        self.voice_ref_path = voice_ref_path
        self.voice_ref_b64: Optional[str] = None
        self._load_voice_ref()

    def _load_voice_ref(self):
        """Load reference voice for cloning."""
        if self.voice_ref_path and Path(self.voice_ref_path).exists():
            import base64
            with open(self.voice_ref_path, "rb") as f:
                self.voice_ref_b64 = base64.b64encode(f.read()).decode("utf-8")
            logger.info(f"Voice reference loaded: {self.voice_ref_path}")
        else:
            logger.warning("No voice reference file found. Voice clone unavailable.")

    def speak(self, text: str, use_clone: bool = True) -> bytes:
        """Convert text to speech. Returns WAV audio bytes.

        Args:
            text: Text to speak
            use_clone: If True, use voice clone; if False, use standard TTS

        Returns:
            WAV audio bytes
        """
        # Check cache first
        if self.cache:
            cache_key = self._cache_key(text, use_clone)
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"TTS cache hit for: {text[:50]}...")
                return cached

        # Generate audio
        if use_clone and self.voice_ref_b64:
            audio = self._clone_speak(text)
        else:
            audio = self._standard_speak(text)

        # Cache the result
        if self.cache and audio:
            self.cache.set(cache_key, audio, ttl=86400)  # 24h cache

        return audio

    def _standard_speak(self, text: str) -> bytes:
        """Standard TTS without voice cloning."""
        try:
            return self.client.tts(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""

    def _clone_speak(self, text: str) -> bytes:
        """TTS with voice cloning. V5 pipeline with prosody and emphasis."""
        try:
            # V5: Optimize text with emphasis, prosody, and natural phrases
            optimized = optimize_for_voice_clone(text)
            if optimized != text:
                logger.debug(f"V5 optimized: {text[:50]}... -> {optimized[:50]}...")
            return self.client.voice_clone(optimized, self.voice_ref_path)
        except Exception as e:
            logger.error(f"Voice clone TTS error: {e}")
            logger.info("Falling back to standard TTS")
            return self._standard_speak(text)

    async def speak_async(
        self,
        text: str,
        on_complete: Optional[Callable[[bytes], Awaitable[None]]] = None,
        use_clone: bool = True,
    ) -> bytes:
        """Generate TTS asynchronously using a thread pool.

        Runs the blocking TTS call in a thread so the event loop
        stays free for streaming text chunks to the client.

        Args:
            text: Text to speak
            on_complete: Optional async callback(audio_bytes) when done
            use_clone: Use voice clone

        Returns:
            WAV audio bytes (empty on failure)
"""
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, self.speak, text, use_clone)
        if on_complete and audio:
            await on_complete(audio)
        return audio

    def _cache_key(self, text: str, use_clone: bool) -> str:
        """Generate cache key for TTS."""
        mode = "clone" if use_clone else "standard"
        return f"tts:{mode}:{hashlib.md5(text.encode()).hexdigest()}"


class AudioPlayer:
    """Plays audio bytes through the system audio output."""

    @staticmethod
    def play_wav(audio_bytes: bytes):
        """Play WAV audio bytes."""
        try:
            import pyaudio
            import wave

            wf = wave.open(io.BytesIO(audio_bytes), "rb")
            p = pyaudio.PyAudio()

            stream = p.open(
                format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )

            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)

            stream.stop_stream()
            stream.close()
            p.terminate()
        except ImportError:
            logger.error("pyaudio not installed - cannot play audio")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    @staticmethod
    def save_wav(audio_bytes: bytes, path: str):
        """Save WAV audio bytes to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"Audio saved: {path}")
