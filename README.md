# Gmail MCP Extended

Extended fork of [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp) - now a **monorepo with three MCP servers** for comprehensive Google Workspace and document processing.

**Version 2.3.0** - Monorepo with complete backlog implementation.

## Three MCP Servers

| Server | Tools | Google Auth | Use Case |
|--------|-------|-------------|----------|
| `gmail-mcp` | 93 | Yes | Email, Calendar, Contacts, Subscriptions |
| `drive-mcp` | 54 | Yes | Google Drive files, folders, sharing, labels, comments, revisions |
| `docs-mcp` | 32 | No | Local DOCX/XLSX/PPTX/PDF processing, OCR, vault export |
| **Total** | **179** | | |

### Deployment Flexibility

```yaml
# Personal use (email + calendar only)
mcpServers:
  gmail: gmail-mcp

# Full suite (all Google + local docs)
mcpServers:
  gmail: gmail-mcp
  drive: drive-mcp
  docs: docs-mcp

# Offline document work (no Google needed)
mcpServers:
  docs: docs-mcp
```

---

## Quick Start

### Installation

```bash
git clone https://github.com/mideliberto/gmail-mcp-extended.git
cd gmail-mcp-extended

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install base package
pip install -e .

# For docs-mcp (local document processing)
pip install python-docx openpyxl python-pptx pypdf pdfplumber pytesseract pdf2image Pillow

# For OCR support (optional)
brew install tesseract poppler  # macOS
# apt install tesseract-ocr poppler-utils  # Linux
```

### Google Cloud Setup

Required for `gmail-mcp` and `drive-mcp`. See [docs/setup.md](docs/setup.md) for detailed guide.

