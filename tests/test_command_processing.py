"""Unit tests for command processing components"""

import pytest
from src.core.command_interpreter import (
    CommandInterpreter,
    CommandIntent,
    Command
)
from src.core.command_executor import (
    CommandExecutor,
    ExecutionStatus
)
from src.core.response_generator import ResponseGenerator


class TestCommandInterpreter:
    """Test command interpreter"""

    def test_initialization(self):
        """Test interpreter initialization"""
        interpreter = CommandInterpreter()
        assert interpreter.context_window == 5
        assert len(interpreter.conversation_history) == 0

    def test_parse_application_launch(self):
        """Test parsing application launch command"""
        interpreter = CommandInterpreter()
        command = interpreter.parse_command("open notepad")

        assert command.intent == CommandIntent.APPLICATION_LAUNCH
        assert "app_name" in command.entities
        assert command.confidence > 0.5

    def test_parse_system_command(self):
        """Test parsing system command"""
        interpreter = CommandInterpreter()
        command = interpreter.parse_command("shutdown the computer")

        assert command.intent == CommandIntent.SYSTEM_COMMAND

    def test_parse_information_retrieval(self):
        """Test parsing information retrieval"""
        interpreter = CommandInterpreter()
        command = interpreter.parse_command("what is the weather")

        assert command.intent == CommandIntent.INFORMATION_RETRIEVAL

    def test_requires_confirmation(self):
        """Test confirmation requirement detection"""
        interpreter = CommandInterpreter()
        command = interpreter.parse_command("delete all files")

        assert command.requires_confirmation is True

    def test_conversation_history(self):
        """Test conversation history tracking"""
        interpreter = CommandInterpreter()
        interpreter.parse_command("open notepad")
        interpreter.parse_command("open calculator")

        assert len(interpreter.conversation_history) == 2

    def test_clarification_request(self):
        """Test clarification request generation"""
        interpreter = CommandInterpreter()
        command = Command(
            intent=CommandIntent.UNKNOWN,
            action="something",
            entities={},
            confidence=0.0
        )

        clarification = interpreter.request_clarification(command)
        assert len(clarification) > 0

    def test_clear_history(self):
        """Test clearing history"""
        interpreter = CommandInterpreter()
        interpreter.parse_command("open notepad")
        interpreter.clear_history()

        assert len(interpreter.conversation_history) == 0


class TestCommandExecutor:
    """Test command executor"""

    def test_initialization(self):
        """Test executor initialization"""
        executor = CommandExecutor()
        assert len(executor.safe_commands) > 0
        assert len(executor.blocked_commands) > 0

    def test_validate_blocked_command(self):
        """Test blocked command validation"""
        executor = CommandExecutor()
        command = Command(
            intent=CommandIntent.FILE_OPERATION,
            action="format c:",
            entities={},
            confidence=0.9
        )

        result = executor._validate_command(command)
        assert result.status == ExecutionStatus.PERMISSION_DENIED

    def test_validate_low_confidence(self):
        """Test low confidence validation"""
        executor = CommandExecutor()
        command = Command(
            intent=CommandIntent.APPLICATION_LAUNCH,
            action="maybe open something",
            entities={},
            confidence=0.3
        )

        result = executor._validate_command(command)
        assert result.status == ExecutionStatus.INVALID_COMMAND

    def test_execute_application_launch(self):
        """Test application launch execution"""
        executor = CommandExecutor()
        command = Command(
            intent=CommandIntent.APPLICATION_LAUNCH,
            action="open notepad",
            entities={"app_name": "notepad"},
            confidence=0.9
        )

        # Note: This will actually try to launch notepad
        # In production, would mock this
        result = executor._execute_application_launch(command)
        assert result.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]

    def test_confirmation_pending(self):
        """Test pending confirmation status"""
        executor = CommandExecutor()
        command = Command(
            intent=CommandIntent.SYSTEM_COMMAND,
            action="shutdown",
            entities={},
            confidence=0.9,
            requires_confirmation=True
        )

        result = executor.execute(command)
        assert result.status == ExecutionStatus.PENDING_CONFIRMATION


class TestResponseGenerator:
    """Test response generator"""

    def test_initialization(self):
        """Test generator initialization"""
        generator = ResponseGenerator(max_words=100)
        assert generator.max_words == 100
        assert len(generator.templates) > 0

    def test_generate_template_response(self):
        """Test template response generation"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.APPLICATION_LAUNCH,
            entities={"app_name": "notepad"}
        )

        assert response.text is not None
        assert response.is_template is True
        assert response.confidence > 0.5

    def test_generate_generic_response(self):
        """Test generic response generation"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.UNKNOWN
        )

        assert response.text is not None
        assert len(response.text) > 0

    def test_format_for_voice(self):
        """Test voice formatting"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.APPLICATION_LAUNCH,
            entities={"app_name": "notepad"}
        )

        voice_text = generator.format_for_voice(response)
        assert len(voice_text) <= generator.max_words * 10  # Rough estimate

    def test_format_for_display(self):
        """Test display formatting"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.APPLICATION_LAUNCH,
            entities={"app_name": "notepad"}
        )

        display_text = generator.format_for_display(response)
        assert display_text == response.text

    def test_apply_butler_persona(self):
        """Test butler persona application"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.APPLICATION_LAUNCH,
            entities={"app_name": "notepad"}
        )

        butler_text = generator.apply_persona(response, butler_mode=True)
        assert len(butler_text) > len(response.text)

    def test_validate_response_quality(self):
        """Test response quality validation"""
        generator = ResponseGenerator()
        response = generator.generate_response(
            intent=CommandIntent.APPLICATION_LAUNCH,
            entities={"app_name": "notepad"}
        )

        quality = generator.validate_response_quality(response)
        assert 0 <= quality <= 1.5  # Can be > 1 due to template bonus

    def test_truncate_to_word_limit(self):
        """Test word limit truncation"""
        generator = ResponseGenerator(max_words=5)
        long_text = "This is a very long text with many words that should be truncated"

        truncated = generator._truncate_to_word_limit(long_text)
        word_count = len(truncated.split())

        assert word_count <= generator.max_words + 1  # +1 for "..."
