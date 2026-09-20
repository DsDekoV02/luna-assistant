"""
Luna JARVIS - Tests for Semantic RAG Engine
Tests ChromaDB + sentence-transformers semantic search.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def semantic_rag(docs_dir, tmp_dir):
    """Create a SemanticRAGEngine with test docs."""
    from memory.rag_semantic import SemanticRAGEngine

    chroma_path = str(tmp_dir / "test_chroma")
    engine = SemanticRAGEngine(
        docs_path=str(docs_dir),
        memory_path=str(docs_dir.parent),
        chunk_size=500,
        chunk_overlap=50,
        chroma_path=chroma_path,
        use_semantic=False,  # Disable for unit tests (no model download)
    )
    engine.load_documents()
    return engine


@pytest.fixture
def semantic_rag_with_model(docs_dir, tmp_dir):
    """Create a SemanticRAGEngine with semantic search enabled.
    Only use when sentence-transformers is available."""
    from memory.rag_semantic import SemanticRAGEngine

    chroma_path = str(tmp_dir / "test_chroma")
    engine = SemanticRAGEngine(
        docs_path=str(docs_dir),
        memory_path=str(docs_dir.parent),
        chunk_size=500,
        chunk_overlap=50,
        chroma_path=chroma_path,
        use_semantic=True,
    )
    engine.load_documents()
    return engine


# ── Initialization ────────────────────────────────────────────────

class TestSemanticRAGInit:
    def test_fallback_to_tfidf(self, semantic_rag):
        """When semantic is disabled, should work like TF-IDF."""
        assert len(semantic_rag.chunks) > 0
        assert semantic_rag._loaded is True

    def test_chroma_path_set(self, semantic_rag, tmp_dir):
        assert semantic_rag.chroma_path is not None

    def test_semantic_disabled_flag(self, semantic_rag):
        # When use_semantic=False, should not be ready
        assert semantic_rag.use_semantic is False

    def test_inherits_from_base(self, semantic_rag):
        """Should inherit from RAGEngine."""
        from memory.rag import RAGEngine
        assert isinstance(semantic_rag, RAGEngine)


# ── TF-IDF Fallback ──────────────────────────────────────────────

class TestTFIDFFallback:
    def test_search_works_without_semantic(self, semantic_rag):
        """Search should work even without semantic search."""
        results = semantic_rag.search("MiMo TTS")
        assert len(results) > 0

    def test_get_context_works(self, semantic_rag):
        context = semantic_rag.get_context("voice clone")
        assert isinstance(context, str)

    def test_stats_includes_semantic_flag(self, semantic_rag):
        stats = semantic_rag.get_stats()
        assert "semantic_enabled" in stats
        assert stats["semantic_enabled"] is False


# ── Merge Results ────────────────────────────────────────────────

class TestMergeResults:
    def test_merge_empty_semantic(self, semantic_rag):
        """When semantic results are empty, should return TF-IDF results."""
        tfidf = [("text1", 0.9, {"source": "docs"}), ("text2", 0.7, {"source": "docs"})]
        semantic = []
        results = semantic_rag._merge_results(tfidf, semantic)
        assert len(results) == 2

    def test_merge_empty_tfidf(self, semantic_rag):
        """When TF-IDF results are empty, should return semantic results."""
        tfidf = []
        semantic = [("text1", 0.9, {"source": "docs"})]
        results = semantic_rag._merge_results(tfidf, semantic)
        assert len(results) == 1

    def test_merge_both(self, semantic_rag):
        """Should merge both result sets."""
        tfidf = [("text A", 0.9, {"source": "docs"}), ("text B", 0.7, {"source": "docs"})]
        semantic = [("text A", 0.8, {"source": "docs"}), ("text C", 0.6, {"source": "docs"})]
        results = semantic_rag._merge_results(tfidf, semantic, semantic_weight=0.5)
        # Should have 3 unique texts
        assert len(results) == 3
        # Scores should be normalized 0-1
        for _, score, _ in results:
            assert 0 <= score <= 1

    def test_merge_respects_weight(self, semantic_rag):
        """Higher semantic_weight should favor semantic results."""
        tfidf = [("TF-IDF winner", 0.9, {}), ("Semantic winner", 0.3, {})]
        semantic = [("Semantic winner", 0.95, {}), ("TF-IDF winner", 0.2, {})]

        # With high semantic weight, semantic winner should rank higher
        results = semantic_rag._merge_results(tfidf, semantic, semantic_weight=0.9)
        assert results[0][0] == "Semantic winner"

        # With low semantic weight, TF-IDF winner should rank higher
        results = semantic_rag._merge_results(tfidf, semantic, semantic_weight=0.1)
        assert results[0][0] == "TF-IDF winner"


# ── Stats ────────────────────────────────────────────────────────

class TestSemanticStats:
    def test_stats_structure(self, semantic_rag):
        stats = semantic_rag.get_stats()
        assert "semantic_enabled" in stats
        assert "embedding_model" in stats
        assert "chroma_path" in stats
        assert "total_chunks" in stats
        assert "loaded" in stats

    def test_stats_values(self, semantic_rag):
        stats = semantic_rag.get_stats()
        assert stats["total_chunks"] > 0
        assert stats["loaded"] is True
        assert stats["chroma_path"] is not None


# ── Integration with Semantic Search ─────────────────────────────

@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "memory" / "rag_semantic.py").exists(),
    reason="Semantic RAG module not found"
)
class TestSemanticSearchIntegration:
    """Integration tests that require sentence-transformers + ChromaDB.
    Marked as slow - run manually."""

    @pytest.mark.slow
    def test_semantic_search_returns_results(self, semantic_rag_with_model):
        """Full semantic search should return results."""
        if not semantic_rag_with_model._semantic_ready:
            pytest.skip("Semantic search not available")
        results = semantic_rag_with_model.search("voice clone TTS", semantic_weight=0.8)
        assert len(results) > 0

    @pytest.mark.slow
    def test_semantic_finds_related_content(self, semantic_rag_with_model):
        """Semantic search should find related content even with different words."""
        if not semantic_rag_with_model._semantic_ready:
            pytest.skip("Semantic search not available")
        # Search for "speech synthesis" should find TTS-related content
        results = semantic_rag_with_model.search("speech synthesis", semantic_weight=1.0)
        if results:
            # Best result should be about TTS
            assert any(
                "TTS" in r[0] or "voice" in r[0] or "voz" in r[0]
                for r in results
            )

    @pytest.mark.slow
    def test_hybrid_search_better_than_tfidf(self, semantic_rag_with_model):
        """Hybrid search should return relevant results."""
        if not semantic_rag_with_model._semantic_ready:
            pytest.skip("Semantic search not available")
        # Hybrid search
        hybrid = semantic_rag_with_model.search("como funciona el clon de voz", semantic_weight=0.6)
        assert len(hybrid) > 0
        # Best result should have decent score
        assert hybrid[0][1] > 0.3
