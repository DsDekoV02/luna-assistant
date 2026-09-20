"""
Luna JARVIS - Emotion Detection & Adaptive Response System
Detects user emotion from text and adapts Luna's personality accordingly.

Uses keyword-based detection (no ML dependency) for fast, reliable results.
MiMo brain can override/supplement this with its own understanding.
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("luna.emotion")


class Emotion(Enum):
    """Primary emotion categories."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    TIRED = "tired"
    CURIOUS = "curious"
    CONFUSED = "confused"
    GRATEFUL = "grateful"
    SARCASTIC = "sarcastic"


@dataclass
class EmotionState:
    """Detected emotional state with confidence and context."""
    primary: Emotion = Emotion.NEUTRAL
    confidence: float = 0.0
    secondary: Optional[Emotion] = None
    intensity: float = 0.5  # 0.0 = very mild, 1.0 = very strong
    triggers: List[str] = field(default_factory=list)  # What caused this detection

    def to_dict(self) -> Dict:
        return {
            "primary": self.primary.value,
            "confidence": round(self.confidence, 2),
            "secondary": self.secondary.value if self.secondary else None,
            "intensity": round(self.intensity, 2),
            "triggers": self.triggers[:3],  # Limit for brevity
        }


# ── Emotion Keywords ─────────────────────────────────────────────
# Each entry: (keywords, emotion, base_confidence)

EMOTION_PATTERNS: List[Tuple[List[str], Emotion, float]] = [
    # Happy / positive
    (["jeje", "jaja", "jj", "haha", "lol", "xd", "uwu", "owo", ":)", ":D", "😄", "😊", "🎉", "❤️", "🥰"],
     Emotion.HAPPY, 0.7),
    (["genial", "increíble", "awesome", "cool", "bkn", "bacán", "wena", "la raja", "filete",
      "estupendo", "maravilloso", "perfecto", "excelente", "brutal", "top",
      "feliz", "contento", "alegre", "radiante", "encantado", "fantastico", "hermoso", "buenisimo"],
     Emotion.HAPPY, 0.6),
    (["gracias", "te pasaste", "se agradece", "ty", "thanks", "thx"],
     Emotion.GRATEFUL, 0.7),

    # Excited
    (["!!!", "!!", "vamos", "wena", "yapo", "dale", "let's go", "vamoo"],
     Emotion.EXCITED, 0.6),
    (["emocionado", "ansioso por", "no veo la hora", "hyper", "hyped"],
     Emotion.EXCITED, 0.7),

    # Sad
    (["noooo", ":( :(", "😢", "😭", "💔", "meh", "uff", "pucha", "qué pena",
      "qué lata", "triste", "mal", "aww"],
     Emotion.SAD, 0.6),
    (["no puedo más", "estoy mal", "todo mal", "depre", "deprimido", "agotado"],
     Emotion.SAD, 0.8),

    # Frustrated
    (["pucha", "csm", "ctm", "conchetumare", "mierda", "puta", "la wea",
      "qué wea", "wtf", "bruh", "facepalm", "no puede ser"],
     Emotion.FRUSTRATED, 0.7),
    (["no funciona", "no sirve", "no andaa", "qué onda", "por qué no",
      "lleva rato", "ya van", "otra vez"],
     Emotion.FRUSTRATED, 0.6),
    (["odio", "detesto", "no soporto", "insoportable"],
     Emotion.ANGRY, 0.7),

    # Anxious / worried
    (["ayuda", "urgente", "rápido", "ya", "por favor", "ayúdame",
      "no sé qué hacer", "estoy perdido"],
     Emotion.ANXIOUS, 0.6),
    (["preocupado", "nervioso", "ansiedad", "miedo", "no sé si",
      "será que", "y si", "qué pasa si"],
     Emotion.ANXIOUS, 0.7),

    # Tired
    (["sueño", "cansado", "muerto", "agotado", "zzz", "💤", "ya no puedo",
      "estoy para la cama", "necesito dormir"],
     Emotion.TIRED, 0.7),
    (["largo día", "duro día", "pesado", "agotadora"],
     Emotion.TIRED, 0.6),

    # Curious
    (["cómo", "como", "por qué", "qué es", "cuál", "dónde", "cuándo",
      "explícame", "cuéntame", "sabes qué", "qué tal si",
      "y si", "sería posible", "se puede"],
     Emotion.CURIOUS, 0.5),
    (["interesante", "fascinante", "no sabía", "til", "hoy aprendí",
      "curioso", "raro"],
     Emotion.CURIOUS, 0.6),

    # Confused
    (["no entiendo", "no cacho", "no pillo", "qué", "cómo así",
      "no tiene sentido", "explica", "repíteme", "de nuevo"],
     Emotion.CONFUSED, 0.6),
    (["??", "¿¿", "pero qué", "espera", "momento"],
     Emotion.CONFUSED, 0.5),

    # Sarcastic
    (["claro", "obvio", "sí po", "ya claro", "aja", "ajá",
      "seguro", "dale, claro", "mm-hmm"],
     Emotion.SARCASTIC, 0.4),  # Lower confidence, context-dependent
]


