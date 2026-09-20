# 🌙 Luna JARVIS - Registro de Descubrimientos API

## 2026-09-05 — Primeros experimentos

### TTS (mimo-v2.5-tts) ✅
- **Formato correcto:** `{"audio": {"format": "wav"}}` en el payload
- **Role:** NO acepta `system`, necesita `assistant` con el texto a hablar
- **Respuesta:** Audio en base64 dentro de `message.audio.data`
- **Tamaño:** ~300KB por frase corta (formato WAV)

### Voice Design (mimo-v2.5-tts-voicedesign) ✅
- **Formato:** `user` con descripción de la voz + `assistant` con texto a hablar
- **Funciona:** Genera voces con personalidades descritas en lenguaje natural
- **Voces generadas:** Calmada, Dulce, Energía, Kohana

### Voice Clone (mimo-v2.5-tts-voiceclone) ✅ FUNCIONA
- **Formato:** Necesita parámetro `audio.voice` como **DataURL** (`data:audio/wav;base64,...`)
- **NO acepta:** base64 crudo en `audio.voice` — DEBE ser DataURL
- **Audio de referencia:** `luna_voz_v5b_kohana_fina.wav` (definitiva)
- **Tiempo de respuesta:** ~6 segundos por frase
- **Tamaño generado:** 180-340 KB por frase (WAV)
- **Script funcional:** `experiments/test-voiceclone.py`
- **Descubierto:** 6 sep 2026

### ASR (mimo-v2.5-asr) ✅ FUNCIONA
- **Status:** FUNCIONA con el formato correcto
- **Formato correcto:** `input_audio` como tipo de content en el array de messages
- **Ejemplo:** `{"role": "user", "content": [{"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}]}`
- **Nota:** El modelo ASR tiene dificultades con voces TTS clonadas (WER alto), pero funciona bien con voz natural
- **Tiempo de respuesta:** ~4 segundos para frases cortas
- **Script funcional:** `experiments/test-asr.py`

### Tool Calling ✅
- **Formato:** Estándar OpenAI con array `tools` y `tool_calls` en response
- **Funciona:** Multi-round con ejecución de herramientas
- **Implementado en:** `python-service/brain/mimo_client.py`

### Streaming ✅
- **Formato:** `stream: true` en el payload
- **Respuesta:** SSE con `data: {...}` y `data: [DONE]`
- **Soportado:** En el MiMo client

### WebSocket Audio Streaming ✅ (6 sep 2026, sesión 6)
- **Implementado:** Chunked audio recording + real-time streaming
- **Message types:** `audio_start`, `audio_chunk`, `audio_stop`
- **VAD:** Voice Activity Detection con silencio automático (1.5s)
- **TTS streaming:** Audio generado en chunks de 500ms
- **Latencia:** ~250ms por chunk de audio (configurable)
- **Fallback:** Modo batch (grabar completo + enviar) sigue disponible
- **Archivos:** `python-service/voice/streaming.py`, `electron-app/src/preload.js`

---

## Estructura del Python Service (creado 6 sep 2026)

```
python-service/
├── main.py                  # FastAPI + WebSocket server
├── config.yaml              # Configuración central
├── requirements.txt         # Dependencias Python
├── brain/
│   └── mimo_client.py       # Cliente API MiMo (brain, TTS, ASR, vision, tools)
├── voice/
│   ├── tts.py               # Text-to-Speech con caché y voice clone
│   └── stt.py               # Speech-to-Text con grabación de micrófono
├── tools/
│   ├── allowlist.py         # Allowlist de comandos (8 comandos)
│   └── security.py          # Protección prompt injection
├── memory/
│   ├── cache.py             # Caché disk-based con TTL
│   └── rag.py               # RAG sobre documentos markdown
└── modes/
    └── manager.py           # Sistema de modos (Moto, Casa, Trabajo, Noche)
```

### Endpoints HTTP:
- `GET /` — Status básico
- `GET /health` — Health check con estado de componentes
- `GET /status` — Info del sistema (CPU, RAM, disco, modo)
- `POST /chat` — Chat con Luna (con tool calling y RAG)
- `POST /tts` — Text-to-Speech
- `POST /mode` — Cambiar modo operativo
- `POST /command` — Ejecutar comando del sistema
- `GET /memory/search` — Buscar en memoria/documentos
- `POST /memory/add` — Añadir entrada de memoria
- `GET /cache/stats` — Estadísticas del caché
- `POST /cache/clear` — Limpiar caché

