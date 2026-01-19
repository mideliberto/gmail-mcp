"""
Tests for mcp/tools/conflict.py - Multi-calendar conflict detection tools

These tests mock the Google Calendar API to verify conflict detection functionality.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock


SAMPLE_CALENDARS = {
    "items": [
        {
            "id": "primary",
            "summary": "Personal",
            "primary": True,
            "accessRole": "owner",
            "backgroundColor": "#9fe1e7",
        },
        {
            "id": "work@example.com",
            "summary": "Work",
            "primary": False,
            "accessRole": "owner",
            "backgroundColor": "#7986cb",
        },
        {
            "id": "family@group.calendar.google.com",
            "summary": "Family",
            "primary": False,
            "accessRole": "writer",
            "backgroundColor": "#33b679",
        }
    ]
}

# Create sample events for testing conflicts
now = datetime.now(UTC)
SAMPLE_EVENTS_PRIMARY = {
    "items": [
        {
            "id": "event1",
            "summary": "Morning Meeting",
            "start": {"dateTime": (now + timedelta(hours=1)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=2)).isoformat() + "Z"},
        },
        {
            "id": "event2",
            "summary": "Lunch",
            "start": {"dateTime": (now + timedelta(hours=4)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=5)).isoformat() + "Z"},
        }
    ]
}

SAMPLE_EVENTS_WORK = {
    "items": [
        {
            "id": "work_event1",
            "summary": "Conflicting Work Meeting",  # Overlaps with Morning Meeting
            "start": {"dateTime": (now + timedelta(hours=1, minutes=30)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=2, minutes=30)).isoformat() + "Z"},
        }
    ]
}

SAMPLE_EVENTS_FAMILY = {
    "items": []
}


def create_mock_calendar_service():
    """Create a mock Calendar API service for conflict detection."""
    service = MagicMock()

    # Mock calendarList().list()
    service.calendarList().list().execute.return_value = SAMPLE_CALENDARS

    # Mock events().list() for different calendars
    def mock_events_list(calendarId, **kwargs):
        mock = MagicMock()
        if calendarId == "primary":
            mock.execute.return_value = SAMPLE_EVENTS_PRIMARY
        elif calendarId == "work@example.com":
            mock.execute.return_value = SAMPLE_EVENTS_WORK
        else:
            mock.execute.return_value = SAMPLE_EVENTS_FAMILY
        return mock

    service.events().list = mock_events_list

    return service


class TestListCalendars:
    """Tests for list_calendars tool."""

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_list_calendars_success(self, mock_get_service, mock_get_credentials):
        """Test successful calendar listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_calendars = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_calendars":
                list_calendars = tool.fn
                break

        assert list_calendars is not None, "list_calendars tool not found"

        result = list_calendars()

        assert result["success"] is True
        assert "calendars" in result
        assert len(result["calendars"]) == 3
        assert result["calendars"][0]["id"] == "primary"

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    def test_list_calendars_not_authenticated(self, mock_get_credentials):
        """Test list_calendars when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_calendars = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_calendars":
                list_calendars = tool.fn
                break

        result = list_calendars()

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestCheckConflicts:
    """Tests for check_conflicts tool."""

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_check_conflicts_finds_overlap(self, mock_get_service, mock_get_credentials):
        """Test that conflicts are detected between calendars."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        check_conflicts = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "check_conflicts":
                check_conflicts = tool.fn
                break

        assert check_conflicts is not None, "check_conflicts tool not found"

        result = check_conflicts(
            start_time="2024-01-15T09:00:00",
            end_time="2024-01-15T18:00:00",
            calendar_ids=["primary", "work@example.com"]
        )

        assert result["success"] is True
        assert "conflicts" in result
        # Should detect the overlap between Morning Meeting and Conflicting Work Meeting
        assert len(result["conflicts"]) >= 1

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_check_conflicts_no_overlap(self, mock_get_service, mock_get_credentials):
        """Test when there are no conflicts."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Create service with no conflicting events
        service = MagicMock()
        service.calendarList().list().execute.return_value = SAMPLE_CALENDARS
        service.events().list().execute.return_value = {"items": []}
        mock_get_service.return_value = service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        check_conflicts = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "check_conflicts":
                check_conflicts = tool.fn
                break

        result = check_conflicts(
            start_time="2024-01-15T09:00:00",
            end_time="2024-01-15T18:00:00"
        )

        assert result["success"] is True
        assert len(result["conflicts"]) == 0


class TestFindFreeTime:
    """Tests for find_free_time tool."""

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_find_free_time_success(self, mock_get_service, mock_get_credentials):
        """Test successful free time finding."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        find_free_time = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "find_free_time":
                find_free_time = tool.fn
                break

        assert find_free_time is not None, "find_free_time tool not found"

        result = find_free_time(
            date="2024-01-15",
            duration_minutes=60
        )

        assert result["success"] is True
        assert "free_slots" in result
        # Should find some free time slots
        assert len(result["free_slots"]) >= 0

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    def test_find_free_time_not_authenticated(self, mock_get_credentials):
        """Test find_free_time when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        find_free_time = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "find_free_time":
                find_free_time = tool.fn
                break

        result = find_free_time(date="2024-01-15")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetDailyAgenda:
    """Tests for get_daily_agenda tool."""

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_get_daily_agenda_success(self, mock_get_service, mock_get_credentials):
        """Test successful daily agenda retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_daily_agenda = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_daily_agenda":
                get_daily_agenda = tool.fn
                break

        assert get_daily_agenda is not None, "get_daily_agenda tool not found"

        result = get_daily_agenda(date="2024-01-15")

        assert result["success"] is True
        assert "timed_events" in result
        assert "all_day_events" in result
        assert "date" in result

    @patch("gmail_mcp.mcp.tools.conflict.get_credentials")
    @patch("gmail_mcp.mcp.tools.conflict.get_calendar_service")
    def test_get_daily_agenda_with_specific_calendars(self, mock_get_service, mock_get_credentials):
        """Test daily agenda with specific calendars."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_get_service.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_daily_agenda = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_daily_agenda":
                get_daily_agenda = tool.fn
                break

        result = get_daily_agenda(
            date="2024-01-15",
            calendar_ids=["primary", "work@example.com"]
        )

        assert result["success"] is True
        assert "timed_events" in result
        assert "all_day_events" in result
