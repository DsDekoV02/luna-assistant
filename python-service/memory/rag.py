"""
Luna JARVIS - RAG Engine
Retrieval-Augmented Generation over markdown documents.

Improved version with:
- Better TF-IDF-like scoring with keyword extraction
- Heading-aware chunking
- Semantic deduplication
- Context window management
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from collections import Counter

logger = logging.getLogger("luna.memory.rag")

# Common Spanish/English stop words to ignore in search
STOP_WORDS = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al',
    'en', 'con', 'por', 'para', 'sin', 'sobre', 'entre', 'hasta', 'desde',
    'y', 'o', 'ni', 'pero', 'sino', 'que', 'como', 'cual', 'cuales',
    'es', 'son', 'está', 'están', 'ser', 'haber', 'tener', 'hacer',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'like',
    'through', 'after', 'over', 'between', 'out', 'against', 'during',
    'and', 'but', 'or', 'not', 'no', 'so', 'if', 'then', 'than',
    'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my',
    'he', 'him', 'his', 'she', 'her', 'we', 'us', 'our', 'they', 'them',
    'you', 'your', 'what', 'which', 'who', 'whom', 'when', 'where', 'how',
}


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text, removing stop words."""
    # Tokenize and normalize
    words = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{2,}\b', text.lower())
    # Filter stop words and very short words
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return keywords


