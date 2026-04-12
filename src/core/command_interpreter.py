"""
Command Interpreter

Parses natural language commands and routes to appropriate handlers
with intent classification, entity extraction, and context awareness.
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class CommandIntent(Enum):
    """Command intent types"""
    SYSTEM_COMMAND = "system_command"
    APPLICATION_LAUNCH = "application_launch"
    INFORMATION_RETRIEVAL = "information_retrieval"
    TASK_AUTOMATION = "task_automation"
    FILE_OPERATION = "file_operation"
    UNKNOWN = "unknown"


@dataclass
class Command:
    """Parsed command"""
    intent: CommandIntent
    action: str
    entities: Dict[str, Any]
    confidence: float
    requires_confirmation: bool = False
    context_used: bool = False


class CommandInterpreter:
    """
    Interprets natural language commands.
    
    Features:
    - Intent classification
    - Entity extraction
    - Context awareness
    - Clarification request logic
    - Safety checks
    """

    def __init__(self):
        """Initialize command interpreter"""
        self.conversation_history: List[str] = []
        self.context_window = 5  # Remember last 5 commands

        # Intent patterns
        self.intent_patterns = {
            CommandIntent.APPLICATION_LAUNCH: [
                "open", "launch", "start", "run", "execute"
            ],
            CommandIntent.SYSTEM_COMMAND: [
                "shutdown", "restart", "sleep", "lock", "logout"
            ],
            CommandIntent.INFORMATION_RETRIEVAL: [
                "what", "when", "where", "who", "how", "tell", "show", "get"
            ],
            CommandIntent.FILE_OPERATION: [
                "copy", "move", "delete", "rename", "create", "save"
            ],
            CommandIntent.TASK_AUTOMATION: [
                "schedule", "remind", "set", "create", "add"
            ]
        }

        # Sensitive commands requiring confirmation
        self.sensitive_commands = [
            "delete", "shutdown", "restart", "format", "uninstall"
        ]

    def parse_command(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Command:
        """
        Parse natural language command.

        Args:
            text: Command text
            context: Optional context from conversation history

        Returns:
            Parsed Command object
        """
        try:
            text_lower = text.lower().strip()

            # Add to history
            self.conversation_history.append(text)
            if len(self.conversation_history) > self.context_window:
                self.conversation_history.pop(0)

            # Classify intent
            intent = self._classify_intent(text_lower)

            # Extract entities
            entities = self._extract_entities(text_lower, intent)

            # Calculate confidence
            confidence = self._calculate_confidence(text_lower, intent)

            # Check if confirmation needed
            requires_confirmation = self._requires_confirmation(text_lower)

            # Check if context was used
            context_used = context is not None and len(context) > 0

            command = Command(
                intent=intent,
                action=text_lower,
                entities=entities,
                confidence=confidence,
                requires_confirmation=requires_confirmation,
                context_used=context_used
            )

            logger.info(f"Parsed command: {command.intent.value} (confidence: {confidence:.2f})")
            return command

        except Exception as e:
            logger.error(f"Error parsing command: {e}")
            return Command(
                intent=CommandIntent.UNKNOWN,
                action=text,
                entities={},
                confidence=0.0
            )

    def _classify_intent(self, text: str) -> CommandIntent:
        """Classify command intent"""
        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    return intent

        return CommandIntent.UNKNOWN

    def _extract_entities(
        self,
        text: str,
        intent: CommandIntent
    ) -> Dict[str, Any]:
        """Extract entities from command"""
        entities = {}

        if intent == CommandIntent.APPLICATION_LAUNCH:
            # Extract application name
            keywords = ["open", "launch", "start", "run"]
            for keyword in keywords:
                if keyword in text:
                    parts = text.split(keyword)
                    if len(parts) > 1:
                        app_name = parts[1].strip()
                        entities["app_name"] = app_name
                        break

        elif intent == CommandIntent.FILE_OPERATION:
            # Extract file names
            if "copy" in text or "move" in text:
                entities["operation"] = "copy" if "copy" in text else "move"
            elif "delete" in text:
                entities["operation"] = "delete"
            elif "rename" in text:
                entities["operation"] = "rename"

        elif intent == CommandIntent.INFORMATION_RETRIEVAL:
            # Extract query
            entities["query"] = text

        return entities

    def _calculate_confidence(self, text: str, intent: CommandIntent) -> float:
        """Calculate confidence score"""
        if intent == CommandIntent.UNKNOWN:
            return 0.0

        # Base confidence
        confidence = 0.7

        # Increase confidence for clear commands
        if len(text) > 5:
            confidence += 0.1

        # Decrease confidence for ambiguous commands
        if "maybe" in text or "possibly" in text:
            confidence -= 0.2

        return min(1.0, max(0.0, confidence))

    def _requires_confirmation(self, text: str) -> bool:
        """Check if command requires user confirmation"""
        for sensitive_cmd in self.sensitive_commands:
            if sensitive_cmd in text:
                return True
        return False

    def request_clarification(self, command: Command) -> str:
        """
        Generate clarification request for ambiguous command.

        Args:
            command: Ambiguous command

        Returns:
            Clarification question
        """
        if command.intent == CommandIntent.UNKNOWN:
            return "I'm not sure what you want me to do. Could you rephrase that?"

        if command.intent == CommandIntent.APPLICATION_LAUNCH:
            if "app_name" not in command.entities:
                return "Which application would you like me to open?"

        if command.intent == CommandIntent.FILE_OPERATION:
            return "Could you specify which file you'd like me to work with?"

        return "Could you provide more details?"

    def get_context(self) -> str:
        """Get conversation context"""
        if not self.conversation_history:
            return ""

        return " ".join(self.conversation_history[-self.context_window:])

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def get_status(self) -> Dict[str, Any]:
        """Get interpreter status"""
        return {
            "history_length": len(self.conversation_history),
            "context_window": self.context_window,
            "recent_commands": self.conversation_history[-3:] if self.conversation_history else []
        }

    def interpret(self, text: str) -> dict:
        """
        Convenience wrapper around parse_command that returns a plain dict.

        Args:
            text: Natural language command text

        Returns:
            Dict with 'intent', 'action', 'entities', 'confidence' keys
        """
        cmd = self.parse_command(text)
        return {
            "intent": cmd.intent.value,
            "action": cmd.action,
            "entities": cmd.entities,
            "confidence": cmd.confidence,
            "requires_confirmation": cmd.requires_confirmation,
        }

    @property
    def is_listening(self) -> bool:
        """Compatibility shim used by tests."""
        return False
