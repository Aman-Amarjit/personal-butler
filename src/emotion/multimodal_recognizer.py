"""
Multimodal Emotion Recognition - Phase 3 Research Implementation

Combines speech prosody, text sentiment, and facial expression analysis
to produce a fused emotion estimate.

DISCLAIMER: Research implementation. Requires user opt-in.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .occ_model import EmotionCategory


@dataclass
class ModalityResult:
    """Emotion estimate from a single modality."""
    emotion: Optional[EmotionCategory]
    confidence: float   # 0.0 – 1.0
    valence: float      # -1.0 to +1.0
    arousal: float      # -1.0 to +1.0


@dataclass
class FusedEmotionResult:
    """Fused emotion estimate from all modalities."""
    emotion: Optional[EmotionCategory]
    confidence: float
    valence: float
    arousal: float
    modality_weights: Dict[str, float] = field(default_factory=dict)


class SpeechProsodyAnalyzer:
    """Analyzes speech prosody features to estimate emotion."""

    def analyze(
        self,
        pitch_hz: float,
        rate_wpm: float,
        energy_db: float,
    ) -> ModalityResult:
        """
        Estimate emotion from prosody features.

        Args:
            pitch_hz:   Average fundamental frequency in Hz
            rate_wpm:   Speech rate in words per minute
            energy_db:  Average energy in dB

        Returns:
            ModalityResult with emotion estimate
        """
        # Normalize features to -1..+1 ranges
        pitch_norm   = (pitch_hz - 150) / 150    # baseline ~150 Hz
        rate_norm    = (rate_wpm - 130) / 130    # baseline ~130 wpm
        energy_norm  = (energy_db + 30) / 30     # baseline ~-30 dB

        arousal  = (abs(pitch_norm) + abs(rate_norm) + abs(energy_norm)) / 3
        valence  = pitch_norm * 0.5 + energy_norm * 0.5

        arousal  = max(-1.0, min(1.0, arousal))
        valence  = max(-1.0, min(1.0, valence))

        emotion = self._map_to_emotion(valence, arousal)
        confidence = min(1.0, (abs(valence) + abs(arousal)) / 2)

        return ModalityResult(emotion=emotion, confidence=confidence,
                              valence=valence, arousal=arousal)

    @staticmethod
    def _map_to_emotion(valence: float, arousal: float) -> EmotionCategory:
        if valence > 0.2 and arousal > 0.2:
            return EmotionCategory.JOY
        if valence > 0.2 and arousal <= 0.2:
            return EmotionCategory.SATISFACTION
        if valence <= -0.2 and arousal > 0.2:
            return EmotionCategory.FEAR
        if valence <= -0.2 and arousal <= -0.2:
            return EmotionCategory.DISTRESS
        return EmotionCategory.HOPE


class TextSentimentAnalyzer:
    """Rule-based text sentiment analysis for emotion estimation."""

    POSITIVE = ["happy", "great", "wonderful", "love", "excellent", "amazing",
                "good", "fantastic", "joy", "pleased", "glad", "excited"]
    NEGATIVE = ["sad", "angry", "frustrated", "hate", "terrible", "awful",
                "bad", "horrible", "fear", "worried", "upset", "distressed"]
    NEGATIONS = ["not", "no", "never", "don't", "doesn't", "didn't", "won't"]

    def analyze(self, text: str) -> ModalityResult:
        """Estimate emotion from text sentiment."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        pos, neg = 0, 0
        negate = False
        for token in tokens:
            if token in self.NEGATIONS:
                negate = True
                continue
            if token in self.POSITIVE:
                neg += 1 if negate else 0
                pos += 0 if negate else 1
            elif token in self.NEGATIVE:
                pos += 1 if negate else 0
                neg += 0 if negate else 1
            negate = False

        total = pos + neg or 1
        valence = (pos - neg) / total
        arousal = min(1.0, (pos + neg) * 0.15)
        confidence = min(1.0, (pos + neg) * 0.2)

        if valence > 0.3:
            emotion = EmotionCategory.JOY
        elif valence < -0.3:
            emotion = EmotionCategory.DISTRESS
        else:
            emotion = EmotionCategory.HOPE

        return ModalityResult(emotion=emotion, confidence=confidence,
                              valence=valence, arousal=arousal)


class FacialExpressionAnalyzer:
    """
    Placeholder facial expression analyzer.

    In production this would use a vision model on screenshots.
    Returns neutral result when no image data is provided.
    """

    def analyze(self, image_data: Optional[bytes] = None) -> ModalityResult:
        """
        Estimate emotion from facial expression.

        Args:
            image_data: Raw image bytes (None for placeholder)

        Returns:
            ModalityResult (neutral when no image provided)
        """
        if image_data is None:
            return ModalityResult(
                emotion=None, confidence=0.0, valence=0.0, arousal=0.0
            )
        # Placeholder: real implementation would run a vision model
        return ModalityResult(
            emotion=EmotionCategory.HOPE, confidence=0.3, valence=0.1, arousal=0.1
        )


class MultimodalEmotionRecognizer:
    """
    Fuses emotion estimates from speech, text, and facial modalities.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    DEFAULT_WEIGHTS = {"speech": 0.4, "text": 0.4, "face": 0.2}

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self.speech_analyzer = SpeechProsodyAnalyzer()
        self.text_analyzer   = TextSentimentAnalyzer()
        self.face_analyzer   = FacialExpressionAnalyzer()
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def recognize(
        self,
        text: str = "",
        pitch_hz: float = 150.0,
        rate_wpm: float = 130.0,
        energy_db: float = -30.0,
        image_data: Optional[bytes] = None,
    ) -> FusedEmotionResult:
        """
        Fuse emotion estimates from all available modalities.

        Returns:
            FusedEmotionResult with weighted fusion
        """
        results = {
            "speech": self.speech_analyzer.analyze(pitch_hz, rate_wpm, energy_db),
            "text":   self.text_analyzer.analyze(text),
            "face":   self.face_analyzer.analyze(image_data),
        }

        total_weight = 0.0
        fused_valence = 0.0
        fused_arousal = 0.0
        emotion_votes: Dict[Optional[EmotionCategory], float] = {}

        for modality, result in results.items():
            w = self.weights.get(modality, 0.0) * result.confidence
            total_weight += w
            fused_valence += result.valence * w
            fused_arousal += result.arousal * w
            emotion_votes[result.emotion] = emotion_votes.get(result.emotion, 0.0) + w

        if total_weight > 0:
            fused_valence /= total_weight
            fused_arousal /= total_weight

        dominant_emotion = max(emotion_votes, key=emotion_votes.get) if emotion_votes else None
        confidence = min(1.0, total_weight)

        return FusedEmotionResult(
            emotion=dominant_emotion,
            confidence=confidence,
            valence=fused_valence,
            arousal=fused_arousal,
            modality_weights={m: self.weights.get(m, 0.0) for m in results},
        )
