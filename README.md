# Gmail MCP Extended

Extended fork of [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp) with comprehensive email and calendar management tools.

**Version 2.0.0** - Major refactor with modular architecture, new features, and improved performance.

## What's New in v2.0.0

### Vault Integration (Obsidian/Markdown)
- `save_email_to_vault` - Save emails as markdown files with frontmatter
- `batch_save_emails_to_vault` - Batch save multiple emails
- Configurable vault path, inbox folder, and tags
- Automatic attachment download support

### Multi-Calendar Conflict Detection
- `list_calendars` - List all accessible calendars
- `check_conflicts` - Detect scheduling conflicts across calendars
- `find_free_time` - Find available time slots across all calendars
- `get_daily_agenda` - Unified view of events from all calendars

### Gmail Filter Management
- `list_filters` - View all Gmail filters
- `create_filter` - Create new filters with criteria and actions
- `delete_filter` - Remove filters
- `get_filter` - Get details of a specific filter
- `create_claude_review_filter` - Create filters that route emails to Claude review labels

### Claude Review Label System
- `setup_claude_review_labels` - Create Claude-specific labels for email triage
- `get_emails_for_claude_review` - Get emails flagged for Claude attention
- Pre-configured labels: Claude/Review, Claude/Urgent, Claude/Reply-Needed, Claude/Summarize, Claude/Action-Required

### Performance Improvements
- Gmail Batch API for list/search operations (N+1 query fix)
- Service caching to reduce API calls
- Modular code architecture for maintainability

---

## All Features

### Email Compose & Send
- `compose_email` - Send new emails (not just replies)
- `forward_email` - Forward existing emails
- `send_email_reply` - Create reply draft
- `confirm_send_email` - Send after user confirmation
- `prepare_email_reply` - Get context for crafting replies

### Email Organization
- `archive_email` - Archive emails (remove from inbox)
- `trash_email` - Move to trash
- `delete_email` - Permanent delete
- `star_email` / `unstar_email` - Star management
- `mark_as_read` / `mark_as_unread` - Read status

### Label Management
- `list_labels` - Get all labels
- `create_label` - Create new label with optional colors
- `apply_label` / `remove_label` - Apply/remove labels from emails

### Attachments
- `get_attachments` - List attachments in an email
- `download_attachment` - Save attachment to disk

### Bulk Operations
- `bulk_archive` - Archive all emails matching a query
- `bulk_label` - Label all emails matching a query
- `bulk_trash` - Trash all emails matching a query
- `cleanup_old_emails` - Archive old emails by age

### Email Reading
- `get_email_overview` - Quick summary of inbox
- `list_emails` - List emails with pagination
- `search_emails` - Search with Gmail query syntax
- `get_email` - Get full email details
- `get_email_count` - Get inbox statistics

### Calendar Management
- `list_calendar_events` - View upcoming events
- `create_calendar_event` - Create new events
- `create_recurring_event` - Create recurring events (daily, weekly, monthly, yearly with RRULE)
- `update_calendar_event` - Modify existing events
- `delete_calendar_event` - Remove events
- `rsvp_event` - Respond to invitations
- `suggest_meeting_times` - Find available slots
- `detect_events_from_email` - Extract events from emails

### Utilities
- `find_unsubscribe_link` - Extract unsubscribe links from newsletters

### Authentication
- `check_auth_status` - Check if authenticated
- `authenticate` - Start OAuth flow
- `logout` - Revoke access

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/mideliberto/gmail-mcp-extended.git
   cd gmail-mcp-extended
   ```

2. Set up a virtual environment:
   ```bash
   pip install uv
   uv venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   uv pip install -e .
   ```

## Configuration

### Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable:
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - [Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
3. Configure OAuth consent screen (External, add your email as test user)
4. Create OAuth 2.0 credentials (Desktop app)
5. Add required scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.labels`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.settings.basic` (for filters)
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`

### config.yaml

Copy `config.yaml.example` to `config.yaml` and customize:

