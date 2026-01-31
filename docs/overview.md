# Gmail MCP Extended Overview

Complete reference for all tools, resources, and prompts across the three MCP servers.

---

## Server 1: gmail-mcp (93 tools)

### Authentication (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `login_tool` | Get OAuth login URL | None |
| `authenticate` | Start OAuth flow (opens browser) | None |
| `process_auth_code_tool` | Process OAuth callback | `code`, `state` |
| `logout` | Revoke tokens and log out | None |
| `check_auth_status` | Check authentication status | None |

### Email - Reading (7 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_email_count` | Get inbox/total email counts | None |
| `list_emails` | List emails from a label | `max_results`, `label` |
| `get_email` | Get full email details | `email_id`, `include_thread` |
| `search_emails` | Search with Gmail syntax + NLP dates | `query`, `max_results`, `after`*, `before`*, `date_range`* |
| `get_email_overview` | Quick inbox summary | None |
| `get_thread` | Get full conversation thread | `thread_id` |
| `get_thread_summary` | Get condensed thread summary | `thread_id` |

*Supports NLP dates

### Email - Composing (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `compose_email` | Create new email draft | `to`, `subject`, `body`, `cc`, `bcc`, `send_at`* |
| `forward_email` | Forward an email | `email_id`, `to`, `additional_message` |
| `prepare_email_reply` | Get context for reply | `email_id` |
| `send_email_reply` | Create reply draft | `email_id`, `reply_text`, `include_original` |
| `confirm_send_email` | Send a draft | `draft_id` |

*`send_at` supports NLP ("tomorrow 8am") - creates draft + calendar reminder

### Email - Organization (7 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `archive_email` | Archive (remove from inbox) | `email_id` |
| `trash_email` | Move to trash | `email_id` |
| `delete_email` | Permanently delete | `email_id` |
| `mark_as_read` | Mark as read | `email_id` |
| `mark_as_unread` | Mark as unread | `email_id` |
| `star_email` | Add star | `email_id` |
| `unstar_email` | Remove star | `email_id` |

### Labels (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_labels` | List all labels | None |
| `create_label` | Create new label | `name`, `background_color`, `text_color` |
| `delete_label` | Delete a label | `label_id` |
| `apply_label` | Apply label to email | `email_id`, `label_id` or `label` (fuzzy match) |
| `remove_label` | Remove label from email | `email_id`, `label_id` or `label` |

### Attachments (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_attachments` | List attachments in email | `email_id` |
| `download_attachment` | Download attachment | `email_id`, `attachment_id`, `save_path` |

### Bulk Operations (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `bulk_archive` | Archive emails matching query | `query`, `max_emails` |
| `bulk_label` | Label emails matching query | `query`, `label_id`, `max_emails` |
| `bulk_remove_label` | Remove label from emails | `query`, `label_id`, `max_emails` |
| `bulk_trash` | Trash emails matching query | `query`, `max_emails` |
| `cleanup_old_emails` | Archive/trash old emails | `query`, `days_old`, `action`, `max_emails` |

### Drafts (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_drafts` | List all drafts | `max_results` |
| `get_draft` | Get draft content | `draft_id` |
| `update_draft` | Update draft | `draft_id`, `to`, `subject`, `body`, `cc`, `bcc` |
| `delete_draft` | Delete draft | `draft_id` |

### Filters (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_filters` | List all filters | None |
| `create_filter` | Create filter | `from_address`, `to_address`, `subject`, `query`, `has_attachment`, `add_label_ids`, `remove_label_ids`, `archive`, `mark_read`, `star`, `forward_to`, `never_spam`, `mark_important` |
| `get_filter` | Get filter details | `filter_id` |
| `delete_filter` | Delete filter | `filter_id` |

### Settings (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_vacation_responder` | Get vacation auto-reply status | None |
| `set_vacation_responder` | Configure vacation auto-reply | `enabled`, `subject`, `message`, `start_date`*, `end_date`*, `contacts_only`, `domain_only` |
| `disable_vacation_responder` | Turn off vacation auto-reply | None |

*Supports NLP dates