1. Create project at [Google Cloud Console](https://console.cloud.google.com/)
2. Enable APIs:
   - Gmail API
   - Calendar API
   - People API (contacts)
   - Drive API (for drive-mcp)
   - Drive Labels API (for drive-mcp labels)
   - Drive Activity API (for drive-mcp activity)
3. Create OAuth 2.0 credentials (Desktop app)
4. Add scopes (see Configuration section below)

### Claude Desktop / Claude Code Config

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
    },
    "drive-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/drive_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
        "GOOGLE_CLIENT_ID": "<your-client-id>",
        "GOOGLE_CLIENT_SECRET": "<your-client-secret>",
        "TOKEN_ENCRYPTION_KEY": "<generate-a-random-key>"
      }
    },
    "docs-mcp": {
      "command": "/path/to/gmail-mcp-extended/.venv/bin/mcp",
      "args": ["run", "/path/to/gmail-mcp-extended/docs_mcp/main.py:mcp"],
      "cwd": "/path/to/gmail-mcp-extended",
      "env": {
        "PYTHONPATH": "/path/to/gmail-mcp-extended",
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

## Server 1: gmail-mcp (93 tools)

Email, Calendar, Contacts, and Subscription management.

### OAuth Scopes

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.labels
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.settings.basic
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/contacts.readonly
https://www.googleapis.com/auth/contacts
```

### Features

#### Email (32 tools)

**Reading & Search:**
- `list_emails`, `search_emails`, `get_email`, `get_email_overview`, `get_email_count`
- `get_thread`, `get_thread_summary`

**Composing:**
- `compose_email`, `forward_email`, `prepare_email_reply`, `send_email_reply`, `confirm_send_email`

**Organization:**
- `archive_email`, `trash_email`, `delete_email`, `star_email`, `unstar_email`
- `mark_as_read`, `mark_as_unread`

**Labels:**
- `list_labels`, `create_label`, `delete_label`, `apply_label`, `remove_label`

**Attachments:**
- `get_attachments`, `download_attachment`

**Bulk Operations:**
- `bulk_archive`, `bulk_label`, `bulk_remove_label`, `bulk_trash`, `cleanup_old_emails`

**Drafts:**
- `list_drafts`, `get_draft`, `update_draft`, `delete_draft`

**Filters:**
- `list_filters`, `create_filter`, `delete_filter`, `get_filter`

**Settings:**
- `get_vacation_responder`, `set_vacation_responder`, `disable_vacation_responder`

**Retention:**
- `setup_retention_labels`, `enforce_retention_policies`, `get_retention_status`

**Claude Review:**
- `setup_claude_review_labels`, `get_emails_for_claude_review`, `create_claude_review_filter`

#### Calendar (15 tools)

**Events:**
- `list_calendar_events`, `create_calendar_event`, `create_recurring_event`
- `update_calendar_event`, `delete_calendar_event`, `rsvp_event`
- `get_calendar_event`, `duplicate_calendar_event`

**Scheduling:**
- `suggest_meeting_times`, `find_free_time`, `check_conflicts`, `check_attendee_availability`
- `add_travel_buffer` - Add blocking travel time before meetings

**Multi-Calendar:**
- `list_calendars`, `get_daily_agenda`

#### Contacts (17 tools)

**Basic (read-only):**
- `list_contacts`, `search_contacts`, `get_contact`

**CRUD (requires write scope):**
- `create_contact`, `update_contact`, `delete_contact`

**Hygiene:**
- `find_duplicate_contacts` - Fuzzy matching for potential duplicates
- `find_stale_contacts` - Contacts with no email activity in N months
- `find_incomplete_contacts` - Contacts missing required fields
- `merge_contacts` - Combine duplicate contacts
- `enrich_contact_from_email` - Extract info from email signatures

**Groups:**
- `list_contact_groups`, `create_contact_group`, `delete_contact_group`
- `add_contacts_to_group`, `remove_contacts_from_group`

**Export:**
- `export_contacts` - Export to CSV

#### Subscriptions (6 tools)

- `setup_subscription_labels` - Create Subscriptions/Review, Retained, Unsubscribed labels
- `find_subscription_emails` - Find newsletter senders with unsubscribe links
- `get_unsubscribe_link` - Extract unsubscribe link from email
- `unsubscribe_and_cleanup` - Full unsubscribe workflow (get link, create filter, archive)
- `create_subscription_filter` - Create filter for subscription sender (retain or junk)
- `mark_sender_as_junk` - Filter sender to trash and report spam

#### Vault Integration (2 tools)

- `save_email_to_vault`, `batch_save_emails_to_vault`

### NLP Date Support

All date parameters support natural language:
- `tomorrow`, `next monday`, `in 3 days`
- `last week`, `past 7 days`, `this month`
- `tomorrow at 2pm`, `next friday at 10am`
- Recurrence: `every weekday`, `biweekly`, `daily for 2 weeks`

---

## Server 2: drive-mcp (54 tools)

Google Drive file management. Shares OAuth tokens with gmail-mcp.

### Additional OAuth Scopes

```
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.labels
https://www.googleapis.com/auth/drive.activity.readonly
```

### Features

#### File Operations (12 tools)
- `list_drive_files`, `search_drive_files`, `get_drive_file`, `read_drive_file`
- `create_drive_file`, `update_drive_file`, `rename_drive_file`, `move_drive_file`
- `copy_drive_file`, `trash_drive_file`, `restore_drive_file`, `delete_drive_file`

#### Folders (3 tools)
- `create_drive_folder`, `get_folder_tree`, `get_folder_path`

#### Google Workspace Files (4 tools)
- `create_google_doc`, `create_google_sheet`, `create_google_slides`, `export_google_file`

#### Sharing & Permissions (6 tools)
- `get_drive_permissions`, `share_drive_file`, `update_drive_permission`
- `remove_drive_permission`, `transfer_drive_ownership`, `create_drive_shortcut`

#### Shared Drives (3 tools)
- `list_shared_drives`, `get_shared_drive`, `list_shared_drive_members`

#### Bulk Operations (4 tools)
- `bulk_move_files`, `bulk_trash_files`, `bulk_delete_files`, `bulk_share_files`

#### Storage & Activity (2 tools)
- `get_drive_quota`, `get_drive_activity`

#### Drive Labels (6 tools)
- `list_drive_labels`, `get_drive_label`, `get_file_labels`
- `set_file_label`, `remove_file_label`, `search_by_label`

#### Drive OCR (3 tools)
Uses Google Drive's native OCR to extract text from images/PDFs:
- `upload_image_with_ocr`, `ocr_existing_image`, `upload_pdf_with_ocr`

---

## Server 3: docs-mcp (32 tools)

Local document processing. **No Google auth required.**

### Dependencies

```bash
# Office documents
pip install python-docx openpyxl python-pptx

# PDF processing
pip install pypdf pdfplumber

# OCR (optional)
pip install pytesseract pdf2image Pillow

# System dependencies for OCR
brew install tesseract poppler  # macOS
# apt install tesseract-ocr poppler-utils  # Linux
```

### Features

#### Office Reading (3 tools)
- `read_docx_content` - Extract text, tables, structure from DOCX
- `read_xlsx_content` - Read spreadsheet data (sheets, cells, formulas)
- `read_pptx_content` - Extract slides, text, speaker notes

#### Office Templates (6 tools)
- `fill_docx_template`, `fill_xlsx_template`, `fill_pptx_template`
- `create_docx_from_template`, `create_xlsx_from_template`, `create_pptx_from_template`

Template syntax: `{{variable_name}}` placeholders in documents.

#### Office Export (3 tools)
- `docx_to_markdown`, `xlsx_to_csv`, `pptx_to_markdown`

#### PDF Processing (7 tools)
- `read_pdf_content` - Extract text from native PDFs
- `get_pdf_metadata` - Get PDF properties
- `pdf_to_markdown` - Convert to markdown
- `extract_pdf_images` - Extract embedded images
- `merge_pdfs` - Combine multiple PDFs
- `split_pdf` - Split into separate pages/ranges
- `fill_pdf_form` - Fill PDF form fields

#### Local OCR (4 tools)
Uses Tesseract for offline OCR:
- `ocr_image_local` - OCR image files (PNG, JPG, TIFF, etc.)
- `ocr_pdf_local` - OCR scanned PDFs
- `ocr_file` - Auto-detect and OCR any supported file
- `ocr_to_vault` - OCR and save to vault

#### Vault Integration (4 tools)
- `save_text_to_vault` - Save text content as markdown
- `save_file_to_vault` - Save any file to vault
- `batch_save_to_vault` - Save multiple files
- `doc_to_vault` - Convert document to markdown and save

---

## Architecture

```
gmail-mcp-extended/
├── gmail_mcp/                    # Server 1: Email + Calendar + Contacts
│   ├── main.py                   # Entry point
│   ├── auth/                     # OAuth management
│   ├── gmail/                    # Gmail helpers
│   ├── calendar/                 # Calendar processing
│   └── mcp/tools/                # Tool definitions
│       ├── email.py
│       ├── calendar.py
│       ├── contacts.py
│       ├── subscriptions.py
│       └── ...
│
├── drive_mcp/                    # Server 2: Google Drive
│   ├── main.py                   # Entry point
│   ├── drive/processor.py        # Drive API wrapper
│   └── mcp/tools/                # Tool definitions
│
├── docs_mcp/                     # Server 3: Local Documents
│   ├── main.py                   # Entry point
│   ├── processors/
│   │   ├── office.py             # DOCX/XLSX/PPTX
│   │   ├── pdf.py                # PDF operations
│   │   ├── ocr.py                # Tesseract OCR
│   │   └── vault.py              # Vault export
│   └── mcp/tools/                # Tool definitions
│
├── shared/                       # Shared utilities
│   └── types.py                  # TypedDict definitions
│
├── tests/                        # Test suite (417 tests)
│
└── pyproject.toml                # All three entry points
```

---

## Usage Examples

### gmail-mcp
```
"Send an email to john@example.com about the meeting"
"What's on my calendar next week?"
"Archive all newsletters older than 30 days"
"Find a free hour for a meeting with Alice tomorrow"
"Find subscription emails and show me unsubscribe options"
"Add 30 minutes travel time before my 2pm meeting"
```

### drive-mcp
```
"List files in my project folder"
"Share the budget spreadsheet with the team"
"Search Drive for files modified this week"
"Export the proposal doc as PDF"
"OCR this scanned receipt and extract the text"
```

### docs-mcp
```
"Read the contents of report.docx"
"Fill the invoice template with this data"
"Convert this PDF to markdown"
"OCR this image and save to my vault"
"Merge these three PDFs into one"
```

---

## Configuration

### config.yaml

```yaml
server:
  host: localhost
  port: 8000
  debug: false
  log_level: INFO

calendar:
  enabled: true

contacts:
  contacts_api_enabled: true

vault:
  inbox_folder: 0-inbox
  attachment_folder: attachments
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | gmail/drive | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | gmail/drive | OAuth client secret |
| `TOKEN_ENCRYPTION_KEY` | gmail/drive | Fernet encryption key |
| `VAULT_PATH` | Optional | Path to Obsidian vault |
| `CONFIG_FILE_PATH` | Optional | Path to config.yaml |

---

## Security

- **Encrypted Token Storage**: OAuth tokens encrypted at rest (Fernet + PBKDF2)
- **CSRF Protection**: OAuth state verification
- **Automatic Token Refresh**: Tokens refreshed on expiry
- **Shared Auth**: drive-mcp reuses gmail-mcp tokens (no re-auth needed)

---

## Testing

```bash
source .venv/bin/activate
pytest  # 417 tests
```

---

## License

MIT License

## Credits

- Original: [bastienchabal/gmail-mcp](https://github.com/bastienchabal/gmail-mcp)
- Extended by: [@mideliberto](https://github.com/mideliberto)
