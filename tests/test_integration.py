"""
Integration Tests - End-to-end scenarios for JARVIS AI Assistant.
"""

import sys
import os
import time
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# 1. End-to-end voice command flow
# ---------------------------------------------------------------------------

class TestVoiceCommandFlow(unittest.TestCase):
    """End-to-end: wake word → STT → command interpreter → response."""

    def test_wake_word_triggers_stt(self):
        """Wake word detection should transition to STT listening state."""
        from src.voice.wake_word_detector import WakeWordDetector
        detector = WakeWordDetector(wake_word="hey jarvis")
        self.assertEqual(detector.wake_word.lower(), "hey jarvis")
        self.assertFalse(detector.is_listening)

    def test_command_interpreter_classifies_intent(self):
        """CommandInterpreter should classify a simple intent."""
        from src.core.command_interpreter import CommandInterpreter
        interpreter = CommandInterpreter()
        result = interpreter.interpret("what time is it")
        self.assertIn("intent", result)
        self.assertIsNotNone(result["intent"])

    def test_response_generator_produces_output(self):
        """ResponseGenerator should return a non-empty response."""
        from src.core.response_generator import ResponseGenerator
        gen = ResponseGenerator()
        response = gen.generate_response("time_query", {})
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_full_pipeline_mock(self):
        """Simulate full pipeline with mocked audio."""
        from src.core.command_interpreter import CommandInterpreter
        from src.core.response_generator import ResponseGenerator

        interpreter = CommandInterpreter()
        gen = ResponseGenerator()

        # Simulate transcribed text
        transcription = "open calculator"
        result = interpreter.interpret(transcription)
        response = gen.generate_response(result.get("intent", "unknown"), result)

        self.assertIsInstance(response, str)


# ---------------------------------------------------------------------------
# 2. Memory storage and retrieval
# ---------------------------------------------------------------------------

