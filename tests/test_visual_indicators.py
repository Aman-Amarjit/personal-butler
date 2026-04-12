"""
Unit Tests - Visual Indicators
"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ui.visual_indicators import VisualIndicators, AlertLevel


class TestCameraIndicator(unittest.TestCase):
    def setUp(self):
        self.vi = VisualIndicators()

    def test_camera_inactive_by_default(self):
        state = self.vi.get_camera_indicator(0.016)
        self.assertFalse(state["active"])

    def test_camera_active_flag(self):
        self.vi.set_camera_active(True)
        state = self.vi.get_camera_indicator(0.016)
        self.assertTrue(state["active"])

    def test_camera_deactivate(self):
        self.vi.set_camera_active(True)
        self.vi.set_camera_active(False)
        state = self.vi.get_camera_indicator(0.016)
        self.assertFalse(state["active"])

    def test_camera_indicator_has_color(self):
        self.vi.set_camera_active(True)
        state = self.vi.get_camera_indicator(0.016)
        self.assertIn("color", state)
        self.assertEqual(len(state["color"]), 4)


class TestProcessingIndicator(unittest.TestCase):
    def setUp(self):
        self.vi = VisualIndicators()

    def test_processing_hidden_by_default(self):
        state = self.vi.get_processing_indicator(0.016)
        self.assertFalse(state["visible"])

    def test_processing_visible_when_active(self):
        self.vi.set_processing(True)
        state = self.vi.get_processing_indicator(0.016)
        self.assertTrue(state["visible"])

    def test_spinner_angle_advances(self):
        self.vi.set_processing(True)
        state1 = self.vi.get_processing_indicator(0.1)
        state2 = self.vi.get_processing_indicator(0.1)
        self.assertGreater(state2["angle"], state1["angle"])

    def test_processing_stops(self):
        self.vi.set_processing(True)
        self.vi.set_processing(False)
        state = self.vi.get_processing_indicator(0.016)
        self.assertFalse(state["visible"])


class TestAlertIndicator(unittest.TestCase):
    def setUp(self):
        self.vi = VisualIndicators()

    def test_no_alert_by_default(self):
        state = self.vi.get_alert_indicator()
        self.assertFalse(state["visible"])

    def test_info_alert(self):
        self.vi.show_alert("Info message", AlertLevel.INFO, duration=60.0)
        state = self.vi.get_alert_indicator()
        self.assertTrue(state["visible"])
        self.assertEqual(state["level"], "info")

    def test_warning_alert_color(self):
        self.vi.show_alert("Warning!", AlertLevel.WARNING, duration=60.0)
        state = self.vi.get_alert_indicator()
        self.assertEqual(state["color"], VisualIndicators.COLOR_ALERT_WARNING)

    def test_critical_alert_color(self):
        self.vi.show_alert("Critical!", AlertLevel.CRITICAL, duration=60.0)
        state = self.vi.get_alert_indicator()
        self.assertEqual(state["color"], VisualIndicators.COLOR_ALERT_CRITICAL)

    def test_alert_dismiss(self):
        self.vi.show_alert("Test", duration=60.0)
        self.vi.dismiss_alert()
        state = self.vi.get_alert_indicator()
        self.assertFalse(state["visible"])

    def test_alert_auto_expires(self):
        self.vi.show_alert("Expiring", duration=0.0)
        state = self.vi.get_alert_indicator()
        self.assertFalse(state["visible"])


class TestPrivacyIndicator(unittest.TestCase):
    def setUp(self):
        self.vi = VisualIndicators()

    def test_privacy_hidden_by_default(self):
        state = self.vi.get_privacy_indicator(0.016)
        self.assertFalse(state["visible"])

    def test_privacy_visible_when_enabled(self):
        self.vi.set_privacy_mode(True)
        state = self.vi.get_privacy_indicator(0.016)
        self.assertTrue(state["visible"])

    def test_privacy_label(self):
        self.vi.set_privacy_mode(True)
        state = self.vi.get_privacy_indicator(0.016)
        self.assertIn("PRIVACY", state["label"])

    def test_privacy_disable(self):
        self.vi.set_privacy_mode(True)
        self.vi.set_privacy_mode(False)
        state = self.vi.get_privacy_indicator(0.016)
        self.assertFalse(state["visible"])


class TestCompositeUpdate(unittest.TestCase):
    def test_update_returns_all_keys(self):
        vi = VisualIndicators()
        state = vi.update(0.016)
        self.assertIn("camera", state)
        self.assertIn("processing", state)
        self.assertIn("alert", state)
        self.assertIn("privacy", state)


if __name__ == "__main__":
    unittest.main()
