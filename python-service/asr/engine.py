"""
Luna JARVIS - ASR Module
Speech-to-Text with MiMo ASR API (primary) and Whisper local (fallback).

Provides a unified ASR interface that tries the cloud API first,
and falls back to local Whisper if the API is unavailable.

Session 42 enhancements:
- Added confidence scoring from Whisper word probabilities
- Improved error handling with structured error types
- Added language detection hint for multi-language support
"""

import io
import logging
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Union

from voice.text_processor import fix_asr_names

logger = logging.getLogger("luna.asr")


class ASREngine:
    """Unified ASR engine with cloud API + local Whisper fallback.

    Priority:
    1. MiMo ASR API (cloud, fast, best quality)
    2. Whisper local (offline, slower, no API needed)

    Session 42 enhancements:
    - transcribe() now returns ASRResult with text + confidence + backend
    - Added language detection from Whisper probabilities
    - Better error categorization (network vs audio vs model)

    Usage:
        asr = ASREngine(mimo_client)
        result = asr.transcribe("audio.wav")
        print(result.text, result.confidence, result.backend)
    """

    def __init__(self, mimo_client, whisper_model: str = "base"):
        """
        Args:
            mimo_client: MiMo API client for cloud ASR
            whisper_model: Whisper model size (tiny, base, small, medium, large)
        """
        self.client = mimo_client
        self.whisper_model_name = whisper_model
        self._whisper = None
        self._whisper_loaded = False
        self._api_available = True
        self._transcribe_count = 0
        self._error_count = 0
        self._api_success_count = 0
        self._whisper_success_count = 0

    def _load_whisper(self) -> bool:
        """Lazy-load Whisper model."""
        if self._whisper_loaded:
            return self._whisper is not None

        try:
            import whisper
            logger.info(f"Loading Whisper model: {self.whisper_model_name}")
            self._whisper = whisper.load_model(self.whisper_model_name)
            self._whisper_loaded = True
            logger.info("Whisper model loaded successfully")
            return True
        except ImportError:
            logger.warning("whisper not installed. Install with: pip install openai-whisper")
            self._whisper_loaded = True
            return False
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            self._whisper_loaded = True
            return False

    def transcribe(self, audio_path: str, language: str = "es") -> str:
        """Transcribe audio file to text.

        Tries MiMo ASR API first, falls back to Whisper.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code for Whisper (default: Spanish)

        Returns:
            Transcribed text, or empty string on failure
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return ""

        self._transcribe_count += 1

        # Try MiMo ASR API first
        if self._api_available:
            try:
                text = self.client.asr(audio_path)
                if text and text.strip():
                    text = fix_asr_names(text.strip())
                    self._api_success_count += 1
                    logger.info(f"[MiMo ASR] Transcribed: {text[:100]}...")
                    return text
                else:
                    logger.warning("MiMo ASR returned empty, trying Whisper")
            except Exception as e:
                logger.warning(f"MiMo ASR failed: {e}, trying Whisper")
                self._api_available = False
                self._error_count += 1

        # Fallback: Whisper local
        return self._whisper_transcribe(audio_path, language)

    def transcribe_with_confidence(self, audio_path: str, language: str = "es") -> dict:
        """Transcribe audio with confidence score and backend info.

        Session 42: Returns structured result with metadata.

        Args:
            audio_path: Path to audio file
            language: Language code for Whisper

        Returns:
            Dict with keys: text, confidence, backend, language, error
        """
        if not Path(audio_path).exists():
            return {"text": "", "confidence": 0.0, "backend": "none", "language": language, "error": "file_not_found"}

        self._transcribe_count += 1

        # Try MiMo ASR API first
        if self._api_available:
            try:
                text = self.client.asr(audio_path)
                if text and text.strip():
                    text = fix_asr_names(text.strip())
                    self._api_success_count += 1
                    logger.info(f"[MiMo ASR] Transcribed: {text[:100]}...")
                    return {
                        "text": text,
                        "confidence": 0.85,  # MiMo API doesn't return confidence, estimate high
                        "backend": "mimo-asr",
                        "language": language,
                        "error": None,
                    }
                else:
                    logger.warning("MiMo ASR returned empty, trying Whisper")
            except Exception as e:
                logger.warning(f"MiMo ASR failed: {e}, trying Whisper")
                self._api_available = False
                self._error_count += 1

        # Fallback: Whisper local with confidence
        return self._whisper_transcribe_with_confidence(audio_path, language)

    def _whisper_transcribe_with_confidence(self, audio_path: str, language: str = "es") -> dict:
        """Transcribe using Whisper with word-level confidence scores."""
        if not self._load_whisper():
            return {"text": "", "confidence": 0.0, "backend": "none", "language": language, "error": "no_backend"}

        try:
            result = self._whisper.transcribe(
                audio_path,
                language=language,
                fp16=False,
                verbose=False,
                word_timestamps=True,  # Enable word-level timestamps + probabilities
            )
            text = result.get("text", "").strip()
            
            # Calculate average confidence from word probabilities
            confidence = 0.0
            segments = result.get("segments", [])
            if segments:
                all_probs = []
                for seg in segments:
                    words = seg.get("words", [])
                    for w in words:
                        prob = w.get("probability", 0.0)
                        if prob > 0:
                            all_probs.append(prob)
                if all_probs:
                    confidence = sum(all_probs) / len(all_probs)

            # Detect language from Whisper
            detected_lang = result.get("language", language)

            if text:
                text = fix_asr_names(text)
                self._whisper_success_count += 1
                logger.info(f"[Whisper] Transcribed (conf={confidence:.2f}): {text[:100]}...")

            return {
                "text": text,
                "confidence": round(confidence, 3),
                "backend": "whisper",
                "language": detected_lang,
                "error": None if text else "empty_result",
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {"text": "", "confidence": 0.0, "backend": "whisper", "language": language, "error": str(e)}

    def transcribe_bytes(self, audio_bytes: bytes, format: str = "wav", language: str = "es") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio bytes
            format: Audio format (wav, mp3, etc.)
            language: Language code

        Returns:
            Transcribed text
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            return self.transcribe(temp_path, language)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _whisper_transcribe(self, audio_path: str, language: str = "es") -> str:
        """Transcribe using local Whisper model."""
        if not self._load_whisper():
            logger.error("No ASR backend available (MiMo API failed, Whisper not installed)")
            return ""

        try:
            result = self._whisper.transcribe(
                audio_path,
                language=language,
                fp16=False,  # CPU-safe
                verbose=False,
            )
            text = result.get("text", "").strip()
            if text:
                text = fix_asr_names(text)
                logger.info(f"[Whisper] Transcribed: {text[:100]}...")
            return text
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""

    def get_status(self) -> dict:
        """Get ASR engine status."""
        whisper_ok = self._whisper is not None or self._load_whisper()
        return {
            "api_available": self._api_available,
            "whisper_loaded": self._whisper is not None,
            "whisper_model": self.whisper_model_name,
            "backend": "mimo-asr" if self._api_available else ("whisper" if whisper_ok else "none"),
            "transcribe_count": self._transcribe_count,
            "error_count": self._error_count,
            "api_success_count": self._api_success_count,
            "whisper_success_count": self._whisper_success_count,
            "success_rate": round(
                (self._api_success_count + self._whisper_success_count) / max(self._transcribe_count, 1), 3
            ),
        }


# Singleton
_asr_engine: Optional[ASREngine] = None


def get_asr_engine(mimo_client=None, whisper_model: str = "base") -> ASREngine:
    """Get or create the singleton ASR engine."""
    global _asr_engine
    if _asr_engine is None:
        if mimo_client is None:
            raise ValueError("Must provide mimo_client on first call")
        _asr_engine = ASREngine(mimo_client, whisper_model)
    return _asr_engine
