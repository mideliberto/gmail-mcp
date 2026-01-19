# Gmail MCP Extended

Extended fork of [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp) with comprehensive email and calendar management tools.

## What's New in This Fork

### Email Compose & Send
- `compose_email` - Send new emails (not just replies)
- `forward_email` - Forward existing emails

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

### Utilities
- `find_unsubscribe_link` - Extract unsubscribe links from newsletters

### Calendar Management
- `update_calendar_event` - Modify existing events
- `delete_calendar_event` - Remove events
- `rsvp_event` - Respond to invitations (accepted/declined/tentative)

---

## Original Features

All original gmail-mcp features are preserved:

- **Email Reading**: `get_email_overview`, `list_emails`, `search_emails`, `get_email`
- **Email Replies**: `prepare_email_reply`, `send_email_reply`, `confirm_send_email`
- **Calendar**: `list_calendar_events`, `create_calendar_event`, `suggest_meeting_times`, `detect_events_from_email`
- **Auth**: `check_auth_status`, `authenticate`

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
        "TOKEN_ENCRYPTION_KEY": "<generate-a-random-key>"
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

# Labels
"Create a label called 'Important' with red background"
"Label all emails from my boss as 'Priority'"

# Calendar
"Accept the meeting invitation for tomorrow"
"Move my dentist appointment to 3pm"
"Delete the test event I created"
```

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

153 tests covering:
- Token management and encryption
- OAuth flow and state verification
- Gmail and Calendar API operations
- Email management (compose, forward, archive, labels)
- Bulk operations
- Attachments

## Patches Applied

This fork includes fixes for:
- FastMCP constructor compatibility (removed unsupported kwargs)
- OAuth scope relaxation (`OAUTHLIB_RELAX_TOKEN_SCOPE`) for Google's scope response handling

---

## License

MIT License (same as original)

## Credits

- Original: [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp)
- Extended by: [@mideliberto](https://github.com/mideliberto)
