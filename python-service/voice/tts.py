"""
Luna JARVIS - TTS Module
Text-to-Speech using MiMo TTS API and Microsoft Edge TTS.
"""

import io
import hashlib
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Callable, Awaitable
from voice.text_processor import optimize_for_voice_clone

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

logger = logging.getLogger("luna.voice.tts")


class TTSEngine:
    """Handles text-to-speech conversion with multiple backends.
    
    Supported backends (in priority order):
    1. Edge TTS (Microsoft) - High quality, free, many voices
    2. Voice Design (MiMo) - Custom voice from text description
    3. Voice Clone (MiMo) - Clones from reference audio
    4. Standard TTS (MiMo) - Basic TTS
    
    Voice Clone Quality Optimizer Settings (tested 2026-09-20):
    - Best reference: session23_voice_test_1.wav (4.5s clean clone)
    - Optimal text length: 9-19 words
    - Best punctuation: natural pauses with '...'
    - Best style: conversational/mixed
    
    Voice Design (tested 2026-09-20 session 27):
    - Model: mimo-v2.5-tts-voicedesign
    - Produces higher quality than voice clone
    - No reference audio needed — uses text description
    - Recommended for production use
    
    Edge TTS (added 2026-09-21 session 33):
    - Uses Microsoft Edge's online TTS service
    - High quality Spanish voices (es-MX-DaliaNeural default)
    - Free, no API key needed
    - Best option for production Spanish TTS
    """

    # Reference audio priority (best quality first)
    REFERENCE_PRIORITY = [
        "session23_voice_test_1.wav",  # Best quality (clean clone)
        "luna_voz_v5b_kohana_fina.wav",  # Original reference
        "luna_clone_v6_test1.wav",  # V6 test
    ]

    # Voice design descriptions for Luna
    VOICE_DESIGN_DESCRIPTIONS = {
        "anime_es": "Una chica anime española con voz suave y expresiva, ligeramente infantil pero inteligente",
        "joven_latina": "Una chica joven latinoamericana de voz dulce y cálida, como una asistente virtual amigable",
        "calm_assistant": "Una asistente virtual femenina de voz calmada, clara y profesional, con acento latino neutro",
    }

    # Available Edge TTS voices for Spanish
    EDGE_VOICES = {
        "es-MX-DaliaNeural": "Mujer joven mexicana, cálida y expresiva (default)",
        "es-MX-JorgeNeural": "Hombre mexicano, profesional y claro",
        "es-ES-ElviraNeural": "Mujer española, elegante y clara",
        "es-ES-AlvaroNeural": "Hombre español, profesional",
        "es-AR-ElenaNeural": "Mujer argentina, cercana y amigable",
        "es-CO-SalomeNeural": "Mujer colombiana, dulce y clara",
        "es-CL-CatalinaNeural": "Mujer chilena, natural y cercana",
    }

    def __init__(self, mimo_client, cache=None, voice_ref_path: Optional[str] = None,
                 voice_design_profile: str = "anime_es", default_tts: str = "edge",
                 edge_voice: str = "es-MX-DaliaNeural"):
        self.client = mimo_client
        self.cache = cache
        self.voice_ref_path = voice_ref_path
        self.voice_ref_b64: Optional[str] = None
        self.voice_design_profile = voice_design_profile
        self.default_tts = default_tts
        self.edge_voice = edge_voice
        self._load_voice_ref()
        if EDGE_TTS_AVAILABLE:
            logger.info(f"Edge TTS available, voice: {self.edge_voice}, default_tts: {self.default_tts}")
        else:
            logger.warning("Edge TTS not available, install with: pip install edge-tts")

    def _load_voice_ref(self):
        """Load reference voice for cloning."""
        if self.voice_ref_path and Path(self.voice_ref_path).exists():
            import base64
            with open(self.voice_ref_path, "rb") as f:
                self.voice_ref_b64 = base64.b64encode(f.read()).decode("utf-8")
            logger.info(f"Voice reference loaded: {self.voice_ref_path}")
        else:
            logger.warning("No voice reference file found. Voice clone unavailable.")

    def speak(self, text: str, use_clone: bool = True, use_design: bool = False,
              use_edge: Optional[bool] = None) -> bytes:
        """Convert text to speech. Returns WAV audio bytes.

        Args:
            text: Text to speak
            use_clone: If True, use voice clone; if False, use standard TTS
            use_design: If True, use voice design (overrides use_clone)
            use_edge: If True, use Edge TTS (overrides all). If None, uses self.default_tts.

        Returns:
            WAV audio bytes
        """
        # Determine if we should use Edge TTS
        if use_edge is None:
            use_edge = (self.default_tts == "edge" and EDGE_TTS_AVAILABLE)

        # Check cache first
        if self.cache:
            cache_key = self._cache_key(text, use_clone, use_design, use_edge)
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"TTS cache hit for: {text[:50]}...")
                return cached

        # Generate audio — priority: edge > design > clone > standard
        if use_edge and EDGE_TTS_AVAILABLE:
            audio = self._edge_speak(text)
        elif use_design:
            audio = self._design_speak(text)
        elif use_clone and self.voice_ref_b64:
            audio = self._clone_speak(text)
        else:
            audio = self._standard_speak(text)

        # Cache the result
        if self.cache and audio:
            self.cache.set(cache_key, audio, ttl=86400)  # 24h cache

        return audio

    def _edge_speak(self, text: str) -> bytes:
        """TTS using Microsoft Edge TTS (high quality, free)."""
        try:
            # Try to use existing event loop if running
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, use run_in_executor pattern
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._edge_speak_async(text))
                    return future.result(timeout=30)
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                return asyncio.run(self._edge_speak_async(text))
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            logger.info("Falling back to standard TTS")
            return self._standard_speak(text)

    async def _edge_speak_async(self, text: str) -> bytes:
        """Async Edge TTS implementation."""
        communicate = edge_tts.Communicate(text, self.edge_voice)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        if not audio_data:
            raise ValueError("Edge TTS produced no audio")
        return bytes(audio_data)

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

    def _design_speak(self, text: str) -> bytes:
        """TTS with voice design — generates a custom voice from description."""
        try:
            description = self.VOICE_DESIGN_DESCRIPTIONS.get(
                self.voice_design_profile,
                self.VOICE_DESIGN_DESCRIPTIONS["anime_es"]
            )
            return self.client.voice_design(description, text)
        except Exception as e:
            logger.error(f"Voice design TTS error: {e}")
            logger.info("Falling back to standard TTS")
            return self._standard_speak(text)

    async def speak_async(
        self,
        text: str,
        on_complete: Optional[Callable[[bytes], Awaitable[None]]] = None,
        use_clone: bool = True,
        use_design: bool = False,
        use_edge: Optional[bool] = None,
    ) -> bytes:
        """Generate TTS asynchronously using a thread pool.

        Runs the blocking TTS call in a thread so the event loop
        stays free for streaming text chunks to the client.

        Args:
            text: Text to speak
            on_complete: Optional async callback(audio_bytes) when done
            use_clone: Use voice clone
            use_design: Use voice design (overrides use_clone)
            use_edge: Use Edge TTS (overrides all). None = use config default.

        Returns:
            WAV audio bytes (empty on failure)
        """
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, self.speak, text, use_clone, use_design, use_edge)
        if on_complete and audio:
            await on_complete(audio)
        return audio

    def _cache_key(self, text: str, use_clone: bool, use_design: bool = False,
                   use_edge: bool = False) -> str:
        """Generate cache key for TTS."""
        if use_edge:
            mode = f"edge:{self.edge_voice}"
        elif use_design:
            mode = f"design:{self.voice_design_profile}"
        elif use_clone:
            mode = "clone"
        else:
            mode = "standard"
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