```yaml
server:
  host: localhost
  port: 8000
  debug: false
  log_level: INFO

calendar:
  enabled: true

vault:
  inbox_folder: 0-inbox
  attachment_folder: attachments

claude_review:
  labels:
    - name: Claude/Review
      color: "#4986e7"
    - name: Claude/Urgent
      color: "#e66550"
```

### Claude Code / Claude Desktop Config

Add to your MCP config (`~/.claude/settings.json` for Claude Code):

```json
{
  "mcpServers": {
    "gmail-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/gmail_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "CONFIG_FILE_PATH": "/path/to/gmail-mcp-extended/config.yaml",
        "GOOGLE_CLIENT_ID": "<your-client-id>",
        "GOOGLE_CLIENT_SECRET": "<your-client-secret>",
        "TOKEN_ENCRYPTION_KEY": "<generate-a-random-key>",
        "VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Usage Examples

```
# Email
"Send an email to john@example.com about the meeting"
"Archive all emails from linkedin older than 7 days"
"Find unsubscribe links in that newsletter"
"Download the PDF attachment from the last email"

# Labels & Filters
"Create a label called 'Important' with red background"
"Label all emails from my boss as 'Priority'"
"Create a filter to route newsletters to Claude/Review"
"Show me all my Gmail filters"

# Calendar
"Accept the meeting invitation for tomorrow"
"Move my dentist appointment to 3pm"
"Do I have any scheduling conflicts this week?"
"Find a free hour for a meeting with John tomorrow"
"Create a recurring daily standup at 9am for 2 weeks"
"Set up a bi-weekly 1:1 meeting every other Tuesday"

# Vault Integration
"Save this email to my vault"
"Save all emails with attachments from this week to my vault"

# Claude Review
"Set up Claude review labels"
"Show me emails that need my attention"
```

---

## Architecture

The codebase is organized into modular components:

```
gmail_mcp/
├── main.py              # MCP server entry point
├── types.py             # Type definitions for IDE support
├── auth/                # OAuth and token management
├── gmail/               # Gmail helper functions
├── calendar/            # Calendar processing
├── utils/               # Config, logging, services
└── mcp/
    └── tools/           # Modular tool definitions
        ├── auth.py      # Authentication tools
        ├── email_read.py
        ├── email_send.py
        ├── email_manage.py
        ├── labels.py
        ├── attachments.py
        ├── bulk.py
        ├── calendar.py
        ├── filters.py   # Gmail filter management
        ├── vault.py     # Obsidian vault integration
        └── conflict.py  # Multi-calendar conflict detection
```

## Type Support

The package includes:
- `py.typed` marker for PEP 561 compliance
- Type stubs (`.pyi` files) for key modules
- TypedDict definitions for all API responses
- IDE-friendly type exports in `gmail_mcp/__init__.py`

## API Response Format

All tools return a consistent response format:

**Success responses:**
```json
{
  "success": true,
  "message": "Operation completed",
  // ... additional data
}
```

**Error responses:**
```json
{
  "success": false,
  "error": "Error description"
}
```

This consistent format makes error handling predictable across all 54 tools.

---

## Security Features

- **Encrypted Token Storage**: OAuth tokens are encrypted at rest using Fernet encryption with PBKDF2 key derivation
- **CSRF Protection**: OAuth state verification prevents cross-site request forgery attacks
- **Automatic Token Refresh**: Tokens are automatically refreshed when expired
- **Secure Callback**: Browser-based OAuth flow with local callback server

## Testing

Run the test suite with:
```bash
cd /path/to/gmail-mcp-extended
source .venv/bin/activate
pytest
```

Tests cover:
- Token management and encryption
- OAuth flow and state verification
- Gmail and Calendar API operations
- Email management (compose, forward, archive, labels)
- Bulk operations
- Attachments
- Filter management
- Vault integration
- Conflict detection

---

## License

MIT License (same as original)

## Credits

- Original: [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp)
- Extended by: [@mideliberto](https://github.com/mideliberto)
