Crea un diagrama de arquitectura profesional para el proyecto Luna AI.

Stack tecnologico:
- Backend: Python + FastAPI + WebSocket (puerto 8765)
- Frontend: Electron + Three.js (avatar 3D)
- Motor cognitivo: MiMo v2.5 Pro API
- TTS: MiMo v2.5 TTS + Voice Clone
- STT: MiMo v2.5 ASR
- Memoria: ChromaDB + sentence-transformers
- Deteccion de emociones: analisis de texto en tiempo real

Modulos del python-service:
- brain/ (mimo_client.py, emotion.py)
- voice/ (speech.py, streaming.py, voice_listener.py, text_processor.py, voice_clone.py)
- memory/ (conversation.py, rag_semantic.py)
- tools/ (registry.py, security.py, allowlist.py)
- modes/ (manager.py)
- proactive/ (engine.py)
- asr/, tts/, llm/, rag/

El diagrama debe mostrar:
1. Flujo de datos: Usuario -> Electron -> WebSocket -> Python Service -> MiMo API
2. Modulos principales y sus conexiones
3. Sistema de emociones (texto -> emocion -> avatar)
4. Pipeline de voz (STT -> Brain -> TTS)
5. Memoria persistente (conversaciones + RAG)

Formato: Diagrama visual con colores, iconos y flechas de flujo.
Estilo: Moderno, tech, dark theme (como el README del repo).
Resolucion: Alta, suitable para README de GitHub.