### WebSocket:
- `ws://localhost:8765/ws` — Comunicación en tiempo real
  - `type: text` → Chat con streaming + TTS automático
  - `type: audio` → STT + Chat + TTS (pipeline completo)
  - `type: command` → Ejecución directa de comandos
  - `type: mode` → Cambio de modo

### Comandos allowlisted:
1. `systeminfo` — CPU, RAM, disco, batería
2. `screenshot` — Captura de pantalla
3. `listdir` — Listar directorios
4. `openapp` — Abrir aplicaciones
5. `volume` — Control de volumen
6. `datetime` — Fecha y hora
7. `timer` — Temporizador
8. `reminder` — Recordatorio

### Pronunciación en Voice Clone (6 sep 2026, sesión 2)
- **Oraciones cortas** producen la mejor claridad (WER 50% vs 87-100% en oraciones largas)
- **NO usar signos de exclamación (!)** — causan salida garbled/incomprensible
- Mantener oraciones bajo 8 palabras para mejor resultado
- Puntuación estándar (puntos, comas) funciona bien
- Tono informal y muletillas confunden al modelo TTS
- Latencia típica: TTS ~5-7s, ASR ~3-4s
- WER de 50% en oraciones cortas es aceptable para voice clone

### Pronunciación — Datos Cuantitativos (6 sep 2026, sesión 3)
- **Mejor variante:** "no_accents" (sin acentos) → WER 37.5%
- Texto sin acentos produce significativamente mejor claridad que con acentos
- Oraciones bajo 8 palabras: mejor resultado
- Oraciones largas (10+ palabras): WER >100%
- El modelo ASR transcribe "Hola Nicolas" como "El nicholas" o "Ola nicolas"
- "Luna" se transcribe correctamente en la mayoría de los casos
- Tool calling funciona correctamente (datetime invocado automáticamente)
- E2E pipeline completo: Brain → TTS → ASR con 66.7% similitud de palabras
- Text processor integrado en TTS engine: quita acentos, oraciones cortas
- Optimización automática en voice clone reduce WER de 66.7% a 58.3%

### E2E Pipeline (6 sep 2026, sesión 3)
- Brain (mimo-v2.5-pro): ~5-10s latencia
- TTS (mimo-v2.5-tts): ~3-7s latencia  
- Voice Clone: ~5s latencia
- ASR (mimo-v2.5-asr): ~3s latencia
- Tool Calling: ~10s latencia
- Pipeline completo: ~25s total