# ── Response Style Modifiers ─────────────────────────────────────

@dataclass
class ResponseStyle:
    """How Luna should adapt her response style based on detected emotion."""
    tone: str = "normal"        # warm, gentle, energetic, calm, playful
    emoji_frequency: str = "moderate"  # none, minimal, moderate, frequent
    response_length: str = "normal"    # brief, normal, detailed
    formality: str = "casual"          # casual, normal, formal
    include_humor: bool = False
    include_comfort: bool = False
    extra_enthusiasm: bool = False

    def to_prompt_modifier(self) -> str:
        """Convert style to a system prompt modifier."""
        modifiers = []

        if self.tone == "warm":
            modifiers.append("Sé especialmente cálida y cariñosa en tu respuesta.")
        elif self.tone == "gentle":
            modifiers.append("Sé suave y comprensiva. No seas brusca.")
        elif self.tone == "energetic":
            modifiers.append("Muestra entusiasmo y energía en tu respuesta.")
        elif self.tone == "calm":
            modifiers.append("Mantén un tono calmado y tranquilizador.")
        elif self.tone == "playful":
            modifiers.append("Sé juguetona y un poco traviesa en tu respuesta.")

        if self.include_comfort:
            modifiers.append("Ofrece consuelo y apoyo emocional. Valida sus sentimientos.")

        if self.include_humor:
            modifiers.append("Puedes incluir un toque de humor ligero para animar.")

        if self.extra_enthusiasm:
            modifiers.append("¡Muestra mucho entusiasmo! Celebra con el usuario.")

        if self.response_length == "brief":
            modifiers.append("Sé breve y directa. No te extiendas.")
        elif self.response_length == "detailed":
            modifiers.append("Da una respuesta completa y detallada.")

        return " ".join(modifiers)


def get_response_style(emotion: EmotionState) -> ResponseStyle:
    """Map detected emotion to response style adjustments."""
    style = ResponseStyle()

    emotion_map = {
        Emotion.HAPPY: ResponseStyle(
            tone="warm", emoji_frequency="frequent",
            include_humor=True, extra_enthusiasm=True,
        ),
        Emotion.EXCITED: ResponseStyle(
            tone="energetic", emoji_frequency="frequent",
            extra_enthusiasm=True,
        ),
        Emotion.SAD: ResponseStyle(
            tone="gentle", emoji_frequency="minimal",
            response_length="brief", include_comfort=True,
        ),
        Emotion.FRUSTRATED: ResponseStyle(
            tone="calm", emoji_frequency="minimal",
            response_length="brief", include_comfort=True,
        ),
        Emotion.ANGRY: ResponseStyle(
            tone="calm", emoji_frequency="none",
            response_length="brief", include_comfort=True,
        ),
        Emotion.ANXIOUS: ResponseStyle(
            tone="calm", emoji_frequency="minimal",
            include_comfort=True,
        ),
        Emotion.TIRED: ResponseStyle(
            tone="gentle", emoji_frequency="minimal",
            response_length="brief",
        ),
        Emotion.CURIOUS: ResponseStyle(
            tone="warm", emoji_frequency="moderate",
            response_length="detailed",
        ),
        Emotion.CONFUSED: ResponseStyle(
            tone="warm", emoji_frequency="minimal",
            response_length="detailed",
        ),
        Emotion.GRATEFUL: ResponseStyle(
            tone="warm", emoji_frequency="moderate",
            include_humor=True,
        ),
        Emotion.SARCASTIC: ResponseStyle(
            tone="playful", emoji_frequency="moderate",
            include_humor=True,
        ),
        Emotion.NEUTRAL: ResponseStyle(),
    }

    return emotion_map.get(emotion.primary, style)


