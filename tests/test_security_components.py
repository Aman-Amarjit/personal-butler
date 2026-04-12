"""Unit tests for security components"""

import pytest
import tempfile
import os
from src.security.encryption_manager import EncryptionManager
from src.security.audit_logger import AuditLogger
from src.security.capability_gate import CapabilityGate, TrustLevel, Capability
from src.security.circuit_breaker import CircuitBreaker, LoopProtector


class TestEncryptionManager:
    """Test encryption manager"""

    def test_initialization(self):
        """Test encryption manager initialization"""
        manager = EncryptionManager(password="test_password")
        assert manager.cipher_suite is not None
        assert manager.salt is not None

    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        manager = EncryptionManager(password="test_password")
        plaintext = "sensitive data"

        encrypted = manager.encrypt_data(plaintext)
        assert encrypted != plaintext

        decrypted = manager.decrypt_data(encrypted)
        assert decrypted == plaintext

    def test_store_retrieve_encrypted(self):
        """Test storing and retrieving encrypted data"""
        manager = EncryptionManager(password="test_password")
        storage = {}

        manager.store_encrypted("key1", "secret_value", storage)
        assert "key1" in storage

        retrieved = manager.retrieve_encrypted("key1", storage)
        assert retrieved == "secret_value"

    def test_key_rotation(self):
        """Test key rotation"""
        manager = EncryptionManager(password="old_password")
        storage = {}

        manager.store_encrypted("key1", "data1", storage)
        manager.store_encrypted("key2", "data2", storage)

        # Rotate keys
        success = manager.rotate_encryption_keys("new_password", storage)
        assert success is True

        # Verify data is still accessible
        assert manager.retrieve_encrypted("key1", storage) == "data1"
        assert manager.retrieve_encrypted("key2", storage) == "data2"

    def test_status(self):
        """Test encryption manager status"""
        manager = EncryptionManager(password="test_password")
        status = manager.get_status()

        assert status["cipher_initialized"] is True
        assert status["has_password"] is True
        assert status["salt_length"] > 0


class TestAuditLogger:
    """Test audit logger"""

    def test_initialization(self):
        """Test audit logger initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            logger = AuditLogger(db_path=db_path)
            assert os.path.exists(db_path)

    def test_log_action(self):
        """Test logging an action"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            logger = AuditLogger(db_path=db_path)

            success = logger.log_action(
                action="test_action",
                user="test_user",
                details={"key": "value"}
            )
            assert success is True

    def test_verify_log_integrity(self):
        """Test log integrity verification"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            logger = AuditLogger(db_path=db_path)

            logger.log_action("test_action", "test_user")

            # Verify first log entry
            is_valid = logger.verify_log_integrity(1)
            assert is_valid is True

    def test_get_audit_trail(self):
        """Test retrieving audit trail"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            logger = AuditLogger(db_path=db_path)

            logger.log_action("action1", "user1")
            logger.log_action("action2", "user2")

            trail = logger.get_audit_trail()
            assert len(trail) == 2

    def test_export_audit_logs(self):
        """Test exporting audit logs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            export_path = os.path.join(tmpdir, "export.json")

            logger = AuditLogger(db_path=db_path)
            logger.log_action("test_action", "test_user")

            success = logger.export_audit_logs(export_path, format="json")
            assert success is True
            assert os.path.exists(export_path)

    def test_log_rotation(self):
        """Test log rotation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "audit.db")
            logger = AuditLogger(db_path=db_path, retention_days=0)

            logger.log_action("test_action", "test_user")

            # Rotate logs (should delete all since retention is 0)
            deleted = logger.rotate_logs()
            assert deleted >= 0