### Retention (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `setup_retention_labels` | Create retention labels (7-day, 30-day, etc.) | None |
| `enforce_retention_policies` | Delete/archive expired emails | `dry_run`, `max_emails_per_label` |
| `get_retention_status` | Show retention label status | None |

### Claude Review (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `setup_claude_review_labels` | Create Claude/Review, Claude/Urgent, etc. | None |
| `get_emails_for_claude_review` | Get emails flagged for review | `label_name`, `max_results` |
| `create_claude_review_filter` | Create filter for Claude review | `from_address`, `subject_contains`, `query`, `review_type` |

### Calendar (15 tools)

All calendar tools support **natural language dates**: `tomorrow`, `next monday`, `in 3 days`

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_calendar_events` | List events | `max_results`, `time_min`*, `time_max`*, `query` |
| `get_calendar_event` | Get single event by ID | `event_id`, `calendar_id` |
| `create_calendar_event` | Create event | `summary`, `start_time`*, `end_time`*, `description`, `location`, `attendees`, `color_name`, `reminders` |
| `create_recurring_event` | Create recurring event | `summary`, `start_time`*, `frequency`, `recurrence_pattern`*, `interval`, `count`, `until`, `by_day`, `reminders` |
| `update_calendar_event` | Update event | `event_id`, `summary`, `start_time`*, `end_time`*, `description`, `location`, `reminders` |
| `delete_calendar_event` | Delete event | `event_id` |
| `duplicate_calendar_event` | Copy event to new time | `event_id`, `new_start_time`*, `new_summary`, `calendar_id` |
| `rsvp_event` | Respond to invitation | `event_id`, `response` |
| `suggest_meeting_times` | Find available slots | `start_date`*, `end_date`*, `duration`/`duration_minutes`, `working_hours` |
| `find_free_time` | Find free slots on a date | `date`*, `duration`/`duration_minutes`, `calendar_ids`, `working_hours` |
| `check_conflicts` | Check for scheduling conflicts | `start_time`*, `end_time`*, `calendar_ids`, `exclude_all_day` |
| `check_attendee_availability` | Query freebusy for attendees | `attendees`, `start_date`*, `end_date`*, `duration`/`duration_minutes`, `working_hours` |
| `list_calendars` | List all calendars | None |
| `get_daily_agenda` | Get unified daily agenda | `date`*, `calendar_ids`, `include_all_day` |
| `add_travel_buffer` | Add travel time before event | `event_id`, `minutes`, `label` |

*Supports NLP dates

**Reminders format:**
```python
reminders=["30 minutes", "1 hour", "1 day before by email"]
# or
reminders=[{"method": "popup", "minutes": 30}, {"method": "email", "minutes": 1440}]
```

### Contacts - Basic (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_contacts` | List Google Contacts | `max_results`, `page_token` |
| `search_contacts` | Search contacts | `query`, `max_results` |
| `get_contact` | Get contact details | `email` or `resource_name` |

### Contacts - CRUD (3 tools)

*Requires contacts write scope*

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_contact` | Create new contact | `name`, `email`, `phone`, `organization`, `title`, `notes` |
| `update_contact` | Update contact | `resource_name`, `name`, `email`, `phone`, `organization`, `title`, `notes` |
| `delete_contact` | Delete contact | `resource_name` |

### Contacts - Hygiene (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `find_duplicate_contacts` | Find potential duplicates | `threshold`, `max_results` |
| `find_stale_contacts` | Find contacts with no activity | `months`, `max_results` |
| `find_incomplete_contacts` | Find contacts missing fields | `require_email`, `require_phone`, `require_organization` |
| `merge_contacts` | Merge duplicate contacts | `resource_names`, `primary_index`, `dry_run` |
| `enrich_contact_from_email` | Extract info from signatures | `email_id`, `resource_name` |

### Contacts - Groups (5 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_contact_groups` | List contact groups | None |
| `create_contact_group` | Create group | `name` |
| `delete_contact_group` | Delete group | `group_resource_name` |
| `add_contacts_to_group` | Add contacts to group | `group_resource_name`, `contact_resource_names` |
| `remove_contacts_from_group` | Remove contacts from group | `group_resource_name`, `contact_resource_names` |

### Contacts - Export (1 tool)

