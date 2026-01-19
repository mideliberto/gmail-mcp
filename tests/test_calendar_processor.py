"""
Tests for calendar/processor.py - Calendar processing helpers
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestGetColorIdFromName:
    """Tests for get_color_id_from_name function."""

    def test_standard_colors(self):
        """Test standard color names return correct IDs."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("blue") == "1"
        assert get_color_id_from_name("green") == "2"
        assert get_color_id_from_name("purple") == "3"
        assert get_color_id_from_name("red") == "4"
        assert get_color_id_from_name("yellow") == "5"
        assert get_color_id_from_name("orange") == "6"

    def test_color_aliases(self):
        """Test color aliases return correct IDs."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("light blue") == "1"
        assert get_color_id_from_name("lavender") == "3"
        assert get_color_id_from_name("salmon") == "4"
        assert get_color_id_from_name("cyan") == "7"

    def test_case_insensitive(self):
        """Test color names are case insensitive."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("BLUE") == "1"
        assert get_color_id_from_name("Red") == "4"
        assert get_color_id_from_name("GREEN") == "2"

    def test_numeric_color_ids(self):
        """Test numeric color IDs are returned as-is."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("1") == "1"
        assert get_color_id_from_name("5") == "5"
        assert get_color_id_from_name("11") == "11"

    def test_invalid_numeric_ids(self):
        """Test invalid numeric IDs return default."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("0") == "1"  # Default
        assert get_color_id_from_name("12") == "1"  # Default
        assert get_color_id_from_name("99") == "1"  # Default

    def test_unknown_color_returns_default(self):
        """Test unknown colors return default blue."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("magenta") == "1"
        assert get_color_id_from_name("unknown") == "1"
        assert get_color_id_from_name("foobar") == "1"

    def test_empty_and_none(self):
        """Test empty string returns default."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("") == "1"

    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        from gmail_mcp.calendar.processor import get_color_id_from_name

        assert get_color_id_from_name("  blue  ") == "1"
        assert get_color_id_from_name("\tred\n") == "4"


class TestParseEventTime:
    """Tests for parse_event_time function."""

    def test_simple_time(self):
        """Test parsing simple time like '3pm'."""
        from gmail_mcp.calendar.processor import parse_event_time

        start, end = parse_event_time("3pm")

        assert start is not None
        assert end is not None
        assert start.hour == 15
        assert start.minute == 0
        # Default duration is 60 minutes
        assert (end - start).total_seconds() == 3600

    def test_time_with_minutes(self):
        """Test parsing time with minutes like '3:30pm'."""
        from gmail_mcp.calendar.processor import parse_event_time

        start, end = parse_event_time("3:30pm")

        assert start is not None
        assert start.hour == 15
        assert start.minute == 30

    def test_time_range(self):
        """Test parsing time range like '3pm-4pm'."""
        from gmail_mcp.calendar.processor import parse_event_time

        start, end = parse_event_time("3pm-4pm")

        assert start is not None
        assert end is not None
        assert start.hour == 15
        assert end.hour == 16

    def test_time_range_with_explicit_date(self):
        """Test parsing time range with explicit date."""
        from gmail_mcp.calendar.processor import parse_event_time
        from datetime import datetime

        # Use explicit date format that the parser handles
        start, end = parse_event_time("January 20 9am-10am")

        assert start is not None
        assert end is not None
        assert start.hour == 9
        assert end.hour == 10

    def test_custom_duration(self):
        """Test custom default duration."""
        from gmail_mcp.calendar.processor import parse_event_time

        start, end = parse_event_time("3pm", default_duration_minutes=30)

        assert start is not None
        assert end is not None
        assert (end - start).total_seconds() == 1800  # 30 minutes

    def test_date_time_parsing(self):
        """Test date and time parsing."""
        from gmail_mcp.calendar.processor import parse_event_time

        # Test that basic time parsing works
        start, end = parse_event_time("June 15 2pm")

        assert start is not None
        assert end is not None
        assert start.hour == 14
        assert start.month == 6
        assert start.day == 15


class TestGetUserTimezone:
    """Tests for get_user_timezone function."""

    @patch("gmail_mcp.calendar.processor.get_credentials")
    def test_not_authenticated(self, mock_get_credentials):
        """Test returns UTC when not authenticated."""
        from gmail_mcp.calendar.processor import get_user_timezone

        mock_get_credentials.return_value = None

        tz = get_user_timezone()
        assert tz == "UTC"

    @patch("gmail_mcp.calendar.processor.get_credentials")
    @patch("gmail_mcp.calendar.processor.build")
    def test_returns_user_timezone(self, mock_build, mock_get_credentials):
        """Test returns user's configured timezone."""
        from gmail_mcp.calendar.processor import get_user_timezone

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.settings().list().execute.return_value = {
            "items": [
                {"id": "timezone", "value": "America/New_York"}
            ]
        }
        mock_build.return_value = mock_service

        tz = get_user_timezone()
        assert tz == "America/New_York"

    @patch("gmail_mcp.calendar.processor.get_credentials")
    @patch("gmail_mcp.calendar.processor.build")
    def test_returns_utc_on_error(self, mock_build, mock_get_credentials):
        """Test returns UTC on API error."""
        from gmail_mcp.calendar.processor import get_user_timezone

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = MagicMock()
        mock_service.settings().list().execute.side_effect = Exception("API Error")
        mock_build.return_value = mock_service

        tz = get_user_timezone()
        assert tz == "UTC"


class TestCalendarColorMapping:
    """Tests for CALENDAR_COLOR_MAPPING constant."""

    def test_all_standard_colors_exist(self):
        """Test all standard colors are in mapping."""
        from gmail_mcp.calendar.processor import CALENDAR_COLOR_MAPPING

        standard_colors = ["blue", "green", "purple", "red", "yellow", "orange", "turquoise", "gray"]
        for color in standard_colors:
            assert color in CALENDAR_COLOR_MAPPING

    def test_color_ids_are_valid(self):
        """Test all color IDs are 1-11."""
        from gmail_mcp.calendar.processor import CALENDAR_COLOR_MAPPING

        for color, color_id in CALENDAR_COLOR_MAPPING.items():
            assert color_id.isdigit()
            assert 1 <= int(color_id) <= 11
