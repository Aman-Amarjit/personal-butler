"""Integration tests for JARVIS AI Assistant

Tests end-to-end workflows and component interactions.
"""

import pytest
import tempfile
import os
from datetime import datetime

from src.core.ollama_integration import OllamaIntegration, ModelSize
from src.core.command_interpreter import CommandInterpreter, CommandIntent
from src.core.command_executor import CommandExecutor, ExecutionStatus
from src.core.response_generator import ResponseGenerator
from src.voice.wake_word_detector import WakeWordDetector
from src.voice.speech_to_text import SpeechToTextEngine
from src.voice.text_to_speech import TextToSpeechEngine
from src.ui.information_display import InformationDisplay
from src.security.encryption_manager import EncryptionManager
from src.security.audit_logger import AuditLogger
from src.security.capability_gate import CapabilityGate, TrustLevel, Capability
from src.security.circuit_breaker import CircuitBreaker


class TestVoiceCommandFlow:
    """Test end-to-end voice command flow"""

    def test_complete_voice_command_workflow(self):
        """Test complete workflow from voice to execution"""
        # Initialize components
        interpreter = CommandInterpreter()
        executor = CommandExecutor()
        generator = ResponseGenerator()

        # Parse command
        command = interpreter.parse_command("open notepad")
        assert command.intent == CommandIntent.APPLICATION_LAUNCH

        # Execute command
        result = executor.execute(command)
        assert result.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]

        # Generate response
        response = generator.generate_response(
            intent=command.intent,
            entities=command.entities
        )
        assert response.text is not None
        assert len(response.text) > 0

    def test_command_with_context(self):
        """Test command interpretation with context"""
        interpreter = CommandInterpreter()

        # First command
        cmd1 = interpreter.parse_command("open notepad")
        assert cmd1.intent == CommandIntent.APPLICATION_LAUNCH

        # Second command with context
        context = interpreter.get_context()
        cmd2 = interpreter.parse_command("close it", context=context)
        assert cmd2.context_used is True

    def test_clarification_workflow(self):
        """Test clarification request workflow"""
        interpreter = CommandInterpreter()
        executor = CommandExecutor()

        # Ambiguous command
        command = interpreter.parse_command("do something")
        assert command.intent == CommandIntent.UNKNOWN

        # Request clarification
        clarification = interpreter.request_clarification(command)
        assert len(clarification) > 0


class TestSecurityWorkflow:
    """Test security features workflow"""

    def test_encryption_and_audit_workflow(self):
        """Test encryption and audit logging together"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            
            # Initialize security components
            encryptor = EncryptionManager(password="test_password")
            auditor = AuditLogger(db_path=db_path)

            # Encrypt sensitive data
            sensitive_data = "user_credentials"
            encrypted = encryptor.encrypt_data(sensitive_data)

            # Log the encryption action
            auditor.log_action(
                action="encrypt_data",
                user="system",
                details={"data_type": "credentials"}
            )

            # Verify audit trail
            trail = auditor.get_audit_trail()
            assert len(trail) > 0

            # Verify log integrity
            is_valid = auditor.verify_log_integrity(1)
            assert is_valid is True

    def test_capability_gating_workflow(self):
        """Test capability gating with trust progression"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.UNTRUSTED)

        # Basic capabilities available
        assert gate.can_execute(Capability.VOICE_INTERACTION) is True

        # Restricted capabilities blocked
        assert gate.can_execute(Capability.FILE_DELETION) is False

        # Increase trust level
        gate.increase_trust_level()
        assert gate.trust_level == TrustLevel.LOW

        # More capabilities available
        assert gate.can_execute(Capability.APPLICATION_LAUNCH) is True

        # Continue progression
        gate.increase_trust_level()
        gate.increase_trust_level()
        assert gate.trust_level == TrustLevel.HIGH

        # High trust capabilities available
        assert gate.can_execute(Capability.SYSTEM_SHUTDOWN) is True

    def test_circuit_breaker_protection(self):
        """Test circuit breaker protecting against infinite loops"""
        breaker = CircuitBreaker(max_iterations=10)

        # Simulate loop
        iterations = 0
        while iterations < 20:
            if not breaker.increment_iteration():
                break
            iterations += 1

        # Should stop at max iterations
        assert iterations == 10
        assert breaker.is_circuit_open() is True


class TestInformationDisplayWorkflow:
    """Test information display workflow"""

    def test_information_display_startup(self):
        """Test starting all information display widgets"""
        display = InformationDisplay()

        # Start all widgets
        display.start_all_widgets()
        assert display.is_active is True

        # Get all display text
        text = display.get_all_display_text()
        assert "weather" in text
        assert "calendar" in text
        assert "system_status" in text
        assert "time" in text

        # Stop widgets
        display.stop_all_widgets()
        assert display.is_active is False

    def test_notification_workflow(self):
        """Test notification queue workflow"""
        display = InformationDisplay()

        # Add notifications
        from src.ui.information_display import Notification
        
        for i in range(3):
            notification = Notification(
                title=f"Alert {i}",
                message=f"Test message {i}",
                timestamp=datetime.now(),
                priority="normal"
            )
            display.notifications.add_notification(notification)

        # Get notifications
        notifications = display.notifications.get_notifications(count=2)
        assert len(notifications) == 2


