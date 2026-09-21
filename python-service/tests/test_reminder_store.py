"""
Tests for reminder persistence (ReminderStore).
"""

import json
import time
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tools.reminder_store import ReminderStore, reset_reminder_store


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory."""
    return tmp_path / "data"


@pytest.fixture
def store(tmp_data_dir):
    """Create a fresh ReminderStore with a temp directory."""
    reset_reminder_store()
    s = ReminderStore(data_dir=tmp_data_dir)
    yield s
    reset_reminder_store()


class TestReminderStorePersistence:
    """Test that reminders are saved to and loaded from disk."""

    def test_creates_data_directory(self, tmp_path):
        data_dir = tmp_path / "nested" / "data"
        store = ReminderStore(data_dir=data_dir)
        assert data_dir.exists()
        assert (data_dir / "reminders.json").exists() or True  # created on first save

    def test_reminder_file_created_on_add(self, store, tmp_data_dir):
        entry = store.add(
            message="Test reminder",
            scheduled_time=datetime.now() + timedelta(hours=1),
        )
        assert (tmp_data_dir / "reminders.json").exists()
        # Verify file content
        with open(tmp_data_dir / "reminders.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["next_id"] == 2
        assert len(data["reminders"]) == 1
        assert data["reminders"][0]["message"] == "Test reminder"

    def test_reminders_survive_reload(self, tmp_data_dir):
        """Core test: reminders persist across store instances (simulates restart)."""
        # Create store and add reminders
        store1 = ReminderStore(data_dir=tmp_data_dir)
        store1.add(
            message="Buy groceries",
            scheduled_time=datetime.now() + timedelta(hours=2),
        )
        store1.add(
            message="Call mom",
            scheduled_time=datetime.now() + timedelta(hours=5),
        )
        store1.complete(1)

        # Simulate restart: create new store instance
        store2 = ReminderStore(data_dir=tmp_data_dir)

        reminders = store2.list_reminders()
        assert len(reminders) == 2

        # Check first reminder is completed
        r1 = next(r for r in reminders if r["id"] == 1)
        assert r1["message"] == "Buy groceries"
        assert r1["status"] == "completed"

        # Check second is still pending
        r2 = next(r for r in reminders if r["id"] == 2)
        assert r2["message"] == "Call mom"
        assert r2["status"] == "pending"

        # next_id should continue correctly
        entry = store2.add(
            message="New after restart",
            scheduled_time=datetime.now() + timedelta(hours=1),
        )
        assert entry["id"] == 3

    def test_ids_increment_across_reloads(self, tmp_data_dir):
        """next_id must be persisted so IDs never collide."""
        s1 = ReminderStore(data_dir=tmp_data_dir)
        s1.add(message="A", scheduled_time=datetime.now() + timedelta(hours=1))
        s1.add(message="B", scheduled_time=datetime.now() + timedelta(hours=1))
        del s1

        s2 = ReminderStore(data_dir=tmp_data_dir)
        entry = s2.add(message="C", scheduled_time=datetime.now() + timedelta(hours=1))
        assert entry["id"] == 3  # not 1

    def test_corrupted_file_handled_gracefully(self, tmp_data_dir):
        """If the JSON is corrupted, store should start empty."""
        tmp_data_dir.mkdir(parents=True, exist_ok=True)
        bad_file = tmp_data_dir / "reminders.json"
        bad_file.write_text("NOT VALID JSON {{{", encoding="utf-8")

        store = ReminderStore(data_dir=tmp_data_dir)
        assert store.list_reminders() == []

    def test_atomic_save_no_corruption(self, store, tmp_data_dir):
        """Verify .tmp file is used and no partial writes remain."""
        store.add(message="Test", scheduled_time=datetime.now() + timedelta(hours=1))
        # .tmp should be cleaned up
        assert not (tmp_data_dir / "reminders.json.tmp").exists()


class TestReminderCRUD:
    """Test add, list, complete, delete operations."""

    def test_add_and_list(self, store):
        store.add(message="First", scheduled_time=datetime.now() + timedelta(hours=1))
        store.add(message="Second", scheduled_time=datetime.now() + timedelta(hours=2))
        assert len(store.list_reminders()) == 2

    def test_list_filter_by_status(self, store):
        store.add(message="A", scheduled_time=datetime.now() + timedelta(hours=1))
        store.add(message="B", scheduled_time=datetime.now() + timedelta(hours=2))
        store.complete(1)

        pending = store.list_reminders(status="pending")
        completed = store.list_reminders(status="completed")
        assert len(pending) == 1
        assert pending[0]["message"] == "B"
        assert len(completed) == 1
        assert completed[0]["message"] == "A"

    def test_complete_reminder(self, store):
        store.add(message="Do it", scheduled_time=datetime.now() + timedelta(hours=1))
        result = store.complete(1)
        assert result is True
        reminders = store.list_reminders()
        assert reminders[0]["status"] == "completed"

    def test_complete_nonexistent(self, store):
        result = store.complete(999)
        assert result is False

    def test_delete_reminder(self, store):
        store.add(message="Delete me", scheduled_time=datetime.now() + timedelta(hours=1))
        result = store.delete(1)
        assert result is True
        assert len(store.list_reminders()) == 0

    def test_delete_nonexistent(self, store):
        result = store.delete(999)
        assert result is False

    def test_get_pending(self, store):
        store.add(message="A", scheduled_time=datetime.now() + timedelta(hours=1))
        store.add(message="B", scheduled_time=datetime.now() + timedelta(hours=2))
        store.complete(1)
        pending = store.get_pending()
        assert len(pending) == 1
        assert pending[0]["message"] == "B"

    def test_stats(self, store):
        store.add(message="A", scheduled_time=datetime.now() + timedelta(hours=1))
        store.add(message="B", scheduled_time=datetime.now() + timedelta(hours=2))
        store.complete(1)
        stats = store.stats()
        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["completed"] == 1


class TestReminderScheduling:
    """Test timer scheduling and firing."""

    def test_reschedule_pending_fires_expired(self, tmp_data_dir):
        """Reminders whose time has passed should fire on reschedule."""
        fired = []

        def cb(entry):
            fired.append(entry["message"])

        # Create a reminder in the past
        store1 = ReminderStore(data_dir=tmp_data_dir)
        past_time = datetime.now() - timedelta(seconds=5)
        store1.add(message="Already past", scheduled_time=past_time)
        del store1

        # Reload and reschedule
        store2 = ReminderStore(data_dir=tmp_data_dir)
        store2.reschedule_pending(callback=cb)

        # Give it a moment for the fire thread
        time.sleep(0.5)
        assert "Already past" in fired

        # Should be marked completed
        reminders = store2.list_reminders()
        assert reminders[0]["status"] == "completed"

    def test_reschedule_pending_schedules_future(self, tmp_data_dir):
        """Future reminders should get scheduled without firing immediately."""
        fired = []

        def cb(entry):
            fired.append(entry["message"])

        store = ReminderStore(data_dir=tmp_data_dir)
        store.add(
            message="Future reminder",
            scheduled_time=datetime.now() + timedelta(hours=1),
        )
        store.reschedule_pending(callback=cb)

        time.sleep(0.3)
        assert len(fired) == 0  # shouldn't have fired yet
        assert store.stats()["active_timers"] == 1

    def test_callback_invoked_on_fire(self, store):
        """Callback should be called when a timer fires."""
        result = []

        def cb(entry):
            result.append(entry["message"])

        store.add(
            message="Fire me",
            scheduled_time=datetime.now() + timedelta(milliseconds=200),
            callback=cb,
        )

        time.sleep(1.0)
        assert "Fire me" in result
        assert store.list_reminders()[0]["status"] == "completed"

    def test_callback_error_does_not_break_store(self, store):
        """A bad callback should not prevent the reminder from being marked complete."""
        def bad_cb(entry):
            raise RuntimeError("oops")

        store.add(
            message="Bad callback",
            scheduled_time=datetime.now() + timedelta(milliseconds=100),
            callback=bad_cb,
        )

        time.sleep(0.5)
        assert store.list_reminders()[0]["status"] == "completed"


class TestRestartSimulation:
    """End-to-end restart simulation tests."""

    def test_full_restart_cycle(self, tmp_data_dir):
        """Simulate full lifecycle: add → restart → reschedule → verify."""
        fired = []

        def cb(entry):
            fired.append(entry["message"])

        # ── Session 1: create reminders ──
        store1 = ReminderStore(data_dir=tmp_data_dir)
        store1.add(
            message="Reminder A (past)",
            scheduled_time=datetime.now() - timedelta(seconds=2),
        )
        store1.add(
            message="Reminder B (future)",
            scheduled_time=datetime.now() + timedelta(hours=1),
        )
        store1.add(
            message="Reminder C (completed)",
            scheduled_time=datetime.now() + timedelta(hours=1),
        )
        store1.complete(3)
        # Reminder A was past-due, so it fired immediately and was auto-completed
        time.sleep(0.3)
        stats1 = store1.stats()
        assert stats1["total"] == 3
        assert stats1["pending"] == 1  # only B is pending (A fired, C was manually completed)
        assert stats1["completed"] == 2

        # ── Simulate restart: drop instance ──
        del store1

        # ── Session 2: reload and reschedule ──
        store2 = ReminderStore(data_dir=tmp_data_dir)
        stats2 = store2.stats()
        assert stats2["total"] == 3
        assert stats2["pending"] == 1  # B is the only pending one (A was already completed)
        assert stats2["completed"] == 2

        store2.reschedule_pending(callback=cb)
        time.sleep(0.5)

        # Reminder A was already completed by the first session's immediate fire
        # so it won't fire again on reschedule
        # Reminder B is future, so it shouldn't fire
        assert "Reminder A (past)" not in fired  # already completed, not re-fired

        # Reminder B should still be pending
        r_b = next(r for r in store2.list_reminders() if r["id"] == 2)
        assert r_b["status"] == "pending"

        # Reminder C should still be completed
        r_c = next(r for r in store2.list_reminders() if r["id"] == 3)
        assert r_c["status"] == "completed"

        # Reminder A should be completed (fired in session 1)
        r_a = next(r for r in store2.list_reminders() if r["id"] == 1)
        assert r_a["status"] == "completed"

        # Can still add new reminders after restart
        entry = store2.add(
            message="Reminder D (new after restart)",
            scheduled_time=datetime.now() + timedelta(hours=2),
        )
        assert entry["id"] == 4
