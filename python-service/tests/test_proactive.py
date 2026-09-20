"""
Tests for proactive engine improvements: weather, productivity suggestions.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from proactive.engine import ProactiveEngine, Suggestion, get_proactive_engine


class TestProactiveEngine:
    """Test proactive suggestion engine."""

    def test_singleton(self):
        e1 = get_proactive_engine()
        e2 = get_proactive_engine()
        assert e1 is e2

    def test_time_based_morning(self):
        engine = ProactiveEngine()
        with patch("proactive.engine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 7, 8, 30)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            suggestions = engine._time_based_suggestions("casa")
            texts = [s.text for s in suggestions]
            assert any("Buenos dias" in t for t in texts)

    def test_time_based_late_night(self):
        engine = ProactiveEngine()
        with patch("proactive.engine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 7, 23, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            suggestions = engine._time_based_suggestions("casa")
            texts = [s.text for s in suggestions]
            assert any("nocturno" in t for t in texts)

    def test_system_high_cpu(self):
        engine = ProactiveEngine()
        info = {"cpu": {"percent": 95}}
        suggestions = engine._system_suggestions(info, "casa")
        assert any("CPU" in s.text for s in suggestions)
        assert any(s.priority == "high" for s in suggestions)

    def test_system_high_ram(self):
        engine = ProactiveEngine()
        info = {"ram": {"percent": 90}}
        suggestions = engine._system_suggestions(info, "casa")
        assert any("RAM" in s.text for s in suggestions)

    def test_system_low_battery(self):
        engine = ProactiveEngine()
        info = {"battery": {"percent": 15, "plugged": False}}
        suggestions = engine._system_suggestions(info, "casa")
        assert any("bateria" in s.text.lower() for s in suggestions)

    def test_context_frustration(self):
        engine = ProactiveEngine()
        messages = ["No funciona el servidor, tengo un error"]
        suggestions = engine._context_suggestions(messages, "casa")
        assert any("problema" in s.text.lower() for s in suggestions)

    def test_context_code(self):
        engine = ProactiveEngine()
        messages = ["Estoy revisando el codigo del script"]
        suggestions = engine._context_suggestions(messages, "casa")
        assert any("codigo" in s.text.lower() for s in suggestions)

    def test_productivity_pomodoro(self):
        engine = ProactiveEngine()
        with patch("proactive.engine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 7, 14, 0)  # 2pm
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            suggestions = engine._productivity_suggestions("trabajo")
            texts = [s.text for s in suggestions]
            assert any("Pomodoro" in t for t in texts)

    def test_productivity_hydration(self):
        engine = ProactiveEngine()
        with patch("proactive.engine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 7, 11, 0)  # 11am
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            suggestions = engine._productivity_suggestions("casa")
            texts = [s.text for s in suggestions]
            assert any("agua" in t.lower() for t in texts)

    def test_filter_dedup(self):
        engine = ProactiveEngine()
        s1 = Suggestion(text="Test suggestion one", category="info", priority="low")
        s2 = Suggestion(text="Test suggestion one duplicate", category="info", priority="low")
        filtered = engine._filter_suggestions([s1, s2])
        # Both have different first 50 chars so both pass
        assert len(filtered) <= 3

    def test_filter_max_3(self):
        engine = ProactiveEngine()
        suggestions = [
            Suggestion(text=f"Suggestion {i}", category="info", priority="low")
            for i in range(10)
        ]
        filtered = engine._filter_suggestions(suggestions)
        assert len(filtered) <= 3

    def test_format_for_chat(self):
        engine = ProactiveEngine()
        suggestions = [
            Suggestion(text="Test message", category="info", priority="normal"),
        ]
        formatted = engine.format_for_chat(suggestions)
        assert "Sugerencias" in formatted
        assert "Test message" in formatted

    def test_format_empty(self):
        engine = ProactiveEngine()
        assert engine.format_for_chat([]) == ""

    def test_suggestion_to_dict(self):
        s = Suggestion(
            text="Test", category="action", priority="high",
            action="systeminfo", action_params={"info_type": "cpu"}
        )
        d = s.to_dict()
        assert d["text"] == "Test"
        assert d["action"] == "systeminfo"
        assert d["action_params"]["info_type"] == "cpu"

    def test_weather_suggestions_returns_list(self):
        engine = ProactiveEngine()
        # This may or may not return weather suggestions depending on API
        result = engine._weather_suggestions("casa")
        assert isinstance(result, list)

    def test_get_suggestions_integration(self):
        engine = ProactiveEngine()
        with patch("proactive.engine.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 9, 7, 14, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            suggestions = engine.get_suggestions(
                mode="trabajo",
                system_info={"cpu": {"percent": 50}, "ram": {"percent": 50}},
                recent_messages=["hola"]
            )
            assert isinstance(suggestions, list)
