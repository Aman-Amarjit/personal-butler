"""Unit tests for information display components"""

import pytest
import time
from datetime import datetime, timedelta
from src.ui.information_display import (
    WeatherWidget,
    CalendarWidget,
    SystemStatusWidget,
    TimeWidget,
    NotificationQueue,
    Notification,
    InformationDisplay
)


class TestWeatherWidget:
    """Test weather widget"""

    def test_initialization(self):
        """Test weather widget initialization"""
        widget = WeatherWidget(location="New York")
        assert widget.location == "New York"
        assert widget.is_updating is False

    def test_get_display_text(self):
        """Test getting display text"""
        widget = WeatherWidget()
        widget._fetch_weather()

        text = widget.get_display_text()
        assert len(text) > 0
        assert "°F" in text or "Humidity" in text

    def test_status(self):
        """Test widget status"""
        widget = WeatherWidget()
        status = widget.get_status()

        assert "location" in status
        assert "is_updating" in status
        assert "last_updated" in status


class TestCalendarWidget:
    """Test calendar widget"""

    def test_initialization(self):
        """Test calendar widget initialization"""
        widget = CalendarWidget()
        assert widget.is_updating is False
        assert len(widget.events) == 0

    def test_get_upcoming_events(self):
        """Test getting upcoming events"""
        widget = CalendarWidget()
        upcoming = widget.get_upcoming_events()

        assert isinstance(upcoming, list)

    def test_get_display_text(self):
        """Test getting display text"""
        widget = CalendarWidget()
        text = widget.get_display_text()

        assert len(text) > 0

    def test_status(self):
        """Test widget status"""
        widget = CalendarWidget()
        status = widget.get_status()

        assert "is_updating" in status
        assert "event_count" in status


class TestSystemStatusWidget:
    """Test system status widget"""

    def test_initialization(self):
        """Test system status widget initialization"""
        widget = SystemStatusWidget()
        assert widget.is_updating is False

    def test_fetch_status(self):
        """Test fetching system status"""
        widget = SystemStatusWidget()
        widget._fetch_status()

        assert widget.status is not None
        assert 0 <= widget.status.cpu_percent <= 100
        assert 0 <= widget.status.memory_percent <= 100

    def test_get_display_text(self):
        """Test getting display text"""
        widget = SystemStatusWidget()
        widget._fetch_status()

        text = widget.get_display_text()
        assert "CPU" in text
        assert "Memory" in text

    def test_status(self):
        """Test widget status"""
        widget = SystemStatusWidget()
        status = widget.get_status()

        assert "is_updating" in status
        assert "data" in status


class TestTimeWidget:
    """Test time widget"""

    def test_initialization(self):
        """Test time widget initialization"""
        widget = TimeWidget()
        assert widget.is_updating is False

    def test_get_display_text(self):
        """Test getting display text"""
        widget = TimeWidget()
        widget.current_time = datetime.now()

        text = widget.get_display_text()
        assert len(text) > 0
        assert ":" in text  # Should contain time separator

    def test_status(self):
        """Test widget status"""
        widget = TimeWidget()
        status = widget.get_status()

        assert "is_updating" in status
        assert "current_time" in status


class TestNotificationQueue:
    """Test notification queue"""

    def test_initialization(self):
        """Test notification queue initialization"""
        queue = NotificationQueue(max_queue_size=10)
        assert len(queue.queue) == 0

    def test_add_notification(self):
        """Test adding notification"""
        queue = NotificationQueue()
        notification = Notification(
            title="Test",
            message="Test message",
            timestamp=datetime.now()
        )

        queue.add_notification(notification)
        assert len(queue.queue) == 1

    def test_queue_size_limit(self):
        """Test queue size limit"""
        queue = NotificationQueue(max_queue_size=3)

        for i in range(5):
            notification = Notification(
                title=f"Test {i}",
                message="Test message",
                timestamp=datetime.now()
            )
            queue.add_notification(notification)

        assert len(queue.queue) == 3

    def test_get_notifications(self):
        """Test getting notifications"""
        queue = NotificationQueue()

        for i in range(5):
            notification = Notification(
                title=f"Test {i}",
                message="Test message",
                timestamp=datetime.now()
            )
            queue.add_notification(notification)

        notifications = queue.get_notifications(count=3)
        assert len(notifications) == 3

    def test_clear_queue(self):
        """Test clearing queue"""
        queue = NotificationQueue()

        notification = Notification(
            title="Test",
            message="Test message",
            timestamp=datetime.now()
        )
        queue.add_notification(notification)

        assert len(queue.queue) == 1

        queue.clear_queue()
        assert len(queue.queue) == 0

    def test_status(self):
        """Test queue status"""
        queue = NotificationQueue()
        status = queue.get_status()

        assert "queue_size" in status
        assert "max_size" in status
        assert "notifications" in status


class TestInformationDisplay:
    """Test information display"""

    def test_initialization(self):
        """Test information display initialization"""
        display = InformationDisplay()
        assert display.is_active is False

    def test_start_all_widgets(self):
        """Test starting all widgets"""
        display = InformationDisplay()
        display.start_all_widgets()

        assert display.is_active is True
        assert display.weather.is_updating is True
        assert display.calendar.is_updating is True
        assert display.system_status.is_updating is True
        assert display.time.is_updating is True

        # Cleanup
        display.stop_all_widgets()

    def test_stop_all_widgets(self):
        """Test stopping all widgets"""
        display = InformationDisplay()
        display.start_all_widgets()

        assert display.is_active is True

        display.stop_all_widgets()

        assert display.is_active is False
        assert display.weather.is_updating is False

    def test_get_all_display_text(self):
        """Test getting all display text"""
        display = InformationDisplay()

        # Fetch data first
        display.weather._fetch_weather()
        display.system_status._fetch_status()
        display.time.current_time = datetime.now()

        text = display.get_all_display_text()

        assert "weather" in text
        assert "calendar" in text
        assert "system_status" in text
        assert "time" in text

    def test_status(self):
        """Test display status"""
        display = InformationDisplay()
        status = display.get_status()

        assert "is_active" in status
        assert "weather" in status
        assert "calendar" in status
        assert "system_status" in status
        assert "time" in status
        assert "notifications" in status

    def test_cleanup(self):
        """Test cleanup"""
        display = InformationDisplay()
        display.start_all_widgets()

        display.cleanup()

        assert display.is_active is False
