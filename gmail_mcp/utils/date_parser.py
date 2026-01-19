"""
Centralized Natural Language Date Parser

Provides robust NLP date parsing that works consistently across all date-accepting functions.
Supports ISO format and rich natural language expressions.

Supported patterns:
- Relative days: yesterday, today, tomorrow, day before yesterday, day after tomorrow
- Days of week: last monday, this tuesday, next wednesday
- Periods: last week, next month, last quarter, next year, last weekend, next weekend
- Numeric relative: 3 days ago, in 5 days, in 2 hours, 30 minutes ago
- Ranges: past 7 days, next 2 weeks, in the past 3 months
- ISO format: 2026-01-20, 2026-01-20T15:00:00
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from zoneinfo import ZoneInfo

import dateparser

from gmail_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Error hint for users when date parsing fails
DATE_PARSING_HINT = (
    "Supported formats: 'tomorrow', 'next monday', 'in 3 days', "
    "'2026-01-20', 'tomorrow at 2pm', 'this week', 'last week'"
)

# Patterns that indicate user wants past dates
PAST_INDICATORS = {'last', 'ago', 'previous', 'before', 'yesterday', 'past'}
FUTURE_INDICATORS = {'next', 'upcoming', 'in', 'after', 'tomorrow', 'coming'}

# ISO format patterns for fast path
ISO_DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ISO_DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$')

# Custom patterns that dateparser might not handle well
CUSTOM_PATTERNS = {
    'day before yesterday': lambda now: now - timedelta(days=2),
    'day after tomorrow': lambda now: now + timedelta(days=2),
}


def _parse_day_of_week_pattern(date_string: str, now: datetime) -> Optional[datetime]:
    """
    Parse "next X", "this X", "last X" day-of-week patterns.

    Args:
        date_string: The date string to parse
        now: Reference datetime

    Returns:
        datetime or None if not a day-of-week pattern
    """
    lower = date_string.lower().strip()

    # Extract time component if present (e.g., "next monday at 10am")
    time_match = re.search(r'\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', lower, re.IGNORECASE)
    time_hour = None
    time_minute = 0
    if time_match:
        time_str = time_match.group(1).strip().lower()
        # Parse the time
        if 'pm' in time_str:
            hour = int(re.search(r'\d+', time_str).group())
            time_hour = hour + 12 if hour != 12 else 12
        elif 'am' in time_str:
            hour = int(re.search(r'\d+', time_str).group())
            time_hour = hour if hour != 12 else 0
        else:
            time_hour = int(re.search(r'\d+', time_str).group())

        minute_match = re.search(r':(\d{2})', time_str)
        if minute_match:
            time_minute = int(minute_match.group(1))

    # Check for "next <day>" pattern
    next_match = re.search(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', lower)
    if next_match:
        day_name = next_match.group(1)
        target_weekday = DAY_NAMES.get(day_name)
        if target_weekday is not None:
            current_weekday = now.weekday()
            # "next X" means the X in the following week
            days_until = (target_weekday - current_weekday) % 7
            if days_until == 0:
                days_until = 7  # Same day of week means next week
            else:
                days_until += 7  # Push to next week

            result = now + timedelta(days=days_until)
            result = result.replace(hour=time_hour or 0, minute=time_minute, second=0, microsecond=0)
            return result

    # Check for "this <day>" pattern
    this_match = re.search(r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', lower)
    if this_match:
        day_name = this_match.group(1)
        target_weekday = DAY_NAMES.get(day_name)
        if target_weekday is not None:
            current_weekday = now.weekday()
            # "this X" means the X in the current week
            days_until = (target_weekday - current_weekday) % 7
            if days_until == 0:
                days_until = 0  # Today

            result = now + timedelta(days=days_until)
            result = result.replace(hour=time_hour or 0, minute=time_minute, second=0, microsecond=0)
            return result

    # Check for "last <day>" pattern
    last_match = re.search(r'\blast\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', lower)
    if last_match:
        day_name = last_match.group(1)
        target_weekday = DAY_NAMES.get(day_name)
        if target_weekday is not None:
            current_weekday = now.weekday()
            # "last X" means the X in the previous week
            days_ago = (current_weekday - target_weekday) % 7
            if days_ago == 0:
                days_ago = 7  # Same day of week means last week

            result = now - timedelta(days=days_ago)
            result = result.replace(hour=time_hour or 0, minute=time_minute, second=0, microsecond=0)
            return result

    return None

# Day name to weekday mapping
DAY_NAMES = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}

# Recurrence pattern mappings
FREQUENCY_ALIASES = {
    'daily': 'DAILY',
    'every day': 'DAILY',
    'weekly': 'WEEKLY',
    'every week': 'WEEKLY',
    'biweekly': 'WEEKLY',  # interval=2
    'bi-weekly': 'WEEKLY',
    'fortnightly': 'WEEKLY',
    'monthly': 'MONTHLY',
    'every month': 'MONTHLY',
    'yearly': 'YEARLY',
    'annually': 'YEARLY',
    'every year': 'YEARLY',
}

WEEKDAY_CODES = {
    'monday': 'MO', 'mon': 'MO',
    'tuesday': 'TU', 'tue': 'TU', 'tues': 'TU',
    'wednesday': 'WE', 'wed': 'WE',
    'thursday': 'TH', 'thu': 'TH', 'thur': 'TH', 'thurs': 'TH',
    'friday': 'FR', 'fri': 'FR',
    'saturday': 'SA', 'sat': 'SA',
    'sunday': 'SU', 'sun': 'SU',
}


def parse_natural_date(
    date_string: str,
    timezone: Optional[str] = None,
    prefer_future: Optional[bool] = None,
    return_end_of_day: bool = False,
    base_date: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Parse natural language or ISO date strings.

    Args:
        date_string: The date string to parse (e.g., "tomorrow", "next monday", "2026-01-20")
        timezone: User's timezone (defaults to UTC if not provided)
        prefer_future: For ambiguous dates, prefer future dates. If None, auto-detect from context.
        return_end_of_day: Return 23:59:59 instead of 00:00:00 for date-only strings
        base_date: Reference date for relative calculations (defaults to now)

    Returns:
        Timezone-aware datetime or None if parsing fails

    Examples:
        >>> parse_natural_date("tomorrow")
        datetime(2026, 1, 20, 0, 0, tzinfo=ZoneInfo('UTC'))

        >>> parse_natural_date("next monday at 2pm")
        datetime(2026, 1, 27, 14, 0, tzinfo=ZoneInfo('UTC'))

        >>> parse_natural_date("3 days ago")
        datetime(2026, 1, 16, ..., tzinfo=ZoneInfo('UTC'))
    """
    if not date_string or not date_string.strip():
        return None

    date_string = date_string.strip()

    # Auto-detect date direction if not specified (Item 5: past date preference)
    if prefer_future is None:
        detected = detect_date_direction(date_string)
        prefer_future = detected if detected is not None else True

    # Determine timezone - validate it first
    tz_name = timezone if timezone else 'UTC'
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Invalid timezone '{timezone}', using UTC")
        tz = ZoneInfo('UTC')
        tz_name = 'UTC'

    # Get reference datetime
    now = base_date or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    # Fast path: Try ISO format first
    result = _try_iso_parse(date_string, tz)
    if result:
        return _apply_end_of_day(result, return_end_of_day, tz)

    # Check custom patterns that dateparser might not handle well
    lower_string = date_string.lower().strip()
    for pattern, handler in CUSTOM_PATTERNS.items():
        if lower_string == pattern:
            result = handler(now)
            if result.tzinfo is None:
                result = result.replace(tzinfo=tz)
            return _apply_end_of_day(result, return_end_of_day, tz)

    # Handle "next X", "this X", "last X" day-of-week patterns
    dow_result = _parse_day_of_week_pattern(date_string, now)
    if dow_result:
        if dow_result.tzinfo is None:
            dow_result = dow_result.replace(tzinfo=tz)
        return _apply_end_of_day(dow_result, return_end_of_day, tz)

    # Use dateparser with appropriate settings - always use valid timezone
    settings = {
        'PREFER_DATES_FROM': 'future' if prefer_future else 'past',
        'PREFER_DAY_OF_MONTH': 'first',
        'RETURN_AS_TIMEZONE_AWARE': True,
        'TIMEZONE': tz_name,  # Use validated timezone name
        'RELATIVE_BASE': now.replace(tzinfo=None),  # dateparser wants naive datetime
    }

    try:
        result = dateparser.parse(date_string, settings=settings)

        if result:
            # Ensure timezone awareness
            if result.tzinfo is None:
                result = result.replace(tzinfo=tz)

            # Handle the "next X" pattern more accurately
            result = _adjust_for_next_pattern(date_string, result, now)

            return _apply_end_of_day(result, return_end_of_day, tz)
    except Exception as e:
        logger.warning(f"dateparser failed for '{date_string}': {e}")

    return None


