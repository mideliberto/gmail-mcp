"""
Tests for mcp/tools.py - Calendar tools

These tests mock the Google Calendar API to verify calendar tool functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


# Sample Calendar API response data
SAMPLE_EVENT = {
    "id": "event001",
    "summary": "Team Meeting",
    "description": "Weekly sync",
    "location": "Conference Room A",
    "start": {
        "dateTime": "2024-06-15T14:00:00-07:00",
        "timeZone": "America/Los_Angeles"
    },
    "end": {
        "dateTime": "2024-06-15T15:00:00-07:00",
        "timeZone": "America/Los_Angeles"
    },
    "attendees": [
        {"email": "user@example.com", "responseStatus": "accepted"},
        {"email": "colleague@example.com", "responseStatus": "needsAction"},
    ],
    "htmlLink": "https://calendar.google.com/event?eid=event001",
    "status": "confirmed",
}

SAMPLE_EVENT_2 = {
    "id": "event002",
    "summary": "Lunch",
    "start": {
        "dateTime": "2024-06-15T12:00:00-07:00",
        "timeZone": "America/Los_Angeles"
    },
    "end": {
        "dateTime": "2024-06-15T13:00:00-07:00",
        "timeZone": "America/Los_Angeles"
    },
    "htmlLink": "https://calendar.google.com/event?eid=event002",
    "status": "confirmed",
}

SAMPLE_CALENDAR_SETTINGS = {
    "items": [
        {"id": "timezone", "value": "America/Los_Angeles"}
    ]
}


def create_mock_calendar_service():
    """Create a mock Calendar API service."""
    service = MagicMock()

    # Mock calendarList().get() for primary calendar
    service.calendarList().get().execute.return_value = {
        "id": "primary",
        "summary": "user@example.com",
        "timeZone": "America/Los_Angeles"
    }

    # Mock events().list()
    service.events().list().execute.return_value = {
        "items": [SAMPLE_EVENT, SAMPLE_EVENT_2],
        "nextPageToken": None,
    }

    # Mock events().insert()
    service.events().insert().execute.return_value = {
        "id": "new_event_001",
        "summary": "New Meeting",
        "htmlLink": "https://calendar.google.com/event?eid=new_event_001",
        "start": {"dateTime": "2024-06-15T14:00:00-07:00"},
        "end": {"dateTime": "2024-06-15T15:00:00-07:00"},
    }

    # Mock events().get()
    def mock_get_event(calendarId, eventId):
        mock = MagicMock()
        if eventId == "event001":
            mock.execute.return_value = SAMPLE_EVENT
        elif eventId == "event002":
            mock.execute.return_value = SAMPLE_EVENT_2
        else:
            mock.execute.return_value = SAMPLE_EVENT
        return mock

    service.events().get = mock_get_event

    # Mock events().update()
    service.events().update().execute.return_value = {
        "id": "event001",
        "summary": "Updated Meeting",
        "htmlLink": "https://calendar.google.com/event?eid=event001",
    }

    # Mock events().delete()
    service.events().delete().execute.return_value = None

    # Mock events().patch() for RSVP
    service.events().patch().execute.return_value = {
        "id": "event001",
        "summary": "Team Meeting",
        "htmlLink": "https://calendar.google.com/event?eid=event001",
    }

    # Mock settings().list() for timezone
    service.settings().list().execute.return_value = SAMPLE_CALENDAR_SETTINGS

    return service


class TestCreateCalendarEvent:
    """Tests for create_calendar_event tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    @patch("gmail_mcp.calendar.processor.get_credentials")
    @patch("gmail_mcp.calendar.processor.build")
    def test_create_event_success(self, mock_proc_build, mock_proc_creds,
                                   mock_build, mock_get_credentials):
        """Test successful event creation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_proc_creds.return_value = mock_credentials
        mock_service = create_mock_calendar_service()
        mock_build.return_value = mock_service
        mock_proc_build.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_calendar_event":
                create_calendar_event = tool.fn
                break

        assert create_calendar_event is not None

        result = create_calendar_event(
            summary="Test Meeting",
            start_time="2024-06-15T14:00:00",
            end_time="2024-06-15T15:00:00"
        )

        assert "error" not in result or result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_create_event_not_authenticated(self, mock_get_credentials):
        """Test create_calendar_event when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_calendar_event":
                create_calendar_event = tool.fn
                break

        result = create_calendar_event(
            summary="Test Meeting",
            start_time="tomorrow 3pm"
        )

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestListCalendarEvents:
    """Tests for list_calendar_events tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_list_events_success(self, mock_build, mock_get_credentials):
        """Test successful event listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_calendar_events = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_calendar_events":
                list_calendar_events = tool.fn
                break

        assert list_calendar_events is not None

        result = list_calendar_events(max_results=10)

        assert "error" not in result
        assert "events" in result
        assert len(result["events"]) == 2

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_list_events_not_authenticated(self, mock_get_credentials):
        """Test list_calendar_events when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_calendar_events = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_calendar_events":
                list_calendar_events = tool.fn
                break

        result = list_calendar_events(max_results=10)

        assert "error" in result
        assert "Not authenticated" in result["error"]

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_list_events_with_query(self, mock_build, mock_get_credentials):
        """Test listing events with search query."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_calendar_events = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_calendar_events":
                list_calendar_events = tool.fn
                break

        result = list_calendar_events(max_results=10, query="meeting")

        assert "error" not in result
        assert "events" in result


