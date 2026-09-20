"""
Tests for Emotion Detection module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.emotion import (
    Emotion,
    EmotionState,
    EmotionDetector,
    get_response_style,
    get_emotion_detector,
)


@pytest.fixture
def detector():
    return EmotionDetector()


class TestEmotionDetection:
    def test_neutral(self, detector):
        state = detector.detect("Hola Luna")
        assert state.primary == Emotion.NEUTRAL

    def test_happy(self, detector):
        state = detector.detect("¡Genial! Me encanta, jaja :D")
        assert state.primary == Emotion.HAPPY
        assert state.confidence > 0

    def test_happy_emojis(self, detector):
        state = detector.detect("😊🎉❤️")
        assert state.primary == Emotion.HAPPY

    def test_sad(self, detector):
        state = detector.detect("Estoy triste hoy, todo mal 😢")
        assert state.primary == Emotion.SAD

    def test_frustrated(self, detector):
        state = detector.detect("No funciona esta wea, pucha!")
        assert state.primary == Emotion.FRUSTRATED

    def test_tired(self, detector):
        state = detector.detect("Estoy agotado, tengo mucho sueño")
        assert state.primary == Emotion.TIRED

    def test_curious(self, detector):
        state = detector.detect("¿Cómo funciona esto? Explícame")
        assert state.primary == Emotion.CURIOUS

    def test_confused(self, detector):
        state = detector.detect("No entiendo, no cacho qué onda")
        assert state.primary == Emotion.CONFUSED

    def test_grateful(self, detector):
        state = detector.detect("Gracias, te pasaste!")
        assert state.primary == Emotion.GRATEFUL

    def test_anxious(self, detector):
        state = detector.detect("Estoy preocupado, no sé qué hacer")
        assert state.primary == Emotion.ANXIOUS


class TestEmotionIntensity:
    def test_caps_increases_intensity(self, detector):
        state = detector.detect("NOOOO")
        assert state.intensity > 0.5

    def test_multiple_exclamation_marks(self, detector):
        state = detector.detect("Increíble!!!")
        assert state.intensity > 0.5

    def test_short_emotional_message(self, detector):
        state = detector.detect("jaja :D")
        assert state.intensity >= 0.5


class TestEmotionHistory:
    def test_mood_trend(self, detector):
        for _ in range(4):
            detector.detect("Estoy mal, todo triste :(")
        trend = detector.get_mood_trend()
        assert trend == Emotion.SAD

    def test_no_trend_with_few_messages(self, detector):
        detector.detect("hola")
        trend = detector.get_mood_trend()
        assert trend is None

    def test_stats(self, detector):
        detector.detect("hola")
        detector.detect("genial!")
        stats = detector.get_stats()
        assert stats["total_analyzed"] == 2
        assert "emotion_distribution" in stats


class TestResponseStyle:
    def test_happy_style(self):
        emotion = EmotionState(primary=Emotion.HAPPY, confidence=0.8)
        style = get_response_style(emotion)
        assert style.tone == "warm"
        assert style.extra_enthusiasm is True

    def test_sad_style(self):
        emotion = EmotionState(primary=Emotion.SAD, confidence=0.7)
        style = get_response_style(emotion)
        assert style.tone == "gentle"
        assert style.include_comfort is True

    def test_neutral_style(self):
        emotion = EmotionState(primary=Emotion.NEUTRAL, confidence=0.3)
        style = get_response_style(emotion)
        assert style.tone == "normal"
        modifier = style.to_prompt_modifier()
        assert modifier == ""  # No modifier for neutral

    def test_style_has_prompt_modifier(self):
        emotion = EmotionState(primary=Emotion.FRUSTRATED, confidence=0.8)
        style = get_response_style(emotion)
        modifier = style.to_prompt_modifier()
        assert len(modifier) > 0

    def test_tired_style_brief(self):
        emotion = EmotionState(primary=Emotion.TIRED, confidence=0.7)
        style = get_response_style(emotion)
        assert style.response_length == "brief"
