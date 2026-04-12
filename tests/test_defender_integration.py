"""
Unit Tests - Windows Defender Integration
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.security.defender_integration import (
    EventLogMonitor,
    DefenderStatus,
    DefenderStatusResult,
    ProcessMonitor,
    ThreatNotificationSystem,
    ThreatEvent,
    DEFENDER_EVENT_IDS,
)


class TestEventLogMonitor(unittest.TestCase):
    def test_instantiation(self):
        monitor = EventLogMonitor(poll_interval=60.0)
        self.assertFalse(monitor._running)
        self.assertEqual(monitor.events, [])

    def test_get_recent_events_empty(self):
        monitor = EventLogMonitor()
        self.assertEqual(monitor.get_recent_events(), [])

    def test_get_recent_events_limit(self):
        monitor = EventLogMonitor()
        for i in range(15):
            monitor.events.append(ThreatEvent(
                event_id=1116,
                timestamp="2026-01-01T00:00:00",
                description="test",
            ))
        recent = monitor.get_recent_events(limit=5)
        self.assertEqual(len(recent), 5)

    def test_extract_threat_name(self):
        msg = "Threat Name: Trojan:Win32/Fake\nSeverity: High"
        name = EventLogMonitor._extract_threat_name(msg)
        self.assertEqual(name, "Trojan:Win32/Fake")

    def test_extract_threat_name_unknown(self):
        name = EventLogMonitor._extract_threat_name("No threat info here")
        self.assertEqual(name, "Unknown")

    @patch("subprocess.run")
    def test_poll_events_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        monitor = EventLogMonitor()
        events = monitor._poll_events()
        self.assertEqual(events, [])

    @patch("subprocess.run")
    def test_poll_events_parses_json(self, mock_run):
        import json
        payload = json.dumps([{
            "Id": 1116,
            "TimeCreated": "2026-01-01T12:00:00",
            "Message": "Threat Name: TestVirus\nSeverity: High"
        }])
        mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
        monitor = EventLogMonitor()
        events = monitor._poll_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, 1116)
        self.assertEqual(events[0].threat_name, "TestVirus")


class TestDefenderStatus(unittest.TestCase):
    @patch("subprocess.run")
    def test_get_status_success(self, mock_run):
        import json
        payload = json.dumps({
            "RealTimeProtectionEnabled": True,
            "AntivirusEnabled": True,
            "AntispywareSignatureAge": 0,
            "QuickScanAge": 1,
            "ThreatCount": 0,
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
        result = DefenderStatus.get_status()
        self.assertTrue(result.real_time_protection)
        self.assertTrue(result.antivirus_enabled)
        self.assertTrue(result.definitions_up_to_date)
        self.assertIsNone(result.error)

    @patch("subprocess.run")
    def test_get_status_error(self, mock_run):
        import json
        payload = json.dumps({"error": "Access denied"})
        mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
        result = DefenderStatus.get_status()
        self.assertIsNotNone(result.error)

    @patch("subprocess.run", side_effect=Exception("timeout"))
    def test_get_status_exception(self, mock_run):
        result = DefenderStatus.get_status()
        self.assertIsNotNone(result.error)


class TestProcessMonitor(unittest.TestCase):
    def test_baseline_not_captured_initially(self):
        pm = ProcessMonitor()
        self.assertFalse(pm.baseline_captured)

    def test_get_anomalies_without_baseline(self):
        pm = ProcessMonitor()
        anomalies = pm.get_anomalies()
        self.assertEqual(anomalies, [])

    @patch("psutil.process_iter")
    def test_capture_baseline(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "python.exe"}
        mock_iter.return_value = [mock_proc]
        pm = ProcessMonitor()
        pm.capture_baseline()
        self.assertTrue(pm.baseline_captured)
        self.assertIn("python.exe", pm.baseline)

    @patch("psutil.process_iter")
    def test_anomaly_detection_new_process(self, mock_iter):
        # Baseline: python.exe only
        mock_proc1 = MagicMock()
        mock_proc1.info = {"name": "python.exe"}
        mock_iter.return_value = [mock_proc1]

        pm = ProcessMonitor()
        pm.capture_baseline()

        # Now add a new process
        mock_proc2 = MagicMock()
        mock_proc2.info = {"name": "malware.exe"}
        mock_iter.return_value = [mock_proc1, mock_proc2]

        anomalies = pm.get_anomalies()
        names = [a["name"] for a in anomalies]
        self.assertIn("malware.exe", names)


class TestThreatNotificationSystem(unittest.TestCase):
    def test_register_and_notify(self):
        received = []
        tns = ThreatNotificationSystem()
        tns.register_handler(lambda e: received.append(e))

        event = ThreatEvent(
            event_id=1116,
            timestamp="2026-01-01T00:00:00",
            description="Malware detected",
            threat_name="TestVirus",
        )
        tns.notify(event)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].threat_name, "TestVirus")

    def test_multiple_handlers(self):
        counts = [0, 0]
        tns = ThreatNotificationSystem()
        tns.register_handler(lambda e: counts.__setitem__(0, counts[0] + 1))
        tns.register_handler(lambda e: counts.__setitem__(1, counts[1] + 1))

        event = ThreatEvent(event_id=1117, timestamp="", description="")
        tns.notify(event)
        self.assertEqual(counts, [1, 1])

    def test_handler_exception_does_not_propagate(self):
        tns = ThreatNotificationSystem()
        tns.register_handler(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        event = ThreatEvent(event_id=1116, timestamp="", description="")
        # Should not raise
        tns.notify(event)


class TestDefenderEventIds(unittest.TestCase):
    def test_known_event_ids_present(self):
        self.assertIn(1116, DEFENDER_EVENT_IDS)
        self.assertIn(1117, DEFENDER_EVENT_IDS)

    def test_event_descriptions_non_empty(self):
        for eid, desc in DEFENDER_EVENT_IDS.items():
            self.assertGreater(len(desc), 0)


if __name__ == "__main__":
    unittest.main()
