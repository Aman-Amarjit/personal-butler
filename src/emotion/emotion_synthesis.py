"""
Emotion Synthesis & Response Generation - Phase 2 Research Implementation

Implements affective decoding, dual emotion encoding, and emotion-aware
response generation with prosody application to TTS.

DISCLAIMER: Research implementation. Requires user opt-in.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .occ_model import EmotionCategory, EmotionState, AppraisalResult


# ---------------------------------------------------------------------------
# Emotion-aware response templates
# ---------------------------------------------------------------------------

EMOTION_TEMPLATES: Dict[str, List[str]] = {
    "joy": [
        "That's wonderful! {content}",
        "Great news! {content}",
        "I'm happy to help with that. {content}",
    ],
    "distress": [
        "I understand this is difficult. {content}",
        "I'm sorry to hear that. {content}",
        "Let me help you through this. {content}",
    ],
    "hope": [
        "Things are looking up. {content}",
        "There's a good chance that {content}",
        "I'm optimistic that {content}",
    ],
    "fear": [
        "I understand your concern. {content}",
        "Let's address this carefully. {content}",
        "I'll help you handle this. {content}",
    ],
    "neutral": [
        "{content}",
        "Here's what I found: {content}",
        "Sure, {content}",
    ],
}


@dataclass
class DualEmotionEncoding:
    """Encodes both speaker and listener emotional states."""
    speaker_emotion: Optional[EmotionCategory] = None
    speaker_intensity: float = 0.0
    listener_emotion: Optional[EmotionCategory] = None
    listener_intensity: float = 0.0
    balanced_valence: float = 0.0

    def balance(self) -> float:
        """Compute a balanced valence considering both parties."""
        speaker_val = self.speaker_intensity * (
            1.0 if self.speaker_emotion and self.speaker_emotion.value in
            ("joy", "hope", "satisfaction", "admiration", "pride", "gratitude", "love")
            else -1.0
        ) if self.speaker_emotion else 0.0

        listener_val = self.listener_intensity * (
            1.0 if self.listener_emotion and self.listener_emotion.value in
            ("joy", "hope", "satisfaction", "admiration", "pride", "gratitude", "love")
            else -1.0
        ) if self.listener_emotion else 0.0

        self.balanced_valence = (speaker_val + listener_val) / 2.0
        return self.balanced_valence


@dataclass
class ProsodySettings:
    """TTS prosody settings derived from emotional state."""
    rate: float = 1.0       # Speech rate multiplier
    pitch: float = 1.0      # Pitch multiplier
    volume: float = 1.0     # Volume multiplier
    emphasis: str = "none"  # none / moderate / strong


class EmotionConsistencyChecker:
    """Checks that generated responses are emotionally consistent."""

    POSITIVE_EMOTIONS = {
        EmotionCategory.JOY, EmotionCategory.HOPE, EmotionCategory.SATISFACTION,
        EmotionCategory.RELIEF, EmotionCategory.ADMIRATION, EmotionCategory.PRIDE,
        EmotionCategory.GRATITUDE, EmotionCategory.LOVE, EmotionCategory.GRATIFICATION,
        EmotionCategory.HAPPY_FOR,
    }
    NEGATIVE_EMOTIONS = {
        EmotionCategory.DISTRESS, EmotionCategory.FEAR, EmotionCategory.DISAPPOINTMENT,
        EmotionCategory.FEARS_CONFIRMED, EmotionCategory.REPROACH, EmotionCategory.SHAME,
        EmotionCategory.ANGER, EmotionCategory.HATE, EmotionCategory.REMORSE,
        EmotionCategory.RESENTMENT, EmotionCategory.GLOATING, EmotionCategory.PITY,
    }

    def check(self, response: str, emotion: Optional[EmotionCategory]) -> bool:
        """
        Verify the response text is consistent with the emotion.

        Returns True if consistent, False if contradiction detected.
        """
        if emotion is None:
            return True

        response_lower = response.lower()
        positive_words = {"great", "wonderful", "happy", "excellent", "good", "sure"}
        negative_words = {"sorry", "difficult", "concern", "careful", "understand"}

        has_positive = any(w in response_lower for w in positive_words)
        has_negative = any(w in response_lower for w in negative_words)

        if emotion in self.POSITIVE_EMOTIONS and has_negative and not has_positive:
            return False
        if emotion in self.NEGATIVE_EMOTIONS and has_positive and not has_negative:
            return False
        return True


class AffinityDecoder:
    """Decodes affective content from text for language generation."""

    POSITIVE_MARKERS = ["happy", "great", "wonderful", "love", "excellent", "amazing"]
    NEGATIVE_MARKERS = ["sad", "angry", "frustrated", "hate", "terrible", "awful"]

    def decode(self, text: str) -> Tuple[float, float]:
        """
        Decode affective content from text.

        Returns:
            (valence, arousal) both in range -1.0 to +1.0
        """
        text_lower = text.lower()
        pos_count = sum(1 for w in self.POSITIVE_MARKERS if w in text_lower)
        neg_count = sum(1 for w in self.NEGATIVE_MARKERS if w in text_lower)
        total = pos_count + neg_count or 1
        valence = (pos_count - neg_count) / total
        arousal = min(1.0, (pos_count + neg_count) * 0.2)
        return valence, arousal


class EmotionAwareResponseGenerator:
    """
    Generates emotion-aware responses using dual encoding and templates.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    def __init__(self):
        self.decoder = AffinityDecoder()
        self.consistency_checker = EmotionConsistencyChecker()
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def encode_dual_emotion(
        self,
        speaker_state: EmotionState,
        listener_text: str,
    ) -> DualEmotionEncoding:
        """Encode both speaker and listener emotional states."""
        encoding = DualEmotionEncoding()

        if speaker_state.dominant:
            encoding.speaker_emotion = speaker_state.dominant
            encoding.speaker_intensity = speaker_state.emotions.get(
                speaker_state.dominant, 0.0
            )

        valence, _ = self.decoder.decode(listener_text)
        if valence > 0.3:
            encoding.listener_emotion = EmotionCategory.JOY
            encoding.listener_intensity = valence
        elif valence < -0.3:
            encoding.listener_emotion = EmotionCategory.DISTRESS
            encoding.listener_intensity = abs(valence)

        encoding.balance()
        return encoding

    def apply_prosody(self, emotion: Optional[EmotionCategory]) -> ProsodySettings:
        """Derive TTS prosody settings from the current emotion."""
        settings = ProsodySettings()
        if emotion is None:
            return settings

        prosody_map = {
            EmotionCategory.JOY:          ProsodySettings(rate=1.1, pitch=1.1, volume=1.0, emphasis="moderate"),
            EmotionCategory.DISTRESS:     ProsodySettings(rate=0.9, pitch=0.9, volume=0.9, emphasis="moderate"),
            EmotionCategory.FEAR:         ProsodySettings(rate=1.2, pitch=1.2, volume=0.8, emphasis="strong"),
            EmotionCategory.ANGER:        ProsodySettings(rate=1.1, pitch=0.8, volume=1.1, emphasis="strong"),
            EmotionCategory.HOPE:         ProsodySettings(rate=1.0, pitch=1.05, volume=1.0, emphasis="none"),
            EmotionCategory.SATISFACTION: ProsodySettings(rate=0.95, pitch=1.0, volume=1.0, emphasis="none"),
        }
        return prosody_map.get(emotion, settings)

    def generate(
        self,
        content: str,
        emotion: Optional[EmotionCategory] = None,
    ) -> Tuple[str, ProsodySettings]:
        """
        Generate an emotion-aware response.

        Args:
            content: Core response content
            emotion: Target emotion for the response

        Returns:
            (response_text, prosody_settings)
        """
        if not self._enabled or emotion is None:
            return content, ProsodySettings()

        templates = EMOTION_TEMPLATES.get(
            emotion.value,
            EMOTION_TEMPLATES["neutral"]
        )
        template = templates[0]
        response = template.format(content=content)

        if not self.consistency_checker.check(response, emotion):
            response = content  # Fall back to plain content

        prosody = self.apply_prosody(emotion)
        return response, prosody
