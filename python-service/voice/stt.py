"""
Luna JARVIS - STT Module
Speech-to-Text using MiMo ASR API with voice activity detection.
"""

import io
import logging
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, Callable

from voice.text_processor import fix_asr_names

logger = logging.getLogger("luna.voice.stt")


class STTEngine:
    """Handles speech-to-text conversion using MiMo ASR."""

    def __init__(self, mimo_client, sample_rate: int = 16000):
        self.client = mimo_client
        self.sample_rate = sample_rate
        self.is_listening = False

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)

        Returns:
            Transcribed text
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return ""

        try:
            text = self.client.asr(audio_path)
            # Fix common ASR misrecognitions (proper nouns, etc.)
            text = fix_asr_names(text)
            logger.info(f"Transcribed: {text[:100]}...")
            return text.strip()
        except Exception as e:
            logger.error(f"ASR error: {e}")
            return ""

    def transcribe_bytes(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio bytes
            format: Audio format (wav, mp3, etc.)

        Returns:
            Transcribed text
        """
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            return self.transcribe_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def record_and_transcribe(
        self,
        duration: Optional[float] = None,
        silence_threshold: float = 300,
        silence_duration: float = 1.5,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable] = None
    ) -> str:
        """Record audio from microphone and transcribe.

        Args:
            duration: Fixed recording duration in seconds (None = auto-detect)
            silence_threshold: RMS threshold for silence detection
            silence_duration: Seconds of silence before stopping
            on_speech_start: Callback when speech is detected
            on_speech_end: Callback when speech ends

        Returns:
            Transcribed text
        """
        try:
            import pyaudio
            import wave
        except ImportError:
            logger.error("pyaudio not installed - cannot record audio")
            return ""

        frames = []
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024
        )

        logger.info("Recording...")
        self.is_listening = True
        silence_counter = 0
        speech_detected = False

        try:
            while self.is_listening:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)

                # Calculate RMS
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))

                if rms > silence_threshold:
                    silence_counter = 0
                    if not speech_detected:
                        speech_detected = True
                        if on_speech_start:
                            on_speech_start()
                else:
                    silence_counter += len(data) / (self.sample_rate * 2)  # 2 bytes per sample

                # Stop conditions
                if duration:
                    total_frames = len(frames) * 1024 / self.sample_rate
                    if total_frames >= duration:
                        break
                elif speech_detected and silence_counter >= silence_duration:
                    break

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            self.is_listening = False

        if on_speech_end:
            on_speech_end()

        if not frames:
            return ""

        # Save to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(frames))
            wf.close()
            temp_path = f.name

        try:
            return self.transcribe_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def stop_listening(self):
        """Stop an active recording."""
        self.is_listening = False