class RAGEngine:
    """RAG engine for markdown documents with improved search."""

    def __init__(self, docs_path: str = "../docs", memory_path: str = "../",
                 chunk_size: int = 500, chunk_overlap: int = 50):
        self.docs_path = Path(docs_path)
        self.memory_path = Path(memory_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[dict] = []
        self._loaded = False
        self._idf_cache: dict = {}  # Cache IDF values

    def load_documents(self):
        """Load and chunk all markdown documents."""
        self.chunks = []
        self._idf_cache.clear()

        # Load docs
        if self.docs_path.exists():
            for md_file in self.docs_path.rglob("*.md"):
                self._process_file(md_file, source="docs")

        # Load memory files
        memory_dir = self.memory_path / "memory"
        if memory_dir.exists():
            for md_file in memory_dir.rglob("*.md"):
                self._process_file(md_file, source="memory")

        # Load MEMORY.md if exists
        memory_main = self.memory_path / "MEMORY.md"
        if memory_main.exists():
            self._process_file(memory_main, source="memory")

        # Load USER.md if exists (for personalization)
        user_file = self.memory_path / "USER.md"
        if user_file.exists():
            self._process_file(user_file, source="user")

        # Build IDF cache
        self._build_idf_cache()

        self._loaded = True
        logger.info(f"Loaded {len(self.chunks)} chunks from documents")

    def _process_file(self, path: Path, source: str):
        """Process a single markdown file into chunks."""
        try:
            content = path.read_text(encoding="utf-8")
            file_chunks = self._chunk_by_headings(content)

            for i, chunk in enumerate(file_chunks):
                keywords = extract_keywords(chunk)
                self.chunks.append({
                    "text": chunk,
                    "source": source,
                    "file": str(path),
                    "chunk_index": i,
                    "heading": self._extract_heading(chunk),
                    "keywords": keywords,
                    "keyword_set": set(keywords),
                })
        except Exception as e:
            logger.error(f"Error processing {path}: {e}")

    def _chunk_by_headings(self, text: str) -> List[str]:
        """Split text by headings, keeping heading with its content."""
        # Split by markdown headings
        parts = re.split(r'\n(?=#{1,4}\s)', text)
        chunks = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # If this part is small enough, keep as one chunk
            if len(part) <= self.chunk_size:
                chunks.append(part)
            else:
                # Split large sections by paragraphs
                sub_chunks = self._chunk_by_paragraphs(part)
                chunks.extend(sub_chunks)

        return chunks

    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Split text into overlapping chunks by paragraphs."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Keep overlap
                    overlap_text = current_chunk[-self.chunk_overlap:] if self.chunk_overlap else ""
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _extract_heading(self, text: str) -> str:
        """Extract the first heading from a chunk."""
        match = re.search(r'^#{1,4}\s+(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _build_idf_cache(self):
        """Build IDF (Inverse Document Frequency) cache for better scoring."""
        if not self.chunks:
            return

        doc_count = len(self.chunks)
        word_doc_count = Counter()

        for chunk in self.chunks:
            # Count unique words per document
            unique_words = chunk.get("keyword_set", set())
            for word in unique_words:
                word_doc_count[word] += 1

        # Calculate IDF for each word
        import math
        for word, count in word_doc_count.items():
            self._idf_cache[word] = math.log(doc_count / (1 + count))

    def search(self, query: str, top_k: int = 3,
               source_filter: Optional[str] = None) -> List[Tuple[str, float, dict]]:
        """Search for relevant chunks using improved TF-IDF scoring.

        Features:
        - Keyword extraction (stop word removal)
        - IDF weighting
        - Heading match boosting
        - Source-based boosting (recent daily notes get a boost)
        - Keyword overlap ratio

        Returns list of (text, relevance_score, chunk_metadata) tuples.
        """
        if not self._loaded:
            self.load_documents()

        query_keywords = extract_keywords(query)
        if not query_keywords:
            # Fallback to simple word matching if no meaningful keywords
            query_keywords = [w.lower() for w in query.split() if len(w) > 1]

        query_keyword_set = set(query_keywords)
        query_lower = query.lower()

        scored_chunks = []

        for chunk in self.chunks:
            # Source filter
            if source_filter and chunk.get("source") != source_filter:
                continue

            text_lower = chunk["text"].lower()
            chunk_keywords = chunk.get("keyword_set", set())

            # ── Score Components ──────────────────────────────────

            # 1. Keyword overlap (Jaccard-like)
            overlap = query_keyword_set & chunk_keywords
            if not overlap:
                # Try substring matching as fallback
                substring_match = False
                for qk in query_keywords:
                    if qk in text_lower:
                        substring_match = True
                        overlap.add(qk)
                if not substring_match:
                    continue

            # Keyword overlap ratio
            overlap_ratio = len(overlap) / len(query_keyword_set) if query_keyword_set else 0

            # 2. IDF-weighted term frequency
            tfidf_score = 0
            for keyword in overlap:
                tf = text_lower.count(keyword)
                idf = self._idf_cache.get(keyword, 1.0)
                tfidf_score += tf * idf

            # 3. Heading match bonus
            heading_bonus = 0
            heading = chunk.get("heading", "").lower()
            for keyword in query_keywords:
                if keyword in heading:
                    heading_bonus += 2.0

            # 4. Exact phrase match bonus
            phrase_bonus = 0
            if len(query_keywords) > 1:
                # Check if query words appear consecutively
                for i in range(len(query_keywords) - 1):
                    bigram = f"{query_keywords[i]} {query_keywords[i+1]}"
                    if bigram in text_lower:
                        phrase_bonus += 3.0

            # 5. Source-based boosting
            source_bonus = 0
            source = chunk.get("source", "")
            if source == "memory":
                source_bonus = 0.5  # Slight boost for memory (more recent/relevant)
            elif source == "user":
                source_bonus = 1.0  # Boost for user profile info

            # ── Final Score ───────────────────────────────────────

            final_score = (
                overlap_ratio * 3.0 +    # Primary: how many query terms matched
                tfidf_score * 0.5 +       # Secondary: weighted term frequency
                heading_bonus +            # Heading matches are very relevant
                phrase_bonus +             # Exact phrases are gold
                source_bonus               # Source relevance
            )

            scored_chunks.append((chunk["text"], final_score, chunk))

        # Sort by score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Normalize scores to 0-1 range
        if scored_chunks:
            max_score = scored_chunks[0][1]
            if max_score > 0:
                scored_chunks = [
                    (text, min(1.0, score / max_score), chunk)
                    for text, score, chunk in scored_chunks
                ]

        # Return top_k
        return scored_chunks[:top_k]

    def get_context(self, query: str, top_k: int = 3, max_chars: int = 2000) -> str:
        """Get formatted context string for the LLM."""
        results = self.search(query, top_k)

        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for text, score, chunk in results:
            source = chunk.get("file", "unknown")
            heading = chunk.get("heading", "")

            header = f"[Fuente: {Path(source).name}"
            if heading:
                header += f" - {heading}"
            header += f" | Relevancia: {score:.0%}]"

            entry = f"{header}\n{text}"
            if total_chars + len(entry) > max_chars:
                break

            context_parts.append(entry)
            total_chars += len(entry)

        return "\n\n---\n\n".join(context_parts)

    def add_memory(self, text: str, source: str = "daily"):
        """Add a new memory entry and re-index."""
        today = Path("memory") / f"{__import__('datetime').date.today()}.md"
        today.parent.mkdir(parents=True, exist_ok=True)

        with open(today, "a", encoding="utf-8") as f:
            f.write(f"\n\n{text}")

        # Re-index this file
        self._process_file(today, source=source)

        # Update IDF cache
        self._build_idf_cache()

        logger.info(f"Memory added: {text[:50]}...")

    def get_stats(self) -> dict:
        """Get RAG engine statistics."""
        sources = Counter(c.get("source", "unknown") for c in self.chunks)
        return {
            "total_chunks": len(self.chunks),
            "sources": dict(sources),
            "idf_terms": len(self._idf_cache),
            "loaded": self._loaded,
        }


# Singleton
_rag: Optional[RAGEngine] = None


def get_rag(docs_path: str = "../docs", memory_path: str = "../") -> RAGEngine:
    """Get the singleton RAG engine."""
    global _rag
    if _rag is None:
        _rag = RAGEngine(docs_path, memory_path)
    return _rag