class TestMemoryAndContextWorkflow:
    """Test memory and context management"""

    def test_conversation_history_management(self):
        """Test conversation history tracking"""
        interpreter = CommandInterpreter()

        # Add multiple commands
        commands = [
            "open notepad",
            "what is the weather",
            "close it",
            "open calculator"
        ]

        for cmd in commands:
            interpreter.parse_command(cmd)

        # Check history
        assert len(interpreter.conversation_history) == 4

        # Get context
        context = interpreter.get_context()
        assert len(context) > 0

        # Clear history
        interpreter.clear_history()
        assert len(interpreter.conversation_history) == 0


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery"""

    def test_command_execution_error_recovery(self):
        """Test recovery from command execution errors"""
        executor = CommandExecutor()
        interpreter = CommandInterpreter()

        # Try to execute invalid command
        command = interpreter.parse_command("delete all files")
        result = executor.execute(command)

        # Should handle gracefully
        assert result.status in [
            ExecutionStatus.PENDING_CONFIRMATION,
            ExecutionStatus.PERMISSION_DENIED
        ]

    def test_ollama_fallback_workflow(self):
        """Test Ollama fallback when unavailable"""
        ollama = OllamaIntegration()

        # Check if running
        is_running = ollama.verify_running()

        if not is_running:
            # Use fallback response
            fallback = ollama.handle_unavailable()
            assert len(fallback) > 0
            assert "unavailable" in fallback.lower() or "unable" in fallback.lower()


class TestPerformanceWorkflow:
    """Test performance characteristics"""

    def test_command_processing_latency(self):
        """Test command processing latency"""
        import time

        interpreter = CommandInterpreter()
        executor = CommandExecutor()
        generator = ResponseGenerator()

        start_time = time.time()

        # Process command
        command = interpreter.parse_command("open notepad")
        result = executor.execute(command)
        response = generator.generate_response(
            intent=command.intent,
            entities=command.entities
        )

        elapsed = time.time() - start_time

        # Should complete within reasonable time
        assert elapsed < 1.0  # Less than 1 second

    def test_encryption_performance(self):
        """Test encryption/decryption performance"""
        import time

        encryptor = EncryptionManager(password="test_password")

        # Encrypt multiple items
        start_time = time.time()

        for i in range(100):
            data = f"sensitive_data_{i}"
            encrypted = encryptor.encrypt_data(data)
            decrypted = encryptor.decrypt_data(encrypted)
            assert decrypted == data

        elapsed = time.time() - start_time

        # Should complete quickly
        assert elapsed < 5.0  # Less than 5 seconds for 100 operations


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios"""

    def test_user_interaction_scenario(self):
        """Test complete user interaction scenario"""
        # Initialize all components
        interpreter = CommandInterpreter()
        executor = CommandExecutor()
        generator = ResponseGenerator()
        display = InformationDisplay()
        gate = CapabilityGate(initial_trust_level=TrustLevel.LOW)

        # Scenario: User asks for weather
        command = interpreter.parse_command("what is the weather")
        assert command.intent == CommandIntent.INFORMATION_RETRIEVAL

        # Check capability
        assert gate.can_execute(Capability.INFORMATION_RETRIEVAL) is True

        # Execute
        result = executor.execute(command)
        assert result.status == ExecutionStatus.SUCCESS

        # Generate response
        response = generator.generate_response(
            intent=command.intent,
            entities=command.entities
        )
        assert response.text is not None

    def test_secure_operation_scenario(self):
        """Test secure operation with audit trail"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")

            # Initialize security
            encryptor = EncryptionManager(password="secure_password")
            auditor = AuditLogger(db_path=db_path)
            gate = CapabilityGate(initial_trust_level=TrustLevel.MEDIUM)

            # Scenario: Secure file operation
            storage = {}

            # Encrypt credentials
            credentials = "user:password"
            encryptor.store_encrypted("credentials", credentials, storage)

            # Log the operation
            auditor.log_action(
                action="store_credentials",
                user="admin",
                details={"storage_key": "credentials"}
            )

            # Verify capability
            assert gate.can_execute(Capability.FILE_WRITING) is True

            # Retrieve and decrypt
            retrieved = encryptor.retrieve_encrypted("credentials", storage)
            assert retrieved == credentials

            # Verify audit trail
            trail = auditor.get_audit_trail()
            assert len(trail) > 0
