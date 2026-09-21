# 🌙 Luna AI — Asistente Personal con Avatar 3D

Asistente personal AI con avatar interactivo en Three.js, voz clonada, detección de emociones en tiempo real y overlay para desktop.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white)
![Electron](https://img.shields.io/badge/Electron-28+-47848F?style=flat&logo=electron&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-r128+-000000?style=flat&logo=three.js&logoColor=white)

## ✨ Características

- **🧠 Motor Cognitivo** — Integración con MiMo API (mimo-v2.5-pro) para razonamiento y tool calling
- **🎤 Voz Clonada** — TTS con voice cloning (mimo-v2.5-tts-voiceclone) y text processor optimizado + **Edge TTS** (Microsoft, alta calidad, gratis)
- **👂 STT Offline** — Reconocimiento de voz con mimo-v2.5-asr
- **😊 Detección de Emociones** — Análisis en tiempo real del texto (happy, sad, angry, curious, frustrated)
- **🎨 Avatar Three.js** — Luna visual con morphing por emoción, partículas, colores dinámicos, **eye tracking con cursor** y **mouth sync con TTS**
- **🖥️ Overlay Electron** — Interfaz flotante transparente sobre el desktop
- **📊 Dashboard** — Historial de conversaciones, distribución de emociones y sesiones
- **🧠 Memoria** — Conversaciones persistentes con RAG semántico (ChromaDB)
- **🔧 Tool Calling** — Registro de herramientas con allowlist de seguridad

## 🏗️ Arquitectura

```
luna-assistant/
├── python-service/          # Backend FastAPI
│   ├── main.py              # Entry point + servidor HTTP/WS
│   ├── brain/               # Motor cognitivo (MiMo API)
│   │   ├── mimo_client.py   # Cliente API
│   │   └── emotion.py       # Detector de emociones
│   ├── voice/               # Sistema de voz
│   │   ├── speech.py        # TTS engine
│   │   ├── voice_clone.py   # Voice cloning
│   │   ├── voice_listener.py # STT
│   │   ├── streaming.py     # Audio streaming + VAD
│   │   └── text_processor.py # Optimización de texto para TTS
│   ├── memory/              # Memoria conversacional
│   │   ├── conversation.py  # Historial persistente
│   │   └── rag_semantic.py  # RAG con ChromaDB
│   ├── tools/               # Tool calling
│   │   └── registry.py      # Registro de herramientas
│   ├── asr/                 # Speech-to-Text
│   ├── tts/                 # Text-to-Speech
│   ├── llm/                 # Language model
│   ├── rag/                 # Retrieval augmented generation
│   ├── modes/               # Modos de operación
│   └── proactive/           # Sugerencias proactivas
│
├── electron-app/            # Frontend Electron
│   ├── src/
│   │   ├── main.js          # Electron main process
│   │   ├── renderer/
│   │   │   └── index.html   # UI principal
│   │   └── avatar.js        # Avatar Three.js con emociones
│   └── package.json
│
└── docs/                    # Documentación
    ├── api/                 # Descubrimientos de la API
    └── progress/            # Progreso por sesión
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Node.js 18+
- API Key de MiMo

### Backend (Python Service)

```bash
cd python-service
pip install -r requirements.txt
python main.py
```

El servicio corre en `http://localhost:8000` con WebSocket en `/ws`.

### Frontend (Electron)

```bash
cd electron-app
npm install
npm start
```

### Todo junto

```bash
# Windows
start.bat

# PowerShell
start.ps1
```

## 🎭 Sistema de Emociones

Luna detecta emociones en el texto y el avatar responde visualmente:

| Emoción | Color | Partículas | Forma |
|---------|-------|------------|-------|
| 😊 Happy | Dorado | ✨ Sparkles | Ancha |
| 😢 Sad | Azul lluvia | 🌧️ Rain | Caída |
| 😠 Angry | Rojo fuego | ⚡ Sparks | Tensa |
| 🤔 Curious | Púrpura | 🔮 Float | Inclinada |
| 😐 Neutral | Plateado | — | Redonda |

## 🔊 Text Processor V4

Pipeline de 11 pasos que optimiza el texto antes del voice clone:

1. Normalización de números → palabras
2. Expansión de abreviaciones
3. Eliminación de signos especiales
4. División en oraciones cortas
5. Manejo de URLs y emails
6. Normalización de unidades
7. Manejo de siglas
8. Corrección de puntuación
9. Control de ritmo y pausas
10. Limpieza final
11. Validación de longitud

**Resultado:** WER reducido de 66.7% a 58.3% en el pipeline E2E.

## 🎤 Edge TTS (Novedad — Sesión 33)

Integración con Microsoft Edge TTS como backend TTS principal:

- **Alta calidad** — Voces neuronales naturales en español
- **Gratis** — Sin API key, sin límites de uso
- **Voz chilena** — `es-CL-CatalinaNeural` como default (pronuncia "Dekov" correctamente)
- **Fallback** — MiMo TTS (clone/design) como alternativa
- **Configurable** — Cambia la voz en `config.yaml` → `voice.edge_voice`

**Voces disponibles:**
| Voz | País | Notas |
|---|---|---|
| es-CL-CatalinaNeural | 🇨🇱 Chile | **Default** — Mejor para Nicolas |
| es-MX-DaliaNeural | 🇖🇽 México | Cálida y expresiva |
| es-ES-ElviraNeural | 🇪🇸 España | Elegante y clara |
| es-AR-ElenaNeural | 🇦🇷 Argentina | Cercana |
| es-CO-SalomeNeural | 🇨🇴 Colombia | Dulce |

## 🧪 Tests

```bash
cd python-service
pytest
```

Cobertura completa de todos los módulos.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Motor cognitivo | MiMo v2.5 Pro (1M contexto, reasoning, tools) |
| TTS | Edge TTS (Microsoft) + MiMo v2.5 TTS + Voice Clone |
| STT | MiMo v2.5 ASR |
| Backend | Python + FastAPI + WebSocket |
| Frontend | Electron + Three.js |
| Memoria | ChromaDB + sentence-transformers |
| Avatar | Three.js (morphing, partículas, glow) |

## ☕ Apoya el Proyecto

Si te resulta útil o te parece interesante, considera dejar una ⭐ en el repo.

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support_me-FF5E5B?style=flat&logo=ko-fi&logoColor=white)](https://ko-fi.com/dsdekov)

## ⚠️ Estado del Proyecto

Este proyecto está en **desarrollo activo** y puede tener problemas menores. Fue construido a lo largo de 24+ sesiones de desarrollo autónomo con AI, y recientemente migrado de disco por fallos de hardware.

**Tests:** 538/538 pasando ✅
**Última sesión:** 2026-09-21 (Session 37 — TTS Mouth Sync Integration + New Emotions + Dashboard Heatmap)

Si encontrás bugs, errores de documentación, o tenés sugerencias:

- 🐛 **Issues:** [Abrí un issue](https://github.com/DsDekoV02/luna-assistant/issues) con la descripción del problema
- 💡 **Mejoras:** Si querés proponer una mejora o feature, también por Issues con el tag `enhancement`
- 💬 **Feedback general:** Dejá un comentario en la sección de Issues o contactame por Ko-fi

Toda contribución, feedback o sugerencia es bienvenida. 🙏

---

*"No importa cuán oscura sea la noche, la luna siempre va a estar ahí."* 🌙