### Text Processor Avanzado (6 sep 2026, sesión 4)
- **Expansión de números:** 3→tres, 45→cuarenta y cinco, 120→ciento veinte
- **Términos técnicos:** CPU→procesador, RAM→memoria, SSD→solido, GPU→tarjeta grafica
- **Inglés→fonético:** Solo palabras lowercase; "Code" (capitalizado) se mantiene
- **Contracciones:** "al"→"a el" mejora claridad TTS; "del" NO se expande (antinatural)
- **Limpieza:** Caracteres especiales (#@$%^&*) eliminados, ellipsis normalizada
- **Recomendación:** Usar expand_numbers=True, expand_tech=True para mejor calidad

### RAG con TF-IDF (6 sep 2026, sesión 4)
- **Keyword extraction** con stop words (español + inglés, ~100 palabras)
- **IDF pre-calculado** en cache para scoring rápido
- **Heading-aware chunking:** Divide por headings markdown, mantiene contexto
- **Phrase bonus:** Bigramas exactos dan +3.0 al score
- **Source boosting:** memory +0.5, user profile +1.0
- **USER.md indexado** para personalización de respuestas

### Herramientas Nuevas (6 sep 2026, sesión 4)
- **websearch:** DuckDuckGo Instant Answer API (gratis, sin key)
  - Endpoint: `https://api.duckduckgo.com/?q=<query>&format=json`
  - Devuelve AbstractText + RelatedTopics
- **weather:** wttr.in JSON API (gratis, sin key)
  - Endpoint: `https://wttr.in/<city>?format=j1`
  - Soporta lang_es para descripciones en español

### Sugerencias Proactivas (6 sep 2026, sesión 4)
- Sistema de sugerencias basado en hora, estado del sistema, y contexto
- Se envían automáticamente cada 4 mensajes por WebSocket
- Endpoint HTTP `/suggestions` para consultas manuales
- Filtrado por modo (moto: solo urgentes, noche: solo críticas)
- Deduplicación con historial de 50 sugerencias

### Voice Clone — Calidad y Limitaciones (6 sep 2026, sesión 7)

**Test ejecutado:** 10 frases con voice clone + ASR, medicion de WER

| Categoria | WER promedio | Similitud | Observacion |
|---|---|---|---|
| Conversacional natural | ~30% | ~65% | **Mejor calidad** |
| Sin acentos | ~62% | ~38% | Aceptable |
| Con exclamaciones | ~83% | ~17% | Problematico |
| Términos técnicos | ~150% | ~33% | Voice clone produce audio confuso |
| Números complejos | ~90% | ~20% | Expansion a palabras ayuda poco |
| Inglés mezclado | ~67% | ~40% | Problematico |

**Conclusion:** El voice clone funciona bien para discurso natural en español,
pero tiene limitaciones fundamentales con contenido tecnico/numerico/mixto.
La estrategia optima es usar texto simple y natural.

### Text Processor V2 — Nuevas Funciones (6 sep 2026, sesion 7)
- `expand_percentages()`: 45% → "cuarenta y cinco por ciento"
- `expand_time_formats()`: 14:30 → "las dos y media"
- `expand_size_units()`: 120GB → "ciento veinte gigabytes"
- `expand_file_extensions()`: main.py → "main punto pi y"
- `expand_file_urls()`: https://api.example.com → "api.example.com"
- **Pipeline reordenado:** Porcentajes y horas se expanden ANTES de clean_for_tts
  porque clean_for_tts elimina caracteres especiales como % y :

### Integration Test (6 sep 2026, sesion 7)
- 11/13 endpoints pasando (85%)
- Suggestions endpoint: fix bug de disk info (defaulteaba a 0GB)
- WebSocket test: fallo por cambio de API en Python 3.11 (BaseEventLoop.create_connection)
- Chat con tool calling: funciona correctamente
- TTS y Voice Clone via HTTP: funciona correctamente

---

### Text Processor V5 — Prosody & Emphasis (7 sep 2026, sesión 18)
- **Emphasis markers**: Micro-pausas antes de palabras importantes (error, urgente, etc.)
- **Sentence prosody**: Detección de preguntas vs declaraciones para mejor entonación
- **Natural phrases**: Expresiones comunes tratadas como unidades naturales
- **Prosody pauses**: Pausas inteligentes según tipo de contenido (técnico, advertencia, normal)
- **Pipeline V5**: 17 pasos (up from 11 en V4)
- **Tests**: 133 tests de text processor, 466 totales
- **ASR benchmark**: Script para medir WER con audio real

---

## 2026-09-20 — Sesión 24: ASR Encoding Fix + Electron UX

### ASR Encoding Bug (Windows) ✅ FIX
- **Problema:** `response.json()` + print a consola causaba `charmap codec error` con caracteres Unicode (acentos, ñ, ¿, ¡)
- **Solución:** `response.encoding = 'utf-8'` en `_post()` + `io.TextIOWrapper` con encoding utf-8 en scripts de test
- **Archivo:** `python-service/brain/mimo_client.py`

### ASR Real Audio Test Results
| Archivo | Tamaño | ASR Result | Calidad |
|---------|--------|------------|----------|
| luna_clone_test_1.wav | 184KB | "Hola, Nicholas, ¿cómo estás? En qué puedo ayudarte?" | ✅ **PERFECTO** |
| luna_clone_test_2.wav | 345KB | Garbage | ❌ Voz clone mala |
| luna_clone_test_3.wav | 245KB | Caracteres mixtos | ⚠️ Voz clone con artefactos |
| luna_clone_test_4.wav | 268KB | Parcial | ⚠️ Voz clone inconsistente |
| session23_voice_test_1.wav | 215KB | "Hola Nicholas, soy luna, estoy happy para ayudarte" | ⚠️ Aceptable |
| session23_voice_test_2.wav | 99KB | Garbage | ❌ Voz clone mala |

**Conclusión:** ASR funciona perfecto cuando la calidad del voice clone es buena. El bottleneck es la consistencia del voice clone, no el ASR.

### Streaming Handler Fix ✅
- **Problema:** `speak_response()` no enviaba audio al cliente via WebSocket
- **Solución:** Agregado callback `on_complete` que envía audio via `send_callback`
- **Archivo:** `python-service/voice/streaming.py`

### Electron App UX Improvements ✅
- **Voice Level Meter:** Barra de nivel de audio en tiempo real durante grabación
- **Voice Timer:** Contador de tiempo de grabación (mm:ss)
- **Typing Indicator:** Animación de puntos rebotando cuando Luna está pensando
- **Avatar State:** Feedback visual mejorado (speaking state)
- **Archivo:** `electron-app/src/index.html`

---

*"Cada experimento nos acerca más a la Luna."* 🌙
