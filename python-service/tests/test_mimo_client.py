"""
Luna JARVIS - Tests for MiMo Client
Tests API communication with mocked HTTP responses.
"""

import pytest
import sys
import json
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.mimo_client import MiMoClient, LUNA_TOOLS, LUNA_SYSTEM_PROMPT


@pytest.fixture
def client():
    """Create a MiMoClient with test config."""
    with patch.dict("os.environ", {"MIMO_API_KEY": "test-key-123"}):
        c = MiMoClient(api_key="test-key-123", base_url="https://test.api.com/v1")
        return c


@pytest.fixture
def mock_response():
    """Create a mock requests response."""
    def _make(data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = data
        resp.raise_for_status.return_value = None
        resp.iter_lines.return_value = []
        return resp
    return _make


# ── Initialization ────────────────────────────────────────────────

class TestMiMoClientInit:
    def test_default_init(self, client):
        assert client.api_key == "test-key-123"
        assert "xiaomimimo.com" in client.base_url or "test.api.com" in client.base_url

    def test_custom_base_url(self):
        c = MiMoClient(api_key="k", base_url="https://custom.api.com/v1")
        assert c.base_url == "https://custom.api.com/v1"

    def test_session_headers(self, client):
        assert "Bearer test-key-123" in client.session.headers.get("Authorization", "")


# ── Chat ──────────────────────────────────────────────────────────

class TestMiMoChat:
    @patch("requests.Session.post")
    def test_basic_chat(self, mock_post, client, mock_response):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "Hola Nicolas!"}}]
        })

        result = client.chat([{"role": "user", "content": "Hola"}])
        assert result["choices"][0]["message"]["content"] == "Hola Nicolas!"

    @patch("requests.Session.post")
    def test_chat_with_system_prompt(self, mock_post, client, mock_response):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "ok"}}]
        })

        client.chat(
            [{"role": "user", "content": "test"}],
            system_prompt="Eres Luna"
        )

        call_data = mock_post.call_args[1]["json"]
        assert call_data["messages"][0]["role"] == "system"
        assert "Luna" in call_data["messages"][0]["content"]

    @patch("requests.Session.post")
    def test_chat_with_tools(self, mock_post, client, mock_response):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "ok"}}]
        })

        client.chat([{"role": "user", "content": "test"}], tools=LUNA_TOOLS)
        call_data = mock_post.call_args[1]["json"]
        assert "tools" in call_data
        assert len(call_data["tools"]) > 0

    @patch("requests.Session.post")
    def test_chat_temperature(self, mock_post, client, mock_response):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "ok"}}]
        })

        client.chat([{"role": "user", "content": "test"}], temperature=0.3)
        call_data = mock_post.call_args[1]["json"]
        assert call_data["temperature"] == 0.3


# ── Chat with Tools ──────────────────────────────────────────────

class TestChatWithTools:
    @patch("requests.Session.post")
    def test_no_tool_calls(self, mock_post, client, mock_response):
        """When model responds without tool calls, return text."""
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "Hola!"}}]
        })

        executor = MagicMock()
        result = client.chat_with_tools("Hola", [], executor)
        assert result == "Hola!"
        executor.execute.assert_not_called()

    @patch("requests.Session.post")
    def test_with_tool_call(self, mock_post, client, mock_response):
        """When model requests a tool, execute it and continue."""
        # First call: model requests datetime tool
        # Second call: model responds with text using tool result
        mock_post.side_effect = [
            mock_response({
                "choices": [{
                    "message": {
                        "content": None,
                        "tool_calls": [{
                            "id": "call_123",
                            "function": {
                                "name": "datetime",
                                "arguments": "{}"
                            }
                        }]
                    }
                }]
            }),
            mock_response({
                "choices": [{"message": {"content": "Son las 10:00"}}]
            }),
        ]

        executor = MagicMock()
        executor.execute.return_value = {"time": "10:00:00"}

        result = client.chat_with_tools("¿Qué hora es?", [], executor)
        assert "10:00" in result
        executor.execute.assert_called_once_with("datetime", {})


# ── TTS ──────────────────────────────────────────────────────────

