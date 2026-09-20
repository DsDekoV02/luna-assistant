"""
Luna JARVIS - WebSocket Audio Streaming Handler
Enables real-time bidirectional audio streaming between Electron and Python service.

Features:
- Chunked audio recording and streaming from client
- Real-time transcription as audio arrives
- TTS streaming back to client
- Voice Activity Detection (VAD) for automatic stop

Usage:
  Import and use in main.py WebSocket handler
"""

import io
import json
import wave
import logging
import asyncio
import numpy as np
from typing import Optional, Callable, Dict, Any
from pathlib import Path

logger = logging.getLogger("luna.voice.streaming")


class AudioStreamProcessor:
    """Processes incoming audio chunks and manages TTS output streaming."""

    def __init__(self, mimo_client, tts_engine, stt_engine, sample_rate: int = 16000):
        self.client = mimo_client
        self.tts = tts_engine
        self.stt = stt_engine
        self.sample_rate = sample_rate
        self.is_recording = False
        self.audio_buffer = bytearray()
        self.silence_threshold = 300
        self.silence_duration = 1.5  # seconds
        self._silence_counter = 0.0
        self._speech_detected = False

    def process_chunk(self, audio_chunk_b64: str, format: str = "wav") -> Dict[str, Any]:
        """Process an incoming audio chunk.
        
        Args:
            audio_chunk_b64: Base64-encoded audio chunk
            format: Audio format (wav, webm, etc.)
            
        Returns:
            Dict with status info (transcript if complete, etc.)
        """
        import base64
        chunk_bytes = base64.b64decode(audio_chunk_b64)
        self.audio_buffer.extend(chunk_bytes)
        
        # Check for voice activity
        if format == "wav":
            try:
                audio_data = np.frombuffer(chunk_bytes, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
                
                if rms > self.silence_threshold:
                    self._silence_counter = 0
                    self._speech_detected = True
                    return {"status": "recording", "speech": True}
                else:
                    chunk_duration = len(audio_data) / self.sample_rate
                    self._silence_counter += chunk_duration
                    
                    if self._speech_detected and self._silence_counter >= self.silence_duration:
                        # Silence detected after speech - process the buffer
                        return self._finalize_recording()
                    
                    return {"status": "recording", "speech": False}
            except Exception as e:
                logger.debug(f"VAD error: {e}")
                return {"status": "recording", "speech": None}
        
        return {"status": "buffering"}

    def _finalize_recording(self) -> Dict[str, Any]:
        """Finalize recording and transcribe."""
        if not self.audio_buffer:
            return {"status": "error", "message": "No audio data"}
        
        # Save buffer to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(bytes(self.audio_buffer))
            wf.close()
            temp_path = f.name
        
        try:
            transcript = self.stt.transcribe_file(temp_path)
            self.reset()
            return {
                "status": "complete",
                "transcript": transcript,
                "duration_s": len(self.audio_buffer) / (self.sample_rate * 2)
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.reset()
            return {"status": "error", "message": str(e)}
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def reset(self):
        """Reset the audio buffer and state."""
        self.audio_buffer = bytearray()
        self._silence_counter = 0.0
        self._speech_detected = False

    def force_finalize(self) -> Dict[str, Any]:
        """Force finalize recording (e.g., when user stops manually)."""
        if not self.audio_buffer:
            return {"status": "error", "message": "No audio data"}
        return self._finalize_recording()


class TTSStreamer:
    """Streams TTS audio back to the client in chunks."""

    def __init__(self, tts_engine):
        self.tts = tts_engine

    async def stream_tts(
        self,
        text: str,
        send_callback: Callable,
        chunk_size_ms: int = 500
    ):
        """Generate TTS and stream chunks to client.
        
        Args:
            text: Text to speak
            send_callback: Async function to send audio chunks
            chunk_size_ms: Size of each audio chunk in milliseconds
        """
        try:
            # Generate full audio
            audio_bytes = self.tts.speak(text)
            if not audio_bytes:
                await send_callback({
                    "type": "audio_error",
                    "message": "TTS generation failed"
                })
                return
            
            import base64
            
            # Parse WAV to get audio data
            wf = wave.open(io.BytesIO(audio_bytes), "rb")
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            channels = wf.getnchannels()
            
            chunk_samples = int(sample_rate * chunk_size_ms / 1000)
            chunk_bytes_size = chunk_samples * sample_width * channels
            
            # Send in chunks
            total_frames = wf.getnframes()
            frames_sent = 0
            
            while frames_sent < total_frames:
                frames_to_read = min(chunk_samples, total_frames - frames_sent)
                data = wf.readframes(frames_to_read)
                
                if not data:
                    break
                
                chunk_b64 = base64.b64encode(data).decode("utf-8")
                await send_callback({
                    "type": "audio_chunk",
                    "data": chunk_b64,
                    "format": "wav",
                    "sample_rate": sample_rate,
                    "chunk_index": frames_sent // chunk_samples,
                    "is_final": (frames_sent + frames_to_read) >= total_frames
                })
                
                frames_sent += frames_to_read
                await asyncio.sleep(0.05)  # Small delay between chunks
            
            wf.close()
            
            # Also send the complete audio for fallback playback
            await send_callback({
                "type": "audio",
                "data": base64.b64encode(audio_bytes).decode("utf-8"),
                "format": "wav",
                "size": len(audio_bytes)
            })
            
        except Exception as e:
            logger.error(f"TTS streaming error: {e}")
            await send_callback({
                "type": "audio_error",
                "message": str(e)
            })


class StreamingVoiceHandler:
    """Main handler for streaming voice interactions.
    
    Combines audio stream processing and TTS streaming for
    real-time voice conversations with Luna.
    """

    def __init__(self, mimo_client, tts_engine, stt_engine):
        self.audio_processor = AudioStreamProcessor(mimo_client, tts_engine, stt_engine)
        self.tts_streamer = TTSStreamer(tts_engine)
        self.client = mimo_client
        self.tts_engine = tts_engine

    async def handle_audio_start(self, send_callback: Callable):
        """Handle start of audio recording."""
        self.audio_processor.reset()
        await send_callback({
            "type": "status",
            "state": "listening"
        })

    async def handle_audio_chunk(
        self,
        audio_data_b64: str,
        format: str,
        send_callback: Callable,
        on_transcript: Optional[Callable] = None
    ):
        """Handle incoming audio chunk.
        
        Args:
            audio_data_b64: Base64 audio chunk
            format: Audio format
            send_callback: Async function to send responses
            on_transcript: Optional callback when transcript is ready
        """
        result = self.audio_processor.process_chunk(audio_data_b64, format)
        
        if result["status"] == "recording":
            await send_callback({
                "type": "status",
                "state": "listening",
                "speech": result.get("speech")
            })
        
        elif result["status"] == "complete":
            transcript = result["transcript"]
            await send_callback({
                "type": "transcript",
                "content": transcript,
                "duration_s": result.get("duration_s", 0)
            })
            
            if on_transcript:
                await on_transcript(transcript)
        
        elif result["status"] == "error":
            await send_callback({
                "type": "error",
                "message": result.get("message", "Audio processing failed")
            })

    async def handle_audio_stop(self, send_callback: Callable, on_transcript: Optional[Callable] = None):
        """Handle manual stop of audio recording."""
        result = self.audio_processor.force_finalize()
        
        if result["status"] == "complete":
            transcript = result["transcript"]
            await send_callback({
                "type": "transcript",
                "content": transcript,
                "duration_s": result.get("duration_s", 0)
            })
            
            if on_transcript:
                await on_transcript(transcript)
        
        elif result["status"] == "error":
            await send_callback({
                "type": "error",
                "message": result.get("message", "No audio recorded")
            })

    async def speak_response(self, text: str, send_callback: Callable):
        """Generate and stream TTS response asynchronously."""
        await send_callback({
            "type": "status",
            "state": "speaking"
        })

        # Use async TTS to avoid blocking the event loop
        await self.tts_engine.speak_async(text)

        await send_callback({
            "type": "status",
            "state": "ready"
        })


# Singleton
_streaming_handler: Optional[StreamingVoiceHandler] = None


def get_streaming_handler(mimo_client=None, tts_engine=None, stt_engine=None) -> StreamingVoiceHandler:
    """Get or create the singleton streaming handler."""
    global _streaming_handler
    if _streaming_handler is None:
        if mimo_client is None or tts_engine is None or stt_engine is None:
            raise ValueError("Must provide all dependencies on first call")
        _streaming_handler = StreamingVoiceHandler(mimo_client, tts_engine, stt_engine)
    return _streaming_handler
