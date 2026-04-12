"""
Real-Time Information Display

Displays weather, calendar, system status, and notifications
with automatic updates and caching.
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Widget types"""
    WEATHER = "weather"
    CALENDAR = "calendar"
    SYSTEM_STATUS = "system_status"
    TIME = "time"
    NOTIFICATION = "notification"


@dataclass
class WeatherData:
    """Weather information"""
    temperature: float
    condition: str
    humidity: float
    wind_speed: float
    location: str
    last_updated: datetime


@dataclass
class CalendarEvent:
    """Calendar event"""
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    description: Optional[str] = None


@dataclass
class SystemStatus:
    """System status information"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    temperature: Optional[float] = None
    uptime_seconds: float = 0


@dataclass
class Notification:
    """System notification"""
    title: str
    message: str
    timestamp: datetime
    priority: str = "normal"  # low, normal, high, urgent
    duration_seconds: int = 5


class WeatherWidget:
    """Displays weather information"""

    def __init__(self, location: str = "Current Location", update_interval: int = 1800):
        """
        Initialize weather widget.

        Args:
            location: Location for weather
            update_interval: Update interval in seconds (default 30 minutes)
        """
        self.location = location
        self.update_interval = update_interval
        self.weather_data: Optional[WeatherData] = None
        self.is_updating = False
        self.update_thread: Optional[threading.Thread] = None

    def start_updates(self) -> None:
        """Start automatic weather updates"""
        if self.is_updating:
            return

        self.is_updating = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Weather widget updates started")

    def stop_updates(self) -> None:
        """Stop automatic weather updates"""
        self.is_updating = False
        logger.info("Weather widget updates stopped")

    def _update_loop(self) -> None:
        """Background update loop"""
        while self.is_updating:
            try:
                self._fetch_weather()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating weather: {e}")
                time.sleep(60)  # Retry after 1 minute

    def _fetch_weather(self) -> None:
        """Fetch weather data"""
        try:
            # Placeholder for actual weather API call
            # Would integrate with OpenWeatherMap, WeatherAPI, etc.
            
            self.weather_data = WeatherData(
                temperature=72.0,
                condition="Partly Cloudy",
                humidity=65.0,
                wind_speed=10.0,
                location=self.location,
                last_updated=datetime.now()
            )
            logger.debug(f"Weather updated: {self.weather_data.condition}")
        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")

    def get_display_text(self) -> str:
        """Get formatted weather text"""
        if not self.weather_data:
            return "Weather data unavailable"

        return (
            f"{self.weather_data.condition} "
            f"{self.weather_data.temperature}°F "
            f"Humidity: {self.weather_data.humidity}%"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get widget status"""
        return {
            "location": self.location,
            "is_updating": self.is_updating,
            "last_updated": self.weather_data.last_updated if self.weather_data else None,
            "data": self.weather_data
        }


class CalendarWidget:
    """Displays calendar events"""

    def __init__(self, update_interval: int = 300):
        """
        Initialize calendar widget.

        Args:
            update_interval: Update interval in seconds (default 5 minutes)
        """
        self.update_interval = update_interval
        self.events: List[CalendarEvent] = []
        self.is_updating = False
        self.update_thread: Optional[threading.Thread] = None

    def start_updates(self) -> None:
        """Start automatic calendar updates"""
        if self.is_updating:
            return

        self.is_updating = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Calendar widget updates started")

    def stop_updates(self) -> None:
        """Stop automatic calendar updates"""
        self.is_updating = False
        logger.info("Calendar widget updates stopped")

    def _update_loop(self) -> None:
        """Background update loop"""
        while self.is_updating:
            try:
                self._fetch_events()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating calendar: {e}")
                time.sleep(60)

    def _fetch_events(self) -> None:
        """Fetch calendar events"""
        try:
            # Placeholder for actual calendar API call
            # Would integrate with Outlook, Google Calendar, etc.
            
            self.events = []
            logger.debug("Calendar events updated")
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")

    def get_upcoming_events(self, count: int = 3) -> List[CalendarEvent]:
        """Get upcoming events"""
        now = datetime.now()
        upcoming = [e for e in self.events if e.start_time > now]
        return upcoming[:count]

    def get_display_text(self) -> str:
        """Get formatted calendar text"""
        upcoming = self.get_upcoming_events(1)
        if not upcoming:
            return "No upcoming events"

        event = upcoming[0]
        return f"Next: {event.title} at {event.start_time.strftime('%H:%M')}"

    def get_status(self) -> Dict[str, Any]:
        """Get widget status"""
        return {
            "is_updating": self.is_updating,
            "event_count": len(self.events),
            "upcoming_events": self.get_upcoming_events(3)
        }


