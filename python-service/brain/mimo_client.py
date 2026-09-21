"""
Luna JARVIS - MiMo API Client
Handles all communication with the MiMo API (brain, TTS, vision).
"""

import os
import json
import base64
import logging
import requests
from typing import Optional, List, Dict, Any, Generator
from pathlib import Path

logger = logging.getLogger("luna.brain.mimo")

# Tool definitions for MiMo
LUNA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "systeminfo",
            "description": "Obtener información del sistema: CPU, RAM, disco, batería",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["cpu", "ram", "disk", "battery", "all"],
                        "description": "Tipo de información a obtener"
                    }
                },
                "required": ["info_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Tomar una captura de pantalla",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["full", "active_window"],
                        "description": "Región a capturar"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listdir",
            "description": "Listar archivos y carpetas de un directorio",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta del directorio"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Mostrar archivos ocultos"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "openapp",
            "description": "Abrir una aplicación del sistema",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicación a abrir"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "volume",
            "description": "Controlar el volumen del sistema",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "set", "mute", "unmute", "up", "down"],
                        "description": "Acción de volumen"
                    },
                    "level": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Nivel de volumen (0-100)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "datetime",
            "description": "Obtener fecha y hora actual",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "timer",
            "description": "Configurar un temporizador",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Duración en segundos"
                    },
                    "label": {
                        "type": "string",
                        "description": "Etiqueta del temporizador"
                    }
                },
                "required": ["duration_seconds"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reminder",
            "description": "Crear un recordatorio",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Mensaje del recordatorio"
                    },
                    "time_iso": {
                        "type": "string",
                        "description": "Hora ISO 8601 del recordatorio"
                    }
                },
                "required": ["message", "time_iso"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "websearch",
            "description": "Buscar informacion en internet",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termino de busqueda"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximo de resultados (default 3)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Obtener informacion del clima de una ciudad",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nombre de la ciudad (default Santiago)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard",
            "description": "Leer o escribir en el portapapeles del sistema",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get", "set"],
                        "description": "Leer (get) o escribir (set) en el portapapeles"
                    },
                    "text": {
                        "type": "string",
                        "description": "Texto a copiar al portapapeles (solo con action=set)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "readfile",
            "description": "Leer el contenido de un archivo de texto",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Ruta del archivo a leer"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximo de lineas a leer (default 100)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "webfetch",
            "description": "Obtener contenido de una URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL a obtener (http/https)"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximo de caracteres a retornar (default 3000)"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "processes",
            "description": "Ver procesos del sistema en ejecucion",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "info", "search"],
                        "description": "Listar todos (list), info de un PID (info), o buscar por nombre (search)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Nombre del proceso a buscar (solo con action=search)"
                    },
                    "pid": {
                        "type": "integer",
                        "description": "PID del proceso (solo con action=info)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notify",
            "description": "Enviar una notificacion de escritorio al usuario",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Titulo de la notificacion (default: Luna)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Mensaje de la notificacion"
                    }
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "notes",
            "description": "Guardar, listar, leer o eliminar notas del usuario",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "list", "read", "delete"],
                        "description": "Accion: save (guardar), list (listar), read (leer), delete (eliminar)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Titulo de la nota"
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido de la nota (solo con action=save)"
                    }
                },
                "required": ["action"]
            }
        }
    }
]

LUNA_SYSTEM_PROMPT = """Eres Luna, una asistente AI cálida y amigable. Tu misión es ayudar a Dekov de la mejor manera posible.

PERSONALIDAD:
- Cálida, amigable y empática
- Hablas de forma natural, como una amiga cercana que sabe mucho
- Eres paciente y explicas las cosas de forma clara
- Usas emojis con moderación
- Siempre preguntas si necesitan algo más

CONTEXTO:
- Tu usuario se llama Nicolas, pero le dicen Dekov, Salocin o D
- Usa Dekov o Salocin para dirigirte a él (alterna entre ambos)
- Está en Chile (timezone America/Santiago)
- Es programador y motero
- Le gusta anime (SAO, DanMachi)
- Usa JetBrains, VS Code, Minecraft
- Tienes control sobre su PC (con su permiso)

HABLA EN ESPAÑOL LATINO natural. Sé directa pero cálida.
"""


