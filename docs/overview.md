# Gmail MCP Overview

Overview of all tools, resources, and prompts in the Gmail MCP server.

## Tools

### Authentication

| Tool | Description | Parameters |
|------|-------------|------------|
| `login_tool` | Get OAuth login URL | None |
| `authenticate` | Start OAuth flow (opens browser) | None |
| `process_auth_code_tool` | Process OAuth callback | `code`, `state` |
| `logout` | Revoke tokens and log out | None |
| `check_auth_status` | Check authentication status | None |

### Email - Reading

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_email_count` | Get inbox/total email counts | None |
| `list_emails` | List emails from a label | `max_results`, `label` |
| `get_email` | Get full email details | `email_id` |
| `search_emails` | Search with Gmail syntax | `query`, `max_results` |
| `get_email_overview` | Quick inbox summary | None |

### Email - Composing

| Tool | Description | Parameters |
|------|-------------|------------|
| `compose_email` | Create new email draft | `to`, `subject`, `body`, `cc`, `bcc` |
| `forward_email` | Forward an email | `email_id`, `to`, `additional_message` |
| `prepare_email_reply` | Get context for reply | `email_id` |
| `send_email_reply` | Create reply draft | `email_id`, `reply_text`, `include_original` |
| `confirm_send_email` | Send a draft | `draft_id` |

### Email - Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `archive_email` | Archive (remove from inbox) | `email_id` |
| `trash_email` | Move to trash | `email_id` |
| `delete_email` | Permanently delete | `email_id` |
| `mark_as_read` | Mark as read | `email_id` |
| `mark_as_unread` | Mark as unread | `email_id` |
| `star_email` | Add star | `email_id` |
| `unstar_email` | Remove star | `email_id` |

### Labels

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_labels` | List all labels | None |
| `create_label` | Create new label | `name`, `background_color`, `text_color` |
| `apply_label` | Apply label to email | `email_id`, `label_id` |
| `remove_label` | Remove label from email | `email_id`, `label_id` |

### Attachments

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_attachments` | List attachments in email | `email_id` |
| `download_attachment` | Download attachment | `email_id`, `attachment_id`, `save_path` |

### Bulk Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `bulk_archive` | Archive emails matching query | `query`, `max_emails` |
| `bulk_label` | Label emails matching query | `query`, `label_id`, `max_emails` |
| `bulk_trash` | Trash emails matching query | `query`, `max_emails` |

### Utilities

| Tool | Description | Parameters |
|------|-------------|------------|
| `find_unsubscribe_link` | Find unsubscribe link in email | `email_id` |

### Calendar

All calendar tools support **natural language dates**: `tomorrow`, `next monday`, `in 3 days`, `next week at 2pm`

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_calendar_event` | Create event | `summary`, `start_time`*, `end_time`, `description`, `location`, `attendees`, `color_name` |
| `create_recurring_event` | Create recurring event | `summary`, `start_time`*, `frequency`/`recurrence_pattern`*, `end_time`, `interval`, `count`, `until`, `by_day` |
| `list_calendar_events` | List events | `max_results`, `time_min`*, `time_max`*, `query` |
| `update_calendar_event` | Update event | `event_id`, `summary`, `start_time`*, `end_time`*, `description`, `location` |
| `delete_calendar_event` | Delete event | `event_id` |
| `rsvp_event` | Respond to invitation | `event_id`, `response` |
| `detect_events_from_email` | Extract events from email | `email_id` |
| `suggest_meeting_times` | Find available slots | `start_date`*, `end_date`*, `duration_minutes`, `working_hours` |

*Supports NLP dates (e.g., `tomorrow at 2pm`, `next monday`)

### Multi-Calendar / Conflict Detection

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_calendars` | List all accessible calendars | None |
| `check_conflicts` | Check for scheduling conflicts | `start_time`*, `end_time`*, `calendar_ids`, `exclude_all_day` |
| `find_free_time` | Find available time slots | `date`*, `duration_minutes`, `calendar_ids`, `working_hours` |
| `get_daily_agenda` | Get unified daily agenda | `date`*, `calendar_ids`, `include_all_day` |

*Supports NLP dates

## Resources

| Resource | Description |
|----------|-------------|
| `auth://status` | Authentication status |
| `gmail://status` | Gmail account overview |
| `email://{email_id}` | Email context |
| `thread://{thread_id}` | Thread context |
| `sender://{sender_email}` | Sender history |
| `server://info` | Server information |
| `server://config` | Server configuration |
| `server://status` | System status |
| `debug://help` | Debugging help |
| `health://` | Health check |

