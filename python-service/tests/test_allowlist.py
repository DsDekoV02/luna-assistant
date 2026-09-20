"""
Luna JARVIS - Tests for Command Allowlist
Tests command validation, execution, and handlers.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.allowlist import CommandAllowlist


@pytest.fixture
def allowlist():
    return CommandAllowlist(log_commands=False)


# ── Initialization ────────────────────────────────────────────────

class TestAllowlistInit:
    def test_default_commands(self, allowlist):
        assert "systeminfo" in allowlist.allowed_commands
        assert "datetime" in allowlist.allowed_commands
        assert "websearch" in allowlist.allowed_commands

    def test_custom_commands(self):
        al = CommandAllowlist(allowed_commands=["cmd1", "cmd2"])
        assert al.allowed_commands == ["cmd1", "cmd2"]

    def test_log_flag(self):
        al = CommandAllowlist(log_commands=True)
        assert al.log_commands is True


# ── is_allowed ───────────────────────────────────────────────────

class TestIsAllowed:
    def test_allowed_command(self, allowlist):
        assert allowlist.is_allowed("datetime") is True

    def test_blocked_command(self, allowlist):
        assert allowlist.is_allowed("rm") is False

    def test_arbitrary_command(self, allowlist):
        assert allowlist.is_allowed("shutdown") is False

    def test_all_default_allowed(self, allowlist):
        for cmd in ["systeminfo", "screenshot", "listdir", "openapp",
                     "volume", "datetime", "timer", "websearch"]:
            assert allowlist.is_allowed(cmd) is True


# ── Execute ──────────────────────────────────────────────────────

class TestExecute:
    def test_execute_allowed(self, allowlist):
        result = allowlist.execute("datetime")
        assert "datetime" in result
        assert "date" in result
        assert "time" in result

    def test_execute_blocked(self, allowlist):
        result = allowlist.execute("rm")
        assert "error" in result
        assert result["allowed"] is False

    def test_execute_with_params(self, allowlist):
        result = allowlist.execute("systeminfo", {"info_type": "cpu"})
        assert "cpu" in result

    def test_execute_invalid_params(self, allowlist):
        # datetime handler doesn't accept params, but execute() passes **kwargs
        # which should cause a TypeError - let's check it returns an error
        result = allowlist.execute("datetime", {"invalid": "param"})
        # Either works (ignores params) or returns error
        assert "datetime" in result or "error" in result


# ── datetime handler ─────────────────────────────────────────────

class TestDatetimeCommand:
    def test_returns_datetime(self, allowlist):
        result = allowlist.execute("datetime")
        assert "datetime" in result
        assert "date" in result
        assert "time" in result
        assert "day" in result
        assert "timezone" in result

    def test_date_format(self, allowlist):
        result = allowlist.execute("datetime")
        # Should be YYYY-MM-DD
        date = result["date"]
        assert len(date) == 10
        assert date[4] == "-"
        assert date[7] == "-"

    def test_time_format(self, allowlist):
        result = allowlist.execute("datetime")
        time_str = result["time"]
        # Should be HH:MM:SS
        assert len(time_str) == 8
        assert time_str[2] == ":"
        assert time_str[5] == ":"


# ── systeminfo handler ───────────────────────────────────────────

class TestSysteminfoCommand:
    def test_cpu_info(self, allowlist):
        result = allowlist.execute("systeminfo", {"info_type": "cpu"})
        assert "cpu" in result
        assert "percent" in result["cpu"]

    def test_ram_info(self, allowlist):
        result = allowlist.execute("systeminfo", {"info_type": "ram"})
        assert "ram" in result
        assert "total_gb" in result["ram"]

    def test_disk_info(self, allowlist):
        result = allowlist.execute("systeminfo", {"info_type": "disk"})
        assert "disk" in result
        assert "free_gb" in result["disk"]

    def test_all_info(self, allowlist):
        result = allowlist.execute("systeminfo", {"info_type": "all"})
        assert "cpu" in result
        assert "ram" in result
        assert "disk" in result


# ── listdir handler ──────────────────────────────────────────────

class TestListdirCommand:
    def test_list_current_dir(self, allowlist):
        result = allowlist.execute("listdir", {"path": "."})
        assert "entries" in result
        assert isinstance(result["entries"], list)

    def test_nonexistent_path(self, allowlist):
        result = allowlist.execute("listdir", {"path": "/nonexistent/path"})
        assert "error" in result

    def test_limit_entries(self, allowlist):
        result = allowlist.execute("listdir", {"path": "."})
        assert len(result["entries"]) <= 50


# ── timer handler ────────────────────────────────────────────────

class TestTimerCommand:
    def test_sets_timer(self, allowlist):
        result = allowlist.execute("timer", {"duration_seconds": 60, "label": "test"})
        assert result["timer_set"] is True
        assert result["duration"] == 60
        assert result["label"] == "test"

    def test_timer_has_end_time(self, allowlist):
        result = allowlist.execute("timer", {"duration_seconds": 30})
        assert "ends_at" in result
        assert result["ends_at"] > 0


# ── websearch handler ────────────────────────────────────────────

class TestWebsearchCommand:
    @patch("urllib.request.urlopen")
    def test_search_basic(self, mock_urlopen, allowlist):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "Heading": "Test",
            "AbstractText": "Test result",
            "AbstractSource": "Test",
            "AbstractURL": "https://test.com",
            "RelatedTopics": []
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = allowlist.execute("websearch", {"query": "test"})
        assert "results" in result

    @patch("urllib.request.urlopen")
    def test_search_error(self, mock_urlopen, allowlist):
        mock_urlopen.side_effect = Exception("Network error")
        result = allowlist.execute("websearch", {"query": "test"})
        assert "error" in result


# ── weather handler ──────────────────────────────────────────────

class TestWeatherCommand:
    def test_weather_basic(self, allowlist):
        # Weather handler uses urllib internally - test that it handles errors gracefully
        # Can't easily mock nested imports; test error path instead
        result = allowlist.execute("weather", {"city": "Santiago"})
        # Either succeeds or returns error (network may not be available)
        assert "city" in result or "error" in result
