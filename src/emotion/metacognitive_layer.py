"""
Metacognitive Layer - Phase 4 Research Implementation

Provides self-reflection, response quality evaluation, error detection,
and emotional appropriateness checking.

DISCLAIMER: Research implementation. Requires user opt-in.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .occ_model import EmotionCategory


@dataclass
class QualityReport:
    """Result of response quality evaluation."""
    score: float                    # 0.0 – 1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    emotionally_appropriate: bool = True
    corrected_response: Optional[str] = None


class ResponseQualityEvaluator:
    """Evaluates response quality on multiple dimensions."""

    MAX_WORDS = 100
    MIN_WORDS = 3

    def evaluate(self, response: str, context: Optional[dict] = None) -> float:
        """
        Score a response from 0.0 to 1.0.

        Considers: length, completeness, clarity.
        """
        words = response.split()
        word_count = len(words)

        if word_count < self.MIN_WORDS:
            return 0.2
        if word_count > self.MAX_WORDS:
            return 0.6  # Too long for voice

        # Penalize responses that are just filler
        filler_phrases = ["i don't know", "i'm not sure", "maybe", "perhaps"]
        filler_count = sum(1 for p in filler_phrases if p in response.lower())
        filler_penalty = filler_count * 0.1

        score = 1.0 - filler_penalty
        return max(0.0, min(1.0, score))


class ErrorDetector:
    """Detects common errors in generated responses."""

    CONTRADICTION_PAIRS = [
        ("yes", "no"),
        ("always", "never"),
        ("can", "cannot"),
        ("will", "won't"),
    ]

    def detect(self, response: str) -> List[str]:
        """Return list of detected error descriptions."""
        errors = []
        lower = response.lower()

        # Check for contradictions
        for word_a, word_b in self.CONTRADICTION_PAIRS:
            if word_a in lower and word_b in lower:
                errors.append(f"Potential contradiction: '{word_a}' and '{word_b}'")

        # Check for incomplete sentences
        if response.strip() and not response.strip()[-1] in ".!?":
            errors.append("Response may be incomplete (no terminal punctuation)")

        # Check for excessive repetition
        words = lower.split()
        if len(words) > 5:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.5:
                errors.append("High word repetition detected")

        return errors

    def correct(self, response: str, errors: List[str]) -> str:
        """Apply basic corrections to the response."""
        corrected = response.strip()
        if corrected and corrected[-1] not in ".!?":
            corrected += "."
        return corrected


class EmotionalAppropriatenessChecker:
    """Checks that responses are emotionally appropriate for the context."""

    INAPPROPRIATE_IN_DISTRESS = [
        "that's great", "wonderful", "fantastic", "amazing", "excellent"
    ]
    INAPPROPRIATE_IN_JOY = [
        "i'm sorry", "unfortunately", "sadly", "regrettably"
    ]

    def check(
        self,
        response: str,
        emotion: Optional[EmotionCategory],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check emotional appropriateness.

        Returns:
            (is_appropriate, suggestion_if_not)
        """
        if emotion is None:
            return True, None

        lower = response.lower()

        if emotion in (EmotionCategory.DISTRESS, EmotionCategory.FEAR,
                       EmotionCategory.DISAPPOINTMENT, EmotionCategory.SHAME):
            for phrase in self.INAPPROPRIATE_IN_DISTRESS:
                if phrase in lower:
                    return False, "Avoid overly positive language when user is distressed."

        if emotion in (EmotionCategory.JOY, EmotionCategory.SATISFACTION,
                       EmotionCategory.PRIDE, EmotionCategory.GRATITUDE):
            for phrase in self.INAPPROPRIATE_IN_JOY:
                if phrase in lower:
                    return False, "Avoid apologetic language when user is in a positive state."

        return True, None


class SelfReflectionEngine:
    """Enables PANDA to reflect on its own responses and improve."""

    def __init__(self):
        self._reflection_log: List[Dict] = []

    def reflect(
        self,
        user_input: str,
        response: str,
        quality_score: float,
        errors: List[str],
    ) -> str:
        """
        Reflect on a response and log insights.

        Returns a reflection summary string.
        """
        entry = {
            "user_input": user_input,
            "response": response,
            "quality_score": quality_score,
            "errors": errors,
        }
        self._reflection_log.append(entry)

        if quality_score < 0.5:
            return f"Low quality response detected (score={quality_score:.2f}). Errors: {errors}"
        if errors:
            return f"Response had {len(errors)} issue(s): {'; '.join(errors)}"
        return f"Response quality acceptable (score={quality_score:.2f})."

    def get_reflection_log(self) -> List[Dict]:
        return list(self._reflection_log)

    def clear_log(self) -> None:
        self._reflection_log.clear()


class MetacognitiveLayer:
    """
    Full metacognitive layer combining quality evaluation, error detection,
    emotional appropriateness checking, and self-reflection.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    def __init__(self):
        self.quality_evaluator  = ResponseQualityEvaluator()
        self.error_detector     = ErrorDetector()
        self.appropriateness    = EmotionalAppropriatenessChecker()
        self.reflection_engine  = SelfReflectionEngine()
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def evaluate(
        self,
        user_input: str,
        response: str,
        emotion: Optional[EmotionCategory] = None,
    ) -> QualityReport:
        """
        Run full metacognitive evaluation on a response.

        Args:
            user_input: Original user input
            response:   Generated response to evaluate
            emotion:    Detected user emotion

        Returns:
            QualityReport with score, issues, and optional correction
        """
        score = self.quality_evaluator.evaluate(response)
        errors = self.error_detector.detect(response)
        appropriate, suggestion = self.appropriateness.check(response, emotion)

        issues = list(errors)
        suggestions = []
        if not appropriate and suggestion:
            issues.append("Emotionally inappropriate")
            suggestions.append(suggestion)

        corrected = None
        if errors:
            corrected = self.error_detector.correct(response, errors)

        reflection = self.reflection_engine.reflect(user_input, response, score, errors)

        return QualityReport(
            score=score,
            issues=issues,
            suggestions=suggestions,
            emotionally_appropriate=appropriate,
            corrected_response=corrected,
        )
