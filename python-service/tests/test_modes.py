"""
Luna JARVIS - Tests for Mode Manager
Tests operational modes: Moto, Casa, Trabajo, Noche.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modes.manager import (
    Mode, MotoMode, CasaMode, TrabajoMode, NocheMode,
    ModeManager, MODES, get_mode_manager,
)


# ── Base Mode ────────────────────────────────────────────────────

class TestBaseMode:
    def test_should_respond_default(self):
        mode = Mode("test", "Test mode")
        assert mode.should_respond() is True
        assert mode.should_respond("high") is True

    def test_response_style(self):
        mode = Mode("test", "Test mode")
        assert mode.get_response_style() == "normal"

    def test_format_response_identity(self):
        mode = Mode("test", "Test mode")
        assert mode.format_response("hola") == "hola"


# ── Moto Mode ────────────────────────────────────────────────────

class TestMotoMode:
    def test_name(self):
        mode = MotoMode()
        assert mode.name == "moto"

    def test_should_respond_always(self):
        mode = MotoMode()
        assert mode.should_respond() is True
        assert mode.should_respond("low") is True
        assert mode.should_respond("critical") is True

    def test_response_style_brief(self):
        mode = MotoMode()
        assert mode.get_response_style() == "brief"

    def test_format_response_shortens_long_text(self):
        mode = MotoMode()
        # Needs >200 chars to trigger shortening
        long_text = ". ".join(["Esta es una oracion de prueba numero " + str(i) for i in range(20)])
        assert len(long_text) > 200
        result = mode.format_response(long_text)
        # Should be shortened
        assert len(result) < len(long_text)

    def test_format_response_keeps_short_text(self):
        mode = MotoMode()
        short_text = "Hola Nicolas."
        result = mode.format_response(short_text)
        assert result == short_text


# ── Casa Mode ────────────────────────────────────────────────────

class TestCasaMode:
    def test_name(self):
        mode = CasaMode()
        assert mode.name == "casa"

    def test_should_respond(self):
        mode = CasaMode()
        assert mode.should_respond() is True

    def test_response_style(self):
        mode = CasaMode()
        assert mode.get_response_style() == "normal"


# ── Trabajo Mode ─────────────────────────────────────────────────

class TestTrabajoMode:
    def test_name(self):
        mode = TrabajoMode()
        assert mode.name == "trabajo"

    def test_should_respond_normal_priority(self):
        mode = TrabajoMode()
        # Normal priority should be suppressed in work mode
        assert mode.should_respond("normal") is False

    def test_should_respond_high_priority(self):
        mode = TrabajoMode()
        assert mode.should_respond("high") is True

    def test_should_respond_critical(self):
        mode = TrabajoMode()
        assert mode.should_respond("critical") is True

    def test_response_style(self):
        mode = TrabajoMode()
        assert mode.get_response_style() == "concise"


# ── Noche Mode ───────────────────────────────────────────────────

class TestNocheMode:
    def test_name(self):
        mode = NocheMode()
        assert mode.name == "noche"

    def test_default_hours(self):
        mode = NocheMode()
        assert mode.start_hour == 23
        assert mode.end_hour == 8

    def test_custom_hours(self):
        mode = NocheMode(start_hour=22, end_hour=7)
        assert mode.start_hour == 22
        assert mode.end_hour == 7

    def test_quiet_hours_night(self):
        mode = NocheMode(start_hour=23, end_hour=8)
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 2
            assert mode.is_quiet_hours() is True

    def test_quiet_hours_day(self):
        mode = NocheMode(start_hour=23, end_hour=8)
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 14
            assert mode.is_quiet_hours() is False

    def test_quiet_hours_boundary_start(self):
        mode = NocheMode(start_hour=23, end_hour=8)
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 23
            assert mode.is_quiet_hours() is True

    def test_quiet_hours_boundary_end(self):
        mode = NocheMode(start_hour=23, end_hour=8)
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 8
            assert mode.is_quiet_hours() is False

    def test_should_respond_during_quiet_hours(self):
        mode = NocheMode()
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 2
            # Normal priority should be suppressed
            assert mode.should_respond("normal") is False
            # Critical should still work
            assert mode.should_respond("critical") is True

    def test_should_respond_outside_quiet_hours(self):
        mode = NocheMode()
        with patch("modes.manager.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 14
            assert mode.should_respond("normal") is True


# ── Mode Manager ─────────────────────────────────────────────────

class TestModeManager:
    def test_default_mode(self):
        manager = ModeManager()
        assert manager.current_mode_name == "casa"

    def test_custom_default(self):
        manager = ModeManager("moto")
        assert manager.current_mode_name == "moto"

    def test_set_mode_valid(self):
        manager = ModeManager()
        assert manager.set_mode("moto") is True
        assert manager.current_mode_name == "moto"

    def test_set_mode_invalid(self):
        manager = ModeManager()
        assert manager.set_mode("invalid_mode") is False
        # Should stay on previous mode
        assert manager.current_mode_name == "casa"

    def test_should_respond_delegates(self):
        manager = ModeManager("casa")
        assert manager.should_respond() is True

    def test_system_prompt_modifier_moto(self):
        manager = ModeManager("moto")
        modifier = manager.get_system_prompt_modifier()
        assert "CONDUCCIÓN" in modifier or "conduccion" in modifier.lower()

    def test_system_prompt_modifier_trabajo(self):
        manager = ModeManager("trabajo")
        modifier = manager.get_system_prompt_modifier()
        assert "TRABAJO" in modifier or "trabajo" in modifier.lower()

    def test_system_prompt_modifier_casa(self):
        manager = ModeManager("casa")
        modifier = manager.get_system_prompt_modifier()
        # Casa has no special modifier
        assert modifier == ""

    def test_get_status(self):
        manager = ModeManager("casa")
        status = manager.get_status()
        assert "mode" in status
        assert status["mode"] == "casa"
        assert "description" in status

    def test_get_status_moto(self):
        manager = ModeManager("moto")
        status = manager.get_status()
        assert status["mode"] == "moto"
        assert status["style"] == "brief"


# ── Mode Registry ────────────────────────────────────────────────

class TestModeRegistry:
    def test_all_modes_registered(self):
        assert "moto" in MODES
        assert "casa" in MODES
        assert "trabajo" in MODES
        assert "noche" in MODES

    def test_mode_types(self):
        assert isinstance(MODES["moto"], MotoMode)
        assert isinstance(MODES["casa"], CasaMode)
        assert isinstance(MODES["trabajo"], TrabajoMode)
        assert isinstance(MODES["noche"], NocheMode)


# ── Singleton ────────────────────────────────────────────────────

class TestSingleton:
    def test_get_mode_manager_returns_instance(self):
        # Reset singleton for test
        import modes.manager
        modes.manager._manager = None
        manager = get_mode_manager("casa")
        assert isinstance(manager, ModeManager)
        # Clean up
        modes.manager._manager = None