class TestMiMoTTS:
    @patch("requests.Session.post")
    def test_tts_extracts_audio(self, mock_post, client, mock_response):
        fake_audio = b"RIFF" + b"\x00" * 100
        audio_b64 = base64.b64encode(fake_audio).decode()

        mock_post.return_value = mock_response({
            "message": {"audio": {"data": audio_b64}}
        })

        result = client.tts("Hola mundo")
        assert result == fake_audio

    @patch("requests.Session.post")
    def test_tts_choices_format(self, mock_post, client, mock_response):
        """Test alternate response format with choices array."""
        fake_audio = b"RIFF" + b"\x00" * 50
        audio_b64 = base64.b64encode(fake_audio).decode()

        mock_post.return_value = mock_response({
            "choices": [{"message": {"audio": {"data": audio_b64}}}]
        })

        result = client.tts("Test")
        assert result == fake_audio

    @patch("requests.Session.post")
    def test_tts_no_audio_raises(self, mock_post, client, mock_response):
        mock_post.return_value = mock_response({"no_audio": True})

        with pytest.raises(ValueError, match="No audio data"):
            client.tts("Test")

    @patch("requests.Session.post")
    def test_tts_uses_assistant_role(self, mock_post, client, mock_response):
        fake_audio = b"RIFF" + b"\x00" * 50
        audio_b64 = base64.b64encode(fake_audio).decode()
        mock_post.return_value = mock_response({
            "message": {"audio": {"data": audio_b64}}
        })

        client.tts("Hola")
        call_data = mock_post.call_args[1]["json"]
        assert call_data["messages"][0]["role"] == "assistant"


# ── Voice Clone ──────────────────────────────────────────────────

class TestVoiceClone:
    @patch("requests.Session.post")
    def test_voice_clone_uses_dataurl(self, mock_post, client, mock_response, sample_wav_file):
        fake_audio = b"RIFF" + b"\x00" * 50
        audio_b64 = base64.b64encode(fake_audio).decode()
        mock_post.return_value = mock_response({
            "message": {"audio": {"data": audio_b64}}
        })

        result = client.voice_clone("Hola", sample_wav_file)
        call_data = mock_post.call_args[1]["json"]

        # Check that voice is a DataURL
        voice = call_data["audio"]["voice"]
        assert voice.startswith("data:audio/wav;base64,")


# ── ASR ──────────────────────────────────────────────────────────

class TestASR:
    @patch("requests.Session.post")
    def test_asr_transcribes(self, mock_post, client, mock_response, sample_wav_file):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "hola mundo de prueba"}}]
        })

        result = client.asr(sample_wav_file)
        assert result == "hola mundo de prueba"

    @patch("requests.Session.post")
    def test_asr_uses_input_audio_type(self, mock_post, client, mock_response, sample_wav_file):
        mock_post.return_value = mock_response({
            "choices": [{"message": {"content": "test"}}]
        })

        client.asr(sample_wav_file)
        call_data = mock_post.call_args[1]["json"]

        content = call_data["messages"][0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "input_audio"


# ── Extract Audio ────────────────────────────────────────────────

class TestExtractAudio:
    def test_message_format(self, client):
        data = {
            "message": {
                "audio": {
                    "data": base64.b64encode(b"test_audio").decode()
                }
            }
        }
        result = client._extract_audio(data)
        assert result == b"test_audio"

    def test_choices_format(self, client):
        data = {
            "choices": [{
                "message": {
                    "audio": {
                        "data": base64.b64encode(b"audio2").decode()
                    }
                }
            }]
        }
        result = client._extract_audio(data)
        assert result == b"audio2"

    def test_no_audio_raises(self, client):
        with pytest.raises(ValueError):
            client._extract_audio({"no": "audio"})


# ── System Prompt & Tools ────────────────────────────────────────

class TestConstants:
    def test_system_prompt_exists(self):
        assert "Luna" in LUNA_SYSTEM_PROMPT
        assert "Nicolas" in LUNA_SYSTEM_PROMPT

    def test_tools_defined(self):
        assert len(LUNA_TOOLS) >= 8
        tool_names = [t["function"]["name"] for t in LUNA_TOOLS]
        assert "datetime" in tool_names
        assert "systeminfo" in tool_names
        assert "websearch" in tool_names
        assert "weather" in tool_names
