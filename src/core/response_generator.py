"""
Response Generator

Generates contextually appropriate responses with template-based
and LLM-based generation, response quality validation.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .command_interpreter import CommandIntent


logger = logging.getLogger(__name__)


@dataclass
class Response:
    """Generated response"""
    text: str
    confidence: float
    is_template: bool
    emotion_markers: Dict[str, float]


class ResponseGenerator:
    """
    Generates contextually appropriate responses.
    
    Features:
    - Template-based responses for common scenarios
    - LLM-based responses for complex queries
    - Response length control
    - Quality validation
    - Emotion markers
    """

    def __init__(self, max_words: int = 100):
        """
        Initialize response generator.

        Args:
            max_words: Maximum words for voice output
        """
        self.max_words = max_words

        # Response templates
        self.templates = {
            CommandIntent.APPLICATION_LAUNCH: [
                "Opening {app_name} for you.",
                "Launching {app_name}.",
                "Starting {app_name}.",
            ],
            CommandIntent.SYSTEM_COMMAND: [
                "Executing {command}.",
                "Running {command}.",
                "Performing {command}.",
            ],
            CommandIntent.INFORMATION_RETRIEVAL: [
                "Searching for information about {query}.",
                "Looking up {query}.",
                "Retrieving information on {query}.",
            ],
            CommandIntent.FILE_OPERATION: [
                "Performing file operation: {operation}.",
                "Executing file operation: {operation}.",
            ],
            CommandIntent.UNKNOWN: [
                "I'm not sure what you mean. Could you rephrase that?",
                "I didn't understand that. Could you try again?",
                "Sorry, I didn't catch that.",
            ]
        }

        # Emotion markers
        self.emotion_markers = {
            "happy": {"joy": 0.8, "enthusiasm": 0.7},
            "sad": {"sadness": 0.8, "empathy": 0.6},
            "angry": {"frustration": 0.7, "determination": 0.6},
            "calm": {"serenity": 0.8, "confidence": 0.7},
            "neutral": {"professionalism": 0.8},
        }

    def generate_response(
        self,
        intent,
        context: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        emotion_state: Optional[str] = None
    ) -> Response:
        """
        Generate response for command.

        Args:
            intent: Command intent
            context: Optional context
            entities: Extracted entities
            emotion_state: Emotional state

        Returns:
            Generated Response
        """
        try:
            entities = entities or {}

            # Accept string intent (from interpret()) or CommandIntent enum
            if isinstance(intent, str):
                try:
                    intent = CommandIntent(intent)
                except ValueError:
                    intent = CommandIntent.UNKNOWN

            # Try template-based response first
            template_response = self._generate_template_response(intent, entities)
            if template_response:
                return template_response

            # Fall back to generic response
            return self._generate_generic_response(intent, emotion_state)

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return Response(
                text="I encountered an error processing your request.",
                confidence=0.5,
                is_template=True,
                emotion_markers={}
            )

    def _generate_template_response(
        self,
        intent: CommandIntent,
        entities: Dict[str, Any]
    ) -> Optional[Response]:
        """Generate template-based response"""
        try:
            templates = self.templates.get(intent, [])
            if not templates:
                return None

            # Select first template
            template = templates[0]

            # Format with entities
            try:
                text = template.format(**entities)
            except KeyError:
                # Missing entity, use generic
                return None

            # Validate length
            text = self._truncate_to_word_limit(text)

            return Response(
                text=text,
                confidence=0.9,
                is_template=True,
                emotion_markers={}
            )

        except Exception as e:
            logger.error(f"Error generating template response: {e}")
            return None

    def _generate_generic_response(
        self,
        intent: CommandIntent,
        emotion_state: Optional[str] = None
    ) -> Response:
        """Generate generic response"""
        generic_responses = {
            CommandIntent.APPLICATION_LAUNCH: "Opening the application.",
            CommandIntent.SYSTEM_COMMAND: "Executing the command.",
            CommandIntent.INFORMATION_RETRIEVAL: "Retrieving information.",
            CommandIntent.FILE_OPERATION: "Performing file operation.",
            CommandIntent.TASK_AUTOMATION: "Setting up the task.",
            CommandIntent.UNKNOWN: "I'm not sure what you mean.",
        }

        text = generic_responses.get(
            intent,
            "Processing your request."
        )

        # Get emotion markers
        emotion_markers = self.emotion_markers.get(emotion_state or "neutral", {})

        return Response(
            text=text,
            confidence=0.6,
            is_template=True,
            emotion_markers=emotion_markers
        )

    def format_for_voice(self, response: Response) -> str:
        """
        Format response for voice output.

        Args:
            response: Response to format

        Returns:
            Formatted text for voice
        """
        # Ensure length is appropriate for voice
        text = self._truncate_to_word_limit(response.text)

        # Remove special characters that might confuse TTS
        text = text.replace("_", " ")
        text = text.replace("-", " ")

        return text

    def format_for_display(self, response: Response) -> str:
        """
        Format response for display.

        Args:
            response: Response to format

        Returns:
            Formatted text for display
        """
        return response.text

    def apply_persona(self, response: Response, butler_mode: bool = False) -> str:
        """
        Apply persona to response.

        Args:
            response: Response to modify
            butler_mode: Apply butler persona

        Returns:
            Response with persona applied
        """
        if butler_mode:
            # Add butler-like formality
            prefixes = [
                "If I may, ",
                "Permit me to say, ",
                "I would be delighted to inform you that ",
            ]
            return prefixes[0] + response.text.lower()

        return response.text

    def validate_response_quality(self, response: Response) -> float:
        """
        Validate response quality.

        Args:
            response: Response to validate

        Returns:
            Quality score (0-1)
        """
        score = response.confidence

        # Penalize very short responses
        if len(response.text) < 5:
            score *= 0.5

        # Penalize very long responses
        word_count = len(response.text.split())
        if word_count > self.max_words * 2:
            score *= 0.7

        # Reward template responses
        if response.is_template:
            score *= 1.1

        return min(1.0, score)

    def _truncate_to_word_limit(self, text: str) -> str:
        """Truncate text to word limit"""
        words = text.split()
        if len(words) > self.max_words:
            words = words[:self.max_words]
            text = " ".join(words) + "..."

        return text

    def get_status(self) -> Dict[str, Any]:
        """Get generator status"""
        return {
            "max_words": self.max_words,
            "template_count": sum(len(v) for v in self.templates.values()),
            "emotion_states": list(self.emotion_markers.keys())
        }
