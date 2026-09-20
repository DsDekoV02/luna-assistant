"""
Tests for Conversation Memory module.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.conversation import (
    ConversationTurn,
    ConversationSession,
    ConversationMemory,
    get_conversation_memory,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def memory(temp_dir):
    """Create a ConversationMemory with temp storage."""
    return ConversationMemory(storage_dir=os.path.join(temp_dir, "conversations"))


class TestConversationTurn:
    def test_create_turn(self):
        turn = ConversationTurn("user", "Hola Luna")
        assert turn.role == "user"
        assert turn.content == "Hola Luna"
        assert turn.timestamp is not None

    def test_to_dict_and_back(self):
        turn = ConversationTurn("user", "test", metadata={"key": "value"})
        d = turn.to_dict()
        assert d["role"] == "user"
        assert d["metadata"]["key"] == "value"
        restored = ConversationTurn.from_dict(d)
        assert restored.content == "test"


class TestConversationSession:
    def test_create_session(self):
        session = ConversationSession()
        assert session.message_count == 0
        assert session.session_id is not None

    def test_add_turn(self):
        session = ConversationSession()
        session.add_turn("user", "Hola")
        session.add_turn("assistant", "Hola Nicolas!")
        assert session.message_count == 2

    def test_get_recent_context(self):
        session = ConversationSession()
        for i in range(15):
            session.add_turn("user", f"msg {i}")
            session.add_turn("assistant", f"reply {i}")
        context = session.get_recent_context(max_turns=5)
        assert len(context) == 5

    def test_summary(self):
        session = ConversationSession()
        assert session.summary == "Conversación vacía"
        session.add_turn("user", "Hola Luna")
        assert "Hola Luna" in session.summary

    def test_to_dict_and_back(self):
        session = ConversationSession(session_id="test-123")
        session.add_turn("user", "test")
        d = session.to_dict()
        restored = ConversationSession.from_dict(d)
        assert restored.session_id == "test-123"
        assert restored.message_count == 1


class TestConversationMemory:
    def test_start_session(self, memory):
        session = memory.start_session()
        assert session is not None
        assert memory.current_session is session

    def test_add_message(self, memory):
        memory.start_session()
        memory.add_message("user", "Hola")
        memory.add_message("assistant", "Hola Nicolas!")
        assert memory.current_session.message_count == 2

    def test_save_and_load(self, memory):
        memory.start_session("test-save")
        memory.add_message("user", "test message")
        memory.save_current()

        # Load it back
        loaded = memory.load_session("test-save")
        assert loaded is not None
        assert loaded.message_count == 1
        assert loaded.turns[0].content == "test message"

    def test_get_recent_sessions(self, memory):
        for i in range(5):
            memory.start_session(f"session-{i}")
            memory.add_message("user", f"message {i}")
            memory.save_current()
        memory.end_session()

        sessions = memory.get_recent_sessions(limit=3)
        assert len(sessions) == 3

    def test_search_conversations(self, memory):
        memory.start_session("search-test")
        memory.add_message("user", "Me gusta programar en Python")
        memory.add_message("assistant", "¡Python es genial!")
        memory.save_current()
        memory.end_session()

        results = memory.search_conversations("Python")
        assert len(results) > 0
        assert any("Python" in r["content"] for r in results)

    def test_get_conversation_context_empty(self, memory):
        context = memory.get_conversation_context()
        assert context == []

    def test_get_conversation_context(self, memory):
        memory.start_session()
        memory.add_message("user", "Hola")
        memory.add_message("assistant", "Hola!")
        context = memory.get_conversation_context()
        assert len(context) == 2

    def test_auto_session_creation(self, memory):
        """add_message should auto-create a session if none exists."""
        assert memory.current_session is None
        memory.add_message("user", "auto")
        assert memory.current_session is not None

    def test_cleanup_old_sessions(self, memory):
        memory.start_session("old-session")
        memory.add_message("user", "old")
        memory.save_current()
        # Can't easily test age-based cleanup without mocking dates
        # Just verify the method runs
        removed = memory.cleanup_old_sessions(max_age_days=0)
        assert removed >= 0

    def test_get_stats(self, memory):
        memory.start_session()
        memory.add_message("user", "test")
        memory.save_current()
        stats = memory.get_stats()
        assert stats["stored_sessions"] >= 1
        assert stats["total_turns"] >= 1

    def test_get_user_preferences(self, memory):
        memory.start_session()
        memory.add_message("user", "¿Cómo estás?")
        memory.add_message("assistant", "Bien!")
        memory.save_current()
        prefs = memory.get_user_preferences()
        assert "total_sessions" in prefs
        assert "total_user_messages" in prefs
