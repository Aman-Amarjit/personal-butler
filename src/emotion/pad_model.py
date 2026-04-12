"""
PAD Vector Space - Phase 3 Research Implementation

Implements the Pleasure-Arousal-Dominance (PAD) model for continuous
emotional state representation.

DISCLAIMER: Research implementation. Requires user opt-in.
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from .occ_model import EmotionCategory


@dataclass
class PADVector:
    """
    Pleasure-Arousal-Dominance vector for continuous emotion representation.

    All dimensions range from -1.0 to +1.0.
    """
    pleasure: float = 0.0    # Valence: negative ↔ positive
    arousal: float = 0.0     # Calm ↔ excited
    dominance: float = 0.0   # Submissive ↔ dominant

    def __post_init__(self):
        self.pleasure   = self._clamp(self.pleasure)
        self.arousal    = self._clamp(self.arousal)
        self.dominance  = self._clamp(self.dominance)

    @staticmethod
    def _clamp(v: float) -> float:
        return max(-1.0, min(1.0, v))

    def distance(self, other: "PADVector") -> float:
        """Euclidean distance between two PAD vectors."""
        return math.sqrt(
            (self.pleasure  - other.pleasure)  ** 2 +
            (self.arousal   - other.arousal)   ** 2 +
            (self.dominance - other.dominance) ** 2
        )

    def blend(self, other: "PADVector", alpha: float = 0.5) -> "PADVector":
        """Linear interpolation between two PAD vectors."""
        alpha = max(0.0, min(1.0, alpha))
        return PADVector(
            pleasure   = self.pleasure   + alpha * (other.pleasure   - self.pleasure),
            arousal    = self.arousal    + alpha * (other.arousal    - self.arousal),
            dominance  = self.dominance  + alpha * (other.dominance  - self.dominance),
        )

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.pleasure, self.arousal, self.dominance)


# Canonical PAD mappings for OCC emotions (based on Mehrabian 1996)
EMOTION_PAD_MAP: Dict[EmotionCategory, PADVector] = {
    EmotionCategory.JOY:           PADVector( 0.76,  0.48,  0.35),
    EmotionCategory.DISTRESS:      PADVector(-0.60, -0.33, -0.29),
    EmotionCategory.HOPE:          PADVector( 0.51,  0.23,  0.14),
    EmotionCategory.FEAR:          PADVector(-0.64,  0.60, -0.43),
    EmotionCategory.SATISFACTION:  PADVector( 0.87, -0.18,  0.10),
    EmotionCategory.DISAPPOINTMENT:PADVector(-0.61, -0.15, -0.29),
    EmotionCategory.RELIEF:        PADVector( 0.45, -0.23,  0.29),
    EmotionCategory.FEARS_CONFIRMED:PADVector(-0.70, 0.50, -0.40),
    EmotionCategory.ADMIRATION:    PADVector( 0.50,  0.30, -0.20),
    EmotionCategory.REPROACH:      PADVector(-0.40,  0.20,  0.30),
    EmotionCategory.PRIDE:         PADVector( 0.60,  0.30,  0.60),
    EmotionCategory.SHAME:         PADVector(-0.57, -0.10, -0.60),
    EmotionCategory.GRATITUDE:     PADVector( 0.64,  0.16, -0.30),
    EmotionCategory.ANGER:         PADVector(-0.51,  0.59,  0.25),
    EmotionCategory.LOVE:          PADVector( 0.87,  0.54,  0.46),
    EmotionCategory.HATE:          PADVector(-0.60,  0.60,  0.30),
}


class PADSpace:
    """
    Manages continuous emotional state in PAD vector space.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    def __init__(self, decay_rate: float = 0.05):
        self.current = PADVector()
        self.decay_rate = decay_rate
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def update_from_emotion(
        self,
        emotion: EmotionCategory,
        intensity: float = 1.0,
        blend_alpha: float = 0.3,
    ) -> PADVector:
        """
        Update the PAD state from a discrete emotion.

        Args:
            emotion:     OCC emotion category
            intensity:   Emotion intensity (0.0 – 1.0)
            blend_alpha: How much to shift toward the new emotion

        Returns:
            Updated PAD vector
        """
        target = EMOTION_PAD_MAP.get(emotion, PADVector())
        scaled = PADVector(
            pleasure   = target.pleasure   * intensity,
            arousal    = target.arousal    * intensity,
            dominance  = target.dominance  * intensity,
        )
        self.current = self.current.blend(scaled, blend_alpha)
        return self.current

    def decay(self) -> PADVector:
        """Decay the current PAD state toward neutral (0, 0, 0)."""
        neutral = PADVector()
        self.current = self.current.blend(neutral, self.decay_rate)
        return self.current

    def get_nearest_emotion(self) -> Optional[EmotionCategory]:
        """Find the OCC emotion closest to the current PAD state."""
        if not EMOTION_PAD_MAP:
            return None
        return min(
            EMOTION_PAD_MAP,
            key=lambda e: self.current.distance(EMOTION_PAD_MAP[e])
        )

    def map_emotion_to_pad(self, emotion: EmotionCategory) -> Optional[PADVector]:
        """Return the canonical PAD vector for an OCC emotion."""
        return EMOTION_PAD_MAP.get(emotion)
