"""
Visual Indicators - Status display for camera, processing, alerts, and privacy.
"""

import math
import time
from enum import Enum
from typing import Optional, Tuple


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class IndicatorState(Enum):
    HIDDEN = "hidden"
    VISIBLE = "visible"
    ANIMATING = "animating"


class VisualIndicators:
    """
    Manages all visual status indicators for JARVIS.

    Indicators:
    - Camera: red dot when camera is active
    - Processing: animated spinner during processing
    - Alert: color-coded alert banners
    - Privacy: shield icon when privacy mode is on
    """

    # Colors
    COLOR_CAMERA_ACTIVE = (255, 50, 50, 230)      # Red
    COLOR_CAMERA_INACTIVE = (80, 80, 80, 100)
    COLOR_PROCESSING = (0, 200, 255, 220)          # Cyan
    COLOR_ALERT_INFO = (50, 150, 255, 220)         # Blue
    COLOR_ALERT_WARNING = (255, 180, 0, 220)       # Amber
    COLOR_ALERT_CRITICAL = (255, 50, 50, 220)      # Red
    COLOR_PRIVACY = (100, 255, 100, 220)           # Green

    def __init__(self):
        # Camera indicator
        self.camera_active: bool = False
        self.camera_blink_phase: float = 0.0

        # Processing indicator
        self.processing_active: bool = False
        self.spinner_angle: float = 0.0
        self.spinner_speed: float = 360.0  # degrees/sec

        # Alert indicator
        self.alert_message: Optional[str] = None
        self.alert_level: AlertLevel = AlertLevel.INFO
        self.alert_visible: bool = False
        self.alert_start_time: float = 0.0
        self.alert_duration: float = 5.0  # seconds

        # Privacy mode indicator
        self.privacy_mode: bool = False
        self.privacy_pulse_phase: float = 0.0

        self._start_time = time.monotonic()

    # ------------------------------------------------------------------ #
    # Camera indicator
    # ------------------------------------------------------------------ #

    def set_camera_active(self, active: bool) -> None:
        """Show or hide the camera-active indicator."""
        self.camera_active = active
        self.camera_blink_phase = 0.0

    def get_camera_indicator(self, delta_time: float) -> dict:
        """
        Return rendering data for the camera indicator.

        Returns dict with: visible, color, radius, blink
        """
        self.camera_blink_phase += delta_time * 2.0  # 2 Hz blink
        blink = self.camera_active and (math.sin(self.camera_blink_phase * math.pi) > 0)
        color = self.COLOR_CAMERA_ACTIVE if blink else self.COLOR_CAMERA_INACTIVE
        return {
            "visible": True,
            "active": self.camera_active,
            "color": color,
            "radius": 8,
            "blink": blink,
        }

    # ------------------------------------------------------------------ #
    # Processing indicator
    # ------------------------------------------------------------------ #

    def set_processing(self, active: bool) -> None:
        """Show or hide the processing spinner."""
        self.processing_active = active
        if active:
            self.spinner_angle = 0.0

    def get_processing_indicator(self, delta_time: float) -> dict:
        """
        Return rendering data for the processing spinner.

        Returns dict with: visible, angle, color, segments
        """
        if self.processing_active:
            self.spinner_angle = (self.spinner_angle + self.spinner_speed * delta_time) % 360.0
        return {
            "visible": self.processing_active,
            "angle": self.spinner_angle,
            "color": self.COLOR_PROCESSING,
            "segments": 8,
            "radius": 20,
        }

    # ------------------------------------------------------------------ #
    # Alert indicator
    # ------------------------------------------------------------------ #

    def show_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        duration: float = 5.0,
    ) -> None:
        """Display a color-coded alert."""
        self.alert_message = message
        self.alert_level = level
        self.alert_visible = True
        self.alert_start_time = time.monotonic()
        self.alert_duration = duration

    def dismiss_alert(self) -> None:
        """Dismiss the current alert."""
        self.alert_visible = False
        self.alert_message = None

    def get_alert_indicator(self) -> dict:
        """
        Return rendering data for the alert indicator.

        Auto-dismisses after duration expires.
        """
        if self.alert_visible:
            elapsed = time.monotonic() - self.alert_start_time
            if elapsed >= self.alert_duration:
                self.dismiss_alert()

        color_map = {
            AlertLevel.INFO: self.COLOR_ALERT_INFO,
            AlertLevel.WARNING: self.COLOR_ALERT_WARNING,
            AlertLevel.CRITICAL: self.COLOR_ALERT_CRITICAL,
        }
        return {
            "visible": self.alert_visible,
            "message": self.alert_message or "",
            "level": self.alert_level.value if self.alert_visible else None,
            "color": color_map.get(self.alert_level, self.COLOR_ALERT_INFO),
        }

    # ------------------------------------------------------------------ #
    # Privacy mode indicator
    # ------------------------------------------------------------------ #

    def set_privacy_mode(self, enabled: bool) -> None:
        """Enable or disable privacy mode indicator."""
        self.privacy_mode = enabled
        self.privacy_pulse_phase = 0.0

    def get_privacy_indicator(self, delta_time: float) -> dict:
        """
        Return rendering data for the privacy mode indicator.

        Returns dict with: visible, color, pulse_alpha
        """
        if self.privacy_mode:
            self.privacy_pulse_phase += delta_time * 1.5
        alpha_mod = int(180 + 75 * math.sin(self.privacy_pulse_phase * math.pi))
        color = (*self.COLOR_PRIVACY[:3], alpha_mod)
        return {
            "visible": self.privacy_mode,
            "color": color,
            "label": "PRIVACY MODE",
        }

    # ------------------------------------------------------------------ #
    # Composite update
    # ------------------------------------------------------------------ #

    def update(self, delta_time: float) -> dict:
        """
        Update all indicators and return their current state.

        Args:
            delta_time: Seconds since last frame

        Returns:
            Dict with all indicator states
        """
        return {
            "camera": self.get_camera_indicator(delta_time),
            "processing": self.get_processing_indicator(delta_time),
            "alert": self.get_alert_indicator(),
            "privacy": self.get_privacy_indicator(delta_time),
        }
