"""
Luna JARVIS - Tests for RAG Engine
Tests document indexing, search, and context retrieval.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.rag import RAGEngine, extract_keywords, STOP_WORDS


@pytest.fixture
def rag_engine(docs_dir):
    engine = RAGEngine(
        docs_path=str(docs_dir),
        memory_path=str(docs_dir.parent),
        chunk_size=500,
        chunk_overlap=50
    )
    engine.load_documents()
    return engine


# ── extract_keywords ─────────────────────────────────────────────

class TestExtractKeywords:
    def test_removes_stop_words(self):
        keywords = extract_keywords("el perro de la casa")
        assert "el" not in keywords
        assert "la" not in keywords
        assert "de" not in keywords

    def test_keeps_meaningful_words(self):
        keywords = extract_keywords("voice clone funciona bien")
        assert "voice" in keywords
        assert "clone" in keywords
        assert "funciona" in keywords

    def test_min_length(self):
        keywords = extract_keywords("a b cd efgh")
        assert "a" not in keywords
        assert "b" not in keywords
        # cd is 2 chars, regex requires >= 2
        assert "cd" in keywords or "efgh" in keywords

    def test_empty_text(self):
        assert extract_keywords("") == []

    def test_spanish_stop_words(self):
        keywords = extract_keywords("tengo una casa con jardin grande")
        assert "tengo" in keywords
        assert "casa" in keywords
        assert "jardin" in keywords


# ── Document Loading ─────────────────────────────────────────────

class TestDocumentLoading:
    def test_loads_chunks(self, rag_engine):
        assert len(rag_engine.chunks) > 0

    def test_chunks_have_text(self, rag_engine):
        for chunk in rag_engine.chunks:
            assert "text" in chunk
            assert len(chunk["text"]) > 0

    def test_chunks_have_keywords(self, rag_engine):
        for chunk in rag_engine.chunks:
            assert "keywords" in chunk
            assert "keyword_set" in chunk

    def test_chunks_have_source(self, rag_engine):
        for chunk in rag_engine.chunks:
            assert "source" in chunk

    def test_idf_cache_built(self, rag_engine):
        assert len(rag_engine._idf_cache) > 0

    def test_loaded_flag(self, rag_engine):
        assert rag_engine._loaded is True


# ── Search ───────────────────────────────────────────────────────

class TestSearch:
    def test_search_returns_results(self, rag_engine):
        results = rag_engine.search("MiMo TTS voice")
        assert len(results) > 0

    def test_search_returns_tuples(self, rag_engine):
        results = rag_engine.search("TTS")
        for item in results:
            assert len(item) == 3
            text, score, chunk = item
            assert isinstance(text, str)
            assert isinstance(score, float)
            assert isinstance(chunk, dict)

    def test_search_scores_normalized(self, rag_engine):
        results = rag_engine.search("voice clone")
        if results:
            for _, score, _ in results:
                assert 0 <= score <= 1.0

    def test_search_top_k(self, rag_engine):
        results = rag_engine.search("TTS", top_k=2)
        assert len(results) <= 2

    def test_search_relevance(self, rag_engine):
        results = rag_engine.search("voice clone TTS")
        if results:
            # Best result should have high relevance
            assert results[0][1] > 0.3

    def test_search_no_results(self, rag_engine):
        results = rag_engine.search("xyznonexistent123")
        assert len(results) == 0

    def test_source_filter(self, rag_engine):
        results = rag_engine.search("TTS", source_filter="docs")
        for _, _, chunk in results:
            assert chunk["source"] == "docs"

    def test_heading_match_boost(self, rag_engine):
        # Search for something in a heading
        results = rag_engine.search("Tech Stack")
        if results:
            # Should find chunks with heading match
            assert any(r[2].get("heading", "") for r in results)


# ── get_context ──────────────────────────────────────────────────

class TestGetContext:
    def test_returns_string(self, rag_engine):
        context = rag_engine.get_context("MiMo TTS")
        assert isinstance(context, str)

    def test_returns_empty_for_no_match(self, rag_engine):
        context = rag_engine.get_context("xyznonexistent123")
        assert context == ""

    def test_respects_max_chars(self, rag_engine):
        context = rag_engine.get_context("TTS", max_chars=100)
        assert len(context) <= 150  # Some tolerance for headers

    def test_contains_source_info(self, rag_engine):
        context = rag_engine.get_context("voice clone")
        if context:
            assert "Fuente:" in context or "Relevancia:" in context


# ── Stats ────────────────────────────────────────────────────────

class TestStats:
    def test_stats_structure(self, rag_engine):
        stats = rag_engine.get_stats()
        assert "total_chunks" in stats
        assert "sources" in stats
        assert "idf_terms" in stats
        assert "loaded" in stats

    def test_stats_values(self, rag_engine):
        stats = rag_engine.get_stats()
        assert stats["total_chunks"] > 0
        assert stats["loaded"] is True
        assert stats["idf_terms"] > 0


# ── Heading Extraction ──────────────────────────────────────────

class TestHeadingExtraction:
    def test_extract_h1(self, rag_engine):
        heading = rag_engine._extract_heading("# Mi Encabezado\nContenido aqui")
        assert heading == "Mi Encabezado"

    def test_extract_h2(self, rag_engine):
        heading = rag_engine._extract_heading("## Subtitulo\nMas contenido")
        assert heading == "Subtitulo"

    def test_no_heading(self, rag_engine):
        heading = rag_engine._extract_heading("Solo texto sin heading")
        assert heading == ""
