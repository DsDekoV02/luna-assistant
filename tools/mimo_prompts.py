#!/usr/bin/env python3
"""
MiMo Desktop Prompt Generator
Genera prompts automaticos para MiMo Desktop basados en el estado del proyecto.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
PROMPTS_DIR = ASSETS_DIR / "prompts"
DOCS_DIR = PROJECT_ROOT / "docs"
PROGRESS_DIR = DOCS_DIR / "progress"

PROMPT_TEMPLATES = {
    "architecture_diagram": {
        "filename": "diagrama-arquitectura.md",
        "template": """Crea un diagrama de arquitectura profesional para el proyecto Luna AI.

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
Resolucion: Alta, suitable para README de GitHub."""
    },
    
    "feature_mockup": {
        "filename": "mockup-feature-actual.md",
        "template": """Crea un mockup visual de la interfaz de Luna AI mostrando la feature mas reciente.

Contexto del proyecto:
- Es un asistente personal AI con avatar 3D interactivo
- Overlay transparente sobre el desktop (Electron)
- Avatar de luna con emociones que cambian segun el contexto
- Chat visual con burbujas de mensajes
- Dashboard de conversaciones y emociones

Feature mas reciente: Avatar con intensidad emocional y dashboard

El mockup debe mostrar:
1. La ventana de Electron con fondo transparente
2. El avatar de Luna (luna creciente con particulas)
3. El chat con la nueva feature integrada
4. Indicadores de emocion activa
5. Panel de stats si es relevante

Estilo: Dark theme, neon accents (dorado #f5d5a0), particulas flotantes.
Formato: Screenshot de la app en uso, como si fuera una captura real.
Resolucion: 1200x800, suitable para README."""
    },
    
    "changelog_banner": {
        "filename": "banner-release.md",
        "template": """Crea un banner visual para el release v0.1.0 de Luna AI.

Contenido del release:
- Motor cognitivo con MiMo v2.5 Pro
- Voice cloning con Text Processor V4 (WER 58.3%)
- Avatar Three.js con emociones y particulas
- Deteccion de 9 emociones en tiempo real
- Memoria persistente con RAG semantico
- Tool calling con allowlist de seguridad
- 22+ sesiones de desarrollo autonomo

El banner debe incluir:
1. Titulo: "Luna AI v0.1.0"
2. Tagline descriptiva del release
3. 3-4 iconos representando las features principales
4. Estilo consistente con el repo (dark navy #0d0d1a, golden #f5d5a0)
5. Formato wide (1200x400) para GitHub release

Estilo: Mismo que el cover de Ko-fi, tech-meets-celestial.
Formato: PNG o SVG, optimizado para web."""
    },
    
    "comparison_chart": {
        "filename": "comparativa-ai-assistants.md",
        "template": """Crea una tabla comparativa visual entre Luna AI y otros asistentes AI populares.

Caracteristicas de Luna AI a comparar:
- Avatar 3D con emociones en tiempo real
- Voice cloning con text processor (WER 58.3%)
- Memoria persistente con RAG semantico
- Tool calling con allowlist de seguridad
- Deteccion de 9 emociones
- Overlay transparente para desktop
- Open source (Python + Electron)

Comparar con:
- ChatGPT (OpenAI)
- Claude (Anthropic)
- Copilot (Microsoft)
- Siri (Apple)
- Alexa (Amazon)

Formato: Tabla visual con checkmarks, iconos y colores.
Estilo: Profesional, suitable para portafolio.
Resolucion: Alta, para compartir en redes o Ko-fi."""
    },
    
    "roadmap_visual": {
        "filename": "roadmap-visual.md",
        "template": """Crea un roadmap visual para Luna AI mostrando el pasado, presente y futuro.

Pasado (completado):
- Motor cognitivo con MiMo v2.5 Pro
- Voice cloning con Text Processor V4
- Avatar Three.js con emociones
- Deteccion de emociones en tiempo real
- Memoria persistente con RAG
- Tool calling con allowlist
- 22+ sesiones de desarrollo autonomo

Presente (en progreso):
- GitHub repo publico
- Ko-fi con donaciones
- Documentacion y portafolio
- Testing y estabilizacion

Futuro (planificado):
- Wake word "Hey Luna" en desktop
- Integracion con celular (Android)
- Realidad Aumentada (HUD en casco)
- Multiples voces y personalidades
- Marketplace de skills/plugins

Formato: Timeline visual con iconos, colores y progreso.
Estilo: Mismo dark theme del proyecto.
Resolucion: Wide format (1600x600) para README."""
    }
}


def get_latest_feature():
    if not PROGRESS_DIR.exists():
        return "Avatar con intensidad emocional y dashboard de conversaciones"
    files = sorted(PROGRESS_DIR.glob("*.md"), key=os.path.getmtime, reverse=True)
    if not files:
        return "Avatar con intensidad emocional y dashboard de conversaciones"
    try:
        content = files[0].read_text(encoding='utf-8')[:500]
        return content.split('\n')[0] if content else "Avatar con intensidad emocional"
    except:
        return "Avatar con intensidad emocional y dashboard de conversaciones"


def generate_prompt(prompt_type):
    if prompt_type not in PROMPT_TEMPLATES:
        return None
    template_data = PROMPT_TEMPLATES[prompt_type]
    return {
        "type": prompt_type,
        "filename": template_data["filename"],
        "prompt": template_data["template"],
        "generated_at": datetime.now().isoformat()
    }


def generate_all_prompts():
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    
    for prompt_type in PROMPT_TEMPLATES:
        prompt_data = generate_prompt(prompt_type)
        if prompt_data:
            filepath = PROMPTS_DIR / prompt_data["filename"]
            filepath.write_text(prompt_data["prompt"], encoding='utf-8')
            generated.append(prompt_data)
            print(f"OK: {prompt_data['filename']}")
    
    index_path = PROMPTS_DIR / "index.json"
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "prompts": [{"type": p["type"], "filename": p["filename"], "generated_at": p["generated_at"]} for p in generated]
    }
    index_path.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    print(f"\nTotal: {len(generated)} prompts generados")
    print(f"Ubicacion: {PROMPTS_DIR}")
    print("\nPara usar:")
    print("1. Abre MiMo Desktop")
    print("2. Copia el contenido de cada archivo .md en assets/prompts/")
    print("3. Guarda el resultado en assets/mockups/ o assets/diagrams/")
    print("4. Luna lo commitea automaticamente")
    
    return generated


if __name__ == "__main__":
    print("Generador de prompts para MiMo Desktop")
    print("=" * 50)
    generate_all_prompts()