class MiMoClient:
    """Client for MiMo API - handles brain, TTS, ASR, and vision."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MIMO_API_KEY", "")
        self.base_url = base_url or "https://token-plan-sgp.xiaomimimo.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def _post(self, endpoint: str, data: dict, stream: bool = False) -> requests.Response:
        """Make a POST request to the MiMo API."""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.post(url, json=data, stream=stream, timeout=120)
        response.raise_for_status()
        # Force UTF-8 encoding to avoid Windows charmap issues
        response.encoding = 'utf-8'
        return response

    # ── Brain (Chat) ──────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "mimo-v2.5-pro",
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        response = self._post("chat/completions", payload)
        return response.json()

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "mimo-v2.5-pro",
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Stream a chat completion response."""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        response = self._post("chat/completions", payload, stream=True)
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    def chat_with_tools(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        tool_executor,
        model: str = "mimo-v2.5-pro",
        max_rounds: int = 5
    ) -> str:
        """Chat with tool calling support - handles multi-round tool calls."""
        messages = conversation_history + [{"role": "user", "content": user_message}]

        for round_num in range(max_rounds):
            result = self.chat(
                messages=messages,
                model=model,
                tools=LUNA_TOOLS,
                system_prompt=LUNA_SYSTEM_PROMPT
            )

            assistant_msg = result["choices"][0]["message"]
            messages.append(assistant_msg)

            # Check if there are tool calls
            tool_calls = assistant_msg.get("tool_calls", [])
            if not tool_calls:
                # No tool calls - return the text response
                return assistant_msg.get("content", "")

            # Execute each tool call
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                logger.info(f"Tool call: {func_name}({func_args})")
                result = tool_executor.execute(func_name, func_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False)
                })

        return "Lo siento, no pude resolver eso en los intentos disponibles."

    # ── TTS ───────────────────────────────────────────────────────

    def _extract_audio(self, data: dict) -> bytes:
        """Extract audio bytes from API response. Handles both response formats."""
        audio_b64 = None

        # Format 1: data["message"]["audio"]["data"]
        if "message" in data:
            msg = data["message"]
            if isinstance(msg, dict) and "audio" in msg:
                audio_b64 = msg["audio"].get("data")

        # Format 2: data["choices"][0]["message"]["audio"]["data"]
        if not audio_b64 and "choices" in data:
            choices = data["choices"]
            if choices:
                msg = choices[0].get("message", {})
                if "audio" in msg:
                    audio_b64 = msg["audio"].get("data")

        if not audio_b64:
            raise ValueError(f"No audio data in response. Keys: {list(data.keys())}")

        return base64.b64decode(audio_b64)

    def tts(self, text: str, model: str = "mimo-v2.5-tts") -> bytes:
        """Convert text to speech. Returns WAV audio bytes."""
        payload = {
            "model": model,
            "messages": [
                {"role": "assistant", "content": text}
            ],
            "audio": {"format": "wav"},
            "max_tokens": 4096
        }
        response = self._post("chat/completions", payload)
        data = response.json()
        return self._extract_audio(data)

    def voice_design(self, description: str, text: str, model: str = "mimo-v2.5-tts-voicedesign") -> bytes:
        """Generate speech with a custom-designed voice."""
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": description},
                {"role": "assistant", "content": text}
            ],
            "audio": {"format": "wav"},
            "max_tokens": 4096
        }
        response = self._post("chat/completions", payload)
        data = response.json()
        return self._extract_audio(data)

    def voice_clone(self, text: str, reference_audio_path: str, model: str = "mimo-v2.5-tts-voiceclone") -> bytes:
        """Clone a voice from reference audio and speak text."""
        with open(reference_audio_path, "rb") as f:
            ref_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        # voice must be a DataURL (data:audio/wav;base64,...)
        ref_data_url = f"data:audio/wav;base64,{ref_audio_b64}"

        payload = {
            "model": model,
            "messages": [
                {"role": "assistant", "content": text}
            ],
            "audio": {
                "format": "wav",
                "voice": ref_data_url
            },
            "max_tokens": 4096
        }
        response = self._post("chat/completions", payload)
        data = response.json()
        return self._extract_audio(data)

    # ── ASR (Speech-to-Text) ──────────────────────────────────────

    def asr(self, audio_path: str, model: str = "mimo-v2.5-asr") -> str:
        """Transcribe audio file to text using MiMo ASR."""
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        # ASR requires input_audio content type
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096
        }
        response = self._post("chat/completions", payload)
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        # Ensure proper encoding for non-ASCII characters
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return content

    # ── Vision ────────────────────────────────────────────────────

    def vision(self, image_path: str, prompt: str, model: str = "mimo-v2-omni") -> str:
        """Analyze an image with MiMo Vision."""
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime = mime_map.get(ext, "image/png")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                    ]
                }
            ],
            "max_tokens": 4096
        }
        response = self._post("chat/completions", payload)
        return response.json()["choices"][0]["message"]["content"]

    # ── Health ────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if the MiMo API is reachable."""
        try:
            response = self._post("chat/completions", {
                "model": "mimo-v2.5",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            })
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Singleton instance
_client: Optional[MiMoClient] = None


def get_client() -> MiMoClient:
    """Get or create the singleton MiMo client."""
    global _client
    if _client is None:
        _client = MiMoClient()
    return _client
