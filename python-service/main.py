"""
Luna JARVIS - Main Server
FastAPI + WebSocket server for the Luna JARVIS assistant.
"""

import os
import sys
import json
import yaml
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from brain.mimo_client import MiMoClient, get_client, LUNA_SYSTEM_PROMPT
from brain.emotion import get_emotion_detector, EmotionDetector, get_response_style
from voice.tts import TTSEngine
from voice.stt import STTEngine
from voice.streaming import get_streaming_handler, StreamingVoiceHandler
from asr.engine import get_asr_engine, ASREngine
from tools.allowlist import get_allowlist, CommandAllowlist
from tools.reminder_store import get_reminder_store
from tools.security import check_injection, sanitize_input, validate_command
from memory.cache import get_cache, DiskCache
from memory.rag import get_rag, RAGEngine
from memory.rag_semantic import get_semantic_rag, SemanticRAGEngine
from memory.conversation import get_conversation_memory, ConversationMemory
from modes.manager import get_mode_manager, ModeManager
from proactive.engine import get_proactive_engine, ProactiveEngine
from learning.patterns import get_pattern_engine, PatternEngine

# ── Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("luna.server")

# ── Load Config ───────────────────────────────────────────────────

def load_config() -> dict:
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

config = load_config()

# ── Initialize Components ─────────────────────────────────────────

mimo_client = get_client()
cache = get_cache(
    directory=config.get("cache", {}).get("directory", "./cache"),
    max_size_mb=config.get("cache", {}).get("max_size_mb", 500),
    default_ttl=config.get("cache", {}).get("default_ttl", 3600)
)
# Use semantic RAG (ChromaDB + sentence-transformers) if available, fallback to TF-IDF
try:
    rag = get_semantic_rag(
        docs_path=config.get("memory", {}).get("rag_docs_path", "../docs"),
        memory_path=config.get("memory", {}).get("memory_path", "../"),
        chroma_path=config.get("memory", {}).get("chroma_path", "./chroma_db"),
    )
    rag.load_documents()
    logger.info(f"Semantic RAG initialized: {rag.get_stats()}")
except Exception as e:
    logger.warning(f"Semantic RAG failed, falling back to TF-IDF: {e}")
    rag = get_rag(
        docs_path=config.get("memory", {}).get("rag_docs_path", "../docs"),
        memory_path=config.get("memory", {}).get("memory_path", "../")
    )
allowlist = get_allowlist()

# Reschedule persisted reminders on startup
reminder_store = get_reminder_store(data_dir=Path(__file__).parent / "data")
def _reminder_startup_callback(entry):
    logger.info(f"Expired reminder fired: #{entry['id']} - {entry['message']}")
    allowlist.execute("notify", {"title": "Luna - Recordatorio", "message": entry["message"]})
reminder_store.reschedule_pending(callback=_reminder_startup_callback)
logger.info(f"Reminder store loaded: {reminder_store.stats()}")
mode_manager = get_mode_manager(config.get("modes", {}).get("default", "casa"))
proactive = get_proactive_engine()
pattern_engine = get_pattern_engine()

voice_ref = config.get("voice_ref_path", "../experiments/luna_voz_v5b_kohana_fina.wav")
voice_ref_abs = str(Path(__file__).parent / voice_ref)
tts_default_mode = config.get("voice", {}).get("default_tts", "edge")
edge_voice = config.get("voice", {}).get("edge_voice", "es-MX-DaliaNeural")
tts_use_design = tts_default_mode == "design"
tts_use_clone = tts_default_mode == "clone"
tts_use_edge = tts_default_mode == "edge"
tts_engine = TTSEngine(mimo_client, cache=cache, voice_ref_path=voice_ref_abs, voice_design_profile=config.get("voice_design_profile", "anime_es"), default_tts=tts_default_mode, edge_voice=edge_voice)
stt_engine = STTEngine(mimo_client, sample_rate=config.get("voice", {}).get("sample_rate", 16000))
streaming_handler = get_streaming_handler(mimo_client, tts_engine, stt_engine)

# ASR engine (MiMo API primary, Whisper fallback)
whisper_model = config.get("asr", {}).get("whisper_model", "base")
asr_engine = get_asr_engine(mimo_client, whisper_model=whisper_model)
logger.info(f"ASR engine initialized: {asr_engine.get_status()}")

# Emotion detection
emotion_detector = get_emotion_detector()

# Persistent conversation memory
conv_memory = get_conversation_memory(
    storage_dir=config.get("memory", {}).get("conversations_path", "./memory/conversations")
)
conv_memory.start_session()
logger.info(f"Conversation memory loaded: {conv_memory.get_stats()}")

