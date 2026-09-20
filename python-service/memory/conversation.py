"""
Luna JARVIS - Persistent Conversation Memory
Saves and loads conversation history across restarts.
Provides context-aware recall of recent conversations.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger("luna.memory.conversation")


class ConversationTurn:
    """A single turn in a conversation."""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None,
                 metadata: Optional[Dict] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationTurn":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


class ConversationSession:
    """A conversation session with multiple turns."""

    def __init__(self, session_id: Optional[str] = None, started_at: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.started_at = started_at or datetime.now().isoformat()
        self.turns: List[ConversationTurn] = []
        self._metadata: Dict[str, Any] = {}

    @property
    def message_count(self) -> int:
        return len(self.turns)

    @property
    def last_activity(self) -> Optional[str]:
        return self.turns[-1].timestamp if self.turns else self.started_at

    @property
    def summary(self) -> str:
        """Generate a brief summary of the conversation."""
        if not self.turns:
            return "Conversación vacía"
        user_msgs = [t.content for t in self.turns if t.role == "user"]
        if not user_msgs:
            return "Sin mensajes del usuario"
        # Show first and last user message
        first = user_msgs[0][:60]
        if len(user_msgs) > 1:
            last = user_msgs[-1][:60]
            return f"{first}... ({len(user_msgs)} mensajes, último: {last}...)"
        return first

    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a turn to the conversation."""
        self.turns.append(ConversationTurn(role, content, metadata=metadata))

    def get_recent_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context for the AI brain."""
        recent = self.turns[-max_turns:]
        return [{"role": t.role, "content": t.content} for t in recent]

    def get_topics(self) -> List[str]:
        """Extract mentioned topics from the conversation."""
        topics = set()
        for turn in self.turns:
            if turn.metadata and "topics" in turn.metadata:
                topics.update(turn.metadata["topics"])
        return list(topics)

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "turns": [t.to_dict() for t in self.turns],
            "metadata": self._metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationSession":
        session = cls(
            session_id=data.get("session_id"),
            started_at=data.get("started_at"),
        )
        for turn_data in data.get("turns", []):
            session.turns.append(ConversationTurn.from_dict(turn_data))
        session._metadata = data.get("metadata", {})
        return session


class ConversationMemory:
    """Persistent conversation memory manager.

    Stores conversations to disk and provides retrieval, search,
    and context-aware recall for the AI brain.
    """

    def __init__(self, storage_dir: str = "./memory/conversations",
                 max_sessions: int = 100,
                 max_turns_per_session: int = 200):
        self.storage_dir = Path(storage_dir)
        self.max_sessions = max_sessions
        self.max_turns_per_session = max_turns_per_session
        self.current_session: Optional[ConversationSession] = None
        self._sessions_cache: Dict[str, ConversationSession] = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create storage directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Start a new conversation session."""
        self.current_session = ConversationSession(session_id=session_id)
        logger.info(f"Started new conversation session: {self.current_session.session_id}")
        return self.current_session

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the current session. Auto-creates session if needed."""
        if not self.current_session:
            self.start_session()

        self.current_session.add_turn(role, content, metadata=metadata)

        # Auto-save periodically (every 5 turns)
        if len(self.current_session.turns) % 5 == 0:
            self.save_current()

    def end_session(self):
        """End and save the current session."""
        if self.current_session and self.current_session.turns:
            self.save_current()
            logger.info(
                f"Ended session {self.current_session.session_id} "
                f"({self.current_session.message_count} messages)"
            )
        self.current_session = None

    def save_current(self):
        """Save the current session to disk."""
        if not self.current_session:
            return

        session_id = self.current_session.session_id
        filepath = self.storage_dir / f"{session_id}.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.current_session.to_dict(), f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load a specific session from disk."""
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]

        filepath = self.storage_dir / f"{session_id}.json"
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = ConversationSession.from_dict(data)
            self._sessions_cache[session_id] = session
            return session
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def get_recent_sessions(self, limit: int = 10) -> List[ConversationSession]:
        """Get the most recent sessions sorted by last activity."""
        sessions = []
        for filepath in sorted(self.storage_dir.glob("*.json"), reverse=True)[:limit]:
            session_id = filepath.stem
            session = self.load_session(session_id)
            if session:
                sessions.append(session)
        return sessions

    def get_conversation_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context for the AI brain.

        Returns a list of message dicts that can be prepended to the
        conversation history for context continuity.
        """
        if self.current_session and self.current_session.turns:
            return self.current_session.get_recent_context(max_turns)

        # If no current session, load the most recent one
        recent = self.get_recent_sessions(limit=1)
        if recent:
            return recent[0].get_recent_context(max_turns)

        return []

    def search_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search across all conversations for relevant content.

        Simple keyword-based search. Returns matching turns with context.
        """
        query_lower = query.lower().split()
        results = []

        for filepath in self.storage_dir.glob("*.json"):
            session = self.load_session(filepath.stem)
            if not session:
                continue

            for i, turn in enumerate(session.turns):
                content_lower = turn.content.lower()
                matches = sum(1 for word in query_lower if word in content_lower)
                if matches > 0:
                    # Get surrounding context
                    context_start = max(0, i - 1)
                    context_end = min(len(session.turns), i + 2)
                    context = [
                        {"role": t.role, "content": t.content[:200]}
                        for t in session.turns[context_start:context_end]
                    ]
                    results.append({
                        "session_id": session.session_id,
                        "turn_index": i,
                        "content": turn.content[:300],
                        "timestamp": turn.timestamp,
                        "relevance": matches,
                        "context": context,
                    })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]

    def get_user_preferences(self) -> Dict[str, Any]:
        """Analyze past conversations to extract user preferences."""
        preferences = {
            "common_topics": defaultdict(int),
            "active_hours": defaultdict(int),
            "message_lengths": [],
            "question_ratio": 0,
        }

        total_user_msgs = 0
        questions = 0

        for filepath in self.storage_dir.glob("*.json"):
            session = self.load_session(filepath.stem)
            if not session:
                continue

            for turn in session.turns:
                if turn.role == "user":
                    total_user_msgs += 1
                    preferences["message_lengths"].append(len(turn.content))
                    if "?" in turn.content:
                        questions += 1

                    # Extract hour from timestamp
                    try:
                        dt = datetime.fromisoformat(turn.timestamp)
                        preferences["active_hours"][dt.hour] += 1
                    except (ValueError, TypeError):
                        pass

        if total_user_msgs > 0:
            preferences["question_ratio"] = questions / total_user_msgs

        # Convert to serializable format
        return {
            "total_sessions": len(list(self.storage_dir.glob("*.json"))),
            "total_user_messages": total_user_msgs,
            "avg_message_length": (
                sum(preferences["message_lengths"]) / len(preferences["message_lengths"])
                if preferences["message_lengths"] else 0
            ),
            "question_ratio": round(preferences["question_ratio"], 2),
            "peak_hours": sorted(
                preferences["active_hours"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
        }

    def cleanup_old_sessions(self, max_age_days: int = 30):
        """Remove sessions older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        for filepath in self.storage_dir.glob("*.json"):
            try:
                session = self.load_session(filepath.stem)
                if session and session.started_at:
                    session_date = datetime.fromisoformat(session.started_at)
                    if session_date < cutoff:
                        filepath.unlink()
                        removed += 1
            except Exception as e:
                logger.warning(f"Error cleaning up {filepath}: {e}")

        if removed > 0:
            logger.info(f"Cleaned up {removed} old conversation sessions")
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        sessions = list(self.storage_dir.glob("*.json"))
        total_turns = 0
        for filepath in sessions:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                total_turns += len(data.get("turns", []))
            except Exception:
                pass

        return {
            "stored_sessions": len(sessions),
            "total_turns": total_turns,
            "current_session": self.current_session.session_id if self.current_session else None,
            "storage_dir": str(self.storage_dir),
        }


# Singleton
_memory: Optional[ConversationMemory] = None


def get_conversation_memory(storage_dir: str = "./memory/conversations") -> ConversationMemory:
    """Get or create the singleton conversation memory."""
    global _memory
    if _memory is None:
        _memory = ConversationMemory(storage_dir=storage_dir)
    return _memory
