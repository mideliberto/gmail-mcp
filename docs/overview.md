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

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_calendar_event` | Create event | `summary`, `start_time`, `end_time`, `description`, `location`, `attendees`, `color_name` |
| `list_calendar_events` | List events | `max_results`, `time_min`, `time_max`, `query` |
| `update_calendar_event` | Update event | `event_id`, `summary`, `start_time`, `end_time`, `description`, `location` |
| `delete_calendar_event` | Delete event | `event_id` |
| `rsvp_event` | Respond to invitation | `event_id`, `response` |
| `detect_events_from_email` | Extract events from email | `email_id` |
| `suggest_meeting_times` | Find available slots | `start_date`, `end_date`, `duration_minutes`, `working_hours` |

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

## Notes

- Always check authentication first
- Email replies require user confirmation before sending
- Bulk operations are limited to 100 emails per call
- Calendar events auto-add current user as attendee
