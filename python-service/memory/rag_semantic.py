"""
Luna JARVIS - Semantic RAG Engine
Retrieval-Augmented Generation using ChromaDB + sentence-transformers.

Drop-in replacement for the TF-IDF RAG engine with semantic search.
Falls back to TF-IDF if ChromaDB/sentence-transformers are not available.
"""

import re
import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from collections import Counter

logger = logging.getLogger("luna.memory.rag_semantic")

# Try to import semantic search dependencies
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("ChromaDB not available. Semantic RAG disabled.")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not available. Semantic RAG disabled.")

# Import the base TF-IDF engine as fallback
from memory.rag import RAGEngine, extract_keywords, STOP_WORDS


# Default embedding model (multilingual, good for Spanish)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class SemanticRAGEngine(RAGEngine):
    """RAG engine with semantic search using ChromaDB + sentence-transformers.

    Extends the base TF-IDF RAG engine with:
    - ChromaDB vector storage for persistent embeddings
    - sentence-transformers for semantic similarity
    - Hybrid search: combines TF-IDF keyword matching + semantic similarity
    - Automatic fallback to TF-IDF if dependencies unavailable
    """

    def __init__(
        self,
        docs_path: str = "../docs",
        memory_path: str = "../",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        chroma_path: str = "./chroma_db",
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        use_semantic: bool = True,
    ):
        super().__init__(docs_path, memory_path, chunk_size, chunk_overlap)
        self.chroma_path = Path(chroma_path)
        self.embedding_model_name = embedding_model
        self.use_semantic = use_semantic and CHROMA_AVAILABLE and ST_AVAILABLE

        # Semantic components
        self._embedder: Optional[SentenceTransformer] = None
        self._chroma_client = None
        self._collection = None
        self._semantic_ready = False

        if self.use_semantic:
            self._init_semantic()

    def _init_semantic(self):
        """Initialize ChromaDB and sentence-transformers."""
        try:
            # Initialize sentence-transformers embedder
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedder = SentenceTransformer(self.embedding_model_name)

            # Initialize ChromaDB (persistent storage)
            self.chroma_path.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_path)
            )

            # Get or create collection
            self._collection = self._chroma_client.get_or_create_collection(
                name="luna_docs",
                metadata={"hnsw:space": "cosine"}
            )

            self._semantic_ready = True
            logger.info(f"Semantic RAG initialized. Collection: {self._collection.name}, "
                        f"Documents: {self._collection.count()}")

        except Exception as e:
            logger.error(f"Failed to initialize semantic RAG: {e}")
            self.use_semantic = False
            self._semantic_ready = False

    def load_documents(self):
        """Load documents and build both TF-IDF and semantic indexes."""
        # Load TF-IDF index (parent class)
        super().load_documents()

        # Build semantic index
        if self._semantic_ready:
            self._build_semantic_index()

    def _build_semantic_index(self):
        """Index all chunks into ChromaDB with embeddings."""
        if not self._semantic_ready or not self.chunks:
            return

        existing_count = self._collection.count()

        # Check if we need to re-index
        # Use a hash of total chunks to detect changes
        current_hash = hashlib.md5(
            str(len(self.chunks)).encode()
        ).hexdigest()[:8]

        if existing_count > 0:
            # Check if collection metadata matches
            try:
                meta = self._collection.metadata or {}
                if meta.get("index_hash") == current_hash:
                    logger.info(f"Semantic index up to date ({existing_count} chunks)")
                    return
            except Exception:
                pass

        logger.info(f"Building semantic index for {len(self.chunks)} chunks...")

        # Clear existing collection
        try:
            self._chroma_client.delete_collection("luna_docs")
            self._collection = self._chroma_client.get_or_create_collection(
                name="luna_docs",
                metadata={"hnsw:space": "cosine", "index_hash": current_hash}
            )
        except Exception:
            pass

        # Prepare documents for indexing
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(self.chunks):
            chunk_id = f"chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append({
                "source": chunk.get("source", "unknown"),
                "file": chunk.get("file", "unknown"),
                "heading": chunk.get("heading", ""),
                "chunk_index": chunk.get("chunk_index", 0),
            })

        # Batch insert (ChromaDB handles embedding automatically if we provide documents)
        # But we'll generate embeddings manually for better control
        batch_size = 100
        for start in range(0, len(ids), batch_size):
            end = min(start + batch_size, len(ids))
            batch_ids = ids[start:end]
            batch_docs = documents[start:end]
            batch_meta = metadatas[start:end]

            # Generate embeddings
            embeddings = self._embedder.encode(batch_docs, show_progress_bar=False).tolist()

            self._collection.add(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=embeddings,
                metadatas=batch_meta,
            )

        logger.info(f"Semantic index built: {len(ids)} chunks indexed")

    def _semantic_search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None,
    ) -> List[Tuple[str, float, dict]]:
        """Search using semantic similarity via ChromaDB."""
        if not self._semantic_ready:
            return []

        try:
            # Generate query embedding
            query_embedding = self._embedder.encode([query], show_progress_bar=False).tolist()

            # Build where filter
            where = None
            if source_filter:
                where = {"source": source_filter}

            # Query ChromaDB
            results = self._collection.query(
                query_embeddings=query_embedding,
                n_results=min(top_k, self._collection.count() or 1),
                where=where,
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results["documents"] or not results["documents"][0]:
                return []

            # Convert to our format
            semantic_results = []
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity score (0-1, higher = more similar)
                similarity = max(0, 1 - distance)

                # Find matching chunk metadata
                chunk_meta = {
                    "source": meta.get("source", "unknown"),
                    "file": meta.get("file", "unknown"),
                    "heading": meta.get("heading", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }

                semantic_results.append((doc, similarity, chunk_meta))

            return semantic_results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def search(
        self,
        query: str,
        top_k: int = 3,
        source_filter: Optional[str] = None,
        semantic_weight: float = 0.6,
    ) -> List[Tuple[str, float, dict]]:
        """Hybrid search: combines TF-IDF keyword matching + semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            source_filter: Filter by source (docs, memory, user)
            semantic_weight: Weight for semantic vs TF-IDF (0-1).
                            0 = pure TF-IDF, 1 = pure semantic.
                            Default 0.6 favors semantic.

        Returns:
            List of (text, relevance_score, chunk_metadata) tuples.
        """
        # Get TF-IDF results (always available)
        tfidf_results = super().search(query, top_k=top_k * 2, source_filter=source_filter)

        # Get semantic results if available
        semantic_results = []
        if self._semantic_ready and semantic_weight > 0:
            semantic_results = self._semantic_search(
                query, top_k=top_k * 2, source_filter=source_filter
            )

        # If no semantic results, fall back to TF-IDF only
        if not semantic_results:
            return tfidf_results[:top_k]

        # Merge results using reciprocal rank fusion
        combined = self._merge_results(
            tfidf_results, semantic_results,
            semantic_weight=semantic_weight,
        )

        return combined[:top_k]

    def _merge_results(
        self,
        tfidf_results: List[Tuple[str, float, dict]],
        semantic_results: List[Tuple[str, float, dict]],
        semantic_weight: float = 0.6,
    ) -> List[Tuple[str, float, dict]]:
        """Merge TF-IDF and semantic results using weighted RRF (Reciprocal Rank Fusion)."""
        tfidf_weight = 1 - semantic_weight
        k = 60  # RRF constant

        # Score each unique text
        scores: Dict[str, float] = {}
        text_map: Dict[str, Tuple[str, dict]] = {}

        # Add TF-IDF scores
        for rank, (text, score, chunk) in enumerate(tfidf_results):
            text_key = text[:200]  # Use first 200 chars as key
            rrf_score = tfidf_weight / (k + rank + 1)
            scores[text_key] = scores.get(text_key, 0) + rrf_score
            text_map[text_key] = (text, chunk)

        # Add semantic scores
        for rank, (text, score, chunk) in enumerate(semantic_results):
            text_key = text[:200]
            rrf_score = semantic_weight / (k + rank + 1)
            scores[text_key] = scores.get(text_key, 0) + rrf_score
            text_map[text_key] = (text, chunk)

        # Sort by combined score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        # Normalize scores to 0-1
        max_score = scores[sorted_keys[0]] if sorted_keys else 1

        results = []
        for key in sorted_keys:
            text, chunk = text_map[key]
            normalized_score = min(1.0, scores[key] / max_score)
            results.append((text, normalized_score, chunk))

        return results

    def get_stats(self) -> dict:
        """Get RAG engine statistics including semantic index info."""
        stats = super().get_stats()
        stats["semantic_enabled"] = self._semantic_ready
        stats["embedding_model"] = self.embedding_model_name if self._semantic_ready else None
        stats["chroma_path"] = str(self.chroma_path)
        if self._semantic_ready and self._collection:
            stats["semantic_chunks"] = self._collection.count()
        return stats

    def add_memory(self, text: str, source: str = "daily"):
        """Add memory and update both TF-IDF and semantic indexes."""
        super().add_memory(text, source)

        # Add to semantic index
        if self._semantic_ready and self.chunks:
            new_chunk = self.chunks[-1]  # Last added chunk
            try:
                embedding = self._embedder.encode([text], show_progress_bar=False).tolist()
                self._collection.add(
                    ids=[f"chunk_{len(self.chunks) - 1}"],
                    documents=[text],
                    embeddings=embedding,
                    metadatas=[{
                        "source": source,
                        "file": str(new_chunk.get("file", "")),
                        "heading": new_chunk.get("heading", ""),
                        "chunk_index": new_chunk.get("chunk_index", 0),
                    }],
                )
                logger.info(f"Semantic index updated with new memory")
            except Exception as e:
                logger.error(f"Failed to update semantic index: {e}")


# Factory function
def get_semantic_rag(
    docs_path: str = "../docs",
    memory_path: str = "../",
    chroma_path: str = "./chroma_db",
) -> SemanticRAGEngine:
    """Get or create the semantic RAG engine."""
    engine = SemanticRAGEngine(
        docs_path=docs_path,
        memory_path=memory_path,
        chroma_path=chroma_path,
    )
    return engine