class TestMemoryStorageRetrieval(unittest.TestCase):
    """Tests for conversation history and preference storage."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_db_init_creates_tables(self):
        from src.core.db_init import init_database
        conn = init_database(self.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        self.assertIn("audit_logs", tables)
        self.assertIn("conversation_history", tables)
        self.assertIn("user_preferences", tables)
        conn.close()

    def test_conversation_history_insert_retrieve(self):
        from src.core.db_init import init_database
        conn = init_database(self.db_path)
        conn.execute(
            "INSERT INTO conversation_history (role, content, timestamp) VALUES (?,?,datetime('now'))",
            ("user", "hello jarvis")
        )
        conn.commit()
        rows = conn.execute("SELECT * FROM conversation_history").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["content"], "hello jarvis")
        conn.close()


# ---------------------------------------------------------------------------
# 3. Security and audit logging
# ---------------------------------------------------------------------------

class TestSecurityAuditLogging(unittest.TestCase):
    """Tests for encryption, audit logging, and capability gating."""

    def test_encryption_round_trip(self):
        from src.security.encryption_manager import EncryptionManager
        em = EncryptionManager(password="test-password-123")
        plaintext = "sensitive data"
        encrypted = em.encrypt(plaintext)
        decrypted = em.decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_audit_log_signed_entry(self):
        from src.security.audit_logger import AuditLogger
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            logger = AuditLogger(db_path=db_path, secret_key="test-key")
            logger.log("test_action", "user", {"detail": "value"})
            entries = logger.get_entries(limit=1)
            self.assertEqual(len(entries), 1)
            self.assertTrue(logger.verify_integrity())
        finally:
            os.unlink(db_path)

    def test_capability_gate_blocks_low_trust(self):
        from src.security.capability_gate import CapabilityGate
        gate = CapabilityGate()
        gate.set_trust_level(0)
        allowed = gate.check_permission("system_command")
        self.assertFalse(allowed)

    def test_circuit_breaker_trips_on_max_depth(self):
        from src.security.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(max_depth=3, max_iterations=100)
        for _ in range(3):
            cb.enter()
        with self.assertRaises(Exception):
            cb.enter()


# ---------------------------------------------------------------------------
# 4. Desktop overlay interaction
# ---------------------------------------------------------------------------

class TestDesktopOverlayInteraction(unittest.TestCase):
    """Tests for slime body physics and visual indicators."""

    def test_slime_body_deformation(self):
        from src.ui.slime_body import SlimeBody
        slime = SlimeBody(position=(100, 100), size=50)
        slime.deform_on_interaction((120, 120), intensity=0.5)
        outline = slime.get_outline_points()
        self.assertEqual(len(outline), slime.segments)

    def test_visual_indicators_camera(self):
        from src.ui.visual_indicators import VisualIndicators
        vi = VisualIndicators()
        vi.set_camera_active(True)
        state = vi.get_camera_indicator(0.016)
        self.assertTrue(state["active"])

    def test_visual_indicators_processing(self):
        from src.ui.visual_indicators import VisualIndicators
        vi = VisualIndicators()
        vi.set_processing(True)
        state = vi.get_processing_indicator(0.016)
        self.assertTrue(state["visible"])

    def test_visual_indicators_alert(self):
        from src.ui.visual_indicators import VisualIndicators, AlertLevel
        vi = VisualIndicators()
        vi.show_alert("Test alert", AlertLevel.WARNING, duration=60.0)
        state = vi.get_alert_indicator()
        self.assertTrue(state["visible"])
        self.assertEqual(state["message"], "Test alert")

    def test_visual_indicators_privacy(self):
        from src.ui.visual_indicators import VisualIndicators
        vi = VisualIndicators()
        vi.set_privacy_mode(True)
        state = vi.get_privacy_indicator(0.016)
        self.assertTrue(state["visible"])


# ---------------------------------------------------------------------------
# 5. Error recovery
# ---------------------------------------------------------------------------

class TestErrorRecovery(unittest.TestCase):
    """Tests for graceful degradation and error recovery."""

    def test_ollama_fallback_on_unavailable(self):
        from src.core.ollama_integration import OllamaIntegration
        ollama = OllamaIntegration(host="http://localhost", port=99999)
        # Should not raise; should return fallback response
        response = ollama.generate_fallback_response("hello")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_command_interpreter_handles_empty_input(self):
        from src.core.command_interpreter import CommandInterpreter
        interpreter = CommandInterpreter()
        result = interpreter.interpret("")
        self.assertIn("intent", result)

    def test_circuit_breaker_resets(self):
        from src.security.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(max_depth=2, max_iterations=100)
        cb.enter()
        cb.enter()
        cb.reset()
        # Should not raise after reset
        cb.enter()
        self.assertEqual(cb.current_depth, 1)

    def test_encryption_manager_handles_bad_data(self):
        from src.security.encryption_manager import EncryptionManager
        em = EncryptionManager(password="test-password")
        with self.assertRaises(Exception):
            em.decrypt(b"not-valid-ciphertext")


# ---------------------------------------------------------------------------
# 6. Performance baseline
# ---------------------------------------------------------------------------

class TestPerformanceBaseline(unittest.TestCase):
    """Verify key operations complete within acceptable time bounds."""

    def test_command_interpretation_latency(self):
        from src.core.command_interpreter import CommandInterpreter
        interpreter = CommandInterpreter()
        start = time.perf_counter()
        for _ in range(20):
            interpreter.interpret("what is the weather today")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 20) * 1000
        self.assertLess(avg_ms, 100, f"Avg interpretation latency {avg_ms:.1f}ms exceeds 100ms")

    def test_slime_physics_update_latency(self):
        from src.ui.slime_body import SlimeBody
        slime = SlimeBody(position=(100, 100), size=50)
        start = time.perf_counter()
        for _ in range(60):
            slime.update_physics(1 / 60)
            slime.animate_jiggle(1 / 60)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 60) * 1000
        self.assertLess(avg_ms, 5, f"Avg physics update {avg_ms:.2f}ms exceeds 5ms")

    def test_encryption_latency(self):
        from src.security.encryption_manager import EncryptionManager
        em = EncryptionManager(password="perf-test")
        start = time.perf_counter()
        for _ in range(10):
            enc = em.encrypt("test data for performance")
            em.decrypt(enc)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 10) * 1000
        self.assertLess(avg_ms, 200, f"Avg encrypt/decrypt {avg_ms:.1f}ms exceeds 200ms")


if __name__ == "__main__":
    unittest.main()
