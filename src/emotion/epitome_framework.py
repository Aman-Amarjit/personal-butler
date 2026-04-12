"""
EPITOME Framework - Phase 4 Research Implementation

Implements the Empathetic Processing and Interaction Through Organized
Multimodal Engagement (EPITOME) framework with three phases:
  1. Emotional Reaction  - recognize and validate emotions
  2. Interpretation      - understand context and meaning
  3. Exploration         - suggest appropriate support

DISCLAIMER: Research implementation. Requires user opt-in.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .occ_model import EmotionCategory, EmotionState
from .emotion_synthesis import EmotionAwareResponseGenerator, ProsodySettings


@dataclass
class EPITOMEContext:
    """Context passed through EPITOME phases."""
    user_text: str
    detected_emotion: Optional[EmotionCategory] = None
    emotion_intensity: float = 0.0
    interpreted_need: str = ""
    suggested_support: str = ""
    phase_responses: Dict[str, str] = field(default_factory=dict)


class EmotionalReactionPhase:
    """
    Phase 1: Recognize and validate the user's emotional state.
    """

    VALIDATION_TEMPLATES = {
        EmotionCategory.JOY:           "I can see you're feeling great about this!",
        EmotionCategory.DISTRESS:      "I understand you're going through something difficult.",
        EmotionCategory.FEAR:          "It's completely understandable to feel worried about this.",
        EmotionCategory.ANGER:         "I hear your frustration, and it makes sense.",
        EmotionCategory.HOPE:          "I can sense your optimism about this.",
        EmotionCategory.SATISFACTION:  "It sounds like things are going well for you.",
        EmotionCategory.DISAPPOINTMENT:"I'm sorry things didn't work out as you hoped.",
        EmotionCategory.SHAME:         "I understand this feels uncomfortable.",
        EmotionCategory.GRATITUDE:     "It's wonderful that you feel appreciated.",
        EmotionCategory.PRIDE:         "You have every reason to feel proud.",
    }

    def process(self, context: EPITOMEContext) -> str:
        """Recognize and validate the detected emotion."""
        if context.detected_emotion is None:
            response = "I'm here and listening."
        else:
            response = self.VALIDATION_TEMPLATES.get(
                context.detected_emotion,
                "I understand how you're feeling."
            )
        context.phase_responses["reaction"] = response
        return response


class InterpretationPhase:
    """
    Phase 2: Understand the context and underlying need.
    """

    NEED_PATTERNS = {
        "help":       "You seem to need practical assistance.",
        "understand": "You're looking for clarity and understanding.",
        "support":    "You're seeking emotional support.",
        "information":"You need more information to move forward.",
        "action":     "You want to take action on something.",
    }

    def process(self, context: EPITOMEContext) -> str:
        """Interpret the user's underlying need from their text."""
        text_lower = context.user_text.lower()
        need = "general support"

        for keyword, interpretation in self.NEED_PATTERNS.items():
            if keyword in text_lower:
                need = interpretation
                break

        # Emotion-based interpretation
        if context.detected_emotion in (EmotionCategory.FEAR, EmotionCategory.DISTRESS):
            need = "reassurance and a clear path forward"
        elif context.detected_emotion in (EmotionCategory.JOY, EmotionCategory.SATISFACTION):
            need = "to share and celebrate this moment"
        elif context.detected_emotion == EmotionCategory.ANGER:
            need = "to be heard and to find a resolution"

        context.interpreted_need = need
        response = f"It seems like you're looking for {need}."
        context.phase_responses["interpretation"] = response
        return response


class ExplorationPhase:
    """
    Phase 3: Suggest appropriate support based on context.
    """

    SUPPORT_SUGGESTIONS = {
        EmotionCategory.DISTRESS:      [
            "Would it help to talk through what's bothering you?",
            "I can help you break this down into smaller steps.",
            "Sometimes it helps to focus on what you can control.",
        ],
        EmotionCategory.FEAR:          [
            "Let's look at this together — what specifically worries you most?",
            "I can help you prepare for different scenarios.",
            "Would you like me to find some resources on this?",
        ],
        EmotionCategory.ANGER:         [
            "Would you like to talk through what happened?",
            "I can help you think through your options.",
            "Sometimes writing down your thoughts can help clarify things.",
        ],
        EmotionCategory.JOY:           [
            "That's fantastic! Would you like to build on this momentum?",
            "How can I help you make the most of this?",
        ],
        EmotionCategory.DISAPPOINTMENT:[
            "I'm sorry this didn't work out. What would help most right now?",
            "Would you like to explore alternative approaches?",
        ],
    }

    DEFAULT_SUGGESTIONS = [
        "How can I best support you right now?",
        "Would you like me to help you think through your options?",
        "I'm here to help — what would be most useful?",
    ]

    def process(self, context: EPITOMEContext) -> str:
        """Suggest appropriate support."""
        suggestions = self.SUPPORT_SUGGESTIONS.get(
            context.detected_emotion,
            self.DEFAULT_SUGGESTIONS
        )
        response = suggestions[0]
        context.suggested_support = response
        context.phase_responses["exploration"] = response
        return response


class EPITOMEFramework:
    """
    Full EPITOME empathetic interaction framework.

    Processes user input through three phases to generate
    empathetic, contextually appropriate responses.

    RESEARCH IMPLEMENTATION - requires user opt-in.
    """

    def __init__(self):
        self.reaction_phase     = EmotionalReactionPhase()
        self.interpretation_phase = InterpretationPhase()
        self.exploration_phase  = ExplorationPhase()
        self.response_generator = EmotionAwareResponseGenerator()
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True
        self.response_generator.enable()

    def disable(self) -> None:
        self._enabled = False
        self.response_generator.disable()

    def process(
        self,
        user_text: str,
        detected_emotion: Optional[EmotionCategory] = None,
        emotion_intensity: float = 0.5,
    ) -> Tuple[str, EPITOMEContext]:
        """
        Process user input through all three EPITOME phases.

        Args:
            user_text:          Raw user input text
            detected_emotion:   Emotion detected from multimodal recognition
            emotion_intensity:  Intensity of the detected emotion

        Returns:
            (final_response, context) tuple
        """
        context = EPITOMEContext(
            user_text=user_text,
            detected_emotion=detected_emotion,
            emotion_intensity=emotion_intensity,
        )

        reaction      = self.reaction_phase.process(context)
        interpretation = self.interpretation_phase.process(context)
        exploration   = self.exploration_phase.process(context)

        # Compose final response
        parts = [reaction, interpretation, exploration]
        final_response = " ".join(p for p in parts if p)

        return final_response, context

    def generate_phase_response(
        self,
        phase: str,
        context: EPITOMEContext,
    ) -> str:
        """Generate a response for a specific phase."""
        return context.phase_responses.get(phase, "")
