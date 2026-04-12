"""
Unit Tests - Gaming Module
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── InputController ────────────────────────────────────────────────────────

class TestInputController(unittest.TestCase):

    def _make_controller(self):
        """Create controller with SendInput mocked out."""
        with patch("ctypes.windll"):
            from src.gaming.input_controller import InputController
            ctrl = InputController()
        return ctrl

    def test_resolve_vk_known_key(self):
        from src.gaming.input_controller import InputController
        self.assertIsNotNone(InputController._resolve_vk("w"))
        self.assertIsNotNone(InputController._resolve_vk("space"))
        self.assertIsNotNone(InputController._resolve_vk("f1"))

    def test_resolve_vk_unknown_key(self):
        from src.gaming.input_controller import InputController
        self.assertIsNone(InputController._resolve_vk("xyz_unknown"))

    def test_resolve_vk_mouse_button_returns_none(self):
        from src.gaming.input_controller import InputController
        # Mouse buttons are strings in VK dict, not ints → should return None
        self.assertIsNone(InputController._resolve_vk("lmb"))

    @patch("src.gaming.input_controller._send_input")
    def test_press_known_key(self, mock_send):
        from src.gaming.input_controller import InputController
        ctrl = InputController()
        result = ctrl.press("space")
        self.assertTrue(result)
        self.assertTrue(mock_send.called)

    @patch("src.gaming.input_controller._send_input")
    def test_press_unknown_key_returns_false(self, mock_send):
        from src.gaming.input_controller import InputController
        ctrl = InputController()
        result = ctrl.press("not_a_key")
        self.assertFalse(result)

    @patch("src.gaming.input_controller._send_input")
    def test_hold_and_release(self, mock_send):
        from src.gaming.input_controller import InputController
        ctrl = InputController()
        ctrl.hold("w")
        self.assertIn("w", ctrl._held)
        ctrl.release("w")
        self.assertNotIn("w", ctrl._held)

    @patch("src.gaming.input_controller._send_input")
    def test_release_all(self, mock_send):
        from src.gaming.input_controller import InputController
        ctrl = InputController()
        ctrl._held = {"w", "a", "lshift"}
        ctrl.release_all()
        self.assertEqual(len(ctrl._held), 0)

    @patch("src.gaming.input_controller._send_input")
    def test_macro_executes_steps(self, mock_send):
        from src.gaming.input_controller import InputController, MacroStep
        ctrl = InputController()
        steps = [
            MacroStep(action="press", key="space"),
            MacroStep(action="wait",  duration=0.01),
            MacroStep(action="press", key="r"),
        ]
        ctrl.run_macro(steps, blocking=True)
        self.assertGreaterEqual(mock_send.call_count, 2)


# ── GameDetector ───────────────────────────────────────────────────────────

class TestGameDetector(unittest.TestCase):

    def setUp(self):
        from src.gaming.game_detector import GameDetector
        self.detector = GameDetector()

    def test_list_supported_games_not_empty(self):
        games = self.detector.list_supported_games()
        self.assertGreater(len(games), 0)

    def test_get_profile_minecraft(self):
        profile = self.detector.get_profile("Minecraft")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.genre, "sandbox")

    def test_get_profile_case_insensitive(self):
        profile = self.detector.get_profile("minecraft")
        self.assertIsNotNone(profile)

    def test_get_profile_unknown_returns_none(self):
        profile = self.detector.get_profile("NotARealGame")
        self.assertIsNone(profile)

    def test_minecraft_has_jump_macro(self):
        profile = self.detector.get_profile("Minecraft")
        self.assertIn("jump", profile.macros)

    def test_minecraft_voice_commands_map_to_macros(self):
        profile = self.detector.get_profile("Minecraft")
        for phrase, macro in profile.voice_commands.items():
            self.assertIn(macro, profile.macros,
                          f"Voice command '{phrase}' maps to missing macro '{macro}'")

    @patch.object(
        __import__("src.gaming.game_detector", fromlist=["GameDetector"]).GameDetector,
        "get_foreground_window_title",
        return_value="minecraft 1.21",
    )
    @patch.object(
        __import__("src.gaming.game_detector", fromlist=["GameDetector"]).GameDetector,
        "get_running_processes",
        return_value=["javaw.exe"],
    )
    def test_detect_minecraft_by_window(self, mock_procs, mock_title):
        from src.gaming.game_detector import GameDetector
        detector = GameDetector()
        profile = detector.detect()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Minecraft")


# ── GameAgent ──────────────────────────────────────────────────────────────

class TestGameAgent(unittest.TestCase):

    def _make_agent(self):
        from src.gaming.game_agent import GameAgent
        agent = GameAgent()
        # Don't start the detection thread
        return agent

    @patch("src.gaming.input_controller._send_input")
    def test_handle_voice_command_jump_minecraft(self, mock_send):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        agent.force_profile("Minecraft")
        result = agent.handle_voice_command("jump")
        self.assertIsNotNone(result)
        self.assertIn("jump", result.lower())

    @patch("src.gaming.input_controller._send_input")
    def test_handle_voice_command_unknown_returns_none(self, mock_send):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        result = agent.handle_voice_command("xyzzy_not_a_command")
        self.assertIsNone(result)

    def test_force_profile_valid(self):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        ok = agent.force_profile("Fortnite")
        self.assertTrue(ok)
        self.assertEqual(agent.session.profile.name, "Fortnite")

    def test_force_profile_invalid(self):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        ok = agent.force_profile("NotARealGame")
        self.assertFalse(ok)

    @patch("src.gaming.input_controller._send_input")
    def test_execute_key_press(self, mock_send):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        result = agent.execute_key("space")
        self.assertIn("space", result.lower())

    @patch("src.gaming.input_controller._send_input")
    def test_release_all(self, mock_send):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        result = agent.release_all()
        self.assertIn("released", result.lower())

    def test_get_status(self):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        status = agent.get_status()
        self.assertIn("running", status)
        self.assertIn("supported_games", status)

    @patch("src.gaming.input_controller._send_input")
    def test_callback_on_command_executed(self, mock_send):
        from src.gaming.game_agent import GameAgent
        agent = self._make_agent()
        agent.force_profile("Minecraft")
        received = []
        agent.on_command_executed(lambda cmd: received.append(cmd))
        agent.handle_voice_command("jump")
        self.assertEqual(len(received), 1)


# ── Integration: interpreter + executor ───────────────────────────────────

class TestGamingIntegration(unittest.TestCase):

    def test_interpreter_classifies_game_intent(self):
        from src.core.command_interpreter import CommandInterpreter
        ci = CommandInterpreter()
        result = ci.interpret("jump")
        self.assertEqual(result["intent"], "game_control")

    def test_interpreter_extracts_game_command(self):
        from src.core.command_interpreter import CommandInterpreter
        ci = CommandInterpreter()
        result = ci.interpret("reload my weapon")
        self.assertEqual(result["intent"], "game_control")
        self.assertIn("game_command", result["entities"])

    def test_interpreter_detects_force_profile(self):
        from src.core.command_interpreter import CommandInterpreter
        ci = CommandInterpreter()
        result = ci.interpret("game mode minecraft")
        self.assertEqual(result["intent"], "game_control")
        self.assertIn("force_game", result["entities"])

    def test_interpreter_detects_key_press(self):
        from src.core.command_interpreter import CommandInterpreter
        ci = CommandInterpreter()
        result = ci.interpret("press key f")
        self.assertEqual(result["intent"], "game_control")
        self.assertEqual(result["entities"].get("key"), "f")
        self.assertEqual(result["entities"].get("key_action"), "press")

    @patch("src.gaming.input_controller._send_input")
    def test_executor_handles_game_control(self, mock_send):
        from src.core.command_interpreter import CommandInterpreter, CommandIntent
        from src.core.command_executor import CommandExecutor, ExecutionStatus
        from src.gaming.game_agent import GameAgent
        import src.core.command_executor as ce

        # Inject a real agent with Minecraft profile
        agent = GameAgent()
        agent.force_profile("Minecraft")
        ce._game_agent = agent

        ci = CommandInterpreter()
        executor = CommandExecutor()

        cmd = ci.parse_command("jump")
        result = executor.execute(cmd)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()