def _try_iso_parse(date_string: str, tz: ZoneInfo) -> Optional[datetime]:
    """Fast path for ISO format dates."""
    # Check for ISO date (YYYY-MM-DD)
    if ISO_DATE_PATTERN.match(date_string):
        try:
            dt = datetime.fromisoformat(date_string)
            return dt.replace(tzinfo=tz)
        except ValueError:
            pass

    # Check for ISO datetime
    if ISO_DATETIME_PATTERN.match(date_string):
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        except ValueError:
            pass

    return None


def _adjust_for_next_pattern(date_string: str, result: datetime, now: datetime) -> datetime:
    """
    Adjust for 'next X' patterns to ensure proper week handling.

    dateparser sometimes interprets 'next monday' as this monday if we're
    earlier in the week. We want 'next monday' to always mean the monday
    in the following week.
    """
    lower = date_string.lower()

    # Check for "next <day>" pattern
    match = re.search(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', lower)
    if match:
        day_name = match.group(1)
        target_weekday = DAY_NAMES.get(day_name)

        if target_weekday is not None:
            current_weekday = now.weekday()

            # If result is in the current week, push it to next week
            days_diff = (result.date() - now.date()).days
            if days_diff < 7:
                # Find the next occurrence of target day
                days_until = (target_weekday - current_weekday) % 7
                if days_until == 0:
                    days_until = 7  # "next monday" on a monday means next week
                else:
                    days_until += 7  # Always push to next week for "next X"

                result = result.replace(
                    year=now.year,
                    month=now.month,
                    day=now.day
                ) + timedelta(days=days_until)

    return result


def _apply_end_of_day(dt: datetime, return_end_of_day: bool, tz: ZoneInfo) -> datetime:
    """Apply end of day time if requested and time is midnight."""
    if return_end_of_day and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def parse_week_range(
    week_string: str,
    timezone: Optional[str] = None,
    base_date: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse week expressions like "this week", "next week", "last week".

    Args:
        week_string: Week expression to parse
        timezone: User's timezone
        base_date: Reference date (defaults to now)

    Returns:
        Tuple of (start_datetime, end_datetime) for the week range,
        or (None, None) if not a week expression
    """
    # Determine timezone
    tz_name = timezone if timezone else 'UTC'
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('UTC')

    # Get reference datetime
    now = base_date or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    lower = week_string.lower().strip()

    # Calculate Monday of current week
    current_monday = now - timedelta(days=now.weekday())
    current_monday = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate Friday of current week (end of work week)
    current_friday = current_monday + timedelta(days=4)
    current_friday = current_friday.replace(hour=23, minute=59, second=59, microsecond=0)

    if lower in ('this week', 'current week'):
        return current_monday, current_friday

    if lower == 'next week':
        next_monday = current_monday + timedelta(days=7)
        next_friday = next_monday + timedelta(days=4)
        next_friday = next_friday.replace(hour=23, minute=59, second=59, microsecond=0)
        return next_monday, next_friday

    if lower == 'last week':
        last_monday = current_monday - timedelta(days=7)
        last_friday = last_monday + timedelta(days=4)
        last_friday = last_friday.replace(hour=23, minute=59, second=59, microsecond=0)
        return last_monday, last_friday

    # Check for "past N weeks" or "last N weeks"
    past_weeks_match = re.match(r'(?:past|last)\s+(\d+)\s+weeks?', lower)
    if past_weeks_match:
        num_weeks = int(past_weeks_match.group(1))
        start = current_monday - timedelta(weeks=num_weeks)
        end = current_friday
        return start, end

    # Check for "next N weeks"
    next_weeks_match = re.match(r'next\s+(\d+)\s+weeks?', lower)
    if next_weeks_match:
        num_weeks = int(next_weeks_match.group(1))
        start = current_monday
        end = current_monday + timedelta(weeks=num_weeks, days=4)
        end = end.replace(hour=23, minute=59, second=59, microsecond=0)
        return start, end

    # Check for "past N days" or "last N days"
    past_days_match = re.match(r'(?:past|last)\s+(\d+)\s+days?', lower)
    if past_days_match:
        num_days = int(past_days_match.group(1))
        start = now - timedelta(days=num_days)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return start, end

    # Check for "next N days"
    next_days_match = re.match(r'next\s+(\d+)\s+days?', lower)
    if next_days_match:
        num_days = int(next_days_match.group(1))
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now + timedelta(days=num_days)
        end = end.replace(hour=23, minute=59, second=59, microsecond=0)
        return start, end

    return None, None


def parse_date_range(
    start_string: str,
    end_string: str,
    timezone: Optional[str] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse start and end dates, ensuring end is after start.
    Handles week expressions like "this week", "next week".

    Args:
        start_string: Start date/time string
        end_string: End date/time string
        timezone: User's timezone

    Returns:
        Tuple of (start_datetime, end_datetime), either may be None if parsing fails
    """
    # Check if start_string is a week expression that should expand to a range
    if start_string.lower().strip() == end_string.lower().strip():
        week_start, week_end = parse_week_range(start_string, timezone=timezone)
        if week_start and week_end:
            return week_start, week_end

    # Check for week expressions in individual strings
    start_week, _ = parse_week_range(start_string, timezone=timezone)
    _, end_week = parse_week_range(end_string, timezone=timezone)

    start_dt = start_week if start_week else parse_natural_date(start_string, timezone=timezone, prefer_future=True)
    end_dt = end_week if end_week else parse_natural_date(end_string, timezone=timezone, prefer_future=True, return_end_of_day=True)

    # If end is before start, try adjusting
    if start_dt and end_dt and end_dt <= start_dt:
        # If same day, assume end time is later the same day
        if start_dt.date() == end_dt.date():
            # Keep as is, end time might just be wrong
            pass
        else:
            # Push end date forward by a week
            end_dt = end_dt + timedelta(days=7)

    return start_dt, end_dt


def parse_recurrence_pattern(pattern: str) -> Optional[Dict[str, Any]]:
    """
    Parse natural language recurrence patterns.

    Args:
        pattern: Natural language recurrence (e.g., "every weekday", "weekly until march")

    Returns:
        Dict with frequency, interval, by_day, count, until keys
        or None if not recognized

    Examples:
        >>> parse_recurrence_pattern("every day")
        {'frequency': 'DAILY', 'interval': 1}

        >>> parse_recurrence_pattern("every weekday")
        {'frequency': 'WEEKLY', 'interval': 1, 'by_day': ['MO', 'TU', 'WE', 'TH', 'FR']}

        >>> parse_recurrence_pattern("every 2 weeks")
        {'frequency': 'WEEKLY', 'interval': 2}

        >>> parse_recurrence_pattern("daily for 2 weeks")
        {'frequency': 'DAILY', 'interval': 1, 'count': 14}
    """
    if not pattern:
        return None

    lower = pattern.lower().strip()
    result = {'interval': 1}

    # Check for simple frequency aliases first
    for alias, freq in FREQUENCY_ALIASES.items():
        if lower == alias or lower.startswith(alias + ' '):
            result['frequency'] = freq
            if alias in ('biweekly', 'bi-weekly', 'fortnightly'):
                result['interval'] = 2
            break

    # Check for "every weekday" pattern
    if 'every weekday' in lower or 'weekdays' in lower:
        result['frequency'] = 'WEEKLY'
        result['by_day'] = ['MO', 'TU', 'WE', 'TH', 'FR']
        return result

    # Check for "every weekend" pattern
    if 'every weekend' in lower or 'weekends' in lower:
        result['frequency'] = 'WEEKLY'
        result['by_day'] = ['SA', 'SU']
        return result

    # Check for "every <day>" or "every <day> and <day>" patterns
    day_match = re.findall(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', lower)
    if day_match and ('every' in lower or 'on' in lower):
        result['frequency'] = 'WEEKLY'
        result['by_day'] = list(set(WEEKDAY_CODES[d] for d in day_match))
        # Sort days in week order
        day_order = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
        result['by_day'] = sorted(result['by_day'], key=lambda x: day_order.index(x))
        return result

    # Check for "every N days/weeks/months/years" pattern
    interval_match = re.search(r'every\s+(\d+)\s+(day|week|month|year)s?', lower)
    if interval_match:
        result['interval'] = int(interval_match.group(1))
        unit = interval_match.group(2)
        freq_map = {'day': 'DAILY', 'week': 'WEEKLY', 'month': 'MONTHLY', 'year': 'YEARLY'}
        result['frequency'] = freq_map[unit]

    # Check for "for N days/weeks" pattern (count)
    count_match = re.search(r'for\s+(\d+)\s+(day|week|month|year)s?', lower)
    if count_match:
        count_num = int(count_match.group(1))
        count_unit = count_match.group(2)

        # Convert to occurrence count based on frequency
        freq = result.get('frequency', 'DAILY')
        if count_unit == 'day':
            if freq == 'DAILY':
                result['count'] = count_num
            elif freq == 'WEEKLY':
                result['count'] = count_num // 7 or 1
        elif count_unit == 'week':
            if freq == 'DAILY':
                result['count'] = count_num * 7
            elif freq == 'WEEKLY':
                result['count'] = count_num

    # Check for "until <date>" pattern
    until_match = re.search(r'until\s+(.+?)(?:\s*$|\s+for|\s+every)', lower)
    if until_match:
        until_str = until_match.group(1).strip()
        until_dt = parse_natural_date(until_str)
        if until_dt:
            result['until'] = until_dt.strftime('%Y-%m-%d')
            # Can't have both count and until
            result.pop('count', None)

    # If we have a frequency, return the result
    if 'frequency' in result:
        return result

    return None


def detect_date_direction(date_string: str) -> Optional[bool]:
    """
    Detect if a date string indicates past or future preference.

    Args:
        date_string: The date string to analyze

    Returns:
        True if future preferred, False if past preferred, None if ambiguous
    """
    words = set(date_string.lower().split())

    has_past = bool(words & PAST_INDICATORS)
    has_future = bool(words & FUTURE_INDICATORS)

    if has_past and not has_future:
        return False  # Prefer past
    if has_future and not has_past:
        return True  # Prefer future
    return None  # Ambiguous


def parse_working_hours(hours_string: str) -> Tuple[int, int]:
    """
    Parse working hours from various formats.

    Args:
        hours_string: Working hours string (e.g., "9-17", "9am-5pm", "9:00-17:00")

    Returns:
        Tuple of (start_hour, end_hour) as integers (0-23)
        Defaults to (9, 17) if parsing fails

    Examples:
        >>> parse_working_hours("9-17")
        (9, 17)
        >>> parse_working_hours("9am-5pm")
        (9, 17)
        >>> parse_working_hours("9:00-17:00")
        (9, 17)
        >>> parse_working_hours("9am to 5pm")
        (9, 17)
    """
    if not hours_string:
        return (9, 17)

    hours_string = hours_string.lower().strip()

    # Try simple format "9-17"
    simple_match = re.match(r'^(\d{1,2})-(\d{1,2})$', hours_string)
    if simple_match:
        return (int(simple_match.group(1)), int(simple_match.group(2)))

    # Try "9:00-17:00" format
    time_match = re.match(r'^(\d{1,2}):\d{2}-(\d{1,2}):\d{2}$', hours_string)
    if time_match:
        return (int(time_match.group(1)), int(time_match.group(2)))

    # Try "9am-5pm" or "9am to 5pm" format
    ampm_match = re.match(r'^(\d{1,2})\s*([ap]m?)?\s*(?:-|to)\s*(\d{1,2})\s*([ap]m?)?$', hours_string)
    if ampm_match:
        start_hour = int(ampm_match.group(1))
        start_ampm = ampm_match.group(2) or ''
        end_hour = int(ampm_match.group(3))
        end_ampm = ampm_match.group(4) or ''

        # Convert to 24-hour
        if 'p' in start_ampm and start_hour != 12:
            start_hour += 12
        elif 'a' in start_ampm and start_hour == 12:
            start_hour = 0

        if 'p' in end_ampm and end_hour != 12:
            end_hour += 12
        elif 'a' in end_ampm and end_hour == 12:
            end_hour = 0

        return (start_hour, end_hour)

    # Default fallback
    return (9, 17)


def parse_duration(duration_string: str) -> int:
    """
    Parse duration from various formats to minutes.

    Args:
        duration_string: Duration string (e.g., "60", "1 hour", "90 minutes", "1.5 hours")

    Returns:
        Duration in minutes (defaults to 60 if parsing fails)

    Examples:
        >>> parse_duration("60")
        60
        >>> parse_duration("1 hour")
        60
        >>> parse_duration("90 minutes")
        90
        >>> parse_duration("1.5 hours")
        90
        >>> parse_duration("1 hour 30 minutes")
        90
    """
    if not duration_string:
        return 60

    # Handle integer input
    if isinstance(duration_string, int):
        return duration_string

    duration_string = str(duration_string).lower().strip()

    # Try simple integer
    if duration_string.isdigit():
        return int(duration_string)

    # Special cases
    if duration_string in ('half hour', 'half an hour', 'a half hour', '30 mins'):
        return 30
    if duration_string in ('quarter hour', 'quarter of an hour', '15 mins'):
        return 15

    total_minutes = 0

    # Match hours
    hours_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hr|h)s?', duration_string)
    if hours_match:
        hours = float(hours_match.group(1))
        total_minutes += int(hours * 60)

    # Match minutes
    minutes_match = re.search(r'(\d+)\s*(?:minute|min|m)s?(?!\w)', duration_string)
    if minutes_match:
        total_minutes += int(minutes_match.group(1))

    return total_minutes if total_minutes > 0 else 60


def get_relative_date_description(dt: datetime, base: Optional[datetime] = None) -> str:
    """
    Get a human-readable relative description of a date.

    Args:
        dt: The datetime to describe
        base: Reference datetime (defaults to now)

    Returns:
        String like "tomorrow", "next Monday", "in 3 days"
    """
    if base is None:
        base = datetime.now(dt.tzinfo if dt.tzinfo else ZoneInfo('UTC'))

    diff = dt.date() - base.date()
    days = diff.days

    if days == 0:
        return "today"
    elif days == 1:
        return "tomorrow"
    elif days == -1:
        return "yesterday"
    elif days == 2:
        return "day after tomorrow"
    elif days == -2:
        return "day before yesterday"
    elif 2 < days <= 7:
        return f"this {dt.strftime('%A')}"
    elif -7 <= days < -2:
        return f"last {dt.strftime('%A')}"
    elif days > 7:
        return f"in {days} days"
    elif days < -7:
        return f"{-days} days ago"
    else:
        return f"in {days} days"
