"""
Windows Defender Integration

Monitors Windows Event Log for Defender threat events and queries
Defender status via PowerShell. Also provides process baseline analysis.
"""

import subprocess
import json
import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from datetime import datetime


# Windows Defender threat event IDs
DEFENDER_EVENT_IDS = {
    1116: "Malware detected",
    1117: "Malware action taken",
    1118: "Malware remediation failed",
    1119: "Malware remediation succeeded",
    5001: "Real-time protection disabled",
}


@dataclass
class ThreatEvent:
    """Represents a Windows Defender threat event."""
    event_id: int
    timestamp: str
    description: str
    threat_name: str = ""
    severity: str = "unknown"
    action_taken: str = ""


@dataclass
class DefenderStatusResult:
    """Result of a Defender status query."""
    real_time_protection: bool = False
    antivirus_enabled: bool = False
    definitions_up_to_date: bool = False
    last_scan_time: str = ""
    threat_count: int = 0
    error: Optional[str] = None


class EventLogMonitor:
    """
    Monitors Windows Event Log for Defender threat events.

    Uses PowerShell Get-WinEvent to poll for new events.
    """

    def __init__(
        self,
        poll_interval: float = 30.0,
        on_threat: Optional[Callable[[ThreatEvent], None]] = None,
    ):
        self.poll_interval = poll_interval
        self.on_threat = on_threat
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_check: Optional[datetime] = None
        self.events: List[ThreatEvent] = []

    def start(self) -> None:
        """Start background event log monitoring."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                new_events = self._poll_events()
                for event in new_events:
                    self.events.append(event)
                    if self.on_threat:
                        self.on_threat(event)
            except Exception:
                pass  # Graceful degradation on non-Windows or permission errors
            time.sleep(self.poll_interval)

    def _poll_events(self) -> List[ThreatEvent]:
        """Query Windows Event Log for Defender events via PowerShell."""
        since = self._last_check or datetime.now().replace(hour=0, minute=0, second=0)
        self._last_check = datetime.now()

        event_id_filter = ",".join(str(eid) for eid in DEFENDER_EVENT_IDS)
        ps_script = f"""
$since = [datetime]'{since.strftime('%Y-%m-%dT%H:%M:%S')}'
$events = Get-WinEvent -FilterHashtable @{{
    LogName='Microsoft-Windows-Windows Defender/Operational'
    Id={event_id_filter}
    StartTime=$since
}} -ErrorAction SilentlyContinue
if ($events) {{
    $events | ForEach-Object {{
        [PSCustomObject]@{{
            Id=$_.Id
            TimeCreated=$_.TimeCreated.ToString('o')
            Message=$_.Message
        }}
    }} | ConvertTo-Json -Compress
}}
"""
        result = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )

        if result.returncode != 0 or not result.stdout.strip():
            return []

        try:
            raw = json.loads(result.stdout.strip())
            if isinstance(raw, dict):
                raw = [raw]
            events = []
            for item in raw:
                eid = int(item.get("Id", 0))
                events.append(ThreatEvent(
                    event_id=eid,
                    timestamp=item.get("TimeCreated", ""),
                    description=DEFENDER_EVENT_IDS.get(eid, "Unknown event"),
                    threat_name=self._extract_threat_name(item.get("Message", "")),
                    severity="high" if eid in (1116, 1117, 1118) else "medium",
                ))
            return events
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    @staticmethod
    def _extract_threat_name(message: str) -> str:
        """Extract threat name from event message."""
        for line in message.splitlines():
            if "Threat Name:" in line or "Name:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return "Unknown"

    def get_recent_events(self, limit: int = 10) -> List[ThreatEvent]:
        """Return the most recent threat events."""
        return self.events[-limit:]


class DefenderStatus:
    """Queries Windows Defender status via PowerShell."""

    @staticmethod
    def get_status() -> DefenderStatusResult:
        """Query current Defender status."""
        ps_script = """
try {
    $status = Get-MpComputerStatus -ErrorAction Stop
    [PSCustomObject]@{
        RealTimeProtectionEnabled = $status.RealTimeProtectionEnabled
        AntivirusEnabled = $status.AntivirusEnabled
        AntispywareSignatureAge = $status.AntispywareSignatureAge
        QuickScanAge = $status.QuickScanAge
        ThreatCount = ($status.ThreatCount ?? 0)
    } | ConvertTo-Json -Compress
} catch {
    '{"error": "' + $_.Exception.Message + '"}'
}
"""
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(result.stdout.strip())
            if "error" in data:
                return DefenderStatusResult(error=data["error"])
            return DefenderStatusResult(
                real_time_protection=bool(data.get("RealTimeProtectionEnabled", False)),
                antivirus_enabled=bool(data.get("AntivirusEnabled", False)),
                definitions_up_to_date=int(data.get("AntispywareSignatureAge", 99)) <= 1,
                threat_count=int(data.get("ThreatCount", 0)),
            )
        except Exception as exc:
            return DefenderStatusResult(error=str(exc))


class ProcessMonitor:
    """
    Monitors running processes and detects anomalies against a baseline.
    """

    def __init__(self):
        self.baseline: Dict[str, int] = {}  # name -> typical count
        self._baseline_captured = False

    def capture_baseline(self) -> None:
        """Capture the current process list as the baseline."""
        try:
            import psutil
            counts: Dict[str, int] = {}
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower()
                counts[name] = counts.get(name, 0) + 1
            self.baseline = counts
            self._baseline_captured = True
        except Exception:
            self._baseline_captured = False

    def get_anomalies(self) -> List[Dict]:
        """
        Compare current processes against baseline.

        Returns list of anomaly dicts with name, current_count, baseline_count.
        """
        if not self._baseline_captured:
            return []
        try:
            import psutil
            current: Dict[str, int] = {}
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower()
                current[name] = current.get(name, 0) + 1

            anomalies = []
            for name, count in current.items():
                baseline_count = self.baseline.get(name, 0)
                # Flag if a new process appeared or count increased significantly
                if baseline_count == 0 or count > baseline_count * 3:
                    anomalies.append({
                        "name": name,
                        "current_count": count,
                        "baseline_count": baseline_count,
                        "new": baseline_count == 0,
                    })
            return anomalies
        except Exception:
            return []

    @property
    def baseline_captured(self) -> bool:
        return self._baseline_captured


class ThreatNotificationSystem:
    """Routes threat events to registered notification handlers."""

    def __init__(self):
        self._handlers: List[Callable[[ThreatEvent], None]] = []

    def register_handler(self, handler: Callable[[ThreatEvent], None]) -> None:
        self._handlers.append(handler)

    def notify(self, event: ThreatEvent) -> None:
        for handler in self._handlers:
            try:
                handler(event)
            except Exception:
                pass