class SystemStatusWidget:
    """Displays system status"""

    def __init__(self, update_interval: int = 2):
        """
        Initialize system status widget.

        Args:
            update_interval: Update interval in seconds (default 2 seconds)
        """
        self.update_interval = update_interval
        self.status: Optional[SystemStatus] = None
        self.is_updating = False
        self.update_thread: Optional[threading.Thread] = None

    def start_updates(self) -> None:
        """Start automatic status updates"""
        if self.is_updating:
            return

        self.is_updating = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("System status widget updates started")

    def stop_updates(self) -> None:
        """Stop automatic status updates"""
        self.is_updating = False
        logger.info("System status widget updates stopped")

    def _update_loop(self) -> None:
        """Background update loop"""
        while self.is_updating:
            try:
                self._fetch_status()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating system status: {e}")
                time.sleep(5)

    def _fetch_status(self) -> None:
        """Fetch system status"""
        try:
            import psutil
            
            self.status = SystemStatus(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=psutil.disk_usage("/").percent,
                uptime_seconds=time.time()
            )
            logger.debug(f"System status updated: CPU {self.status.cpu_percent}%")
        except Exception as e:
            logger.error(f"Failed to fetch system status: {e}")

    def get_display_text(self) -> str:
        """Get formatted status text"""
        if not self.status:
            return "System status unavailable"

        return (
            f"CPU: {self.status.cpu_percent:.1f}% | "
            f"Memory: {self.status.memory_percent:.1f}% | "
            f"Disk: {self.status.disk_percent:.1f}%"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get widget status"""
        return {
            "is_updating": self.is_updating,
            "data": self.status
        }


class TimeWidget:
    """Displays current time"""

    def __init__(self, update_interval: int = 1):
        """
        Initialize time widget.

        Args:
            update_interval: Update interval in seconds (default 1 second)
        """
        self.update_interval = update_interval
        self.current_time: Optional[datetime] = None
        self.is_updating = False
        self.update_thread: Optional[threading.Thread] = None

    def start_updates(self) -> None:
        """Start automatic time updates"""
        if self.is_updating:
            return

        self.is_updating = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Time widget updates started")

    def stop_updates(self) -> None:
        """Stop automatic time updates"""
        self.is_updating = False
        logger.info("Time widget updates stopped")

    def _update_loop(self) -> None:
        """Background update loop"""
        while self.is_updating:
            try:
                self.current_time = datetime.now()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error updating time: {e}")

    def get_display_text(self) -> str:
        """Get formatted time text"""
        if not self.current_time:
            self.current_time = datetime.now()

        return self.current_time.strftime("%H:%M:%S")

    def get_status(self) -> Dict[str, Any]:
        """Get widget status"""
        return {
            "is_updating": self.is_updating,
            "current_time": self.current_time
        }


class NotificationQueue:
    """Manages notification queue"""

    def __init__(self, max_queue_size: int = 10):
        """
        Initialize notification queue.

        Args:
            max_queue_size: Maximum notifications in queue
        """
        self.queue: List[Notification] = []
        self.max_queue_size = max_queue_size
        self.on_notification_added: Optional[Callable] = None

    def add_notification(self, notification: Notification) -> None:
        """
        Add notification to queue.

        Args:
            notification: Notification to add
        """
        if len(self.queue) >= self.max_queue_size:
            self.queue.pop(0)  # Remove oldest

        self.queue.append(notification)
        logger.info(f"Notification added: {notification.title}")

        if self.on_notification_added:
            try:
                self.on_notification_added(notification)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

    def get_notifications(self, count: int = 5) -> List[Notification]:
        """Get recent notifications"""
        return self.queue[-count:]

    def clear_queue(self) -> None:
        """Clear notification queue"""
        self.queue.clear()
        logger.info("Notification queue cleared")

    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return {
            "queue_size": len(self.queue),
            "max_size": self.max_queue_size,
            "notifications": self.queue
        }


class InformationDisplay:
    """
    Manages all information display widgets.
    
    Features:
    - Weather widget (30-minute updates)
    - Calendar widget (upcoming events)
    - System status widget (CPU, memory, disk)
    - Time widget (1-second updates)
    - Notification queue system
    """

    def __init__(self):
        """Initialize information display"""
        self.weather = WeatherWidget()
        self.calendar = CalendarWidget()
        self.system_status = SystemStatusWidget()
        self.time = TimeWidget()
        self.notifications = NotificationQueue()

        self.is_active = False

    def start_all_widgets(self) -> None:
        """Start all widgets"""
        self.weather.start_updates()
        self.calendar.start_updates()
        self.system_status.start_updates()
        self.time.start_updates()
        self.is_active = True
        logger.info("All information display widgets started")

    def stop_all_widgets(self) -> None:
        """Stop all widgets"""
        self.weather.stop_updates()
        self.calendar.stop_updates()
        self.system_status.stop_updates()
        self.time.stop_updates()
        self.is_active = False
        logger.info("All information display widgets stopped")

    def get_all_display_text(self) -> Dict[str, str]:
        """Get all display text"""
        return {
            "weather": self.weather.get_display_text(),
            "calendar": self.calendar.get_display_text(),
            "system_status": self.system_status.get_display_text(),
            "time": self.time.get_display_text()
        }

    def get_status(self) -> Dict[str, Any]:
        """Get overall status"""
        return {
            "is_active": self.is_active,
            "weather": self.weather.get_status(),
            "calendar": self.calendar.get_status(),
            "system_status": self.system_status.get_status(),
            "time": self.time.get_status(),
            "notifications": self.notifications.get_status()
        }

    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop_all_widgets()
        logger.info("Information display cleaned up")

    def __del__(self):
        """Destructor"""
        self.cleanup()