# ── Conversation State ───────────────────────────────────────────

conversations: Dict[str, list] = {}  # ws_id -> message history


def get_conversation(ws_id: str) -> list:
    """Get or create conversation history for a connection."""
    if ws_id not in conversations:
        conversations[ws_id] = []
    return conversations[ws_id]


# ── FastAPI App ───────────────────────────────────────────────────

app = FastAPI(
    title="Luna JARVIS",
    description="Luna JARVIS Assistant Service",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = None
    use_rag: bool = True

class TTSRequest(BaseModel):
    text: str
    use_clone: bool = True
    use_design: bool = False
    use_edge: bool = False
    save_path: Optional[str] = None

class ModeRequest(BaseModel):
    mode: str

class CommandRequest(BaseModel):
    command: str
    params: Dict[str, Any] = {}


# ── HTTP Endpoints ────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"name": "Luna JARVIS", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    mimo_ok = mimo_client.health_check()
    return {
        "status": "healthy" if mimo_ok else "degraded",
        "mimo_api": "connected" if mimo_ok else "disconnected",
        "cache": cache.stats(),
        "mode": mode_manager.get_status(),
        "rag": rag.get_stats(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/status")
async def status():
    """Get system status."""
    import psutil
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("C:\\").percent,
        "mode": mode_manager.get_status(),
        "cache": cache.stats(),
        "conversations": len(conversations),
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with Luna via HTTP."""
    # Security check
    injection = check_injection(request.message)
    if injection:
        raise HTTPException(status_code=400, detail="Input rejected: suspicious content")

    message = sanitize_input(request.message)

    # Detect emotion
    emotion = emotion_detector.detect(message)
    style = get_response_style(emotion)

    # Mode switch
    if request.mode:
        mode_manager.set_mode(request.mode)

    # Check mode
    if not mode_manager.should_respond():
        return {"response": "", "mode": mode_manager.current_mode_name, "suppressed": True, "emotion": emotion.to_dict()}

    # Get RAG context
    context = ""
    if request.use_rag:
        context = rag.get_context(message)
        if context:
            context = f"\n\nCONTEXTO RELEVANTE:\n{context}"

    # Get conversation history from persistent memory
    history_context = conv_memory.get_conversation_context(max_turns=8)

    # Build system prompt with emotion-aware style
    system_prompt = (
        LUNA_SYSTEM_PROMPT
        + mode_manager.get_system_prompt_modifier()
        + context
    )
    prompt_modifier = style.to_prompt_modifier()
    if prompt_modifier:
        system_prompt += f"\n\nESTILO DE RESPUESTA ACTUAL: {prompt_modifier}"
    if emotion.primary.value != "neutral":
        system_prompt += f"\n\nEMOCION DETECTADA DEL USUARIO: {emotion.primary.value} (intensidad: {emotion.intensity:.0%})"

    # Get conversation
    conv = get_conversation("http")
    # Inject persistent history as context if conv is short
    if len(conv) < 3 and history_context:
        conv = history_context + conv
    conv.append({"role": "user", "content": message})

    # Keep conversation manageable
    if len(conv) > 20:
        conv[:] = conv[-20:]

    # Save to persistent memory
    conv_memory.add_message("user", message, metadata={"emotion": emotion.to_dict()})

    # Get response
    try:
        def tool_executor():
            class ToolExec:
                def execute(self, name, params):
                    valid, err = validate_command(name, params)
                    if not valid:
                        return {"error": err}
                    return allowlist.execute(name, params)
            return ToolExec()

        response_text = mimo_client.chat_with_tools(
            user_message=message,
            conversation_history=conv[:-1],
            tool_executor=tool_executor(),
            model=config.get("models", {}).get("brain", "mimo-v2.5-pro")
        )

        conv.append({"role": "assistant", "content": response_text})

        # Save response to persistent memory
        conv_memory.add_message("assistant", response_text)

        # Learn from this interaction
        pattern_engine.record_interaction(
            user_message=message,
            response=response_text,
            mode=mode_manager.current_mode_name,
        )

        return {
            "response": response_text,
            "mode": mode_manager.current_mode_name,
            "emotion": emotion.to_dict(),
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech."""
    try:
        audio = tts_engine.speak(request.text, use_clone=request.use_clone, use_design=request.use_design, use_edge=request.use_edge)
        if not audio:
            raise HTTPException(status_code=500, detail="TTS generation failed")

        if request.save_path:
            from voice.tts import AudioPlayer
            AudioPlayer.save_wav(audio, request.save_path)
            return {"saved": request.save_path, "size": len(audio)}

        import base64
        return {"audio": base64.b64encode(audio).decode("utf-8"), "format": "wav", "size": len(audio)}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mode")
async def set_mode(request: ModeRequest):
    """Change operational mode."""
    success = mode_manager.set_mode(request.mode)
    if not success:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {request.mode}")
    return {"mode": mode_manager.get_status()}


@app.post("/command")
async def execute_command(request: CommandRequest):
    """Execute a system command."""
    valid, err = validate_command(request.command, request.params)
    if not valid:
        raise HTTPException(status_code=403, detail=err)

    result = allowlist.execute(request.command, request.params)
    return result


@app.get("/memory/search")
async def memory_search(q: str, top_k: int = 3):
    """Search memory/documents."""
    results = rag.search(q, top_k)
    return {
        "query": q,
        "results": [
            {"text": text[:500], "score": score, "source": chunk.get("file", "unknown")}
            for text, score, chunk in results
        ]
    }


@app.post("/memory/add")
async def add_memory(text: str, source: str = "daily"):
    """Add a memory entry."""
    rag.add_memory(text, source)
    return {"added": True, "text": text[:100]}


@app.get("/suggestions")
async def get_suggestions():
    """Get proactive suggestions."""
    try:
        import psutil
        sys_info = {
            "cpu": {"percent": psutil.cpu_percent(interval=0.5)},
            "ram": {"percent": psutil.virtual_memory().percent},
            "disk": {"free_gb": round(psutil.disk_usage("C:\\").free / (1024**3), 2)},
        }
        battery = psutil.sensors_battery()
        if battery:
            sys_info["battery"] = {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
            }
    except Exception:
        sys_info = {}

    suggestions = proactive.get_suggestions(
        mode=mode_manager.current_mode_name,
        system_info=sys_info,
    )

    return {
        "suggestions": [s.to_dict() for s in suggestions],
        "mode": mode_manager.current_mode_name,
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return cache.stats()


@app.post("/cache/clear")
async def clear_cache():
    """Clear the cache."""
    cache.clear()
    return {"cleared": True}


@app.get("/patterns/stats")
async def patterns_stats():
    """Get pattern learning statistics."""
    return pattern_engine.get_stats()


@app.get("/patterns/topics")
async def patterns_topics(limit: int = 10):
    """Get learned topic preferences."""
    topics = pattern_engine.get_favorite_topics(limit)
    result = []
    for topic in topics:
        stats = pattern_engine.get_topic_stats(topic)
        if stats:
            result.append({"topic": topic, "count": stats.count, "last_mentioned": stats.last_mentioned})
    return {"topics": result}


@app.get("/patterns/context")
async def patterns_context():
    """Get personalization context for the brain."""
    context = pattern_engine.get_personalization_context()
    return {"context": context}


@app.post("/patterns/app")
async def record_app(app_name: str):
    """Record app usage for pattern learning."""
    pattern_engine.record_app_usage(app_name)
    return {"recorded": app_name}


@app.post("/patterns/clear")
async def clear_patterns():
    """Clear all learned patterns."""
    pattern_engine.clear()
    return {"cleared": True}


@app.get("/notes")
async def list_notes_endpoint():
    """List saved notes."""
    from tools.allowlist import get_allowlist
    al = get_allowlist()
    return al.execute("notes", {"action": "list"})


@app.get("/notes/{title}")
async def read_note(title: str):
    """Read a specific note."""
    from tools.allowlist import get_allowlist
    al = get_allowlist()
    return al.execute("notes", {"action": "read", "title": title})


# ── Conversation Memory Endpoints ─────────────────────────────────

@app.get("/conversations")
async def list_conversations(limit: int = 10):
    """List recent conversation sessions."""
    sessions = conv_memory.get_recent_sessions(limit)
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "started_at": s.started_at,
                "message_count": s.message_count,
                "summary": s.summary,
            }
            for s in sessions
        ]
    }


@app.get("/conversations/{session_id}")
async def get_session_messages(session_id: str):
    """Get messages from a specific conversation session."""
    session = conv_memory.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {
        "session_id": session.session_id,
        "started_at": session.started_at,
        "message_count": session.message_count,
        "messages": session.get_recent_context(max_turns=50),
    }


@app.get("/conversations/search")
async def search_conversations(q: str, limit: int = 5):
    """Search across conversation history."""
    results = conv_memory.search_conversations(q, limit)
    return {"query": q, "results": results}


@app.get("/conversations/stats")
async def conversation_stats():
    """Get conversation memory statistics."""
    return conv_memory.get_stats()


@app.get("/conversations/preferences")
async def user_preferences():
    """Get analyzed user preferences from conversation history."""
    return conv_memory.get_user_preferences()


# ── Emotion Endpoints ─────────────────────────────────────────────

@app.get("/emotion/stats")
async def emotion_stats():
    """Get emotion detection statistics."""
    return emotion_detector.get_stats()


@app.get("/emotion/history")
async def emotion_history():
    """Get emotion history as time-series data.

    Returns the last detected emotions with compound info,
    suitable for charting in the dashboard.
    """
    return {
        "history": emotion_detector.get_history(),
        "total": len(emotion_detector._history),
    }


@app.get("/asr/status")
async def asr_status():
    """Get ASR engine status (API availability, Whisper backend)."""
    return asr_engine.get_status()


@app.post("/asr/transcribe")
async def asr_transcribe_endpoint(file_path: str):
    """Transcribe an audio file using ASR (MiMo API or Whisper fallback)."""
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    text = asr_engine.transcribe(file_path)
    if not text:
        raise HTTPException(status_code=500, detail="Transcription failed")
    return {"text": text, "backend": asr_engine.get_status()["backend"]}


async def retry_on_failure(func, max_retries=2, delay=1.0):
    """Retry a synchronous function on failure with backoff."""
    import time as _time
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Retry {attempt + 1}/{max_retries}: {e}")
                _time.sleep(delay * (attempt + 1))
    raise last_error

# ── WebSocket Handler ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication."""
    await websocket.accept()
    ws_id = str(id(websocket))
    conv = get_conversation(ws_id)
    logger.info(f"WebSocket connected: {ws_id}")

    # Send welcome
    await websocket.send_json({
        "type": "status",
        "state": "ready",
        "mode": mode_manager.current_mode_name,
        "message": "Luna JARVIS conectada 🌙"
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "text")

            if msg_type == "text":
                await handle_text_message(websocket, data, conv, ws_id)

            elif msg_type == "audio":
                await handle_audio_message(websocket, data, conv, ws_id)

            elif msg_type == "audio_start":
                await streaming_handler.handle_audio_start(websocket.send_json)

            elif msg_type == "audio_chunk":
                async def on_transcript(text):
                    data["type"] = "text"
                    data["content"] = text
                    await handle_text_message(websocket, data, conv, ws_id)
                await streaming_handler.handle_audio_chunk(
                    data.get("data", ""),
                    data.get("format", "wav"),
                    websocket.send_json,
                    on_transcript=on_transcript
                )

            elif msg_type == "audio_stop":
                async def on_transcript_stop(text):
                    data["type"] = "text"
                    data["content"] = text
                    await handle_text_message(websocket, data, conv, ws_id)
                await streaming_handler.handle_audio_stop(
                    websocket.send_json,
                    on_transcript=on_transcript_stop
                )

            elif msg_type == "command":
                await handle_command_message(websocket, data)

            elif msg_type == "mode":
                mode = data.get("mode", "casa")
                mode_manager.set_mode(mode)
                await websocket.send_json({
                    "type": "system",
                    "action": "mode_changed",
                    "mode": mode_manager.get_status()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {ws_id}")
        if ws_id in conversations:
            del conversations[ws_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


async def handle_text_message(ws: WebSocket, data: dict, conv: list, ws_id: str):
    """Handle text message from WebSocket."""
    message = data.get("content", "")
    if not message:
        return

    # Security
    injection = check_injection(message)
    if injection:
        await ws.send_json({"type": "error", "message": "Input rechazado"})
        return

    message = sanitize_input(message)

    # Detect emotion
    emotion = emotion_detector.detect(message)
    style = get_response_style(emotion)

    # Notify thinking
    await ws.send_json({"type": "status", "state": "thinking"})

    # RAG context + personalization
    context = rag.get_context(message)
    personalization = pattern_engine.get_personalization_context()
    system_prompt = LUNA_SYSTEM_PROMPT + mode_manager.get_system_prompt_modifier()
    if context:
        system_prompt += f"\n\nCONTEXTO RELEVANTE:\n{context}"
    if personalization:
        system_prompt += personalization

    # Add emotion-aware style
    prompt_modifier = style.to_prompt_modifier()
    if prompt_modifier:
        system_prompt += f"\n\nESTILO DE RESPUESTA ACTUAL: {prompt_modifier}"
    if emotion.primary.value != "neutral":
        system_prompt += f"\n\nEMOCION DETECTADA DEL USUARIO: {emotion.primary.value} (intensidad: {emotion.intensity:.0%})"

    # Inject persistent conversation history if conv is short
    if len(conv) < 3:
        history = conv_memory.get_conversation_context(max_turns=6)
        if history:
            conv[:] = history + conv

    conv.append({"role": "user", "content": message})
    if len(conv) > 20:
        conv[:] = conv[-20:]

    # Save to persistent memory
    conv_memory.add_message("user", message, metadata={"emotion": emotion.to_dict()})

    try:
        # Use streaming
        full_response = ""
        for chunk in mimo_client.chat_stream(
            messages=conv[:-1] + [{"role": "user", "content": message}],
            model=config.get("models", {}).get("brain", "mimo-v2.5-pro"),
            system_prompt=system_prompt
        ):
            full_response += chunk
            await ws.send_json({"type": "text", "content": chunk, "streaming": True})

        # Final complete message
        conv.append({"role": "assistant", "content": full_response})
        await ws.send_json({"type": "text", "content": full_response, "streaming": False})

        # Save response to persistent memory
        conv_memory.add_message("assistant", full_response)

        # Always send emotion state to frontend (for avatar reactivity)
        await ws.send_json({"type": "emotion", "emotion": emotion.to_dict()})

        # Learn from this interaction
        pattern_engine.record_interaction(
            user_message=message,
            response=full_response,
            mode=mode_manager.current_mode_name,
        )

        # Generate TTS asynchronously (non-blocking)
        if full_response and mode_manager.current_mode_name != "moto":
            async def _send_audio(audio_bytes: bytes):
                try:
                    import base64 as _b64
                    await ws.send_json({
                        "type": "audio",
                        "data": _b64.b64encode(audio_bytes).decode("utf-8"),
                        "format": "wav"
                    })
                    await ws.send_json({"type": "status", "state": "speaking"})
                except Exception as e:
                    logger.error(f"Audio send error: {e}")

            # Fire-and-forget: TTS runs in thread pool, text already sent
            # Default: voice_design > voice_clone > standard
            asyncio.create_task(
                tts_engine.speak_async(full_response, on_complete=_send_audio, use_clone=tts_use_clone, use_design=tts_use_design, use_edge=tts_use_edge)
            )

        # Send proactive suggestions periodically (every 4 messages)
        if len(conv) > 0 and len(conv) % 4 == 0:
            try:
                import psutil
                sys_info = {
                    "cpu": {"percent": psutil.cpu_percent(interval=0)},
                    "ram": {"percent": psutil.virtual_memory().percent},
                }
                sugg = proactive.get_suggestions(
                    mode=mode_manager.current_mode_name,
                    system_info=sys_info,
                )
                if sugg:
                    await ws.send_json({
                        "type": "suggestions",
                        "items": [s.to_dict() for s in sugg]
                    })
            except Exception as e:
                logger.debug(f"Suggestion generation error: {e}")

        await ws.send_json({"type": "status", "state": "ready"})

    except Exception as e:
        logger.error(f"Chat error: {e}")
        await ws.send_json({"type": "error", "message": str(e)})
        await ws.send_json({"type": "status", "state": "ready"})


async def handle_audio_message(ws: WebSocket, data: dict, conv: list, ws_id: str):
    """Handle audio message (STT + chat + TTS)."""
    import base64

    audio_b64 = data.get("data", "")
    if not audio_b64:
        return

    await ws.send_json({"type": "status", "state": "listening"})

    try:
        # Decode audio
        audio_bytes = base64.b64decode(audio_b64)

        # Transcribe
        text = stt_engine.transcribe_bytes(audio_bytes, format=data.get("format", "wav"))
        if not text:
            await ws.send_json({"type": "error", "message": "No pude entender el audio"})
            return

        await ws.send_json({"type": "transcript", "content": text})

        # Process as text
        data["type"] = "text"
        data["content"] = text
        await handle_text_message(ws, data, conv, ws_id)

    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await ws.send_json({"type": "error", "message": str(e)})


async def handle_command_message(ws: WebSocket, data: dict):
    """Handle direct command execution."""
    command = data.get("command", "")
    params = data.get("params", {})

    valid, err = validate_command(command, params)
    if not valid:
        await ws.send_json({"type": "error", "message": err})
        return

    result = allowlist.execute(command, params)
    await ws.send_json({"type": "command_result", "command": command, "result": result})


# ── Main ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 8765)

    logger.info(f"Starting Luna JARVIS on {host}:{port}")
    logger.info(f"API Docs: http://localhost:{port}/docs")

    # Load RAG on startup
    rag.load_documents()
    logger.info(f"Pattern engine loaded: {pattern_engine.get_stats()}")

    uvicorn.run(app, host=host, port=port, log_level="info")
