"""
Luna JARVIS - Proactive Suggestions Engine
Luna can suggest actions based on context, time, and patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger("luna.proactive")


@dataclass
class Suggestion:
    """A proactive suggestion from Luna."""
    text: str
    category: str  # "info", "action", "reminder", "tip"
    priority: str  # "low", "normal", "high"
    action: Optional[str] = None  # Tool command to execute if accepted
    action_params: Optional[Dict[str, Any]] = None
    auto_dismiss_seconds: int = 30

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "category": self.category,
            "priority": self.priority,
            "action": self.action,
            "action_params": self.action_params,
            "auto_dismiss_seconds": self.auto_dismiss_seconds,
        }


class ProactiveEngine:
    """Generates proactive suggestions based on context."""

    def __init__(self):
        self._last_suggestions: List[Suggestion] = []
        self._suggestion_history: List[str] = []
        self._max_history = 50

    def get_suggestions(
        self,
        mode: str = "casa",
        system_info: Optional[dict] = None,
        recent_messages: Optional[List[str]] = None,
    ) -> List[Suggestion]:
        """Generate contextual suggestions.

        Args:
            mode: Current operational mode
            system_info: System stats (CPU, RAM, disk, battery)
            recent_messages: Recent conversation messages for context

        Returns:
            List of suggestions, filtered by mode appropriateness
        """
        suggestions = []

        # Time-based suggestions
        suggestions.extend(self._time_based_suggestions(mode))

        # System-based suggestions
        if system_info:
            suggestions.extend(self._system_suggestions(system_info, mode))

        # Context-based suggestions
        if recent_messages:
            suggestions.extend(self._context_suggestions(recent_messages, mode))

        # Weather-based suggestions (every ~4 calls to avoid spam)
        import random
        if random.random() < 0.25:
            suggestions.extend(self._weather_suggestions(mode))

        # Productivity suggestions
        suggestions.extend(self._productivity_suggestions(mode))

        # Filter duplicates and low-relevance
        suggestions = self._filter_suggestions(suggestions)

        self._last_suggestions = suggestions
        return suggestions

    def _time_based_suggestions(self, mode: str) -> List[Suggestion]:
        """Suggestions based on time of day."""
        suggestions = []
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday

        # Morning (7-10)
        if 7 <= hour < 10 and mode not in ("noche",):
            suggestions.append(Suggestion(
                text="Buenos dias Nicolas. ¿Quieres que revise tu calendario y emails?",
                category="info",
                priority="normal",
                action="systeminfo",
                action_params={"info_type": "all"},
            ))

        # Work hours (10-18, weekdays)
        if 10 <= hour < 18 and weekday < 5 and mode == "trabajo":
            suggestions.append(Suggestion(
                text="Estas en modo trabajo. ¿Necesitas que te ayude con algo?",
                category="info",
                priority="low",
            ))

        # Evening (18-22)
        if 18 <= hour < 22:
            suggestions.append(Suggestion(
                text="¿Quieres que resuma lo que hiciste hoy?",
                category="info",
                priority="low",
            ))

        # Late night (22-1)
        if 22 <= hour or hour < 1:
            if mode != "noche":
                suggestions.append(Suggestion(
                    text="Es tarde. ¿Quieres cambiar a modo nocturno?",
                    category="action",
                    priority="normal",
                    action="mode",
                    action_params={"mode": "noche"},
                ))

        # Weekend
        if weekday >= 5 and 10 <= hour < 14:
            suggestions.append(Suggestion(
                text="¡Feliz fin de semana! ¿Hay algo divertido que quieras hacer?",
                category="info",
                priority="low",
            ))

        return suggestions

    def _system_suggestions(self, info: dict, mode: str) -> List[Suggestion]:
        """Suggestions based on system state."""
        suggestions = []

        # High CPU
        cpu = info.get("cpu", {})
        if isinstance(cpu, dict):
            cpu_pct = cpu.get("percent", 0)
            if cpu_pct > 90:
                suggestions.append(Suggestion(
                    text=f"El CPU esta al {cpu_pct}%. ¿Quieres ver que procesos estan consumiendo mas?",
                    category="action",
                    priority="high",
                    action="systeminfo",
                    action_params={"info_type": "cpu"},
                ))

        # High RAM
        ram = info.get("ram", {})
        if isinstance(ram, dict):
            ram_pct = ram.get("percent", 0)
            if ram_pct > 85:
                suggestions.append(Suggestion(
                    text=f"La memoria RAM esta al {ram_pct}%. Considera cerrar aplicaciones que no uses.",
                    category="info",
                    priority="high",
                ))

        # Low disk
        disk = info.get("disk", {})
        if isinstance(disk, dict):
            free_gb = disk.get("free_gb", 0)
            if free_gb < 10:
                suggestions.append(Suggestion(
                    text=f"Quedan solo {free_gb:.1f}GB libres en el disco. ¿Quieres que busque archivos grandes?",
                    category="action",
                    priority="high",
                    action="listdir",
                    action_params={"path": "C:\\Users"},
                ))

        # Battery
        battery = info.get("battery", {})
        if isinstance(battery, dict):
            pct = battery.get("percent", 100)
            plugged = battery.get("plugged", True)
            if pct < 20 and not plugged:
                suggestions.append(Suggestion(
                    text=f"La bateria esta al {pct}%. ¡Conecta el cargador!",
                    category="reminder",
                    priority="high",
                ))

        return suggestions

    def _context_suggestions(self, messages: List[str], mode: str) -> List[Suggestion]:
        """Suggestions based on recent conversation context."""
        suggestions = []

        if not messages:
            return suggestions

        last_msg = messages[-1].lower() if messages else ""

        # User seems frustrated
        frustration_words = ["no funciona", "error", "problema", "no puedo", "ayuda"]
        if any(w in last_msg for w in frustration_words):
            suggestions.append(Suggestion(
                text="Veo que tienes un problema. ¿Quieres que busque una solucion?",
                category="action",
                priority="normal",
            ))

        # User mentioned time/schedule
        time_words = ["reunion", "cita", "meeting", "hora", "calendario"]
        if any(w in last_msg for w in time_words):
            suggestions.append(Suggestion(
                text="¿Quieres que revise tu calendario para las proximas horas?",
                category="action",
                priority="normal",
            ))

        # User mentioned code/programming
        code_words = ["codigo", "programar", "bug", "error", "funcion", "script"]
        if any(w in last_msg for w in code_words):
            suggestions.append(Suggestion(
                text="¿Necesitas ayuda con codigo? Puedo revisar archivos o explicar errores.",
                category="tip",
                priority="low",
            ))

        return suggestions

    def _weather_suggestions(self, mode: str) -> List[Suggestion]:
        """Suggestions based on weather conditions."""
        suggestions = []
        try:
            import urllib.request
            import json as _json
            url = "https://wttr.in/Santiago?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "LunaJARVIS/0.1"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            current = data.get("current_condition", [{}])[0]
            temp = int(current.get("temp_C", 20))
            desc = current.get("lang_es", [{}])[0].get("value", "")
            rain_keywords = ["lluvia", "rain", "tormenta", "storm", "chubascos"]
            if any(k in desc.lower() for k in rain_keywords):
                suggestions.append(Suggestion(
                    text=f"Parece que hay {desc} en Santiago. ¡Lleva paraguas si sales!",
                    category="reminder",
                    priority="normal",
                ))
            if temp < 10:
                suggestions.append(Suggestion(
                    text=f"Estan a {temp}°C en Santiago. ¡Abrigate bien!",
                    category="info",
                    priority="low",
                ))
            elif temp > 30:
                suggestions.append(Suggestion(
                    text=f"Hace {temp}°C en Santiago. Mantente hidratado.",
                    category="info",
                    priority="low",
                ))
        except Exception:
            pass  # Weather check is best-effort
        return suggestions

    def _productivity_suggestions(self, mode: str) -> List[Suggestion]:
        """Suggestions for productivity and work-break cycles."""
        suggestions = []
        now = datetime.now()
        hour = now.hour

        # Pomodoro suggestion during work hours
        if 10 <= hour < 18 and mode == "trabajo":
            suggestions.append(Suggestion(
                text="¿Quieres que te avise en 25 minutos para descansar? (Pomodoro)",
                category="action",
                priority="low",
                action="timer",
                action_params={"duration_seconds": 1500, "label": "Pomodoro"},
            ))

        # Hydration reminder every few hours
        if hour in (11, 14, 17, 20):
            suggestions.append(Suggestion(
                text="¿Has tomado agua recuerdamente? ¡Hidratate!",
                category="reminder",
                priority="low",
            ))

        return suggestions

    def _filter_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Filter and deduplicate suggestions."""
        filtered = []
        seen_texts = set()

        # Sort by priority
        priority_order = {"high": 0, "normal": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 2))

        for s in suggestions:
            # Deduplicate by text similarity
            text_key = s.text[:50].lower()
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            # Don't repeat recent suggestions
            if text_key in self._suggestion_history:
                continue

            filtered.append(s)

            # Limit number of suggestions
            if len(filtered) >= 3:
                break

        # Update history
        for s in filtered:
            self._suggestion_history.append(s.text[:50].lower())
        if len(self._suggestion_history) > self._max_history:
            self._suggestion_history = self._suggestion_history[-self._max_history:]

        return filtered

    def format_for_chat(self, suggestions: List[Suggestion]) -> str:
        """Format suggestions as a chat message."""
        if not suggestions:
            return ""

        lines = ["💡 Sugerencias:"]
        for i, s in enumerate(suggestions, 1):
            icon = {"info": "ℹ️", "action": "⚡", "reminder": "🔔", "tip": "💡"}.get(s.category, "•")
            lines.append(f"  {icon} {s.text}")

        return "\n".join(lines)


# Singleton
_engine: Optional[ProactiveEngine] = None


def get_proactive_engine() -> ProactiveEngine:
    """Get the singleton proactive engine."""
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine
