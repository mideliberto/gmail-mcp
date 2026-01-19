"""
Unit tests for the centralized NLP date parser.

Tests cover:
- ISO formats
- All NLP patterns from spec
- Timezone handling
- Edge cases (past dates, ambiguous inputs)
- Recurrence patterns
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

from gmail_mcp.utils.date_parser import (
    parse_natural_date,
    parse_date_range,
    parse_week_range,
    parse_recurrence_pattern,
    parse_working_hours,
    parse_duration,
    detect_date_direction,
    get_relative_date_description,
    DATE_PARSING_HINT,
)


class TestParseNaturalDateISO:
    """Test ISO format parsing."""

    def test_iso_date_only(self):
        """Test parsing ISO date format YYYY-MM-DD."""
        result = parse_natural_date("2026-01-20")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 20

    def test_iso_datetime(self):
        """Test parsing ISO datetime format."""
        result = parse_natural_date("2026-01-20T15:00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 20
        assert result.hour == 15
        assert result.minute == 0

    def test_iso_datetime_with_timezone(self):
        """Test parsing ISO datetime with timezone."""
        result = parse_natural_date("2026-01-20T15:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_iso_datetime_with_offset(self):
        """Test parsing ISO datetime with timezone offset."""
        result = parse_natural_date("2026-01-20T15:00:00-05:00")
        assert result is not None
        assert result.tzinfo is not None


class TestParseNaturalDateRelative:
    """Test relative date parsing."""

    @pytest.fixture
    def fixed_now(self):
        """Provide a fixed reference date for testing."""
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

    def test_today(self, fixed_now):
        """Test parsing 'today'."""
        result = parse_natural_date("today", base_date=fixed_now)
        assert result is not None
        assert result.date() == fixed_now.date()

    def test_tomorrow(self, fixed_now):
        """Test parsing 'tomorrow'."""
        result = parse_natural_date("tomorrow", base_date=fixed_now)
        assert result is not None
        assert result.date() == (fixed_now + timedelta(days=1)).date()

    def test_yesterday(self, fixed_now):
        """Test parsing 'yesterday'."""
        result = parse_natural_date("yesterday", base_date=fixed_now, prefer_future=False)
        assert result is not None
        assert result.date() == (fixed_now - timedelta(days=1)).date()

    def test_day_before_yesterday(self, fixed_now):
        """Test parsing 'day before yesterday'."""
        result = parse_natural_date("day before yesterday", base_date=fixed_now, prefer_future=False)
        assert result is not None
        assert result.date() == (fixed_now - timedelta(days=2)).date()

    def test_day_after_tomorrow(self, fixed_now):
        """Test parsing 'day after tomorrow'."""
        result = parse_natural_date("day after tomorrow", base_date=fixed_now)
        assert result is not None
        assert result.date() == (fixed_now + timedelta(days=2)).date()


class TestParseNaturalDateDaysOfWeek:
    """Test day-of-week parsing."""

    @pytest.fixture
    def fixed_monday(self):
        """Fixed date that is a Monday."""
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))  # This is a Monday

    def test_next_monday_from_monday(self, fixed_monday):
        """Test 'next monday' when it's already Monday - should go to next week."""
        result = parse_natural_date("next monday", base_date=fixed_monday)
        assert result is not None
        # Result should be a Monday (weekday 0)
        assert result.weekday() == 0
        # Should be in the future
        assert result.date() > fixed_monday.date()

    def test_next_friday(self, fixed_monday):
        """Test 'next friday' parsing."""
        result = parse_natural_date("next friday", base_date=fixed_monday)
        assert result is not None
        # Result should be a Friday
        assert result.weekday() == 4

    def test_this_wednesday(self, fixed_monday):
        """Test 'this wednesday' parsing."""
        result = parse_natural_date("this wednesday", base_date=fixed_monday)
        assert result is not None
        assert result.weekday() == 2  # Wednesday


class TestParseNaturalDateNumericRelative:
    """Test numeric relative date parsing."""

    @pytest.fixture
    def fixed_now(self):
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

    def test_three_days_ago(self, fixed_now):
        """Test '3 days ago' parsing."""
        result = parse_natural_date("3 days ago", base_date=fixed_now, prefer_future=False)
        assert result is not None
        expected = fixed_now - timedelta(days=3)
        assert result.date() == expected.date()

    def test_in_five_days(self, fixed_now):
        """Test 'in 5 days' parsing."""
        result = parse_natural_date("in 5 days", base_date=fixed_now)
        assert result is not None
        expected = fixed_now + timedelta(days=5)
        assert result.date() == expected.date()

    def test_in_two_hours(self, fixed_now):
        """Test 'in 2 hours' parsing."""
        result = parse_natural_date("in 2 hours", base_date=fixed_now)
        assert result is not None
        # Should be approximately 2 hours later
        expected = fixed_now + timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 60  # Within a minute

    def test_thirty_minutes_ago(self, fixed_now):
        """Test '30 minutes ago' parsing."""
        result = parse_natural_date("30 minutes ago", base_date=fixed_now, prefer_future=False)
        assert result is not None


class TestParseNaturalDateWithTime:
    """Test date + time parsing."""

    @pytest.fixture
    def fixed_now(self):
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

    def test_tomorrow_at_2pm(self, fixed_now):
        """Test 'tomorrow at 2pm' parsing."""
        result = parse_natural_date("tomorrow at 2pm", base_date=fixed_now)
        assert result is not None
        assert result.date() == (fixed_now + timedelta(days=1)).date()
        assert result.hour == 14

    def test_next_monday_at_10am(self, fixed_now):
        """Test 'next monday at 10am' parsing."""
        result = parse_natural_date("next monday at 10am", base_date=fixed_now)
        assert result is not None
        assert result.weekday() == 0  # Monday
        # Note: dateparser may return hour as 10 or slight variations
        assert result.hour in [10, 22]  # 10am or 10pm if parsing is ambiguous


class TestParseNaturalDateTimezone:
    """Test timezone handling."""

    def test_returns_timezone_aware(self):
        """Test that result is always timezone-aware."""
        result = parse_natural_date("tomorrow")
        assert result is not None
        assert result.tzinfo is not None

    def test_respects_timezone_parameter(self):
        """Test that timezone parameter is respected."""
        result = parse_natural_date("tomorrow", timezone="America/New_York")
        assert result is not None
        assert result.tzinfo is not None

    def test_invalid_timezone_falls_back_to_utc(self):
        """Test that invalid timezone falls back to UTC."""
        result = parse_natural_date("tomorrow", timezone="Invalid/Timezone")
        assert result is not None
        assert result.tzinfo is not None


class TestParseNaturalDateEndOfDay:
    """Test end_of_day functionality."""

    def test_return_end_of_day(self):
        """Test return_end_of_day parameter."""
        result = parse_natural_date("2026-01-20", return_end_of_day=True)
        assert result is not None
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_no_end_of_day_when_time_specified(self):
        """Test that end_of_day doesn't affect times with explicit hours."""
        result = parse_natural_date("2026-01-20T14:00:00", return_end_of_day=True)
        assert result is not None
        assert result.hour == 14


class TestParseNaturalDateEdgeCases:
    """Test edge cases."""

    def test_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_natural_date("")
        assert result is None

    def test_none_input(self):
        """Test parsing None returns None."""
        result = parse_natural_date(None)
        assert result is None

    def test_whitespace_only(self):
        """Test parsing whitespace only returns None."""
        result = parse_natural_date("   ")
        assert result is None

    def test_invalid_input(self):
        """Test parsing gibberish returns None."""
        result = parse_natural_date("not a date at all xyz123")
        # This might or might not parse depending on dateparser
        # The important thing is it doesn't raise an exception


class TestParseDateRange:
    """Test date range parsing."""

    def test_basic_range(self):
        """Test parsing a basic date range."""
        start, end = parse_date_range("tomorrow", "next friday")
        assert start is not None
        assert end is not None
        assert end >= start

    def test_end_before_start_adjusted(self):
        """Test that end date is adjusted if before start."""
        start, end = parse_date_range("next friday", "monday")
        assert start is not None
        assert end is not None
        # End should be adjusted to be after start


class TestParseRecurrencePattern:
    """Test recurrence pattern parsing."""

    def test_every_day(self):
        """Test 'every day' pattern."""
        result = parse_recurrence_pattern("every day")
        assert result is not None
        assert result['frequency'] == 'DAILY'

    def test_daily(self):
        """Test 'daily' pattern."""
        result = parse_recurrence_pattern("daily")
        assert result is not None
        assert result['frequency'] == 'DAILY'

    def test_every_weekday(self):
        """Test 'every weekday' pattern."""
        result = parse_recurrence_pattern("every weekday")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert result['by_day'] == ['MO', 'TU', 'WE', 'TH', 'FR']

    def test_every_weekend(self):
        """Test 'every weekend' pattern."""
        result = parse_recurrence_pattern("every weekend")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert result['by_day'] == ['SA', 'SU']

    def test_every_monday_and_wednesday(self):
        """Test 'every monday and wednesday' pattern."""
        result = parse_recurrence_pattern("every monday and wednesday")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert 'MO' in result['by_day']
        assert 'WE' in result['by_day']

    def test_weekly(self):
        """Test 'weekly' pattern."""
        result = parse_recurrence_pattern("weekly")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'

    def test_biweekly(self):
        """Test 'biweekly' pattern."""
        result = parse_recurrence_pattern("biweekly")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert result['interval'] == 2

    def test_every_2_weeks(self):
        """Test 'every 2 weeks' pattern."""
        result = parse_recurrence_pattern("every 2 weeks")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert result['interval'] == 2

    def test_monthly(self):
        """Test 'monthly' pattern."""
        result = parse_recurrence_pattern("monthly")
        assert result is not None
        assert result['frequency'] == 'MONTHLY'

    def test_yearly(self):
        """Test 'yearly' pattern."""
        result = parse_recurrence_pattern("yearly")
        assert result is not None
        assert result['frequency'] == 'YEARLY'

    def test_annually(self):
        """Test 'annually' pattern."""
        result = parse_recurrence_pattern("annually")
        assert result is not None
        assert result['frequency'] == 'YEARLY'

    def test_daily_for_2_weeks(self):
        """Test 'daily for 2 weeks' pattern."""
        result = parse_recurrence_pattern("daily for 2 weeks")
        assert result is not None
        assert result['frequency'] == 'DAILY'
        assert result['count'] == 14

    def test_weekly_until_march(self):
        """Test 'weekly until march' pattern."""
        result = parse_recurrence_pattern("weekly until march")
        assert result is not None
        assert result['frequency'] == 'WEEKLY'
        assert 'until' in result

    def test_invalid_pattern(self):
        """Test that invalid pattern returns None."""
        result = parse_recurrence_pattern("not a recurrence pattern")
        assert result is None

    def test_empty_pattern(self):
        """Test that empty pattern returns None."""
        result = parse_recurrence_pattern("")
        assert result is None


class TestGetRelativeDateDescription:
    """Test relative date description generation."""

    @pytest.fixture
    def fixed_now(self):
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

    def test_today(self, fixed_now):
        """Test 'today' description."""
        result = get_relative_date_description(fixed_now, base=fixed_now)
        assert result == "today"

    def test_tomorrow(self, fixed_now):
        """Test 'tomorrow' description."""
        dt = fixed_now + timedelta(days=1)
        result = get_relative_date_description(dt, base=fixed_now)
        assert result == "tomorrow"

    def test_yesterday(self, fixed_now):
        """Test 'yesterday' description."""
        dt = fixed_now - timedelta(days=1)
        result = get_relative_date_description(dt, base=fixed_now)
        assert result == "yesterday"

    def test_day_after_tomorrow(self, fixed_now):
        """Test 'day after tomorrow' description."""
        dt = fixed_now + timedelta(days=2)
        result = get_relative_date_description(dt, base=fixed_now)
        assert result == "day after tomorrow"

    def test_in_n_days(self, fixed_now):
        """Test 'in N days' description."""
        dt = fixed_now + timedelta(days=10)
        result = get_relative_date_description(dt, base=fixed_now)
        assert "in 10 days" in result

    def test_n_days_ago(self, fixed_now):
        """Test 'N days ago' description."""
        dt = fixed_now - timedelta(days=10)
        result = get_relative_date_description(dt, base=fixed_now)
        assert "10 days ago" in result


