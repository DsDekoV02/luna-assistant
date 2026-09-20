# 🌙 Luna JARVIS — Documentación Técnica Completa

## 1. Stack Tecnológico

### 1.1 Motor Cognitivo (IA)
| Componente | Modelo | Contexto | Uso |
|------------|--------|----------|-----|
| Cerebro principal | `mimo-v2.5-pro` | 1M tokens | Razonamiento, decisiones, tools |
| Visión | `mimo-v2-omni` | 262k tokens | Leer pantalla, cámara, imágenes |
| Fallback rápido | `mimo-v2.5` | 262k tokens | Respuestas simples, bajo costo |

**API Base URL:** `https://token-plan-sgp.xiaomimimo.com/v1`
**Autenticación:** Bearer token (API Key de Xiaomi)

### 1.2 Sistema de Voz (TTS/STT)
| Componente | Modelo | Uso |
|------------|--------|-----|
| TTS estándar | `mimo-v2.5-tts` | Convertir texto a voz |
| Voice Design | `mimo-v2.5-tts-voicedesign` | Diseñar voz personalizada desde descripción |
| Voice Clone | `mimo-v2.5-tts-voiceclone` | Clonar voz desde audio de referencia |
| STT/ASR | `mimo-v2.5-asr` | Convertir voz a texto (reemplaza faster-whisper) |

**Formato API TTS:**
```json
{
  "model": "mimo-v2.5-tts",
  "messages": [
    {"role": "assistant", "content": "Texto a hablar"}
  ],
  "audio": {"format": "wav"},
  "max_tokens": 4096
}
```

**Formato API Voice Design:**
```json
{
  "model": "mimo-v2.5-tts-voicedesign",
  "messages": [
    {"role": "user", "content": "Descripción de la voz deseada"},
    {"role": "assistant", "content": "Texto a hablar"}
  ],
  "audio": {"format": "wav"},
  "max_tokens": 4096
}
```

**Formato API Voice Clone:**
```json
{
  "model": "mimo-v2.5-tts-voiceclone",
  "messages": [
    {"role": "assistant", "content": "Texto a hablar"}
  ],
  "audio": {
    "format": "wav",
    "voice": "data:audio/wav;base64,<base64_audio_referencia>"
  },
  "max_tokens": 4096
}
```

**Formato API ASR:**
```json
{
  "model": "mimo-v2.5-asr",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_audio",
          "input_audio": {
            "data": "<base64_audio>",
            "format": "wav"
          }
        }
      ]
    }
  ],
  "max_tokens": 4096
}
```

**Notas importantes:**
- NO acepta role `system` en modelos TTS
- Todos los TTS devuelven audio en base64 dentro de `message.audio.data`
- Audio generado: ~180-340KB por frase (formato WAV)
- Voice Clone requiere audio de referencia en `audio.voice` como **DataURL** (`data:audio/wav;base64,...`)
- ASR requiere `input_audio` como tipo en el content array
- Voice Clone latencia: ~6s por frase | ASR latencia: ~4s por frase

### 1.3 Display (Interfaz Visual)
| Componente | Tecnología | Uso |
|------------|------------|-----|
| Framework UI | Vue.js 3 | Componentes reactivos |
| Render 3D | Three.js | Avatar de Luna, efectos visuales |
| Runtime | Electron | Overlay flotante sobre escritorio |
| Estilos | CSS3 + Glassmorphism | Dark theme violeta/negro |

**Características del overlay:**
- Flota sobre todos los programas
- Background transparente
- Se puede mover y redimensionar
- Hotkey para mostrar/ocultar (ej: Ctrl+Shift+L)
- Siempre visible pero no intrusivo

### 1.4 Memoria y Conocimiento
| Componente | Tecnología | Uso |
|------------|------------|-----|
| RAG | LangChain + ChromaDB | Búsqueda semántica en documentos |
| Documentos | Markdown (.md) | MEMORY.md, daily notes, USER.md |
| Embeddings | sentence-transformers | Vectorización de texto |
| Caché | Redis / SQLite | Respuestas frecuentes, estado |

### 1.5 Control del PC
| Componente | Uso |
|------------|-----|
| Python subprocess | Ejecutar comandos del sistema |
| Allowlist | Lista blanca de comandos permitidos |
| Prompt injection protection | Validación de inputs antes de ejecutar |

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    ELECTRON OVERLAY                      │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │   Three.js       │  │        Vue.js UI             │  │
│  │   (Avatar 3D)    │  │  ┌────────┐ ┌────────────┐  │  │
│  │                  │  │  │ Chat   │ │ Status     │  │  │
│  │   🌙 Luna        │  │  │ Area   │ │ Panel      │  │  │
│  │                  │  │  └────────┘ └────────────┘  │  │
│  └─────────────────┘  │  ┌────────────────────────┐  │  │
│                       │  │ Input (text + mic btn)  │  │  │
│                       │  └────────────────────────┘  │  │
│                       └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                   PYTHON SERVICE (FastAPI)                │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ STT      │ │ TTS      │ │ Brain    │ │ Tools      │ │
│  │ mimo-asr │ │ mimo-tts │ │ mimo-pro │ │ allowlist  │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ RAG Engine (LangChain + ChromaDB)                │   │
│  │ MEMORY.md • daily notes • USER.md • project docs │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Cache Layer (Redis/SQLite)                       │   │
│  │ Respuestas frecuentes • Estado • Configuración   │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    OPENCLAW GATEWAY                      │
│         (comunicación con instancia principal)           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Protocolo de Comunicación

