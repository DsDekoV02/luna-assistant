"""
Luna JARVIS - Test Fixtures
Common fixtures for all test modules.
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for tests."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_mimo_client():
    """Create a mock MiMo client."""
    client = MagicMock()
    client.api_key = "test-key"
    client.base_url = "https://test.api.com/v1"
    client.health_check.return_value = True
    client.tts.return_value = b"RIFF" + b"\x00" * 100  # Fake WAV
    client.voice_clone.return_value = b"RIFF" + b"\x00" * 100
    client.asr.return_value = "hola mundo de prueba"
    client.chat.return_value = {
        "choices": [{"message": {"content": "respuesta de prueba"}}]
    }
    return client


@pytest.fixture
def sample_wav_bytes():
    """Generate minimal valid WAV bytes."""
    import struct
    # Minimal WAV header + silence
    sample_rate = 16000
    num_channels = 1
    bits_per_sample = 16
    duration = 0.1  # 100ms
    num_samples = int(sample_rate * duration)
    data_size = num_samples * num_channels * (bits_per_sample // 8)

    wav = b"RIFF"
    wav += struct.pack("<I", 36 + data_size)
    wav += b"WAVE"
    wav += b"fmt "
    wav += struct.pack("<I", 16)  # chunk size
    wav += struct.pack("<HHIIHH", 1, num_channels, sample_rate,
                        sample_rate * num_channels * (bits_per_sample // 8),
                        num_channels * (bits_per_sample // 8), bits_per_sample)
    wav += b"data"
    wav += struct.pack("<I", data_size)
    wav += b"\x00" * data_size
    return wav


@pytest.fixture
def sample_wav_file(tmp_dir, sample_wav_bytes):
    """Create a temporary WAV file."""
    path = tmp_dir / "test.wav"
    path.write_bytes(sample_wav_bytes)
    return str(path)


@pytest.fixture
def docs_dir(tmp_dir):
    """Create a temporary docs directory with sample markdown files."""
    docs = tmp_dir / "docs"
    docs.mkdir()

    (docs / "TECH_STACK.md").write_text(
        "# Tech Stack\n\n"
        "## Motor\n"
        "Usamos MiMo v2.5 Pro como cerebro principal.\n"
        "Tiene soporte para tool calling y 1M de contexto.\n\n"
        "## Voz\n"
        "TTS con voice clone usando mimo-v2.5-tts-voiceclone.\n"
        "STT con mimo-v2.5-asr para transcripcion.\n",
        encoding="utf-8"
    )

    (docs / "VOICE_DESIGN.md").write_text(
        "# Voice Design\n\n"
        "## Voz de Luna\n"
        "Archivo: luna_voz_v5b_kohana_fina.wav\n"
        "Estilo: Chica anime, espanol latino, tono medio-alto.\n"
        "Personalidad: calida y directa.\n",
        encoding="utf-8"
    )

    (docs / "progress").mkdir(exist_ok=True)
    (docs / "progress" / "session1.md").write_text(
        "# Progreso Sesion 1\n\n"
        "- TTS funcionando correctamente\n"
        "- Voice clone mejorado con text processor\n"
        "- WER promedio: 78.2%\n",
        encoding="utf-8"
    )

    return docs