| Tool | Description | Parameters |
|------|-------------|------------|
| `export_contacts` | Export to CSV | `file_path`, `format` |

### Subscriptions (6 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `setup_subscription_labels` | Create Subscriptions/* labels | None |
| `find_subscription_emails` | Find newsletters with unsubscribe | `max_results`, `days` |
| `get_unsubscribe_link` | Get unsubscribe link from email | `email_id` |
| `unsubscribe_and_cleanup` | Full unsubscribe workflow | `from_address`, `archive_existing` |
| `create_subscription_filter` | Create filter for sender | `from_address`, `action` ("retain" or "junk") |
| `mark_sender_as_junk` | Filter to trash + spam report | `from_address`, `trash_existing` |

### Vault Integration (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `save_email_to_vault` | Save email as markdown | `email_id`, `vault_path`, `inbox_folder`, `include_attachments`, `tags` |
| `batch_save_emails_to_vault` | Save multiple emails | `query`, `vault_path`, `max_emails`, `include_attachments`, `tags` |

---

## Server 2: drive-mcp (54 tools)

See [drive-mcp.md](drive-mcp.md) for detailed reference.

### Summary

| Category | Tools |
|----------|-------|
| File Operations | 14 |
| Folders | 3 |
| Google Workspace | 4 |
| Sharing & Permissions | 6 |
| Shared Drives | 6 |
| Bulk Operations | 4 |
| Storage & Activity | 2 |
| Comments | 3 |
| Revisions | 3 |
| Drive Labels | 6 |
| Drive OCR | 3 |

---

## Server 3: docs-mcp (32 tools)

See [docs-mcp.md](docs-mcp.md) for detailed reference.

### Summary

| Category | Tools |
|----------|-------|
| Office Reading | 3 |
| Office Templates | 6 |
| Office Export | 3 |
| PDF Processing | 7 |
| Local OCR | 4 |
| Vault Integration | 4 |

---

## Resources (gmail-mcp)

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

## Prompts (gmail-mcp)

| Prompt | Description |
|--------|-------------|
| `gmail://quickstart` | Getting started guide |
| `gmail://search_guide` | Gmail search syntax |
| `gmail://authentication_guide` | Auth troubleshooting |
| `gmail://debug_guide` | Debugging guide |
| `gmail://reply_guide` | Reply composition guide |

---

## NLP Date Formats

Supported across all date parameters:

| Pattern | Examples |
|---------|----------|
| Relative days | `yesterday`, `today`, `tomorrow` |
| Days of week | `this monday`, `next wednesday`, `last friday` |
| Week ranges | `this week`, `next week`, `past 7 days` |
| Numeric relative | `3 days ago`, `in 5 days`, `in 2 hours` |
| With time | `tomorrow at 2pm`, `next monday at 10am` |
| ISO format | `2026-01-20`, `2026-01-20T15:00:00` |

### Recurrence Patterns

| Pattern | Result |
|---------|--------|
| `every day`, `daily` | Daily |
| `every weekday` | Monday-Friday |
| `weekly`, `every week` | Weekly |
| `biweekly`, `every 2 weeks` | Every 2 weeks |
| `every monday and wednesday` | Specific days |
| `monthly`, `yearly` | Monthly/yearly |
| `daily for 2 weeks` | Daily with count |
| `weekly until march` | Weekly with end date |

### Working Hours

| Format | Example |
|--------|---------|
| Simple range | `9-17` |
| AM/PM | `9am-5pm` |
| With "to" | `9am to 5pm` |
| 24-hour | `09:00-17:00` |

### Duration

| Format | Minutes |
|--------|---------|
| Integer | `60` |
| Hours | `1 hour`, `1.5 hours` |
| Minutes | `90 minutes` |
| Shorthand | `half hour` |

---

## Calendar Colors

| Color | ID | Alternatives |
|-------|-----|--------------|
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

---

## Notes

- Always check authentication first with `check_auth_status()`
- Email replies require user confirmation before sending
- Bulk operations are limited to 100-500 emails per call
- Calendar events auto-add current user as attendee
- drive-mcp shares tokens with gmail-mcp (no separate auth needed)
- docs-mcp requires no authentication (local processing only)
