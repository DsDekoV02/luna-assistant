"""Tests for voice comparison and new endpoints (Session 44)."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the FastAPI app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def app_client():
    """Create a FastAPI TestClient."""
    from fastapi.testclient import TestClient
    # Patch heavy dependencies before importing main
    with patch("brain.mimo_client.MiMoClient") as mock_mc, \
         patch("memory.cache.DiskCache") as mock_cache, \
         patch("memory.rag_semantic.SemanticRAGEngine") as mock_rag:
        mock_mc.return_value = MagicMock()
        mock_mc.return_value.health_check.return_value = True
        mock_cache.return_value = MagicMock()
        mock_cache.return_value.stats.return_value = {"entries": 0}
        mock_rag.return_value = MagicMock()
        mock_rag.return_value.get_stats.return_value = {"chunks": 0}
        from main import app
        client = TestClient(app)
        yield client


class TestVoiceBackends:
    """Test /voice/backends endpoint."""

    def test_backends_returns_structure(self, app_client):
        """GET /voice/backends returns expected structure."""
        resp = app_client.get("/voice/backends")
        assert resp.status_code == 200
        data = resp.json()
        assert "backends" in data
        assert "default" in data
        assert "edge_voice" in data
        for key in ["edge", "clone", "design", "standard"]:
            assert key in data["backends"]
            assert "available" in data["backends"][key]
            assert "quality" in data["backends"][key]

    def test_backends_standard_always_available(self, app_client):
        """Standard TTS is always available."""
        resp = app_client.get("/voice/backends")
        data = resp.json()
        assert data["backends"]["standard"]["available"] is True


class TestConversationExport:
    """Test /conversations/export endpoint."""

    def test_export_json_format(self, app_client):
        """GET /conversations/export?format=json returns sessions."""
        resp = app_client.get("/conversations/export?format=json&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "json"
        assert "sessions" in data
        assert "exported_at" in data

    def test_export_markdown_format(self, app_client):
        """GET /conversations/export?format=markdown returns markdown."""
        resp = app_client.get("/conversations/export?format=markdown&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "markdown"
        assert "content" in data

    def test_export_limit(self, app_client):
        """Export respects limit parameter."""
        resp = app_client.get("/conversations/export?format=json&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) <= 1


class TestVoiceCompareScript:
    """Test the voice comparison script."""

    def test_import(self):
        """Voice comparator module is importable."""
        from voice.compare import VoiceComparator, TEST_PHRASES
        assert len(TEST_PHRASES) >= 3
        assert all("id" in p and "text" in p for p in TEST_PHRASES)

    def test_phrase_categories(self):
        """Test phrases have diverse categories."""
        from voice.compare import TEST_PHRASES
        categories = {p["category"] for p in TEST_PHRASES}
        assert len(categories) >= 3  # at least 3 different categories

    def test_output_dir_creation(self):
        """Comparator creates output directory."""
        from voice.compare import VoiceComparator
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "test_output")
            comp = VoiceComparator(output_dir=out)
            assert comp.output_dir.exists()