class TestCapabilityGate:
    """Test capability gating"""

    def test_initialization(self):
        """Test capability gate initialization"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.UNTRUSTED)
        assert gate.trust_level == TrustLevel.UNTRUSTED

    def test_can_execute_basic_capability(self):
        """Test executing basic capability"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.UNTRUSTED)

        # Basic capabilities should be available at all levels
        assert gate.can_execute(Capability.VOICE_INTERACTION) is True
        assert gate.can_execute(Capability.INFORMATION_RETRIEVAL) is True

    def test_can_execute_restricted_capability(self):
        """Test executing restricted capability"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.UNTRUSTED)

        # Restricted capabilities should not be available
        assert gate.can_execute(Capability.APPLICATION_LAUNCH) is False
        assert gate.can_execute(Capability.FILE_DELETION) is False

    def test_trust_level_progression(self):
        """Test trust level progression"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.UNTRUSTED)

        gate.increase_trust_level()
        assert gate.trust_level == TrustLevel.LOW
        assert gate.can_execute(Capability.APPLICATION_LAUNCH) is True

        gate.increase_trust_level()
        assert gate.trust_level == TrustLevel.MEDIUM
        assert gate.can_execute(Capability.FILE_DELETION) is True

    def test_requires_confirmation(self):
        """Test confirmation requirement"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.HIGH)

        # High trust operations require confirmation
        assert gate.requires_confirmation(Capability.SYSTEM_SHUTDOWN) is True

    def test_get_available_capabilities(self):
        """Test getting available capabilities"""
        gate = CapabilityGate(initial_trust_level=TrustLevel.LOW)

        available = gate.get_available_capabilities()
        assert Capability.VOICE_INTERACTION in available
        assert Capability.APPLICATION_LAUNCH in available
        assert Capability.FILE_DELETION not in available


class TestCircuitBreaker:
    """Test circuit breaker"""

    def test_initialization(self):
        """Test circuit breaker initialization"""
        breaker = CircuitBreaker(max_recursion_depth=10, max_iterations=100)
        assert breaker.state.value == "closed"

    def test_recursion_depth_tracking(self):
        """Test recursion depth tracking"""
        breaker = CircuitBreaker(max_recursion_depth=3)

        assert breaker.enter_recursion() is True
        assert breaker.recursion_depth == 1

        assert breaker.enter_recursion() is True
        assert breaker.recursion_depth == 2

        assert breaker.enter_recursion() is True
        assert breaker.recursion_depth == 3

        # Should break on 4th recursion
        assert breaker.enter_recursion() is False
        assert breaker.state.value == "open"

    def test_iteration_counting(self):
        """Test iteration counting"""
        breaker = CircuitBreaker(max_iterations=5)

        for i in range(5):
            assert breaker.increment_iteration() is True

        # Should break on 6th iteration
        assert breaker.increment_iteration() is False
        assert breaker.state.value == "open"

    def test_circuit_reset(self):
        """Test circuit reset"""
        breaker = CircuitBreaker(max_iterations=5)

        # Break the circuit
        for _ in range(6):
            breaker.increment_iteration()

        assert breaker.state.value == "open"

        # Reset
        breaker.reset_circuit()
        assert breaker.state.value == "closed"
        assert breaker.iteration_count == 0

    def test_context_manager(self):
        """Test circuit breaker as context manager"""
        breaker = CircuitBreaker(max_recursion_depth=2)

        with breaker:
            assert breaker.recursion_depth == 1

        assert breaker.recursion_depth == 0


class TestLoopProtector:
    """Test loop protector"""

    def test_loop_protection(self):
        """Test loop protection"""
        protector = LoopProtector(max_iterations=5)

        count = 0
        with protector:
            while count < 10:
                if not protector.can_continue():
                    break
                count += 1

        assert count == 5  # Should stop at max iterations

    def test_loop_protector_reset(self):
        """Test loop protector reset"""
        protector = LoopProtector(max_iterations=5)

        # First loop
        count = 0
        with protector:
            while count < 10:
                if not protector.can_continue():
                    break
                count += 1

        assert count == 5

        # Reset and try again
        protector.reset()

        count = 0
        with protector:
            while count < 3:
                if not protector.can_continue():
                    break
                count += 1

        assert count == 3