class TestUpdateCalendarEvent:
    """Tests for update_calendar_event tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_update_event_success(self, mock_build, mock_get_credentials):
        """Test successful event update."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_calendar_event":
                update_calendar_event = tool.fn
                break

        assert update_calendar_event is not None

        result = update_calendar_event(
            event_id="event001",
            summary="Updated Meeting Title"
        )

        assert "error" not in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_update_event_not_authenticated(self, mock_get_credentials):
        """Test update_calendar_event when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        update_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "update_calendar_event":
                update_calendar_event = tool.fn
                break

        result = update_calendar_event(event_id="event001", summary="New Title")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestDeleteCalendarEvent:
    """Tests for delete_calendar_event tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_delete_event_success(self, mock_build, mock_get_credentials):
        """Test successful event deletion."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_calendar_event":
                delete_calendar_event = tool.fn
                break

        assert delete_calendar_event is not None

        result = delete_calendar_event(event_id="event001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_delete_event_not_authenticated(self, mock_get_credentials):
        """Test delete_calendar_event when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_calendar_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_calendar_event":
                delete_calendar_event = tool.fn
                break

        result = delete_calendar_event(event_id="event001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestRsvpEvent:
    """Tests for rsvp_event tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_rsvp_accepted(self, mock_build, mock_get_credentials):
        """Test RSVP with accepted response."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        rsvp_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "rsvp_event":
                rsvp_event = tool.fn
                break

        assert rsvp_event is not None

        result = rsvp_event(event_id="event001", response="accepted")

        assert "error" not in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_rsvp_declined(self, mock_build, mock_get_credentials):
        """Test RSVP with declined response."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_calendar_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        rsvp_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "rsvp_event":
                rsvp_event = tool.fn
                break

        result = rsvp_event(event_id="event001", response="declined")

        assert "error" not in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_rsvp_not_authenticated(self, mock_get_credentials):
        """Test rsvp_event when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        rsvp_event = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "rsvp_event":
                rsvp_event = tool.fn
                break

        result = rsvp_event(event_id="event001", response="accepted")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestSuggestMeetingTimes:
    """Tests for suggest_meeting_times tool."""

    @patch("gmail_mcp.calendar.processor.get_credentials")
    @patch("gmail_mcp.calendar.processor.build")
    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_suggest_times_success(self, mock_build, mock_get_credentials,
                                    mock_proc_build, mock_proc_creds):
        """Test successful meeting time suggestions."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP
        from datetime import datetime, timedelta

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_proc_creds.return_value = mock_credentials
        mock_service = create_mock_calendar_service()
        # Return empty events for free/busy
        mock_service.events().list().execute.return_value = {"items": []}
        mock_build.return_value = mock_service
        mock_proc_build.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        suggest_meeting_times = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "suggest_meeting_times":
                suggest_meeting_times = tool.fn
                break

        assert suggest_meeting_times is not None

        # Use explicit date format
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = suggest_meeting_times(
            start_date=future_date,
            end_date=future_date,
            duration_minutes=60
        )

        # The function should not error with valid credentials and date
        assert result.get("success", False) or "suggestions" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_suggest_times_not_authenticated(self, mock_get_credentials):
        """Test suggest_meeting_times when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        suggest_meeting_times = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "suggest_meeting_times":
                suggest_meeting_times = tool.fn
                break

        result = suggest_meeting_times(
            start_date="tomorrow",
            end_date="tomorrow"
        )

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestDetectEventsFromEmail:
    """Tests for detect_events_from_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_detect_events_success(self, mock_build, mock_get_credentials):
        """Test successful event detection from email."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Create mock with email containing date/time info
        mock_service = MagicMock()
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "threadId": "thread001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Meeting on Friday at 3pm"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
                ],
                "body": {"data": "TGV0J3MgbWVldCBvbiBGcmlkYXkgYXQgM3Bt"}  # "Let's meet on Friday at 3pm"
            }
        }
        mock_build.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        detect_events = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "detect_events_from_email":
                detect_events = tool.fn
                break

        assert detect_events is not None

        result = detect_events(email_id="msg001")

        # Should not error
        assert "error" not in result or result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_detect_events_not_authenticated(self, mock_get_credentials):
        """Test detect_events_from_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        detect_events = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "detect_events_from_email":
                detect_events = tool.fn
                break

        result = detect_events(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]