### Electron ↔ Python Service
- **Protocolo:** WebSocket (bidireccional, baja latencia)
- **Puerto:** 8765 (configurable)
- **Formato:** JSON

**Mensajes entrantes (Electron → Python):**
```json
{"type": "text", "content": "Hola Luna"}
{"type": "audio", "data": "<base64_audio>", "format": "wav"}
{"type": "command", "action": "screenshot"}
```

**Mensajes salientes (Python → Electron):**
```json
{"type": "text", "content": "Hola Nicolas"}
{"type": "audio", "data": "<base64_audio>", "format": "wav"}
{"type": "status", "state": "listening|thinking|speaking"}
{"type": "system", "cpu": 45, "ram": 62, "disk": 54}
```

---

## 4. Estructura de Directorios

```
luna-jarvis/
├── docs/                    # Documentación
│   ├── TECH_STACK.md       # Este archivo
│   ├── API_REFERENCE.md    # Referencia de APIs
│   └── VOICE_DESIGN.md     # Diseño de voz
├── experiments/             # Experimentos y pruebas
│   ├── *.wav               # Audios generados
│   └── *.py                # Scripts de prueba
├── electron-app/            # Aplicación Electron
│   ├── main.js             # Entry point Electron
│   ├── preload.js          # Preload script
│   ├── src/
│   │   ├── components/     # Vue components
│   │   ├── App.vue         # App principal
│   │   └── main.js         # Vue entry
│   ├── package.json
│   └── electron-builder.yml
├── python-service/          # Servicio Python
│   ├── main.py             # FastAPI server
│   ├── brain/              # Motor cognitivo
│   │   ├── mimo_client.py  # Cliente API MiMo
│   │   └── rag_engine.py   # Motor RAG
│   ├── voice/              # Sistema de voz
│   │   ├── tts.py          # Text-to-Speech
│   │   ├── stt.py          # Speech-to-Text
│   │   └── voice_design.py # Diseño de voz
│   ├── tools/              # Herramientas del sistema
│   │   ├── allowlist.py    # Lista blanca de comandos
│   │   ├── system.py       # Info del sistema
│   │   └── security.py     # Protección prompt injection
│   ├── memory/             # Sistema de memoria
│   │   ├── rag.py          # RAG sobre markdown
│   │   └── cache.py        # Caché de respuestas
│   ├── requirements.txt
│   └── config.yaml
├── assets/                  # Recursos
│   ├── avatar/             # Modelo 3D de Luna
│   ├── icons/              # Iconos
│   └── sounds/             # Sonidos
└── README.md
```

---

## 5. Dependencias

### Python Service
```
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
requests>=2.31.0
langchain>=0.1.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
redis>=5.0.0
pydantic>=2.5.0
python-multipart>=0.0.6
```

### Electron App
```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "three": "^0.160.0",
    "@vueuse/core": "^10.7.0"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^5.0.0"
  }
}
```

---

## 6. Fases de Desarrollo

### Fase 1: Experimentación ✅ (COMPLETADA)
- [x] Probar mimo-v2.5-tts → FUNCIONA ✅
- [x] Probar mimo-v2.5-tts-voicedesign → FUNCIONA ✅
- [x] Probar mimo-v2.5-tts-voiceclone → FUNCIONA ✅
- [x] Descubrir formato API TTS
- [x] Generar primeras voces de Luna
- [x] Probar mimo-v2.5-asr para STT → FUNCIONA ✅
- [x] Diseñar avatar 3D de Luna → PROTOTIPO ✅
- [x] Prototipo de overlay con Electron → CREADO ✅

### Fase 2: Core ✅ (COMPLETADA)
- [x] Python service con FastAPI
- [x] WebSocket server
- [x] Cliente MiMo con tool calling
- [x] Sistema de allowlist
- [x] RAG sobre documentos markdown
- [x] Caché de respuestas

### Fase 3: Integración ✅ (COMPLETADA)
- [x] Electron app con overlay
- [x] Three.js avatar de Luna
- [x] Comunicación Python ↔ Electron
- [x] Hotkey global (Alt+L)
- [x] Modo voz (pipeline STT + chat + TTS)

### Fase 4: Polish ✅ (COMPLETADA)
- [x] Modos operativos (Moto, Casa, Trabajo, Noche)
- [x] Proactividad (sugerencias, alertas)
- [x] Sistema de voz completo (TTS + voice clone + ASR)
- [x] Text processor avanzado
- [x] Scripts de inicio rápido
- [ ] Aprendizaje de patrones

---

## 7. APIs y Endpoints

### MiMo API
- **Base URL:** `https://token-plan-sgp.xiaomimimo.com/v1`
- **Chat:** `POST /chat/completions`
- **Models:** `GET /models`

### Python Service (interno)
- **WebSocket:** `ws://localhost:8765`
- **Health:** `GET /health`
- **Status:** `GET /status`

---

## 8. Seguridad

### Allowlist de comandos permitidos
- Información del sistema (CPU, RAM, disco)
- Listar archivos y directorios
- Abrir aplicaciones específicas
- Control de volumen
- Screenshot
- Navegación web (URLs específicas)

### Protección contra prompt injection
- Validación de inputs antes de enviar al modelo
- Sanitización de comandos del sistema
- Límites de ejecución (timeout, recursos)
- Logging de todas las acciones ejecutadas

---

*"No importa cuán oscura sea la noche, la luna siempre va a estar ahí."* 🌙
