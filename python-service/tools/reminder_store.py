"""
Luna JARVIS - Reminder Persistence Store
Stores reminders in a JSON file so they survive service restarts.
"""

import json
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("luna.tools.reminder_store")


class ReminderStore:
    """Persistent reminder storage backed by a JSON file."""

    def __init__(self, data_dir: str | Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._data_dir / "reminders.json"
        self._lock = threading.Lock()
        self._timers: Dict[str, threading.Timer] = {}
        self._reminders: List[Dict[str, Any]] = []
        self._next_id = 1
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self):
        """Load reminders from disk."""
        if not self._file.exists():
            self._reminders = []
            self._next_id = 1
            return
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._reminders = data.get("reminders", [])
            self._next_id = data.get("next_id", 1)
            logger.info(f"Loaded {len(self._reminders)} reminders from {self._file}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load reminders: {e}")
            self._reminders = []
            self._next_id = 1

    def _save(self):
        """Save reminders to disk (caller must hold lock)."""
        data = {
            "next_id": self._next_id,
            "reminders": self._reminders,
        }
        tmp = self._file.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(self._file)
        except OSError as e:
            logger.error(f"Failed to save reminders: {e}")
            if tmp.exists():
                tmp.unlink()

    # ── CRUD ──────────────────────────────────────────────────────

    def add(
        self,
        message: str,
        scheduled_time: datetime,
        callback=None,
    ) -> Dict[str, Any]:
        """Create a new reminder, persist it, and schedule its timer."""
        with self._lock:
            reminder_id = self._next_id
            self._next_id += 1
            now = datetime.now()
            entry = {
                "id": reminder_id,
                "message": message,
                "scheduled_time": scheduled_time.isoformat(),
                "created_at": now.isoformat(),
                "status": "pending",
            }
            self._reminders.append(entry)
            self._save()

        # Schedule timer (outside lock to avoid deadlock)
        self._schedule_timer(entry, callback)
        return entry

    def complete(self, reminder_id: int):
        """Mark a reminder as completed and persist."""
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id:
                    r["status"] = "completed"
                    self._save()
                    return True
        return False

    def list_reminders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List reminders, optionally filtered by status."""
        with self._lock:
            if status:
                return [r for r in self._reminders if r["status"] == status]
            return list(self._reminders)

    def get_pending(self) -> List[Dict[str, Any]]:
        """Return all pending reminders."""
        return self.list_reminders(status="pending")

    def delete(self, reminder_id: int) -> bool:
        """Delete a reminder by id."""
        with self._lock:
            for i, r in enumerate(self._reminders):
                if r["id"] == reminder_id:
                    # Cancel timer if active
                    timer = self._timers.pop(reminder_id, None)
                    if timer:
                        timer.cancel()
                    self._reminders.pop(i)
                    self._save()
                    return True
        return False

    # ── Scheduling ────────────────────────────────────────────────

    def reschedule_pending(self, callback=None):
        """Re-schedule all pending reminders (call on startup)."""
        now = datetime.now()
        pending = self.get_pending()
        rescheduled = 0
        expired = 0
        for entry in pending:
            target = datetime.fromisoformat(entry["scheduled_time"])
            delay = (target - now).total_seconds()
            if delay <= 0:
                # Already past due — fire immediately
                expired += 1
                self._fire(entry, callback)
            else:
                self._schedule_timer(entry, callback)
                rescheduled += 1
        logger.info(
            f"Rescheduled {rescheduled} reminders, fired {expired} expired"
        )

    # threading.Timer uses C-level wait with a float; on Windows the
    # underlying WaitForSingleObject has a max of ~2^31 ms (~24 days).
    # Reminders beyond that window are stored but not timer-scheduled.
    _MAX_TIMER_SECONDS = 2_000_000  # ~23 days, safe for all platforms

    def _schedule_timer(self, entry: Dict[str, Any], callback=None):
        """Schedule a threading.Timer for a pending reminder."""
        reminder_id = entry["id"]
        target = datetime.fromisoformat(entry["scheduled_time"])
        delay = (target - datetime.now()).total_seconds()
        if delay <= 0:
            # Fire immediately in a thread to avoid blocking
            threading.Thread(
                target=self._fire, args=(entry, callback), daemon=True
            ).start()
            return

        if delay > self._MAX_TIMER_SECONDS:
            logger.info(
                f"Reminder #{reminder_id} is {delay/86400:.0f} days away — "
                f"stored but not timer-scheduled (max ~23 days). "
                f"Will reschedule on next restart."
            )
            return

        def _timer_fn():
            self._fire(entry, callback)

        timer = threading.Timer(delay, _timer_fn)
        timer.daemon = True
        timer.start()
        self._timers[reminder_id] = timer
        logger.debug(f"Scheduled reminder #{reminder_id} in {delay:.1f}s")

    def _fire(self, entry: Dict[str, Any], callback=None):
        """Fire a reminder: mark complete and invoke callback."""
        rid = entry["id"]
        logger.info(f"Reminder fired: #{rid} - {entry['message']}")
        self.complete(rid)
        if callback:
            try:
                callback(entry)
            except Exception as e:
                logger.error(f"Reminder callback error for #{rid}: {e}")

    # ── Stats ─────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return summary stats."""
        with self._lock:
            total = len(self._reminders)
            pending = sum(1 for r in self._reminders if r["status"] == "pending")
            completed = total - pending
            return {
                "total": total,
                "pending": pending,
                "completed": completed,
                "active_timers": len(self._timers),
            }


# Singleton
_store: Optional[ReminderStore] = None


def get_reminder_store(data_dir: str | Path = None) -> ReminderStore:
    """Get or create the singleton ReminderStore."""
    global _store
    if _store is None:
        _store = ReminderStore(data_dir=data_dir)
    return _store


def reset_reminder_store():
    """Reset singleton (for testing only)."""
    global _store
    _store = None
