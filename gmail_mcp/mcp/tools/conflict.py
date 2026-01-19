"""
Calendar Conflict Detection Tools Module

Handles multi-calendar awareness and conflict detection.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

import dateutil.parser as parser

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_calendar_service
from gmail_mcp.utils.date_parser import parse_natural_date, parse_working_hours, parse_duration, DATE_PARSING_HINT
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.calendar.processor import get_user_timezone

logger = get_logger(__name__)


def setup_conflict_tools(mcp: FastMCP) -> None:
    """Set up calendar conflict detection tools on the FastMCP application."""

    @mcp.tool()
    def list_calendars() -> Dict[str, Any]:
        """
        List all calendars accessible to the user.

        Returns a list of all calendars including shared calendars,
        subscribed calendars, and the primary calendar.

        Returns:
            Dict[str, Any]: List of calendars with IDs and details
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])

            formatted_calendars = []
            for cal in calendars:
                formatted_calendars.append({
                    "id": cal.get("id"),
                    "summary": cal.get("summary"),
                    "description": cal.get("description", ""),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole"),
                    "background_color": cal.get("backgroundColor"),
                    "selected": cal.get("selected", True),
                    "time_zone": cal.get("timeZone")
                })

            return {
                "success": True,
                "count": len(formatted_calendars),
                "calendars": formatted_calendars
            }

        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            return {"success": False, "error": f"Failed to list calendars: {e}"}

    @mcp.tool()
    def check_conflicts(
        start_time: str,
        end_time: str,
        calendar_ids: Optional[List[str]] = None,
        exclude_all_day: bool = True
    ) -> Dict[str, Any]:
        """
        Check for calendar conflicts in a given time range.

        Checks across multiple calendars for events that would conflict
        with the proposed time slot.

        Args:
            start_time (str): Start time in ISO format or natural language
            end_time (str): End time in ISO format or natural language
            calendar_ids (List[str], optional): Specific calendar IDs to check.
                                               If not provided, checks all calendars.
            exclude_all_day (bool): Exclude all-day events from conflict check (default: True)

        Returns:
            Dict[str, Any]: Conflict analysis including:
                - has_conflicts: Whether any conflicts were found
                - conflicts: List of conflicting events
                - calendars_checked: List of calendars that were checked

        Example usage:
        1. Check if a time slot is free:
           check_conflicts(start_time="tomorrow 2pm", end_time="tomorrow 3pm")

        2. Check specific calendars:
           check_conflicts(
               start_time="2024-01-15T14:00:00",
               end_time="2024-01-15T15:00:00",
               calendar_ids=["primary", "work@group.calendar.google.com"]
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)
            user_timezone = get_user_timezone()

            # Parse times using centralized NLP parser
            start_dt = parse_natural_date(start_time, timezone=user_timezone)
            if not start_dt:
                return {
                    "success": False,
                    "error": f"Could not parse start time: {start_time}",
                    "hint": DATE_PARSING_HINT
                }

            end_dt = parse_natural_date(end_time, timezone=user_timezone)
            if not end_dt:
                return {
                    "success": False,
                    "error": f"Could not parse end time: {end_time}",
                    "hint": DATE_PARSING_HINT
                }

            # Handle timezone
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            # Get calendars to check
            if not calendar_ids:
                calendar_list = service.calendarList().list().execute()
                calendar_ids = [cal["id"] for cal in calendar_list.get("items", []) if cal.get("selected", True)]

            time_min = start_dt.isoformat()
            time_max = end_dt.isoformat()

            conflicts = []
            calendars_checked = []

            for cal_id in calendar_ids:
                try:
                    # Get calendar info
                    cal_info = service.calendarList().get(calendarId=cal_id).execute()
                    cal_name = cal_info.get("summary", cal_id)
                    calendars_checked.append({
                        "id": cal_id,
                        "name": cal_name
                    })

                    # Get events in the time range
                    events_result = service.events().list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime"
                    ).execute()

                    for event in events_result.get("items", []):
                        # Check if it's an all-day event
                        is_all_day = "date" in event.get("start", {})

                        if exclude_all_day and is_all_day:
                            continue

                        # Check for actual overlap
                        event_start = event.get("start", {})
                        event_end = event.get("end", {})

                        if is_all_day:
                            event_start_str = event_start.get("date")
                            event_end_str = event_end.get("date")
                        else:
                            event_start_str = event_start.get("dateTime")
                            event_end_str = event_end.get("dateTime")

                        conflicts.append({
                            "calendar_id": cal_id,
                            "calendar_name": cal_name,
                            "event_id": event.get("id"),
                            "summary": event.get("summary", "Untitled"),
                            "start": event_start_str,
                            "end": event_end_str,
                            "is_all_day": is_all_day,
                            "status": event.get("status"),
                            "event_link": event.get("htmlLink", "")
                        })

                except Exception as e:
                    logger.warning(f"Could not check calendar {cal_id}: {e}")

            return {
                "success": True,
                "has_conflicts": len(conflicts) > 0,
                "conflict_count": len(conflicts),
                "conflicts": conflicts,
                "calendars_checked": calendars_checked,
                "time_range": {
                    "start": time_min,
                    "end": time_max
                }
            }

        except Exception as e:
            logger.error(f"Failed to check conflicts: {e}")
            return {"success": False, "error": f"Failed to check conflicts: {e}"}

    @mcp.tool()
    def find_free_time(
        date: str,
        duration_minutes: int = 60,
        duration: Optional[str] = None,
        calendar_ids: Optional[List[str]] = None,
        working_hours: str = "9-17",
        exclude_all_day: bool = True
    ) -> Dict[str, Any]:
        """
        Find free time slots on a given date across multiple calendars.

        Analyzes all specified calendars to find gaps where a meeting
        of the specified duration could be scheduled.

        Args:
            date (str): The date to check (e.g., "tomorrow", "2024-01-15")
            duration_minutes (int): Required duration in minutes (default: 60)
            duration (str, optional): Duration as natural language (e.g., "1 hour", "90 minutes").
                                     If provided, overrides duration_minutes.
            calendar_ids (List[str], optional): Calendars to check. If not provided,
                                               checks all selected calendars.
            working_hours (str): Working hours (e.g., "9-17", "9am-5pm", "9am to 5pm")
            exclude_all_day (bool): Ignore all-day events (default: True)

        Returns:
            Dict[str, Any]: Available time slots

        Example usage:
        1. Find 30-minute slots tomorrow:
           find_free_time(date="tomorrow", duration_minutes=30)

        2. Find slots with custom working hours:
           find_free_time(
               date="next monday",
               duration="1 hour",
               working_hours="9am to 5pm"
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)
            user_tz = get_user_timezone()

            # Parse date using centralized NLP parser
            target_dt = parse_natural_date(date, timezone=user_tz, prefer_future=True)
            if not target_dt:
                return {
                    "success": False,
                    "error": f"Could not parse date: {date}",
                    "hint": DATE_PARSING_HINT
                }
            target_date = target_dt.date()

            # Parse duration (NLP string takes precedence)
            if duration:
                actual_duration = parse_duration(duration)
            else:
                actual_duration = duration_minutes

            # Parse working hours using NLP parser
            work_start_hour, work_end_hour = parse_working_hours(working_hours)

            # Create time boundaries
            day_start = datetime.combine(target_date, datetime.min.time().replace(hour=work_start_hour))
            day_end = datetime.combine(target_date, datetime.min.time().replace(hour=work_end_hour))

            # Add timezone info
            import pytz
            try:
                tz = pytz.timezone(user_tz)
                day_start = tz.localize(day_start)
                day_end = tz.localize(day_end)
            except Exception:
                day_start = day_start.replace(tzinfo=timezone.utc)
                day_end = day_end.replace(tzinfo=timezone.utc)

            # Get calendars to check
            if not calendar_ids:
                calendar_list = service.calendarList().list().execute()
                calendar_ids = [cal["id"] for cal in calendar_list.get("items", []) if cal.get("selected", True)]

            # Collect all busy times
            busy_times = []

            for cal_id in calendar_ids:
                try:
                    events_result = service.events().list(
                        calendarId=cal_id,
                        timeMin=day_start.isoformat(),
                        timeMax=day_end.isoformat(),
                        singleEvents=True,
                        orderBy="startTime"
                    ).execute()

                    for event in events_result.get("items", []):
                        is_all_day = "date" in event.get("start", {})

                        if exclude_all_day and is_all_day:
                            continue

                        if is_all_day:
                            # All-day event blocks entire day
                            busy_times.append((day_start, day_end))
                        else:
                            event_start = parser.parse(event["start"]["dateTime"])
                            event_end = parser.parse(event["end"]["dateTime"])
                            busy_times.append((event_start, event_end))

                except Exception as e:
                    logger.warning(f"Could not check calendar {cal_id}: {e}")

            # Sort and merge overlapping busy times
            busy_times.sort(key=lambda x: x[0])
            merged_busy = []
            for start, end in busy_times:
                if merged_busy and start <= merged_busy[-1][1]:
                    # Overlapping, extend the previous busy time
                    merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], end))
                else:
                    merged_busy.append((start, end))

            # Find free slots
            free_slots = []
            current_time = day_start

            for busy_start, busy_end in merged_busy:
                if current_time < busy_start:
                    # There's a gap before this busy time
                    gap_duration = (busy_start - current_time).total_seconds() / 60
                    if gap_duration >= actual_duration:
                        free_slots.append({
                            "start": current_time.isoformat(),
                            "end": busy_start.isoformat(),
                            "duration_minutes": int(gap_duration),
                            "start_display": current_time.strftime("%I:%M %p"),
                            "end_display": busy_start.strftime("%I:%M %p")
                        })
                current_time = max(current_time, busy_end)

            # Check for gap after last busy time
            if current_time < day_end:
                gap_duration = (day_end - current_time).total_seconds() / 60
                if gap_duration >= actual_duration:
                    free_slots.append({
                        "start": current_time.isoformat(),
                        "end": day_end.isoformat(),
                        "duration_minutes": int(gap_duration),
                        "start_display": current_time.strftime("%I:%M %p"),
                        "end_display": day_end.strftime("%I:%M %p")
                    })

            return {
                "success": True,
                "date": str(target_date),
                "working_hours": f"{work_start_hour}:00 - {work_end_hour}:00",
                "duration_required": actual_duration,
                "free_slots": free_slots,
                "slot_count": len(free_slots),
                "calendars_checked": len(calendar_ids)
            }

        except Exception as e:
            logger.error(f"Failed to find free time: {e}")
            return {"success": False, "error": f"Failed to find free time: {e}"}

    @mcp.tool()
    def get_daily_agenda(
        date: Optional[str] = None,
        calendar_ids: Optional[List[str]] = None,
        include_all_day: bool = True
    ) -> Dict[str, Any]:
        """
        Get a consolidated daily agenda across all calendars.

        Combines events from multiple calendars into a single
        chronological view for the day.

        Args:
            date (str, optional): The date to get agenda for (default: today)
            calendar_ids (List[str], optional): Calendars to include.
                                               If not provided, uses all selected.
            include_all_day (bool): Include all-day events (default: True)

        Returns:
            Dict[str, Any]: Consolidated agenda for the day

        Example usage:
        1. Get today's agenda:
           get_daily_agenda()

        2. Get tomorrow's agenda:
           get_daily_agenda(date="tomorrow")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            # Get user timezone
            user_tz = get_user_timezone()

            # Parse date using centralized NLP parser
            if date:
                target_dt = parse_natural_date(date, timezone=user_tz, prefer_future=True)
                if not target_dt:
                    return {
                        "success": False,
                        "error": f"Could not parse date: {date}",
                        "hint": DATE_PARSING_HINT
                    }
                target_date = target_dt.date()
            else:
                target_date = datetime.now().date()

            # Create time boundaries for the day
            day_start = datetime.combine(target_date, datetime.min.time())
            day_end = datetime.combine(target_date, datetime.max.time())

            import pytz
            try:
                tz = pytz.timezone(user_tz)
                day_start = tz.localize(day_start)
                day_end = tz.localize(day_end)
            except Exception:
                day_start = day_start.replace(tzinfo=timezone.utc)
                day_end = day_end.replace(tzinfo=timezone.utc)

            # Get calendars to check
            if not calendar_ids:
                calendar_list = service.calendarList().list().execute()
                calendar_ids = [cal["id"] for cal in calendar_list.get("items", []) if cal.get("selected", True)]

            # Collect events from all calendars
            all_day_events = []
            timed_events = []
            calendar_names = {}

            for cal_id in calendar_ids:
                try:
                    cal_info = service.calendarList().get(calendarId=cal_id).execute()
                    calendar_names[cal_id] = cal_info.get("summary", cal_id)

                    events_result = service.events().list(
                        calendarId=cal_id,
                        timeMin=day_start.isoformat(),
                        timeMax=day_end.isoformat(),
                        singleEvents=True,
                        orderBy="startTime"
                    ).execute()

                    for event in events_result.get("items", []):
                        is_all_day = "date" in event.get("start", {})

                        event_data = {
                            "event_id": event.get("id"),
                            "summary": event.get("summary", "Untitled"),
                            "calendar_id": cal_id,
                            "calendar_name": calendar_names[cal_id],
                            "location": event.get("location", ""),
                            "description": event.get("description", ""),
                            "status": event.get("status"),
                            "event_link": event.get("htmlLink", ""),
                            "is_all_day": is_all_day
                        }

                        if is_all_day:
                            if include_all_day:
                                event_data["start"] = event["start"]["date"]
                                event_data["end"] = event["end"]["date"]
                                all_day_events.append(event_data)
                        else:
                            start_dt = parser.parse(event["start"]["dateTime"])
                            end_dt = parser.parse(event["end"]["dateTime"])

                            event_data["start"] = event["start"]["dateTime"]
                            event_data["end"] = event["end"]["dateTime"]
                            event_data["start_display"] = start_dt.strftime("%I:%M %p")
                            event_data["end_display"] = end_dt.strftime("%I:%M %p")
                            event_data["duration_minutes"] = int((end_dt - start_dt).total_seconds() / 60)
                            event_data["_sort_key"] = start_dt

                            timed_events.append(event_data)

                except Exception as e:
                    logger.warning(f"Could not get events from calendar {cal_id}: {e}")

            # Sort timed events chronologically
            timed_events.sort(key=lambda x: x.get("_sort_key", datetime.min))

            # Remove sort key from output
            for event in timed_events:
                event.pop("_sort_key", None)

            return {
                "success": True,
                "date": str(target_date),
                "date_display": target_date.strftime("%A, %B %d, %Y"),
                "timezone": user_tz,
                "all_day_events": all_day_events,
                "timed_events": timed_events,
                "total_events": len(all_day_events) + len(timed_events),
                "calendars_included": list(calendar_names.values())
            }

        except Exception as e:
            logger.error(f"Failed to get daily agenda: {e}")
            return {"success": False, "error": f"Failed to get daily agenda: {e}"}
