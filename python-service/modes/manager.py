"""
Luna JARVIS - Modes Module
Different operational modes for different contexts.
"""

import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger("luna.modes")


class Mode:
    """Base operational mode."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def should_respond(self, priority: str = "normal") -> bool:
        """Check if Luna should respond in this mode."""
        return True

    def get_response_style(self) -> str:
        """Get the response style for this mode."""
        return "normal"

    def format_response(self, text: str) -> str:
        """Format response according to mode."""
        return text


class MotoMode(Mode):
    """Driving mode - voice only, quick responses."""

    def __init__(self):
        super().__init__("moto", "Modo conducción - solo voz, respuestas cortas")

    def should_respond(self, priority: str = "normal") -> bool:
        return True  # Always respond, but briefly

    def get_response_style(self) -> str:
        return "brief"

    def format_response(self, text: str) -> str:
        # Shorten responses for driving
        if len(text) > 200:
            sentences = text.split(".")
            return ". ".join(sentences[:2]) + "."
        return text


class CasaMode(Mode):
    """Home mode - full access."""

    def __init__(self):
        super().__init__("casa", "Modo hogar - acceso completo")


class TrabajoMode(Mode):
    """Work mode - minimal, priority only."""

    def __init__(self):
        super().__init__("trabajo", "Modo trabajo - solo alertas importantes")

    def should_respond(self, priority: str = "normal") -> bool:
        return priority in ("high", "critical")

    def get_response_style(self) -> str:
        return "concise"


class NocheMode(Mode):
    """Night mode - very quiet."""

    def __init__(self, start_hour: int = 23, end_hour: int = 8):
        super().__init__("noche", "Modo nocturno - silencioso")
        self.start_hour = start_hour
        self.end_hour = end_hour

    def is_quiet_hours(self) -> bool:
        hour = datetime.now().hour
        if self.start_hour > self.end_hour:
            return hour >= self.start_hour or hour < self.end_hour
        return self.start_hour <= hour < self.end_hour

    def should_respond(self, priority: str = "normal") -> bool:
        if self.is_quiet_hours():
            return priority == "critical"
        return True


# Mode registry
MODES: Dict[str, Mode] = {
    "moto": MotoMode(),
    "casa": CasaMode(),
    "trabajo": TrabajoMode(),
    "noche": NocheMode(),
}


class ModeManager:
    """Manages operational modes."""

    def __init__(self, default_mode: str = "casa"):
        self.current_mode_name = default_mode
        self.current_mode = MODES.get(default_mode, CasaMode())

    def set_mode(self, mode_name: str) -> bool:
        """Switch to a different mode."""
        if mode_name not in MODES:
            logger.error(f"Unknown mode: {mode_name}")
            return False

        self.current_mode_name = mode_name
        self.current_mode = MODES[mode_name]
        logger.info(f"Mode switched to: {mode_name}")
        return True

    def should_respond(self, priority: str = "normal") -> bool:
        """Check if Luna should respond in current mode."""
        return self.current_mode.should_respond(priority)

    def get_system_prompt_modifier(self) -> str:
        """Get mode-specific system prompt additions."""
        mode = self.current_mode

        if isinstance(mode, MotoMode):
            return "\nMODO CONDUCCIÓN: Responde en máximo 2 frases. Solo voz. No distractas."
        elif isinstance(mode, TrabajoMode):
            return "\nMODO TRABAJO: Sé concisa. Solo interrumpe para alertas importantes."
        elif isinstance(mode, NocheMode):
            if mode.is_quiet_hours():
                return "\nMODO NOCHE: Horario de silencio. Solo responde a urgencias."
            return ""
        return ""

    def get_status(self) -> dict:
        """Get current mode status."""
        return {
            "mode": self.current_mode_name,
            "description": self.current_mode.description,
            "style": self.current_mode.get_response_style(),
        }


# Singleton
_manager: Optional[ModeManager] = None


def get_mode_manager(default_mode: str = "casa") -> ModeManager:
    """Get the singleton mode manager."""
    global _manager
    if _manager is None:
        _manager = ModeManager(default_mode)
    return _manager
