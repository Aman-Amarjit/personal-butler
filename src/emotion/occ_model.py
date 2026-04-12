"""
OCC Appraisal Model - Phase 2 Research Implementation

Implements the Ortony-Clore-Collins (OCC) cognitive appraisal model for
emotion synthesis. This is a research implementation with user opt-in.

DISCLAIMER: This is a research implementation. Emotion synthesis is an
active research area and results may not be clinically accurate.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class EmotionCategory(Enum):
    """OCC emotion taxonomy categories."""
    # Reactions to events
    JOY = "joy"
    DISTRESS = "distress"
    HOPE = "hope"
    FEAR = "fear"
    SATISFACTION = "satisfaction"
    DISAPPOINTMENT = "disappointment"
    RELIEF = "relief"
    FEARS_CONFIRMED = "fears_confirmed"
    # Reactions to agents
    ADMIRATION = "admiration"
    REPROACH = "reproach"
    PRIDE = "pride"
    SHAME = "shame"
    GRATITUDE = "gratitude"
    ANGER = "anger"
    # Reactions to objects
    LOVE = "love"
    HATE = "hate"
    # Compound
    GRATIFICATION = "gratification"
    REMORSE = "remorse"
    HAPPY_FOR = "happy_for"
    RESENTMENT = "resentment"
    GLOATING = "gloating"
    PITY = "pity"


@dataclass
class AppraisalResult:
    """Result of an OCC appraisal computation."""
    emotion: EmotionCategory
    intensity: float          # 0.0 – 1.0
    desirability: float       # -1.0 to +1.0
    likelihood: float         # 0.0 – 1.0
    expectedness: float       # 0.0 – 1.0 (1 = fully expected)
    valence: float            # -1.0 to +1.0 (positive/negative)


@dataclass
class EmotionState:
    """Current emotional state as a weighted mix of emotions."""
    emotions: Dict[EmotionCategory, float] = field(default_factory=dict)
    dominant: Optional[EmotionCategory] = None
    overall_valence: float = 0.0

    def update(self, result: AppraisalResult, decay: float = 0.9) -> None:
        """Update state with a new appraisal, applying decay to existing emotions."""
        for cat in list(self.emotions):
            self.emotions[cat] *= decay
            if self.emotions[cat] < 0.01:
                del self.emotions[cat]
        self.emotions[result.emotion] = max(
            self.emotions.get(result.emotion, 0.0),
            result.intensity
        )
        if self.emotions:
            self.dominant = max(self.emotions, key=self.emotions.get)
            self.overall_valence = sum(
                v * (1.0 if cat.value in ("joy", "hope", "satisfaction", "relief",
                                          "admiration", "pride", "gratitude",
                                          "love", "gratification", "happy_for")
                     else -1.0)
                for cat, v in self.emotions.items()
            ) / len(self.emotions)


class EmotionSynthesizer:
    """
    OCC-based emotion synthesizer.

    Computes emotional responses to events using desirability,
    likelihood, and expectedness appraisals.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    # Emotion taxonomy: maps (desirability_sign, likelihood_high, expected) → emotion
    _TAXONOMY: Dict[Tuple, EmotionCategory] = {
        (1, True,  True):  EmotionCategory.SATISFACTION,
        (1, True,  False): EmotionCategory.JOY,
        (1, False, True):  EmotionCategory.HOPE,
        (1, False, False): EmotionCategory.HOPE,
        (-1, True,  True): EmotionCategory.FEARS_CONFIRMED,
        (-1, True,  False): EmotionCategory.DISTRESS,
        (-1, False, True): EmotionCategory.FEAR,
        (-1, False, False): EmotionCategory.FEAR,
    }

    def __init__(self):
        self.state = EmotionState()
        self._enabled = False  # Requires explicit opt-in

    def enable(self) -> None:
        """Enable emotion synthesis (user opt-in required)."""
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def appraise(
        self,
        desirability: float,
        likelihood: float,
        expectedness: float,
    ) -> AppraisalResult:
        """
        Compute an OCC appraisal.

        Args:
            desirability: How desirable the event is (-1.0 to +1.0)
            likelihood:   Probability the event occurs (0.0 to 1.0)
            expectedness: How expected the event was (0.0 to 1.0)

        Returns:
            AppraisalResult with computed emotion and intensity
        """
        desirability = max(-1.0, min(1.0, desirability))
        likelihood   = max(0.0,  min(1.0, likelihood))
        expectedness = max(0.0,  min(1.0, expectedness))

        key = (
            1 if desirability >= 0 else -1,
            likelihood >= 0.5,
            expectedness >= 0.5,
        )
        emotion = self._TAXONOMY.get(key, EmotionCategory.JOY)
        intensity = abs(desirability) * likelihood

        result = AppraisalResult(
            emotion=emotion,
            intensity=intensity,
            desirability=desirability,
            likelihood=likelihood,
            expectedness=expectedness,
            valence=desirability,
        )

        if self._enabled:
            self.state.update(result)

        return result

    def get_emotion_taxonomy(self) -> Dict[str, List[str]]:
        """Return the full emotion taxonomy grouped by category."""
        return {
            "event_reactions": [
                "joy", "distress", "hope", "fear",
                "satisfaction", "disappointment", "relief", "fears_confirmed"
            ],
            "agent_reactions": [
                "admiration", "reproach", "pride", "shame", "gratitude", "anger"
            ],
            "object_reactions": ["love", "hate"],
            "compound": [
                "gratification", "remorse", "happy_for",
                "resentment", "gloating", "pity"
            ],
        }

    def reset_state(self) -> None:
        """Reset the current emotional state."""
        self.state = EmotionState()