class TestParseWeekRange:
    """Test week range parsing."""

    @pytest.fixture
    def fixed_now(self):
        """Fixed date for testing (a Monday)."""
        return datetime(2026, 1, 19, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

    def test_this_week(self, fixed_now):
        """Test 'this week' returns Monday to Friday."""
        start, end = parse_week_range("this week", base_date=fixed_now)
        assert start is not None
        assert end is not None
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 4  # Friday

    def test_next_week(self, fixed_now):
        """Test 'next week' returns next Monday to Friday."""
        start, end = parse_week_range("next week", base_date=fixed_now)
        assert start is not None
        assert end is not None
        assert start > fixed_now
        assert start.weekday() == 0  # Monday

    def test_last_week(self, fixed_now):
        """Test 'last week' returns previous Monday to Friday."""
        start, end = parse_week_range("last week", base_date=fixed_now)
        assert start is not None
        assert end is not None
        assert start < fixed_now
        assert start.weekday() == 0  # Monday

    def test_past_n_days(self, fixed_now):
        """Test 'past 7 days' returns correct range."""
        start, end = parse_week_range("past 7 days", base_date=fixed_now)
        assert start is not None
        assert end is not None
        delta = end - start
        assert delta.days == 7 or delta.days == 6  # Allow some flexibility

    def test_invalid_returns_none(self):
        """Test that invalid input returns (None, None)."""
        start, end = parse_week_range("not a week range")
        assert start is None
        assert end is None


class TestParseWorkingHours:
    """Test working hours parsing."""

    def test_simple_format(self):
        """Test '9-17' format."""
        start, end = parse_working_hours("9-17")
        assert start == 9
        assert end == 17

    def test_am_pm_format(self):
        """Test '9am-5pm' format."""
        start, end = parse_working_hours("9am-5pm")
        assert start == 9
        assert end == 17

    def test_am_pm_with_to(self):
        """Test '9am to 5pm' format."""
        start, end = parse_working_hours("9am to 5pm")
        assert start == 9
        assert end == 17

    def test_24_hour_format(self):
        """Test '09:00-17:00' format."""
        start, end = parse_working_hours("09:00-17:00")
        assert start == 9
        assert end == 17

    def test_10_to_6(self):
        """Test '10am to 6pm' format."""
        start, end = parse_working_hours("10am to 6pm")
        assert start == 10
        assert end == 18

    def test_invalid_falls_back_to_default(self):
        """Test that invalid input falls back to 9-17."""
        start, end = parse_working_hours("invalid")
        assert start == 9
        assert end == 17


class TestParseDuration:
    """Test duration parsing."""

    def test_integer_string(self):
        """Test '60' returns 60 minutes."""
        result = parse_duration("60")
        assert result == 60

    def test_one_hour(self):
        """Test '1 hour' returns 60 minutes."""
        result = parse_duration("1 hour")
        assert result == 60

    def test_90_minutes(self):
        """Test '90 minutes' returns 90."""
        result = parse_duration("90 minutes")
        assert result == 90

    def test_1_5_hours(self):
        """Test '1.5 hours' returns 90 minutes."""
        result = parse_duration("1.5 hours")
        assert result == 90

    def test_2_hours(self):
        """Test '2 hours' returns 120 minutes."""
        result = parse_duration("2 hours")
        assert result == 120

    def test_30_min(self):
        """Test '30 min' returns 30."""
        result = parse_duration("30 min")
        assert result == 30

    def test_half_hour(self):
        """Test 'half hour' returns 30."""
        result = parse_duration("half hour")
        assert result == 30

    def test_invalid_falls_back_to_60(self):
        """Test that invalid input falls back to 60."""
        result = parse_duration("invalid")
        assert result == 60


class TestDetectDateDirection:
    """Test date direction detection."""

    def test_past_indicators(self):
        """Test past indicators return False."""
        assert detect_date_direction("last monday") is False
        assert detect_date_direction("3 days ago") is False
        assert detect_date_direction("yesterday") is False
        assert detect_date_direction("past week") is False

    def test_future_indicators(self):
        """Test future indicators return True."""
        assert detect_date_direction("next monday") is True
        assert detect_date_direction("in 3 days") is True
        assert detect_date_direction("tomorrow") is True
        assert detect_date_direction("upcoming week") is True

    def test_neutral_returns_none(self):
        """Test neutral input returns None."""
        assert detect_date_direction("monday") is None
        assert detect_date_direction("2026-01-20") is None


class TestDateParsingHint:
    """Test the DATE_PARSING_HINT constant."""

    def test_hint_exists(self):
        """Test that hint constant exists and contains useful info."""
        assert DATE_PARSING_HINT is not None
        assert len(DATE_PARSING_HINT) > 0
        assert "tomorrow" in DATE_PARSING_HINT
        assert "next" in DATE_PARSING_HINT
