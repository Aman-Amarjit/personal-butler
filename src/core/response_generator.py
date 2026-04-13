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


class Response(str):
    """
    Generated response — behaves as a plain string (satisfies isinstance(r, str))
    while also exposing structured attributes (.text, .confidence, .is_template,
    .emotion_markers) for callers that use the object form.
    """

    def __new__(
        cls,
        text: str = "",
        confidence: float = 1.0,
        is_template: bool = False,
        emotion_markers: Optional[Dict[str, float]] = None,
    ):
        instance = str.__new__(cls, text)
        instance.text = text
        instance.confidence = confidence
        instance.is_template = is_template
        instance.emotion_markers = emotion_markers if emotion_markers is not None else {}
        return instance


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
            CommandIntent.GAME_CONTROL: [
                "Done.",
                "Executed.",
                "On it.",
            ],
            CommandIntent.SING: [
                "Let me sing for you!",
                "Here we go!",
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
    ) -> "Response":
        """
        Generate response for command.

        Returns a Response object which is also a plain str, so both
        ``isinstance(r, str)`` and ``r.text`` work correctly.
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

    def format_for_voice(self, response) -> str:
        """
        Format response for voice output.

        Args:
            response: Response object or plain string

        Returns:
            Formatted text for voice
        """
        text = response.text if isinstance(response, Response) else response
        text = self._truncate_to_word_limit(text)
        text = text.replace("_", " ")
        text = text.replace("-", " ")
        return text

    def format_for_display(self, response) -> str:
        """
        Format response for display.

        Args:
            response: Response object or plain string

        Returns:
            Formatted text for display
        """
        return response.text if isinstance(response, Response) else response

    def apply_persona(self, response, butler_mode: bool = False) -> str:
        """
        Apply persona to response.

        Args:
            response: Response object or plain string
            butler_mode: Apply butler persona

        Returns:
            Response with persona applied
        """
        text = response.text if isinstance(response, Response) else response
        if butler_mode:
            prefixes = [
                "If I may, ",
                "Permit me to say, ",
                "I would be delighted to inform you that ",
            ]
            return prefixes[0] + text.lower()
        return text

    def validate_response_quality(self, response) -> float:
        """
        Validate response quality.

        Args:
            response: Response object or plain string

        Returns:
            Quality score (0-1)
        """
        if isinstance(response, Response):
            score = response.confidence
            text = response.text
            is_template = response.is_template
        else:
            score = 0.8
            text = response
            is_template = False

        if len(text) < 5:
            score *= 0.5

        word_count = len(text.split())
        if word_count > self.max_words * 2:
            score *= 0.7

        if is_template:
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