class EmotionDetector:
    """Detects user emotion from text messages."""

    def __init__(self):
        self._history: List[EmotionState] = []
        self._max_history = 20

    def detect(self, text: str) -> EmotionState:
        """Analyze text and return detected emotion.

        Uses keyword matching with confidence scoring.
        Multiple matches increase confidence.
        """
        text_lower = text.lower().strip()

        # Score each emotion
        emotion_scores: Dict[Emotion, float] = {}
        emotion_triggers: Dict[Emotion, List[str]] = {}

        for keywords, emotion, base_confidence in EMOTION_PATTERNS:
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if emotion not in emotion_scores:
                        emotion_scores[emotion] = 0.0
                        emotion_triggers[emotion] = []
                    emotion_scores[emotion] += base_confidence
                    emotion_triggers[emotion].append(keyword)

        if not emotion_scores:
            state = EmotionState(primary=Emotion.NEUTRAL, confidence=0.3)
        else:
            # Find the highest scoring emotion
            sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
            primary_emotion, primary_score = sorted_emotions[0]

            # Cap confidence at 1.0
            confidence = min(primary_score, 1.0)

            # Check for secondary emotion
            secondary = None
            if len(sorted_emotions) > 1:
                sec_emotion, sec_score = sorted_emotions[1]
                if sec_score > 0.3:
                    secondary = sec_emotion

            # Calculate intensity based on text features
            intensity = self._calculate_intensity(text_lower, primary_emotion)

            state = EmotionState(
                primary=primary_emotion,
                confidence=confidence,
                secondary=secondary,
                intensity=intensity,
                triggers=emotion_triggers.get(primary_emotion, []),
            )

        # Track history for trend detection
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug(
            f"Emotion detected: {state.primary.value} "
            f"(conf={state.confidence:.2f}, intensity={state.intensity:.2f})"
        )
        return state

    def _calculate_intensity(self, text: str, emotion: Emotion) -> float:
        """Calculate emotional intensity from text features."""
        intensity = 0.5  # Baseline

        # ALL CAPS = higher intensity
        if text.isupper() and len(text) > 3:
            intensity += 0.2

        # Multiple exclamation/question marks
        if re.search(r'[!?]{2,}', text):
            intensity += 0.15

        # Repeated characters (nooooo, aaaa)
        if re.search(r'(.)\1{3,}', text):
            intensity += 0.1

        # Very short messages with emotion = likely intense
        if len(text.split()) <= 3 and emotion != Emotion.NEUTRAL:
            intensity += 0.1

        # Long messages with emotion = venting or detailed concern
        if len(text.split()) > 30 and emotion in (Emotion.FRUSTRATED, Emotion.ANXIOUS, Emotion.SAD):
            intensity += 0.15

        return min(intensity, 1.0)

    def get_mood_trend(self) -> Optional[Emotion]:
        """Analyze recent emotion history for mood trends."""
        if len(self._history) < 3:
            return None

        recent = self._history[-5:]
        # If 3+ of the last 5 messages share the same non-neutral emotion
        emotion_counts: Dict[Emotion, int] = {}
        for state in recent:
            if state.primary != Emotion.NEUTRAL:
                emotion_counts[state.primary] = emotion_counts.get(state.primary, 0) + 1

        for emotion, count in emotion_counts.items():
            if count >= 3:
                return emotion

        return None

    def get_stats(self) -> Dict:
        """Get emotion detection statistics."""
        if not self._history:
            return {"total_analyzed": 0}

        emotion_counts: Dict[str, int] = {}
        for state in self._history:
            key = state.primary.value
            emotion_counts[key] = emotion_counts.get(key, 0) + 1

        return {
            "total_analyzed": len(self._history),
            "emotion_distribution": emotion_counts,
            "mood_trend": self.get_mood_trend().value if self.get_mood_trend() else None,
            "avg_confidence": round(
                sum(s.confidence for s in self._history) / len(self._history), 2
            ),
        }


# Singleton
_detector: Optional[EmotionDetector] = None


def get_emotion_detector() -> EmotionDetector:
    """Get or create the singleton emotion detector."""
    global _detector
    if _detector is None:
        _detector = EmotionDetector()
    return _detector
