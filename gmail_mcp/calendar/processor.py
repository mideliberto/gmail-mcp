"""
Calendar Processing Module

This module provides tools for processing calendar events, including date/time parsing,
timezone handling, and event creation helpers.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dateutil import parser
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.oauth import get_credentials

# Get logger
logger = get_logger(__name__)


class CalendarEvent(BaseModel):
    """
    Schema for calendar event information.
    
    This schema defines the structure of calendar event information
    that is used for creating and managing events.
    """
    summary: str
    start_datetime: datetime
    end_datetime: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = []
    color_id: Optional[str] = None
    timezone: str = "UTC"
    all_day: bool = False


# Color mapping for Google Calendar
# Google Calendar uses color IDs 1-11
CALENDAR_COLOR_MAPPING = {
    # Standard colors
    "blue": "1",
    "green": "2",
    "purple": "3",
    "red": "4",
    "yellow": "5",
    "orange": "6",
    "turquoise": "7",
    "gray": "8",
    "bold blue": "9",
    "bold green": "10",
    "bold red": "11",
    
    # Aliases for easier reference
    "light blue": "1",
    "light green": "2",
    "lavender": "3",
    "salmon": "4",
    "pale yellow": "5",
    "peach": "6",
    "cyan": "7",
    "light gray": "8",
    "dark blue": "9",
    "dark green": "10",
    "dark red": "11",
}

def get_color_id_from_name(color_name: str) -> str:
    """
    Get the color ID from a color name.
    
    This function converts a color name (like "red", "blue", "purple") to the 
    corresponding Google Calendar color ID (1-11). If the color name doesn't match
    any known color, it returns "1" (blue) as the default.
    
    The function also handles the case where the input is already a valid color ID.
    
    Args:
        color_name (str): The name of the color (e.g., "red") or a color ID (e.g., "4")
        
    Returns:
        str: The color ID (1-11) or "1" if not found/invalid
    """
    # Return default blue (1) if no color specified
    if not color_name:
        return "1"
        
    # Normalize color name (lowercase and strip spaces)
    normalized_name = color_name.lower().strip()
    
    # First check if the input is already a valid color ID (1-11)
    if normalized_name.isdigit() and 1 <= int(normalized_name) <= 11:
        return normalized_name
        
    # Otherwise, look up the color name in the mapping
    color_id = CALENDAR_COLOR_MAPPING.get(normalized_name)
    
    # Return default blue (1) if no match found
    return color_id if color_id else "1"


def parse_event_time(time_str: str, default_duration_minutes: int = 60) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse an event time string and return start and end datetimes.
    
    This function handles various time formats including ranges and
    adds a default duration if only a start time is provided.
    
    Args:
        time_str (str): The time string to parse (e.g., "3-4pm")
        default_duration_minutes (int): Default event duration in minutes if no end time is specified
        
    Returns:
        Tuple[Optional[datetime], Optional[datetime]]: The start and end datetimes
    """
    # Get current date and time for reference
    current_datetime = datetime.now()
    
    # Check for time range format (e.g., "3-4pm", "9am-5pm")
    range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', time_str)
    
    if range_match:
        # Extract start and end times
        start_time_str = range_match.group(1)
        end_time_str = range_match.group(2)
        
        # Extract date part (everything before the time range)
        date_part = time_str[:range_match.start()].strip()
        
        # Parse date part
        try:
            if date_part:
                date_dt = parser.parse(date_part, fuzzy=True)
                
                # If year is not specified, assume current year
                if date_dt.year == 1900:
                    date_dt = date_dt.replace(year=current_datetime.year)
                
                # If date is in the past, and no explicit year was mentioned, assume next occurrence
                if date_dt.date() < current_datetime.date() and "year" not in date_part.lower():
                    # If it's a day of week reference, find next occurrence
                    if any(day in date_part.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                        # Find the next occurrence of this day
                        days_ahead = (date_dt.weekday() - current_datetime.weekday()) % 7
                        if days_ahead == 0:  # Same day of week
                            days_ahead = 7
                        date_dt = current_datetime + timedelta(days=days_ahead)
                    else:
                        # Otherwise, just add a day
                        date_dt = date_dt + timedelta(days=1)
            else:
                # If no date part, use today
                date_dt = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception as e:
            logger.warning(f"Failed to parse date part: {e}")
            return None, None
        
        # Parse start and end times
        try:
            start_time = parser.parse(start_time_str)
            end_time = parser.parse(end_time_str)
            
            # Combine date and times
            start_dt = date_dt.replace(
                hour=start_time.hour,
                minute=start_time.minute,
                second=0,
                microsecond=0
            )
            
            end_dt = date_dt.replace(
                hour=end_time.hour,
                minute=end_time.minute,
                second=0,
                microsecond=0
            )
            
            # Handle case where end time is earlier than start time (assume next day)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            return start_dt, end_dt
        except Exception as e:
            logger.warning(f"Failed to parse time range: {e}")
    
    # Handle single time format
    try:
        start_dt = parser.parse(time_str, fuzzy=True)
        
        # If year is not specified, assume current year
        if start_dt.year == 1900:
            start_dt = start_dt.replace(year=current_datetime.year)
        
        # If date is in the past and no explicit year was mentioned, assume next occurrence
        if start_dt < current_datetime and "year" not in time_str.lower():
            # If it's just a time (same day but earlier), keep it today
            if (start_dt.year == current_datetime.year and 
                start_dt.month == current_datetime.month and 
                start_dt.day == current_datetime.day):
                pass  # Keep it today
            # If it's a day of week reference, find next occurrence
            elif any(day in time_str.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                # Find the next occurrence of this day
                days_ahead = (start_dt.weekday() - current_datetime.weekday()) % 7
                if days_ahead == 0:  # Same day of week
                    days_ahead = 7  # Go to next week
                start_dt = current_datetime.replace(hour=start_dt.hour, minute=start_dt.minute) + timedelta(days=days_ahead)
            # Otherwise, if it's a simple time reference like "3pm", move to tomorrow if it's in the past
            elif start_dt.date() == current_datetime.date():
                start_dt = start_dt + timedelta(days=1)
        
        end_dt = start_dt + timedelta(minutes=default_duration_minutes)
        return start_dt, end_dt
    except Exception as e:
        logger.warning(f"Failed to parse time string: {e}")
    
    return None, None


def get_user_timezone() -> str:
    """
    Get the user's timezone from Google Calendar settings.
    
    Returns:
        str: The user's timezone (e.g., "America/New_York") or "UTC" if not found
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.warning("Not authenticated, using UTC timezone")
        return "UTC"
    
    try:
        # Build the Calendar API service
        service = build("calendar", "v3", credentials=credentials)
        
        # Get the calendar settings
        settings = service.settings().list().execute()
        
        # Find the timezone setting
        for setting in settings.get("items", []):
            if setting.get("id") == "timezone":
                return setting.get("value", "UTC")
        
        # If not found, try to get the primary calendar's timezone
        calendar = service.calendars().get(calendarId="primary").execute()
        if "timeZone" in calendar:
            return calendar["timeZone"]
        
        return "UTC"
    except Exception as e:
        logger.warning(f"Failed to get user timezone: {e}")
        return "UTC"


def format_datetime_for_api(dt: datetime, timezone: str = "UTC", all_day: bool = False) -> Dict[str, Any]:
    """
    Format a datetime object for the Google Calendar API.
    
    Args:
        dt (datetime): The datetime to format
        timezone (str): The timezone to use
        all_day (bool): Whether this is an all-day event
        
    Returns:
        Dict[str, Any]: Formatted datetime for the API
    """
    if all_day:
        # For all-day events, use date format
        return {
            "date": dt.strftime("%Y-%m-%d"),
            "timeZone": timezone
        }
    else:
        # For timed events, use dateTime format
        # Ensure the datetime is timezone-aware
        if dt.tzinfo is None:
            try:
                # Try to localize the datetime to the specified timezone
                local_tz = ZoneInfo(timezone)
                dt = dt.replace(tzinfo=local_tz)
            except Exception:
                # If that fails, use UTC
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        
        return {
            "dateTime": dt.isoformat(),
            "timeZone": timezone
        }


def detect_all_day_event(start_dt: datetime, end_dt: datetime) -> bool:
    """
    Detect if an event is likely an all-day event based on its start and end times.
    
    Args:
        start_dt (datetime): The start datetime
        end_dt (datetime): The end datetime
        
    Returns:
        bool: True if the event appears to be an all-day event
    """
    # Check if both times are at midnight
    start_is_midnight = start_dt.hour == 0 and start_dt.minute == 0
    
    # Check if the event spans exactly 24 hours or a multiple of 24 hours
    duration = end_dt - start_dt
    duration_hours = duration.total_seconds() / 3600
    
    # Check if duration is close to a multiple of 24 hours
    is_multiple_of_day = abs(duration_hours % 24) < 0.1
    
    return start_is_midnight and is_multiple_of_day


def extract_attendees_from_text(text: str) -> List[str]:
    """
    Extract potential email addresses of attendees from text.
    
    Args:
        text (str): The text to extract attendees from
        
    Returns:
        List[str]: List of extracted email addresses
    """
    # Simple regex for email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return list(set(re.findall(email_pattern, text)))


def extract_location_from_text(text: str) -> Optional[str]:
    """
    Extract potential location information from text.
    
    Args:
        text (str): The text to extract location from
        
    Returns:
        Optional[str]: Extracted location or None
    """
    # Look for location indicators
    location_patterns = [
        r'(?:at|in|location|place|venue):\s*([^.,:;!?]+)',
        r'(?:at|in)\s+the\s+([^.,:;!?]+)',
        r'(?:meet|meeting)\s+(?:at|in)\s+([^.,:;!?]+)'
    ]
    
    for pattern in location_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0].strip()
    
    return None


def get_user_email() -> str:
    """
    Get the user's email address from Gmail profile.
    
    Returns:
        str: The user's email address or empty string if not found
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.warning("Not authenticated, cannot get user email")
        return ""
    
    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        # Get the profile information
        profile = service.users().getProfile(userId="me").execute()
        
        # Return the email address
        return profile.get("emailAddress", "")
    except Exception as e:
        logger.warning(f"Failed to get user email: {e}")
        return ""


def create_calendar_event_object(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    color_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a calendar event object with proper date/time handling.
    
    This function handles the parsing of date/time strings
    and creates a properly formatted event object for the Google Calendar API.
    
    Args:
        summary (str): The title/summary of the event
        start_time (str): The start time of the event (ISO format or simple date/time)
        end_time (Optional[str]): The end time of the event (ISO format or simple date/time)
        description (Optional[str]): Description or notes for the event
        location (Optional[str]): Location of the event
        attendees (Optional[List[str]]): List of email addresses of attendees
        color_id (Optional[str]): Color ID for the event (1-11 or color name)
        
    Returns:
        Dict[str, Any]: The event object with properly formatted date/time information
    """
    # Get user's timezone
    user_timezone = get_user_timezone()
    
    # Get current date and time for reference
    current_datetime = datetime.now()
    
    # Parse start time
    if "-" in start_time and not end_time:
        # Handle case where start_time contains a range (e.g., "3-4pm")
        try:
            start_dt, end_dt = parse_event_time(start_time)
        except Exception as e:
            logger.warning(f"Failed to parse time range: {e}")
            start_dt, end_dt = None, None
    else:
        # Parse start time using dateutil.parser
        try:
            start_dt = parser.parse(start_time, fuzzy=True)
            
            # If year is not specified, assume current year
            if start_dt.year == 1900:
                start_dt = start_dt.replace(year=current_datetime.year)
                
            # If month/day might be ambiguous and in the past, assume next occurrence
            if start_dt and start_dt < current_datetime and (start_time.lower().find("year") == -1):
                # If it's just a time (same day but earlier), assume today
                if (start_dt.year == current_datetime.year and 
                    start_dt.month == current_datetime.month and 
                    start_dt.day == current_datetime.day):
                    pass  # Keep it today
                # Otherwise, try to find the next occurrence
                elif "day" in start_time.lower() or "week" in start_time.lower() or "month" in start_time.lower():
                    pass  # Keep as is, as it likely has explicit day/week/month references
                else:
                    # For simple time references like "3pm", move to tomorrow if it's in the past
                    if start_dt.date() == current_datetime.date():
                        start_dt = start_dt + timedelta(days=1)
        except Exception as e:
            logger.warning(f"Failed to parse start time: {e}")
            start_dt = None
        
        # Parse end time if provided
        if end_time:
            try:
                end_dt = parser.parse(end_time, fuzzy=True)
                
                # If year is not specified, assume current year
                if end_dt.year == 1900:
                    end_dt = end_dt.replace(year=current_datetime.year)
                    
                # If end time is earlier than start time, assume next day
                if start_dt and end_dt and end_dt < start_dt:
                    end_dt = end_dt + timedelta(days=1)
            except Exception as e:
                logger.warning(f"Failed to parse end time: {e}")
                end_dt = None
        else:
            # Default to 1 hour duration
            end_dt = start_dt + timedelta(hours=1) if start_dt else None
    
    # Check if parsing was successful
    if not start_dt:
        return {
            "error": f"Could not parse start time: {start_time}",
            "parsed_start": None,
            "parsed_end": None,
            "current_datetime": current_datetime.isoformat()
        }
    
    if not end_dt:
        return {
            "error": f"Could not parse end time: {end_time}",
            "parsed_start": start_dt.isoformat(),
            "parsed_end": None,
            "current_datetime": current_datetime.isoformat()
        }
    
    # Detect if this is an all-day event
    all_day = detect_all_day_event(start_dt, end_dt)
    
    # Format for Google Calendar API
    event_body = {
        'summary': summary,
        'start': format_datetime_for_api(start_dt, user_timezone, all_day),
        'end': format_datetime_for_api(end_dt, user_timezone, all_day),
    }
    
    # Add optional fields if provided
    if description:
        event_body['description'] = description
    
    if location:
        event_body['location'] = location
    
    # Handle attendees - always include the user's email
    event_attendees = []
    
    # Get the user's email
    user_email = get_user_email()
    
    # Add user's email as an attendee if we have it
    if user_email:
        event_attendees.append({'email': user_email})
    
    # Add other attendees if provided
    if attendees:
        for email in attendees:
            # Avoid adding duplicates
            if email != user_email:
                event_attendees.append({'email': email})
    
    # Only add attendees if we have at least one
    if event_attendees:
        event_body['attendees'] = event_attendees
    
    # Add color_id if provided
    if color_id:
        event_body['colorId'] = color_id
    
    # Add parsed information for reference
    event_body['_parsed'] = {
        'start_dt': start_dt.isoformat(),
        'end_dt': end_dt.isoformat(),
        'timezone': user_timezone,
        'all_day': all_day,
        'current_datetime': current_datetime.isoformat()
    }
    
    return event_body


def get_available_calendar_colors() -> Dict[str, Dict[str, str]]:
    """
    Get the available calendar colors from the Google Calendar API.
    
    Returns:
        Dict[str, Dict[str, str]]: Dictionary of available colors with their names and hex values
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.warning("Not authenticated, cannot get calendar colors")
        return {}
    
    try:
        # Build the Calendar API service
        service = build("calendar", "v3", credentials=credentials)
        
        # Get the colors
        colors = service.colors().get().execute()
        
        return colors.get("event", {})
    except Exception as e:
        logger.warning(f"Failed to get calendar colors: {e}")
        return {}


def get_free_busy_info(
    start_time: Union[str, datetime],
    end_time: Union[str, datetime],
    calendar_ids: List[str] = ["primary"]
) -> Dict[str, Any]:
    """
    Get free/busy information for the specified time range.
    
    Args:
        start_time (Union[str, datetime]): The start time
        end_time (Union[str, datetime]): The end time
        calendar_ids (List[str]): List of calendar IDs to check
        
    Returns:
        Dict[str, Any]: Free/busy information
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.warning("Not authenticated, cannot get free/busy information")
        return {"error": "Not authenticated"}
    
    try:
        # Parse times if they are strings
        if isinstance(start_time, str):
            try:
                start_dt = parser.parse(start_time, fuzzy=True)
                # If year is not specified, assume current year
                if start_dt.year == 1900:
                    start_dt = start_dt.replace(year=datetime.now().year)
            except Exception as e:
                logger.warning(f"Failed to parse start time: {e}")
                return {"error": f"Could not parse start time: {start_time}"}
        else:
            start_dt = start_time
        
        if isinstance(end_time, str):
            try:
                end_dt = parser.parse(end_time, fuzzy=True)
                # If year is not specified, assume current year
                if end_dt.year == 1900:
                    end_dt = end_dt.replace(year=datetime.now().year)
                # If end time is earlier than start time, assume next day
                if end_dt < start_dt:
                    end_dt = end_dt + timedelta(days=1)
            except Exception as e:
                logger.warning(f"Failed to parse end time: {e}")
                return {"error": f"Could not parse end time: {end_time}"}
        else:
            end_dt = end_time
        
        # Build the Calendar API service
        service = build("calendar", "v3", credentials=credentials)
        
        # Get user email
        profile = service.calendarList().get(calendarId="primary").execute()
        user_email = profile.get("id", "")
        
        # Prepare request body
        body = {
            "timeMin": start_dt.isoformat(),
            "timeMax": end_dt.isoformat(),
            "items": [{"id": calendar_id} for calendar_id in calendar_ids]
        }
        
        # Get free/busy information
        free_busy = service.freebusy().query(body=body).execute()
        
        return {
            "calendars": free_busy.get("calendars", {}),
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "user_email": user_email
        }
    except Exception as e:
        logger.warning(f"Failed to get free/busy information: {e}")
        return {"error": f"Failed to get free/busy information: {e}"}


def suggest_meeting_times(
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    duration_minutes: int = 60,
    working_hours: Tuple[int, int] = (9, 17),  # 9am to 5pm
    calendar_ids: List[str] = ["primary"]
) -> List[Dict[str, Any]]:
    """
    Suggest available meeting times within a date range.
    
    Args:
        start_date (Union[str, datetime]): The start date of the range to check
        end_date (Union[str, datetime]): The end date of the range to check
        duration_minutes (int): The desired meeting duration in minutes
        working_hours (Tuple[int, int]): The working hours as (start_hour, end_hour)
        calendar_ids (List[str]): List of calendar IDs to check
        
    Returns:
        List[Dict[str, Any]]: List of suggested meeting times
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.warning("Not authenticated, cannot suggest meeting times")
        return [{"error": "Not authenticated"}]
    
    try:
        # Parse dates if they are strings
        if isinstance(start_date, str):
            try:
                start_dt = parser.parse(start_date, fuzzy=True)
                # If year is not specified, assume current year
                if start_dt.year == 1900:
                    start_dt = start_dt.replace(year=datetime.now().year)
                # If date is in the past and no explicit year was mentioned, assume next occurrence
                if start_dt < datetime.now() and "year" not in start_date.lower():
                    # If it's a day of week reference, find next occurrence
                    if any(day in start_date.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                        # Find the next occurrence of this day
                        current_datetime = datetime.now()
                        days_ahead = (start_dt.weekday() - current_datetime.weekday()) % 7
                        if days_ahead == 0:  # Same day of week
                            days_ahead = 7  # Go to next week
                        start_dt = current_datetime + timedelta(days=days_ahead)
            except Exception as e:
                logger.warning(f"Failed to parse start date: {e}")
                return [{"error": f"Could not parse start date: {start_date}"}]
        else:
            start_dt = start_date
        
        if isinstance(end_date, str):
            try:
                end_dt = parser.parse(end_date, fuzzy=True)
                # If year is not specified, assume current year
                if end_dt.year == 1900:
                    end_dt = end_dt.replace(year=datetime.now().year)
                # If date is in the past and no explicit year was mentioned, assume next occurrence
                if end_dt < datetime.now() and "year" not in end_date.lower():
                    # If it's a day of week reference, find next occurrence
                    if any(day in end_date.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                        # Find the next occurrence of this day
                        current_datetime = datetime.now()
                        days_ahead = (end_dt.weekday() - current_datetime.weekday()) % 7
                        if days_ahead == 0:  # Same day of week
                            days_ahead = 7  # Go to next week
                        end_dt = current_datetime + timedelta(days=days_ahead)
                # If end date is earlier than start date, assume next day/week
                if end_dt < start_dt:
                    # If they're the same day of week, assume next week
                    if end_dt.weekday() == start_dt.weekday():
                        end_dt = end_dt + timedelta(days=7)
                    else:
                        # Otherwise, find the next occurrence after start_dt
                        days_ahead = (end_dt.weekday() - start_dt.weekday()) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                        end_dt = start_dt + timedelta(days=days_ahead)
            except Exception as e:
                logger.warning(f"Failed to parse end date: {e}")
                return [{"error": f"Could not parse end date: {end_date}"}]
        else:
            end_dt = end_date
        
        # Set to beginning of day for start and end of day for end
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Get free/busy information
        free_busy_info = get_free_busy_info(start_dt, end_dt, calendar_ids)
        
        if "error" in free_busy_info:
            return [{"error": free_busy_info["error"]}]
        
        # Get busy periods
        busy_periods = []
        for calendar_id, calendar_info in free_busy_info.get("calendars", {}).items():
            for busy in calendar_info.get("busy", []):
                start = parser.parse(busy["start"])
                end = parser.parse(busy["end"])
                busy_periods.append((start, end))
        
        # Sort busy periods
        busy_periods.sort(key=lambda x: x[0])
        
        # Get user's timezone
        user_timezone = get_user_timezone()
        
        # Generate suggested times
        suggested_times = []
        current_date = start_dt
        
        while current_date <= end_dt:
            # Skip weekends (0 = Monday, 6 = Sunday)
            if current_date.weekday() >= 5:  # Saturday or Sunday
                current_date += timedelta(days=1)
                current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                continue
            
            # Set working hours for the day
            day_start = current_date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
            day_end = current_date.replace(hour=working_hours[1], minute=0, second=0, microsecond=0)
            
            # Skip if the day is already past
            if day_end < datetime.now():
                current_date += timedelta(days=1)
                current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                continue
            
            # Check each 30-minute slot
            slot_start = day_start
            while slot_start < day_end:
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Check if slot is available
                is_available = True
                for busy_start, busy_end in busy_periods:
                    # If there's any overlap with a busy period, the slot is not available
                    if (slot_start < busy_end and slot_end > busy_start):
                        is_available = False
                        break
                
                if is_available:
                    # Add to suggested times
                    suggested_times.append({
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                        "formatted": {
                            "date": slot_start.strftime("%A, %B %d, %Y"),
                            "time": f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                        }
                    })
                
                # Move to next slot (30-minute increments)
                slot_start += timedelta(minutes=30)
            
            # Move to next day
            current_date += timedelta(days=1)
            current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Limit to top 10 suggestions
        return suggested_times[:10]
    
    except Exception as e:
        logger.warning(f"Failed to suggest meeting times: {e}")
        return [{"error": f"Failed to suggest meeting times: {e}"}] 