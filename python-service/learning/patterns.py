"""
Luna JARVIS - Pattern Learning Engine
Learns user behavior patterns to provide more personalized responses.

Tracks:
- Topic frequency and preferences
- Active hours and daily patterns
- Response style preferences (brief vs detailed)
- Common command sequences
- Frequently used apps and tools
- Conversation sentiment trends

Stores patterns persistently in JSON for continuity across sessions.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("luna.learning.patterns")

# Topic keywords for classification
TOPIC_KEYWORDS = {
    "programming": ["codigo", "programar", "bug", "error", "funcion", "script", "python", "java", "javascript", "api", "deploy", "git", "commit", "debug", "compile", "ide", "vscode", "intellij", "pycharm"],
    "gaming": ["juego", "jugar", "minecraft", "steam", "osu", "gaming", "partida", "servidor", "fps", "ping", "mods", "curseforge"],
    "anime": ["anime", "manga", "capitulo", "temporada", "sao", "danmachi", "vtuber", "hololive", "subaru", "suisei"],
    "music": ["musica", "cancion", "spotify", "playlist", "album", "artista", "escuchar", "reproducir"],
    "system": ["cpu", "ram", "disco", "bateria", "sistema", "procesos", "memoria", "rendimiento", "actualizar"],
    "web": ["buscar", "google", "navegar", "web", "pagina", "url", "enlace", "noticias"],
    "weather": ["clima", "tiempo", "temperatura", "lluvia", "sol", "frio", "calor", "pronostico"],
    "motorcycle": ["moto", "motor", "ruta", "viaje", "casco", "guantes", "aceite", "neumatico"],
    "files": ["archivo", "carpeta", "directorio", "guardar", "abrir", "eliminar", "copiar", "mover"],
    "creative": ["diseñar", "crear", "dibujar", "render", "avatar", "modelo", "3d", "efecto"],
}


@dataclass
class TopicStats:
    """Statistics for a conversation topic."""
    count: int = 0
    last_mentioned: Optional[str] = None  # ISO timestamp
    avg_sentiment: float = 0.0  # -1 to 1
    keywords: List[str] = field(default_factory=list)


@dataclass
class HourlyActivity:
    """Activity level per hour of day."""
    hour: int = 0
    message_count: int = 0
    avg_length: float = 0.0


@dataclass
class CommandPattern:
    """A pattern of commands used together."""
    commands: List[str] = field(default_factory=list)
    count: int = 0
    last_used: Optional[str] = None


@dataclass
class UserPreferences:
    """Learned user preferences."""
    preferred_response_length: str = "normal"  # "brief", "normal", "detailed"
    preferred_language: str = "es"
    favorite_topics: List[str] = field(default_factory=list)
    frequent_apps: Dict[str, int] = field(default_factory=dict)
    active_hours: Dict[int, int] = field(default_factory=dict)  # hour -> count
    avg_session_messages: float = 0.0
    total_interactions: int = 0


class PatternEngine:
    """Learns and stores user behavior patterns for personalization."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path(__file__).parent / "patterns_data.json"
        self.topics: Dict[str, TopicStats] = {}
        self.preferences = UserPreferences()
        self.command_patterns: List[CommandPattern] = []
        self.hourly_activity: Dict[int, HourlyActivity] = {}
        self.session_buffer: List[Dict[str, Any]] = []
        self._dirty = False
        self._last_save = 0.0
        self._auto_save_interval = 300  # 5 minutes

        # Load existing patterns
        self._load()

    # ── Learning ──────────────────────────────────────────────────

    def record_interaction(
        self,
        user_message: str,
        response: str,
        mode: str = "casa",
        commands_used: Optional[List[str]] = None,
        timestamp: Optional[float] = None,
    ):
        """Record a user interaction for pattern learning.

        Args:
            user_message: The user's message text
            response: Luna's response text
            mode: Current operational mode
            commands_used: List of tool commands that were executed
            timestamp: Unix timestamp (defaults to now)
        """
        ts = timestamp or time.time()
        dt = datetime.fromtimestamp(ts)

        # Update topic stats
        detected_topics = self._detect_topics(user_message)
        for topic in detected_topics:
            if topic not in self.topics:
                self.topics[topic] = TopicStats()
            stats = self.topics[topic]
            stats.count += 1
            stats.last_mentioned = dt.isoformat()

        # Update hourly activity
        hour = dt.hour
        if hour not in self.hourly_activity:
            self.hourly_activity[hour] = HourlyActivity(hour=hour)
        activity = self.hourly_activity[hour]
        old_avg = activity.avg_length
        old_count = activity.message_count
        activity.message_count += 1
        msg_len = len(user_message.split())
        activity.avg_length = (old_avg * old_count + msg_len) / (old_count + 1) if old_count > 0 else msg_len

        # Update preferences
        self.preferences.total_interactions += 1
        self.preferences.active_hours[hour] = self.preferences.active_hours.get(hour, 0) + 1

        # Track response length preference
        resp_words = len(response.split())
        if resp_words < 20:
            length_signal = "brief"
        elif resp_words > 80:
            length_signal = "detailed"
        else:
            length_signal = "normal"
        self._update_response_length_pref(length_signal)

        # Track command patterns
        if commands_used:
            self._record_command_pattern(commands_used, dt)

        # Track apps
        if commands_used:
            for cmd in commands_used:
                if cmd == "openapp":
                    # App tracking handled separately
                    pass

        # Buffer for session analysis
        self.session_buffer.append({
            "timestamp": ts,
            "message_len": len(user_message),
            "response_len": len(response),
            "topics": detected_topics,
            "mode": mode,
            "commands": commands_used or [],
        })

        self._dirty = True
        self._maybe_auto_save()

    def record_app_usage(self, app_name: str):
        """Record that an app was opened."""
        name = app_name.lower()
        self.preferences.frequent_apps[name] = self.preferences.frequent_apps.get(name, 0) + 1
        self._dirty = True

    # ── Query ─────────────────────────────────────────────────────

    def get_personalization_context(self) -> str:
        """Generate a context string for the brain to personalize responses.

        Returns:
            A string to append to the system prompt with user patterns.
        """
        parts = []

        # Favorite topics
        fav = self.get_favorite_topics(5)
        if fav:
            topics_str = ", ".join(fav)
            parts.append(f"Temas favoritos del usuario: {topics_str}")

        # Active hours
        peak = self.get_peak_hours(3)
        if peak:
            hours_str = ", ".join(f"{h}:00" for h in peak)
            parts.append(f"Horas más activas: {hours_str}")

        # Response preference
        pref = self.preferences.preferred_response_length
        if pref == "brief":
            parts.append("El usuario prefiere respuestas cortas y directas")
        elif pref == "detailed":
            parts.append("El usuario prefiere respuestas detalladas y completas")

        # Frequent apps
        apps = self.get_frequent_apps(3)
        if apps:
            apps_str = ", ".join(apps)
            parts.append(f"Apps usadas frecuentemente: {apps_str}")

        # Total interactions context
        total = self.preferences.total_interactions
        if total > 100:
            parts.append(f"Usuario experimentado ({total} interacciones)")
        elif total > 20:
            parts.append(f"Usuario regular ({total} interacciones)")

        if not parts:
            return ""

        return "\nPATRONES DEL USUARIO:\n" + "\n".join(f"- {p}" for p in parts)

    def get_favorite_topics(self, limit: int = 5) -> List[str]:
        """Get the user's most discussed topics."""
        sorted_topics = sorted(
            self.topics.items(),
            key=lambda x: x[1].count,
            reverse=True
        )
        return [topic for topic, _ in sorted_topics[:limit]]

    def get_peak_hours(self, limit: int = 3) -> List[int]:
        """Get the hours when the user is most active."""
        if not self.preferences.active_hours:
            return []
        sorted_hours = sorted(
            self.preferences.active_hours.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [hour for hour, _ in sorted_hours[:limit]]

    def get_frequent_apps(self, limit: int = 5) -> List[str]:
        """Get the user's most frequently opened apps."""
        if not self.preferences.frequent_apps:
            return []
        sorted_apps = sorted(
            self.preferences.frequent_apps.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [app for app, _ in sorted_apps[:limit]]

    def get_topic_stats(self, topic: str) -> Optional[TopicStats]:
        """Get stats for a specific topic."""
        return self.topics.get(topic)

    def get_suggested_topics(self, current_hour: Optional[int] = None) -> List[str]:
        """Suggest topics based on time and history.

        Args:
            current_hour: Current hour (0-23), defaults to now

        Returns:
            List of suggested topic names
        """
        hour = current_hour if current_hour is not None else datetime.now().hour

        # Find what the user typically discusses at this hour
        relevant = []
        for entry in self.session_buffer:
            entry_hour = datetime.fromtimestamp(entry["timestamp"]).hour
            if abs(entry_hour - hour) <= 1:  # Within 1 hour
                relevant.extend(entry.get("topics", []))

        if relevant:
            # Return most common topics for this time
            counter = Counter(relevant)
            return [topic for topic, _ in counter.most_common(3)]

        # Fallback to general favorites
        return self.get_favorite_topics(3)

    def get_stats(self) -> Dict[str, Any]:
        """Get pattern learning statistics."""
        return {
            "total_interactions": self.preferences.total_interactions,
            "topics_tracked": len(self.topics),
            "favorite_topics": self.get_favorite_topics(5),
            "peak_hours": self.get_peak_hours(3),
            "response_preference": self.preferences.preferred_response_length,
            "frequent_apps": self.get_frequent_apps(5),
            "session_buffer_size": len(self.session_buffer),
            "patterns_stored": len(self.command_patterns),
        }

    # ── Internal ──────────────────────────────────────────────────

    def _detect_topics(self, text: str) -> List[str]:
        """Detect conversation topics from text."""
        text_lower = text.lower()
        detected = []

        for topic, keywords in TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(topic)
                    break

        return detected if detected else ["general"]

    def _update_response_length_pref(self, signal: str):
        """Update the response length preference using a moving average approach."""
        # Weight recent signals more heavily
        current = self.preferences.preferred_response_length

        # Simple state machine with momentum
        if signal == "brief":
            if current == "detailed":
                self.preferences.preferred_response_length = "normal"
            elif current == "normal":
                # Count brief signals
                brief_count = sum(
                    1 for entry in self.session_buffer[-10:]
                    if entry.get("response_len", 50) < 20
                )
                if brief_count >= 5:
                    self.preferences.preferred_response_length = "brief"
        elif signal == "detailed":
            if current == "brief":
                self.preferences.preferred_response_length = "normal"
            elif current == "normal":
                detailed_count = sum(
                    1 for entry in self.session_buffer[-10:]
                    if entry.get("response_len", 50) > 80
                )
                if detailed_count >= 5:
                    self.preferences.preferred_response_length = "detailed"

    def _record_command_pattern(self, commands: List[str], dt: datetime):
        """Record a sequence of commands as a pattern."""
        if len(commands) < 2:
            return

        # Look for existing pattern
        for pattern in self.command_patterns:
            if pattern.commands == commands:
                pattern.count += 1
                pattern.last_used = dt.isoformat()
                return

        # Add new pattern (limit to 100 patterns)
        if len(self.command_patterns) >= 100:
            # Remove least used
            self.command_patterns.sort(key=lambda p: p.count)
            self.command_patterns.pop(0)

        self.command_patterns.append(CommandPattern(
            commands=commands,
            count=1,
            last_used=dt.isoformat()
        ))

    def _maybe_auto_save(self):
        """Auto-save if enough time has passed."""
        now = time.time()
        if now - self._last_save >= self._auto_save_interval:
            self.save()

    # ── Persistence ───────────────────────────────────────────────

    def save(self):
        """Save patterns to disk."""
        data = {
            "version": 1,
            "saved_at": datetime.now().isoformat(),
            "topics": {
                name: {
                    "count": stats.count,
                    "last_mentioned": stats.last_mentioned,
                    "avg_sentiment": stats.avg_sentiment,
                    "keywords": stats.keywords,
                }
                for name, stats in self.topics.items()
            },
            "preferences": {
                "preferred_response_length": self.preferences.preferred_response_length,
                "preferred_language": self.preferences.preferred_language,
                "favorite_topics": self.preferences.favorite_topics,
                "frequent_apps": self.preferences.frequent_apps,
                "active_hours": {str(k): v for k, v in self.preferences.active_hours.items()},
                "avg_session_messages": self.preferences.avg_session_messages,
                "total_interactions": self.preferences.total_interactions,
            },
            "command_patterns": [
                {
                    "commands": p.commands,
                    "count": p.count,
                    "last_used": p.last_used,
                }
                for p in self.command_patterns
            ],
            "hourly_activity": {
                str(k): {
                    "hour": v.hour,
                    "message_count": v.message_count,
                    "avg_length": v.avg_length,
                }
                for k, v in self.hourly_activity.items()
            },
        }

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._last_save = time.time()
            self._dirty = False
            logger.info(f"Patterns saved: {len(self.topics)} topics, {self.preferences.total_interactions} interactions")
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")

    def _load(self):
        """Load patterns from disk."""
        if not self.storage_path.exists():
            logger.info("No existing patterns file found, starting fresh")
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Load topics
            for name, stats_data in data.get("topics", {}).items():
                self.topics[name] = TopicStats(
                    count=stats_data.get("count", 0),
                    last_mentioned=stats_data.get("last_mentioned"),
                    avg_sentiment=stats_data.get("avg_sentiment", 0.0),
                    keywords=stats_data.get("keywords", []),
                )

            # Load preferences
            prefs = data.get("preferences", {})
            self.preferences = UserPreferences(
                preferred_response_length=prefs.get("preferred_response_length", "normal"),
                preferred_language=prefs.get("preferred_language", "es"),
                favorite_topics=prefs.get("favorite_topics", []),
                frequent_apps=prefs.get("frequent_apps", {}),
                active_hours={int(k): v for k, v in prefs.get("active_hours", {}).items()},
                avg_session_messages=prefs.get("avg_session_messages", 0.0),
                total_interactions=prefs.get("total_interactions", 0),
            )

            # Load command patterns
            for p_data in data.get("command_patterns", []):
                self.command_patterns.append(CommandPattern(
                    commands=p_data.get("commands", []),
                    count=p_data.get("count", 0),
                    last_used=p_data.get("last_used"),
                ))

            # Load hourly activity
            for k, v in data.get("hourly_activity", {}).items():
                self.hourly_activity[int(k)] = HourlyActivity(
                    hour=v.get("hour", 0),
                    message_count=v.get("message_count", 0),
                    avg_length=v.get("avg_length", 0.0),
                )

            logger.info(
                f"Loaded patterns: {len(self.topics)} topics, "
                f"{self.preferences.total_interactions} interactions, "
                f"{len(self.command_patterns)} command patterns"
            )

        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")

    def clear(self):
        """Clear all learned patterns."""
        self.topics.clear()
        self.preferences = UserPreferences()
        self.command_patterns.clear()
        self.hourly_activity.clear()
        self.session_buffer.clear()
        self._dirty = True
        self.save()
        logger.info("All patterns cleared")


# Singleton
_engine: Optional[PatternEngine] = None


def get_pattern_engine(storage_path: Optional[str] = None) -> PatternEngine:
    """Get or create the singleton pattern engine."""
    global _engine
    if _engine is None:
        _engine = PatternEngine(storage_path)
    return _engine