## Prompts

| Prompt | Description |
|--------|-------------|
| `gmail://quickstart` | Getting started guide |
| `gmail://search_guide` | Gmail search syntax |
| `gmail://authentication_guide` | Auth troubleshooting |
| `gmail://debug_guide` | Debugging guide |
| `gmail://reply_guide` | Reply composition guide |

## Calendar Colors

| Color Name | ID | Alternatives |
|------------|-----|--------------|
| blue | 1 | light blue |
| green | 2 | light green |
| purple | 3 | lavender |
| red | 4 | salmon |
| yellow | 5 | pale yellow |
| orange | 6 | peach |
| turquoise | 7 | cyan |
| gray | 8 | light gray |
| bold blue | 9 | dark blue |
| bold green | 10 | dark green |
| bold red | 11 | dark red |

## Usage Flow

1. Check auth: `check_auth_status()`
2. If needed: `authenticate()`
3. Overview: `get_email_overview()`
4. Browse/search emails
5. Manage emails (archive, label, reply)
6. Calendar operations as needed

## NLP Date Formats

Supported natural language date patterns:

| Pattern | Examples |
|---------|----------|
| Relative days | `yesterday`, `today`, `tomorrow`, `day before yesterday`, `day after tomorrow` |
| Days of week | `this monday`, `next wednesday`, `last friday` |
| Week ranges | `this week`, `next week`, `last week`, `past 7 days`, `next 2 weeks` |
| Numeric relative | `3 days ago`, `in 5 days`, `in 2 hours`, `30 minutes ago` |
| With time | `tomorrow at 2pm`, `next monday at 10am` |
| ISO format | `2026-01-20`, `2026-01-20T15:00:00` |

Recurrence patterns (for `create_recurring_event`):

| Pattern | Result |
|---------|--------|
| `every day`, `daily` | Daily recurrence |
| `every weekday` | Monday-Friday |
| `weekly`, `every week` | Weekly |
| `biweekly`, `every 2 weeks` | Every 2 weeks |
| `every monday and wednesday` | Specific days |
| `monthly`, `yearly` | Monthly/yearly |
| `daily for 2 weeks` | Daily with count |
| `weekly until march` | Weekly with end date |

Working hours formats (for `find_free_time`, `suggest_meeting_times`):

| Format | Example |
|--------|---------|
| Simple range | `9-17` |
| AM/PM with dash | `9am-5pm` |
| AM/PM with "to" | `9am to 5pm` |
| 24-hour format | `09:00-17:00` |

Duration formats (for `find_free_time`, `suggest_meeting_times`):

| Format | Minutes |
|--------|---------|
| `60` | 60 |
| `1 hour` | 60 |
| `90 minutes` | 90 |
| `1.5 hours` | 90 |
| `half hour` | 30 |

## Email Search Date Filters

Use `search_emails()` with NLP date parameters:

```python
# Date range expression
search_emails(query="from:boss", date_range="last week")
search_emails(query="invoices", date_range="past 30 days")

# Explicit after/before
search_emails(query="is:unread", after="last monday", before="today")
search_emails(query="from:amazon", after="3 days ago")
```

## Label Fuzzy Matching

`apply_label()` and `remove_label()` support case-insensitive name matching:

```python
# By label ID (traditional)
apply_label(email_id="...", label_id="Label_123")

# By label name (fuzzy matching)
apply_label(email_id="...", label="Important")      # Matches "IMPORTANT"
apply_label(email_id="...", label="claude")         # Matches "Claude/Review" if unique
```

## Notes

- Always check authentication first
- Email replies require user confirmation before sending
- Bulk operations are limited to 100 emails per call
- Calendar events auto-add current user as attendee
- All calendar date parameters support NLP (marked with *)
- Label matching is case-insensitive with suggestions on failure
