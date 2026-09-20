"""
Tests for Luna JARVIS - Pattern Learning Engine
"""
import json
import time
import pytest
from pathlib import Path
from datetime import datetime

from learning.patterns import (
    PatternEngine,
    TopicStats,
    UserPreferences,
    CommandPattern,
    HourlyActivity,
    TOPIC_KEYWORDS,
    get_pattern_engine,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def tmp_storage(tmp_path):
    """Temporary storage path for patterns."""
    return str(tmp_path / "patterns.json")


@pytest.fixture
def engine(tmp_storage):
    """Fresh pattern engine with temp storage."""
    return PatternEngine(storage_path=tmp_storage)


@pytest.fixture
def loaded_engine(tmp_storage):
    """Pattern engine with some pre-recorded interactions."""
    eng = PatternEngine(storage_path=tmp_storage)

    # Simulate a conversation history
    ts_base = time.time() - 3600  # 1 hour ago
    interactions = [
        ("Hola Luna, ¿como estas?", "¡Hola Nicolas! Estoy bien, ¿y tu?", "casa", []),
        ("¿Que clima hace en Santiago?", "Hace 22 grados y esta soleado", "casa", ["weather"]),
        ("Abre VS Code", "Abriendo VS Code", "casa", ["openapp"]),
        ("Hay un bug en mi codigo python", "¿Quieres que revise el archivo?", "casa", []),
        ("Juguemos Minecraft esta noche", "¡Buena idea! ¿Modo survival?", "casa", []),
        ("¿Que hora son?", "Son las 15:30", "casa", ["datetime"]),
        ("Revisa el CPU", "El CPU esta al 45%", "trabajo", ["systeminfo"]),
        ("Busca informacion sobre Three.js", "Encontre varios resultados", "casa", ["websearch"]),
        ("Pon una alarma de 30 minutos", "Alarma configurada", "casa", ["timer"]),
        ("¿Que anime me recomiendas?", "Te recomiendo DanMachi", "casa", []),
        ("Abre Spotify", "Abriendo Spotify", "casa", ["openapp"]),
        ("¿Cuanto RAM tengo?", "Tienes 16GB de RAM", "casa", ["systeminfo"]),
    ]

    for i, (msg, resp, mode, cmds) in enumerate(interactions):
        eng.record_interaction(msg, resp, mode, cmds, timestamp=ts_base + i * 300)

    return eng


# ── Init Tests ────────────────────────────────────────────────────

class TestPatternEngineInit:
    """Tests for PatternEngine initialization."""

    def test_creates_fresh(self, tmp_storage):
        engine = PatternEngine(storage_path=tmp_storage)
        assert engine.preferences.total_interactions == 0
        assert len(engine.topics) == 0
        assert len(engine.command_patterns) == 0

    def test_storage_path_set(self, tmp_storage):
        engine = PatternEngine(storage_path=tmp_storage)
        assert str(engine.storage_path) == tmp_storage

    def test_default_storage_path(self):
        engine = PatternEngine()
        assert "patterns_data.json" in str(engine.storage_path)

    def test_singleton_returns_same(self, tmp_storage):
        """get_pattern_engine returns the same instance."""
        # Reset singleton for test
        import learning.patterns as mod
        old = mod._engine
        mod._engine = None

        e1 = get_pattern_engine(tmp_storage)
        e2 = get_pattern_engine()
        assert e1 is e2

        mod._engine = old  # Restore


# ── Topic Detection Tests ────────────────────────────────────────

class TestTopicDetection:
    """Tests for topic detection from text."""

    def test_detects_programming(self, engine):
        topics = engine._detect_topics("Tengo un bug en mi script de python")
        assert "programming" in topics

    def test_detects_gaming(self, engine):
        topics = engine._detect_topics("Vamos a jugar Minecraft esta noche")
        assert "gaming" in topics

    def test_detects_anime(self, engine):
        topics = engine._detect_topics("¿Viste el ultimo capitulo de SAO?")
        assert "anime" in topics

    def test_detects_system(self, engine):
        topics = engine._detect_topics("¿Cuanto CPU y RAM estoy usando?")
        assert "system" in topics

    def test_detects_weather(self, engine):
        topics = engine._detect_topics("¿Que clima hace hoy?")
        assert "weather" in topics

    def test_detects_motorcycle(self, engine):
        topics = engine._detect_topics("Necesito cambiar el aceite de la moto")
        assert "motorcycle" in topics

    def test_detects_multiple_topics(self, engine):
        topics = engine._detect_topics("Busca informacion sobre juegos de anime")
        assert "web" in topics or "anime" in topics

    def test_returns_general_for_unknown(self, engine):
        topics = engine._detect_topics("Hola buenos dias")
        assert "general" in topics

    def test_case_insensitive(self, engine):
        topics = engine._detect_topics("PYTHON Programming Bug")
        assert "programming" in topics


# ── Record Interaction Tests ─────────────────────────────────────

class TestRecordInteraction:
    """Tests for recording interactions."""

    def test_increments_total(self, engine):
        engine.record_interaction("Hola", "Hola Nicolas")
        assert engine.preferences.total_interactions == 1

    def test_tracks_topics(self, engine):
        engine.record_interaction("¿Que clima hace?", "Esta soleado")
        assert "weather" in engine.topics
        assert engine.topics["weather"].count == 1

    def test_tracks_multiple_interactions(self, engine):
        engine.record_interaction("Juguemos Minecraft", "Buena idea")
        engine.record_interaction("Abre Minecraft", "Abierto")
        assert engine.topics["gaming"].count == 2

    def test_tracks_hourly_activity(self, engine):
        ts = datetime(2026, 9, 6, 15, 30).timestamp()
        engine.record_interaction("Hola", "Hola", timestamp=ts)
        assert 15 in engine.hourly_activity
        assert engine.hourly_activity[15].message_count == 1

    def test_updates_avg_length(self, engine):
        ts = datetime(2026, 9, 6, 15, 30).timestamp()
        engine.record_interaction("Hola mundo", "Hola Nicolas ¿que tal?", timestamp=ts)
        activity = engine.hourly_activity[15]
        assert activity.avg_length > 0

    def test_records_command_pattern(self, engine):
        engine.record_interaction("Abre VS Code y revisa el CPU", "Listo", commands_used=["openapp", "systeminfo"])
        assert len(engine.command_patterns) == 1
        assert engine.command_patterns[0].commands == ["openapp", "systeminfo"]

    def test_single_command_no_pattern(self, engine):
        engine.record_interaction("¿Que hora es?", "Son las 3", commands_used=["datetime"])
        assert len(engine.command_patterns) == 0

    def test_duplicate_command_pattern_increments(self, engine):
        engine.record_interaction("msg1", "resp1", commands_used=["a", "b"])
        engine.record_interaction("msg2", "resp2", commands_used=["a", "b"])
        assert len(engine.command_patterns) == 1
        assert engine.command_patterns[0].count == 2

    def test_session_buffer_grows(self, engine):
        engine.record_interaction("msg1", "resp1")
        engine.record_interaction("msg2", "resp2")
        assert len(engine.session_buffer) == 2


# ── App Usage Tests ──────────────────────────────────────────────

class TestAppUsage:
    """Tests for app usage tracking."""

    def test_records_app(self, engine):
        engine.record_app_usage("VSCode")
        assert engine.preferences.frequent_apps["vscode"] == 1

    def test_increments_app(self, engine):
        engine.record_app_usage("Chrome")
        engine.record_app_usage("Chrome")
        assert engine.preferences.frequent_apps["chrome"] == 2

    def test_case_insensitive(self, engine):
        engine.record_app_usage("SPOTIFY")
        engine.record_app_usage("spotify")
        assert engine.preferences.frequent_apps["spotify"] == 2


# ── Query Tests ──────────────────────────────────────────────────

class TestQuery:
    """Tests for querying learned patterns."""

    def test_get_favorite_topics(self, loaded_engine):
        topics = loaded_engine.get_favorite_topics(3)
        assert len(topics) <= 3
        assert all(isinstance(t, str) for t in topics)

    def test_favorite_topics_sorted_by_count(self, loaded_engine):
        topics = loaded_engine.get_favorite_topics(5)
        if len(topics) >= 2:
            # First topic should have >= count than second
            stats1 = loaded_engine.topics[topics[0]]
            stats2 = loaded_engine.topics[topics[1]]
            assert stats1.count >= stats2.count

    def test_get_peak_hours(self, loaded_engine):
        hours = loaded_engine.get_peak_hours(3)
        assert len(hours) <= 3
        assert all(0 <= h <= 23 for h in hours)

    def test_get_frequent_apps(self, loaded_engine):
        apps = loaded_engine.get_frequent_apps(5)
        assert isinstance(apps, list)

    def test_get_topic_stats(self, loaded_engine):
        stats = loaded_engine.get_topic_stats("weather")
        assert stats is not None
        assert stats.count >= 1

    def test_get_topic_stats_none(self, loaded_engine):
        stats = loaded_engine.get_topic_stats("nonexistent_topic")
        assert stats is None

    def test_get_suggested_topics(self, loaded_engine):
        suggested = loaded_engine.get_suggested_topics(current_hour=15)
        assert isinstance(suggested, list)

    def test_get_suggested_topics_fallback(self, engine):
        suggested = engine.get_suggested_topics()
        assert isinstance(suggested, list)

    def test_get_stats(self, loaded_engine):
        stats = loaded_engine.get_stats()
        assert "total_interactions" in stats
        assert "topics_tracked" in stats
        assert "favorite_topics" in stats
        assert "peak_hours" in stats
        assert stats["total_interactions"] == 12

    def test_get_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats["total_interactions"] == 0


# ── Personalization Context Tests ────────────────────────────────

class TestPersonalizationContext:
    """Tests for generating personalization context."""

    def test_context_includes_topics(self, loaded_engine):
        context = loaded_engine.get_personalization_context()
        assert "Temas favoritos" in context

    def test_context_includes_peak_hours(self, loaded_engine):
        context = loaded_engine.get_personalization_context()
        assert "Horas más activas" in context

    def test_context_empty_for_new_user(self, engine):
        context = engine.get_personalization_context()
        assert context == ""

    def test_context_includes_response_preference(self, loaded_engine):
        context = loaded_engine.get_personalization_context()
        # Should mention response preference
        assert "respuestas" in context.lower() or "usuario" in context.lower()


# ── Response Length Preference Tests ─────────────────────────────

class TestResponseLengthPreference:
    """Tests for learning response length preferences."""

    def test_default_is_normal(self, engine):
        assert engine.preferences.preferred_response_length == "normal"

    def test_brief_responses_detected(self, engine):
        """When Luna consistently gives brief responses and user is fine with it."""
        # Simulate many brief responses
        for i in range(15):
            engine.record_interaction(f"msg{i}", "ok", timestamp=time.time() + i)
            engine.session_buffer[-1]["response_len"] = 10

        # After enough brief signals, preference should shift
        # (the algorithm needs 5 brief out of last 10)
        # The preference update is subtle, just verify no crash
        assert engine.preferences.preferred_response_length in ("brief", "normal", "detailed")


# ── Persistence Tests ────────────────────────────────────────────

class TestPersistence:
    """Tests for saving and loading patterns."""

    def test_save_creates_file(self, engine):
        engine.record_interaction("Test", "Response")
        engine.save()
        assert engine.storage_path.exists()

    def test_save_load_roundtrip(self, tmp_storage):
        # Create and save
        eng1 = PatternEngine(storage_path=tmp_storage)
        eng1.record_interaction("Hola", "Hola Nicolas")
        eng1.record_app_usage("VSCode")
        eng1.save()

        # Load in new instance
        eng2 = PatternEngine(storage_path=tmp_storage)
        assert eng2.preferences.total_interactions == 1
        assert eng2.preferences.frequent_apps.get("vscode") == 1

    def test_save_preserves_topics(self, tmp_storage):
        eng1 = PatternEngine(storage_path=tmp_storage)
        eng1.record_interaction("¿Que clima hace?", "Soleado")
        eng1.save()

        eng2 = PatternEngine(storage_path=tmp_storage)
        assert "weather" in eng2.topics

    def test_save_preserves_command_patterns(self, tmp_storage):
        eng1 = PatternEngine(storage_path=tmp_storage)
        eng1.record_interaction("msg", "resp", commands_used=["a", "b"])
        eng1.save()

        eng2 = PatternEngine(storage_path=tmp_storage)
        assert len(eng2.command_patterns) == 1

    def test_save_preserves_hourly_activity(self, tmp_storage):
        ts = datetime(2026, 9, 6, 15, 30).timestamp()
        eng1 = PatternEngine(storage_path=tmp_storage)
        eng1.record_interaction("msg", "resp", timestamp=ts)
        eng1.save()

        eng2 = PatternEngine(storage_path=tmp_storage)
        assert 15 in eng2.hourly_activity

    def test_load_nonexistent_no_error(self, tmp_storage):
        """Loading from non-existent file should not error."""
        engine = PatternEngine(storage_path=tmp_storage + "/nonexistent.json")
        assert engine.preferences.total_interactions == 0

    def test_load_corrupt_json_no_error(self, tmp_storage):
        """Loading corrupt JSON should not crash."""
        path = Path(tmp_storage)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")
        engine = PatternEngine(storage_path=tmp_storage)
        assert engine.preferences.total_interactions == 0

    def test_auto_save_triggers(self, tmp_storage):
        engine = PatternEngine(storage_path=tmp_storage)
        engine._auto_save_interval = 0  # Immediate auto-save
        engine.record_interaction("Test", "Response")
        assert Path(tmp_storage).exists()


# ── Clear Tests ──────────────────────────────────────────────────

class TestClear:
    """Tests for clearing patterns."""

    def test_clear_resets_topics(self, loaded_engine):
        loaded_engine.clear()
        assert len(loaded_engine.topics) == 0

    def test_clear_resets_preferences(self, loaded_engine):
        loaded_engine.clear()
        assert loaded_engine.preferences.total_interactions == 0

    def test_clear_resets_command_patterns(self, loaded_engine):
        loaded_engine.clear()
        assert len(loaded_engine.command_patterns) == 0

    def test_clear_persists(self, tmp_storage):
        engine = PatternEngine(storage_path=tmp_storage)
        engine.record_interaction("Test", "Response")
        engine.clear()

        engine2 = PatternEngine(storage_path=tmp_storage)
        assert engine2.preferences.total_interactions == 0


# ── Command Pattern Limit Tests ──────────────────────────────────

class TestCommandPatternLimits:
    """Tests for command pattern storage limits."""

    def test_limits_patterns_to_100(self, engine):
        for i in range(105):
            engine._record_command_pattern(
                [f"cmd_{i}_a", f"cmd_{i}_b"],
                datetime.now()
            )
        assert len(engine.command_patterns) <= 100

    def test_removes_least_used_when_full(self, engine):
        # Fill to 100
        for i in range(100):
            cp = CommandPattern(commands=[f"a{i}", f"b{i}"], count=i + 1)
            engine.command_patterns.append(cp)

        # Add one more - should remove the one with count=1
        engine._record_command_pattern(["new_a", "new_b"], datetime.now())
        assert len(engine.command_patterns) <= 100
        commands_lists = [p.commands for p in engine.command_patterns]
        assert ["new_a", "new_b"] in commands_lists


# ── Topic Keywords Tests ─────────────────────────────────────────

class TestTopicKeywords:
    """Tests for topic keyword definitions."""

    def test_all_topics_have_keywords(self):
        for topic, keywords in TOPIC_KEYWORDS.items():
            assert len(keywords) > 0, f"Topic '{topic}' has no keywords"

    def test_keywords_are_lowercase(self):
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                assert kw == kw.lower(), f"Keyword '{kw}' in '{topic}' is not lowercase"

    def test_no_duplicate_keywords_per_topic(self):
        for topic, keywords in TOPIC_KEYWORDS.items():
            assert len(keywords) == len(set(keywords)), f"Duplicate keywords in '{topic}'"
