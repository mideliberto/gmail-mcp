"""
Calendar Tools Module

Handles Google Calendar operations: create, list, update, delete, suggest times, detect events.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

import dateutil.parser as parser

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service, get_calendar_service
from gmail_mcp.utils.date_parser import parse_natural_date, parse_recurrence_pattern, parse_working_hours, parse_duration, DATE_PARSING_HINT
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.gmail.processor import parse_email_message, extract_entities
from gmail_mcp.calendar.processor import (
    get_user_timezone,
    create_calendar_event_object,
    get_color_id_from_name,
    build_rrule
)

logger = get_logger(__name__)


def setup_calendar_tools(mcp: FastMCP) -> None:
    """Set up calendar tools on the FastMCP application."""

    @mcp.tool()
    def create_calendar_event(
        summary: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        color_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new event in the user's Google Calendar.

        This tool creates a new calendar event with the specified details.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            summary (str): The title/summary of the event
            start_time (str): The start time of the event in ISO format (YYYY-MM-DDTHH:MM:SS) or simple date/time format ("5pm", "tomorrow 3pm")
            end_time (str, optional): The end time of the event. If not provided, you should ask the user for this information.
            description (str, optional): Description or notes for the event. If not provided, leave it blank.
            location (str, optional): Location of the event. If not provided, leave it blank.
            attendees (List[str], optional): List of email addresses of attendees. The current user will always be added automatically.
            color_name (str, optional): Color name for the event (e.g., "red", "blue", "green", "purple", "yellow", "orange")

        Returns:
            Dict[str, Any]: The result of the operation, including:
                - success: Whether the operation was successful
                - message: A message describing the result
                - event_id: The ID of the created event
                - event_link: Direct link to the event in Google Calendar
                - missing_info: List of missing information that should be asked from the user

        Example usage:
        1. Create a simple event:
           create_calendar_event(summary="Team Meeting", start_time="2023-12-01T14:00:00")

        2. Create a detailed event:
           create_calendar_event(
               summary="Project Kickoff",
               start_time="next monday at 10am",
               end_time="next monday at 11:30am",
               description="Initial meeting to discuss project scope",
               location="Conference Room A",
               attendees=["colleague@example.com", "manager@example.com"],
               color_name="blue"
           )
        """
        credentials = get_credentials()
        if not credentials:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first.",
                "missing_info": []
            }

        try:
            service = get_calendar_service(credentials)

            if color_name:
                color_id = get_color_id_from_name(color_name)
            else:
                color_id = "1"

            event_body = create_calendar_event_object(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                color_id=color_id
            )

            if "error" in event_body:
                missing_info = []
                if not end_time:
                    missing_info.append("end_time")

                return {
                    "success": False,
                    "error": event_body["error"],
                    "parsed_start": event_body.get("parsed_start"),
                    "parsed_end": event_body.get("parsed_end"),
                    "current_datetime": event_body.get("current_datetime"),
                    "missing_info": missing_info
                }

            created_event = service.events().insert(calendarId="primary", body=event_body).execute()

            event_id = created_event.get("id", "")
            event_link = created_event.get("htmlLink", "")

            return {
                "success": True,
                "message": "Event created successfully.",
                "event_id": event_id,
                "event_link": event_link,
                "event_details": {
                    "summary": summary,
                    "start": event_body.get("start", {}),
                    "end": event_body.get("end", {}),
                    "timezone": event_body.get("_parsed", {}).get("timezone", "UTC"),
                    "all_day": event_body.get("_parsed", {}).get("all_day", False),
                    "current_datetime": event_body.get("_parsed", {}).get("current_datetime", "")
                },
                "missing_info": []
            }

        except HttpError as e:
            logger.error(f"Google Calendar API error creating event: {e}")
            missing_info = []
            if not end_time:
                missing_info.append("end_time")
            return {
                "success": False,
                "error": f"Calendar API error: {e.reason if hasattr(e, 'reason') else str(e)}",
                "missing_info": missing_info
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid input for calendar event: {e}")
            missing_info = []
            if not end_time:
                missing_info.append("end_time")
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "missing_info": missing_info
            }
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            missing_info = []
            if not end_time:
                missing_info.append("end_time")
            return {
                "success": False,
                "error": f"Failed to create calendar event: {e}",
                "missing_info": missing_info
            }

    @mcp.tool()
    def create_recurring_event(
        summary: str,
        start_time: str,
        frequency: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        color_name: Optional[str] = None,
        interval: int = 1,
        count: Optional[int] = None,
        until: Optional[str] = None,
        by_day: Optional[List[str]] = None,
        recurrence_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a recurring event in the user's Google Calendar.

        This tool creates a recurring calendar event with customizable recurrence rules.
        It supports daily, weekly, monthly, and yearly patterns.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            summary (str): The title/summary of the event
            start_time (str): The start time of the first occurrence (ISO format or natural language)
            frequency (str, optional): How often the event repeats - "DAILY", "WEEKLY", "MONTHLY", or "YEARLY"
            end_time (str, optional): The end time of each occurrence. Defaults to 1 hour after start.
            description (str, optional): Description or notes for the event
            location (str, optional): Location of the event
            attendees (List[str], optional): List of email addresses of attendees
            color_name (str, optional): Color name for the event (e.g., "red", "blue", "green")
            interval (int, optional): How often the event repeats (e.g., 2 = every 2 weeks). Defaults to 1.
            count (int, optional): Number of occurrences. Cannot be used with 'until'.
            until (str, optional): End date for recurrence (YYYY-MM-DD). Cannot be used with 'count'.
            by_day (List[str], optional): Days of week for WEEKLY (e.g., ["MO", "WE", "FR"])
            recurrence_pattern (str, optional): Natural language recurrence pattern (e.g., "every weekday",
                "weekly until march", "every monday and wednesday"). If provided, overrides frequency/interval/by_day.

        Returns:
            Dict[str, Any]: The result including:
                - success: Whether the operation was successful
                - event_id: The ID of the created recurring event
                - event_link: Direct link to the event in Google Calendar
                - recurrence: The RRULE string used

        Example usage:
        1. Daily standup for 2 weeks:
           create_recurring_event(
               summary="Daily Standup",
               start_time="2024-01-15T09:00:00",
               frequency="DAILY",
               count=10
           )

        2. Weekly team meeting on Mon/Wed/Fri:
           create_recurring_event(
               summary="Team Sync",
               start_time="next monday at 10am",
               frequency="WEEKLY",
               by_day=["MO", "WE", "FR"],
               until="2024-06-30"
           )

        3. Monthly review meeting:
           create_recurring_event(
               summary="Monthly Review",
               start_time="2024-02-01T14:00:00",
               frequency="MONTHLY",
               interval=1,
               count=12
           )

        4. Bi-weekly 1:1 meeting:
           create_recurring_event(
               summary="1:1 with Manager",
               start_time="next tuesday at 2pm",
               frequency="WEEKLY",
               interval=2
           )

        5. Using natural language recurrence pattern:
           create_recurring_event(
               summary="Daily Standup",
               start_time="tomorrow 9am",
               recurrence_pattern="every weekday"
           )
        """
        credentials = get_credentials()
        if not credentials:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first."
            }

        try:
            # Parse recurrence pattern if provided
            if recurrence_pattern:
                parsed_pattern = parse_recurrence_pattern(recurrence_pattern)
                if not parsed_pattern:
                    return {
                        "success": False,
                        "error": f"Could not parse recurrence pattern: {recurrence_pattern}"
                    }
                # Use parsed values, but allow explicit overrides
                frequency = frequency or parsed_pattern.get('frequency')
                if parsed_pattern.get('interval', 1) > 1 and interval == 1:
                    interval = parsed_pattern.get('interval', 1)
                if parsed_pattern.get('by_day') and not by_day:
                    by_day = parsed_pattern.get('by_day')
                if parsed_pattern.get('count') and not count:
                    count = parsed_pattern.get('count')
                if parsed_pattern.get('until') and not until:
                    until = parsed_pattern.get('until')

            # Require frequency at this point
            if not frequency:
                return {
                    "success": False,
                    "error": "Either 'frequency' or 'recurrence_pattern' must be provided."
                }

            # Build the recurrence rule
            try:
                rrule = build_rrule(
                    frequency=frequency,
                    interval=interval,
                    count=count,
                    until=until,
                    by_day=by_day
                )
            except ValueError as e:
                return {
                    "success": False,
                    "error": f"Invalid recurrence rule: {e}"
                }

            service = get_calendar_service(credentials)

            if color_name:
                color_id = get_color_id_from_name(color_name)
            else:
                color_id = "1"

            # Create the base event object
            event_body = create_calendar_event_object(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                color_id=color_id
            )

            if "error" in event_body:
                return {
                    "success": False,
                    "error": event_body["error"],
                    "parsed_start": event_body.get("parsed_start"),
                    "parsed_end": event_body.get("parsed_end")
                }

            # Add recurrence rule
            event_body["recurrence"] = [rrule]

            # Remove internal _parsed field before sending to API
            event_body.pop("_parsed", None)

            created_event = service.events().insert(calendarId="primary", body=event_body).execute()

            event_id = created_event.get("id", "")
            event_link = created_event.get("htmlLink", "")

            return {
                "success": True,
                "message": "Recurring event created successfully.",
                "event_id": event_id,
                "event_link": event_link,
                "recurrence": rrule,
                "event_details": {
                    "summary": summary,
                    "frequency": frequency,
                    "interval": interval,
                    "count": count,
                    "until": until,
                    "by_day": by_day
                }
            }

        except HttpError as e:
            logger.error(f"Google Calendar API error creating recurring event: {e}")
            return {
                "success": False,
                "error": f"Calendar API error: {e.reason if hasattr(e, 'reason') else str(e)}"
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid input for recurring event: {e}")
            return {
                "success": False,
                "error": f"Invalid input: {e}"
            }
        except Exception as e:
            logger.error(f"Failed to create recurring event: {e}")
            return {
                "success": False,
                "error": f"Failed to create recurring event: {e}"
            }

    @mcp.tool()
    def detect_events_from_email(email_id: str) -> Dict[str, Any]:
        """
        Detect potential calendar events from an email.

        This tool analyzes an email to identify potential calendar events
        based on dates, times, and contextual clues.

        Prerequisites:
        - The user must be authenticated
        - You need an email ID from list_emails() or search_emails()

        Args:
            email_id (str): The ID of the email to analyze for events

        Returns:
            Dict[str, Any]: The detected events including:
                - success: Whether the operation was successful
                - events: List of potential events with details
                - email_link: Link to the original email

        Example usage:
        1. Get an email: email = get_email(email_id="...")
        2. Detect events: events = detect_events_from_email(email_id="...")
        3. Ask the user if they want to add the events to their calendar
        4. Ask the user for any missing information (end time, location, description, attendees)
        5. If confirmed, create the events using create_calendar_event()

        Important:
        - Always ask for user confirmation before creating calendar events
        - Always ask for missing information like end time, location, description, and attendees
        - Never use default values without user input
        - Always include the event_link when discussing events with the user
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)

            entities = extract_entities(content.plain_text)

            thread_id = message["threadId"]
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{email_id}"

            potential_events = []

            dates = entities.get("dates", [])
            times = entities.get("times", [])

            event_patterns = [
                r'(?i)(?:meeting|call|conference|appointment|event|webinar|seminar|workshop|session|interview)\s+(?:on|at|for)\s+([^.,:;!?]+)',
                r'(?i)(?:schedule|scheduled|plan|planning|organize|organizing|host|hosting)\s+(?:a|an)\s+([^.,:;!?]+)',
                r'(?i)(?:invite|invitation|inviting)\s+(?:you|everyone|all)\s+(?:to|for)\s+([^.,:;!?]+)'
            ]

            event_titles = []
            for pattern in event_patterns:
                matches = re.findall(pattern, content.plain_text)
                event_titles.extend(matches)

            parsed_datetimes = []

            datetime_patterns = [
                r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:tomorrow|today|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b'
            ]

            for pattern in datetime_patterns:
                matches = re.findall(pattern, content.plain_text)
                for match in matches:
                    try:
                        dt = parser.parse(match)
                        parsed_datetimes.append(dt)
                    except (ValueError, TypeError):
                        pass

            if not parsed_datetimes and dates and times:
                for date_str in dates:
                    for time_str in times:
                        try:
                            dt = parser.parse(f"{date_str} {time_str}")
                            parsed_datetimes.append(dt)
                        except (ValueError, TypeError):
                            pass

            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            potential_attendees = list(set(re.findall(email_pattern, content.plain_text)))

            location_patterns = [
                r'(?i)(?:at|in|location|place|venue):\s*([^.,:;!?]+)',
                r'(?i)(?:at|in)\s+the\s+([^.,:;!?]+)',
                r'(?i)(?:meet|meeting)\s+(?:at|in)\s+([^.,:;!?]+)'
            ]

            potential_location = None
            for pattern in location_patterns:
                matches = re.findall(pattern, content.plain_text)
                if matches:
                    potential_location = matches[0].strip()
                    break

            for i, dt in enumerate(parsed_datetimes):
                end_dt = dt + timedelta(hours=1)

                title = f"Event from email"
                if i < len(event_titles):
                    title = event_titles[i]
                elif metadata.subject:
                    title = f"Re: {metadata.subject}"

                potential_events.append({
                    "summary": title,
                    "start_time": dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "description": f"Detected from email: {metadata.subject}",
                    "location": potential_location,
                    "attendees": potential_attendees,
                    "confidence": "medium",
                    "source_text": content.plain_text[:200] + "..." if len(content.plain_text) > 200 else content.plain_text
                })

            return {
                "success": True,
                "events": potential_events,
                "email_id": email_id,
                "email_link": email_link,
                "subject": metadata.subject,
                "from": {
                    "email": metadata.from_email,
                    "name": metadata.from_name
                }
            }

        except Exception as e:
            logger.error(f"Failed to detect events from email: {e}")
            return {
                "success": False,
                "error": f"Failed to detect events from email: {e}"
            }

    @mcp.tool()
    def list_calendar_events(
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List events from the user's Google Calendar.

        This tool retrieves a list of upcoming events from the user's calendar.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            max_results (int, optional): Maximum number of events to return. Defaults to 10.
            time_min (str, optional): Start time for the search in ISO format or natural language.
                                     Defaults to now.
            time_max (str, optional): End time for the search in ISO format or natural language.
                                     Defaults to unlimited.
            query (str, optional): Free text search terms to find events that match.

        Returns:
            Dict[str, Any]: The list of events including:
                - events: List of calendar events with details and links
                - next_page_token: Token for pagination (if applicable)

        Example usage:
        1. List upcoming events:
           list_calendar_events()

        2. List events for a specific time range:
           list_calendar_events(time_min="tomorrow", time_max="tomorrow at 11:59pm")

        3. Search for specific events:
           list_calendar_events(query="meeting")

        Important:
        - Always include the event_link when discussing specific events with the user
        - The event_link allows users to directly access their events in Google Calendar
        - When listing multiple events, include the event_link for each event
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            user_timezone = get_user_timezone()

            if not time_min:
                time_min_dt = datetime.now(timezone.utc)
            else:
                time_min_dt = parse_natural_date(time_min, timezone=user_timezone, prefer_future=True)
                if not time_min_dt:
                    return {
                        "success": False,
                        "error": f"Could not parse start time: {time_min}",
                        "message": "Please provide a clearer date and time format for the start time."
                    }

            time_min_formatted = time_min_dt.isoformat() + 'Z' if not time_min_dt.tzinfo else time_min_dt.isoformat()

            time_max_formatted = None
            if time_max:
                time_max_dt = parse_natural_date(time_max, timezone=user_timezone, prefer_future=True, return_end_of_day=True)
                if not time_max_dt:
                    return {
                        "success": False,
                        "error": f"Could not parse end time: {time_max}",
                        "message": "Please provide a clearer date and time format for the end time."
                    }
                time_max_formatted = time_max_dt.isoformat() + 'Z' if not time_max_dt.tzinfo else time_max_dt.isoformat()

            params = {
                'calendarId': 'primary',
                'timeMin': time_min_formatted,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
                'timeZone': user_timezone
            }

            if time_max_formatted:
                params['timeMax'] = time_max_formatted

            if query:
                params['q'] = query

            events_result = service.events().list(**params).execute()
            events = events_result.get('items', [])

            processed_events = []
            for event in events:
                start = event.get('start', {})
                end = event.get('end', {})

                is_all_day = 'date' in start and 'date' in end

                if is_all_day:
                    start_display = start.get('date', '')
                    end_display = end.get('date', '')
                    time_display = "All day"
                else:
                    try:
                        start_dt = parser.parse(start.get('dateTime', ''))
                        end_dt = parser.parse(end.get('dateTime', ''))

                        start_display = start_dt.strftime("%Y-%m-%d %I:%M %p")
                        end_display = end_dt.strftime("%I:%M %p") if start_dt.date() == end_dt.date() else end_dt.strftime("%Y-%m-%d %I:%M %p")
                        time_display = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
                    except Exception:
                        start_display = start.get('dateTime', '')
                        end_display = end.get('dateTime', '')
                        time_display = "Unknown time"

                event_id = event['id']
                event_link = f"https://calendar.google.com/calendar/event?eid={event_id}"

                processed_events.append({
                    "id": event_id,
                    "summary": event.get('summary', 'Untitled Event'),
                    "start": start,
                    "end": end,
                    "start_display": start_display,
                    "end_display": end_display,
                    "time_display": time_display,
                    "is_all_day": is_all_day,
                    "location": event.get('location', ''),
                    "description": event.get('description', ''),
                    "attendees": event.get('attendees', []),
                    "event_link": event_link
                })

            return {
                "success": True,
                "events": processed_events,
                "next_page_token": events_result.get('nextPageToken'),
                "timezone": user_timezone,
                "query_parameters": {
                    "time_min": time_min,
                    "time_max": time_max,
                    "query": query
                }
            }

        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return {
                "success": False,
                "error": f"Failed to list calendar events: {e}"
            }

    @mcp.tool()
    def suggest_meeting_times(
        start_date: str,
        end_date: str,
        duration_minutes: int = 60,
        duration: Optional[str] = None,
        working_hours: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest available meeting times within a date range.

        This tool analyzes the user's calendar and suggests available time slots
        for scheduling meetings based on their existing calendar events.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            start_date (str): The start date of the range to check (can be natural language like "tomorrow")
            end_date (str): The end date of the range to check (can be natural language like "next friday")
            duration_minutes (int, optional): The desired meeting duration in minutes. Defaults to 60.
            duration (str, optional): Duration as natural language (e.g., "1 hour", "90 minutes").
                                     If provided, overrides duration_minutes.
            working_hours (str, optional): Working hours (e.g., "9-17", "9am-5pm", "9am to 5pm"). Defaults to 9am-5pm.

        Returns:
            Dict[str, Any]: The suggested meeting times including:
                - success: Whether the operation was successful
                - suggestions: List of suggested meeting times with formatted date/time
                - message: A message describing the result

        Example usage:
        1. Find meeting times for tomorrow:
           suggest_meeting_times(start_date="tomorrow", end_date="tomorrow")

        2. Find meeting times for next week with custom duration:
           suggest_meeting_times(
               start_date="next monday",
               end_date="next friday",
               duration="30 minutes"
           )

        3. Find meeting times with custom working hours:
           suggest_meeting_times(
               start_date="tomorrow",
               end_date="friday",
               working_hours="10am to 4pm"
           )

        Important:
        - The tool respects the user's existing calendar events
        - Suggestions are limited to working hours (default 9am-5pm)
        - Weekends are excluded by default
        - The tool will return at most 10 suggestions
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            # Parse duration (NLP string takes precedence)
            if duration:
                actual_duration = parse_duration(duration)
            else:
                actual_duration = duration_minutes

            # Parse working hours using NLP parser
            if working_hours:
                work_start_hour, work_end_hour = parse_working_hours(working_hours)
            else:
                work_start_hour, work_end_hour = 9, 17

            from gmail_mcp.calendar.processor import suggest_meeting_times as processor_suggest_times

            suggestions = processor_suggest_times(
                start_date=start_date,
                end_date=end_date,
                duration_minutes=actual_duration,
                working_hours=(work_start_hour, work_end_hour)
            )

            if suggestions and "error" in suggestions[0]:
                return {
                    "success": False,
                    "error": suggestions[0]["error"],
                    "message": "Could not suggest meeting times. Please check your date range."
                }

            return {
                "success": True,
                "suggestions": suggestions,
                "message": f"Found {len(suggestions)} available time slots.",
                "parameters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_minutes": actual_duration,
                    "working_hours": f"{work_start_hour}:00-{work_end_hour}:00"
                }
            }

        except Exception as e:
            logger.error(f"Failed to suggest meeting times: {e}")
            return {
                "success": False,
                "error": f"Failed to suggest meeting times: {e}"
            }

    @mcp.tool()
    def update_calendar_event(
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id (str): The ID of the event to update
            summary (str, optional): New title for the event
            start_time (str, optional): New start time
            end_time (str, optional): New end time
            description (str, optional): New description
            location (str, optional): New location

        Returns:
            Dict[str, Any]: Updated event details
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if location:
                event["location"] = location

            user_timezone = get_user_timezone()

            if start_time:
                start_dt = parse_natural_date(start_time, timezone=user_timezone, prefer_future=True)
                if not start_dt:
                    return {"success": False, "error": f"Could not parse start time: {start_time}"}
                event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": user_timezone}

            if end_time:
                end_dt = parse_natural_date(end_time, timezone=user_timezone, prefer_future=True)
                if not end_dt:
                    return {"success": False, "error": f"Could not parse end time: {end_time}"}
                event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": user_timezone}

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": "Event updated successfully.",
                "event_id": updated_event["id"],
                "event_link": updated_event.get("htmlLink", ""),
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return {"success": False, "error": f"Failed to update calendar event: {e}"}

    @mcp.tool()
    def delete_calendar_event(event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event.

        Args:
            event_id (str): The ID of the event to delete

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            service.events().delete(calendarId="primary", eventId=event_id).execute()

            return {
                "success": True,
                "message": "Event deleted successfully.",
                "event_id": event_id
            }

        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return {"success": False, "error": f"Failed to delete calendar event: {e}"}

    @mcp.tool()
    def rsvp_event(event_id: str, response: str) -> Dict[str, Any]:
        """
        Respond to a calendar event invitation.

        Args:
            event_id (str): The ID of the event
            response (str): Response status - "accepted", "declined", or "tentative"

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        if response not in ["accepted", "declined", "tentative"]:
            return {"success": False, "error": "Response must be 'accepted', 'declined', or 'tentative'"}

        try:
            service = get_calendar_service(credentials)

            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            gmail_service = get_gmail_service(credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")

            attendees = event.get("attendees", [])
            for attendee in attendees:
                if attendee.get("email", "").lower() == user_email.lower():
                    attendee["responseStatus"] = response
                    break

            event["attendees"] = attendees

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": f"RSVP updated to '{response}'.",
                "event_id": event_id,
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to RSVP: {e}")
            return {"success": False, "error": f"Failed to RSVP: {e}"}
