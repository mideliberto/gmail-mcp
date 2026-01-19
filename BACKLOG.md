# Gmail MCP Backlog

## Development Workflow

**Before any major work:**
1. `cd /Users/mike/gmail-mcp && source .venv/bin/activate`
2. `pytest tests/ -v --tb=short` - capture baseline (264 passed)
3. Plan the changes (update this file or create issue)
4. Implement changes
5. `pytest tests/ -v --tb=short` - compare output
6. Fix any regressions
7. Update docs (`README.md`, `docs/overview.md`)
8. Update `_claude/gmail-mcp-test-plan.md` if needed
9. Commit and push

---

## Priority Matrix

| Priority | Items |
|----------|-------|
| **High** | Thread View, Draft Management, Scheduled Send, Bulk Operations Bug |
| **Medium** | Retention Labels, Unsubscribe Management, Attendee Free/Busy, Contact Lookup, Event Reminders |
| **Low** | Vacation Responder, Travel Time, DST Handling |
| **Future** | Google Drive Integration |

---

## Bugs

### 20. Bulk Operations Capped at 20 Emails 🐛 HIGH PRIORITY
**Priority:** High
**Issue:** All bulk operations ignore `max_emails` parameter and cap at 20 emails per call.

**Affected functions:**
- `bulk_trash(query, max_emails)` - always processes only 20
- `bulk_archive(query, max_emails)` - always processes only 20
- `bulk_label(query, label_id, max_emails)` - always processes only 20
- `cleanup_old_emails(query, days_old, action, max_emails)` - always processes only 20

**Current behavior:**
```python
bulk_trash(query="label:Dice older_than:7d", max_emails=100)
# Returns: {"trashed": 20, "failed": 80}  # Only 20 processed regardless
```

**Expected behavior:**
- Should loop through all matching emails up to `max_emails`
- Or process in batches of 20 until done
- Return accurate count of processed emails

**Root cause:** Likely missing pagination loop in bulk operation functions.

**Fix approach:**
1. Audit ALL batched/looped operations in the codebase (not just bulk_*)
2. Find where pagination is handled
3. Ensure loop continues until:
   - All matching emails processed, OR
   - `max_emails` limit reached, OR
   - No more results (next_page_token is None)

**Files to check:**
- `gmail_mcp/mcp/tools/email_manage.py` (bulk_trash, bulk_archive, bulk_label)
- `gmail_mcp/mcp/tools/email_read.py` (cleanup_old_emails)
- Any other function that processes multiple items in batches

**Estimated scope:** ~50-100 lines to fix across multiple files

---

### 23. Filter Creation Requires Missing OAuth Scope 🐛
**Priority:** Medium
**Issue:** `create_filter()` and related filter functions fail with 403 Insufficient Permission.

**Error:**
```
Request had insufficient authentication scopes.
Insufficient Permission
```

**Root cause:** Missing `https://www.googleapis.com/auth/gmail.settings.basic` OAuth scope.

**Fix:**
1. Add scope to `gmail_mcp/auth/oauth.py` SCOPES list
2. User must re-authenticate to grant new scope
3. Test filter creation

**Files:**
- `gmail_mcp/auth/oauth.py`

**Estimated scope:** ~5 lines code, but requires user re-auth

---

## Email Features

### 11. Thread/Conversation View ⭐ HIGH PRIORITY
**Priority:** High
**Issue:** `get_email()` returns single message, not full conversation context.

**Current behavior:**
```python
get_email(email_id="...")  # Returns single message only
```

**Desired behavior:**
```python
get_thread(thread_id="...")  # Returns full conversation
get_email(email_id="...", include_thread=True)  # Option to include thread context
```

**Use cases:**
- Understanding full context before replying
- Seeing what was already discussed
- Finding specific info buried in long email chains

**Game Plan:**

1. **Phase 1: Core Thread Retrieval**
   - New file: `gmail_mcp/mcp/tools/email_thread.py`
   - New function: `get_thread(thread_id: str) -> Dict`
   - Uses Gmail API `threads().get()` with `format=full`
   - Returns:
     ```json
     {
       "thread_id": "...",
       "subject": "Re: Project Update",
       "message_count": 5,
       "participants": ["alice@co.com", "bob@co.com"],
       "messages": [
         {"id": "...", "from": "...", "date": "...", "snippet": "...", "body": "..."},
         ...
       ],
       "thread_link": "https://mail.google.com/mail/u/0/#inbox/..."
     }
     ```

2. **Phase 2: Smart Summarization**
   - Add `get_thread_summary(thread_id: str) -> Dict`
   - Returns condensed view for long threads:
     - First message (original)
     - Key participants
     - Timeline of replies
     - Last 2-3 messages in full
     - Total message count

3. **Phase 3: Integration**
   - Update `get_email()` to accept `include_thread: bool = False`
   - Update `prepare_email_reply()` to use thread context
   - Update `list_emails()` to include `thread_id` in results (already does via Gmail API)

**Files:**
- `gmail_mcp/mcp/tools/email_thread.py` (new)
- `gmail_mcp/mcp/tools/email_read.py` (update get_email)
- `gmail_mcp/mcp/tools/email_compose.py` (update prepare_email_reply)
- `tests/test_email_thread.py` (new)

**API Reference:**
- `threads().get(userId, id, format)` - https://developers.google.com/gmail/api/reference/rest/v1/users.threads/get
- `threads().list(userId, q)` - https://developers.google.com/gmail/api/reference/rest/v1/users.threads/list

**Estimated scope:** ~200 lines code, ~100 lines tests

---

### 12. Draft Management
**Priority:** High
**Issue:** Can create drafts but can't list, edit, or delete existing ones.

**Current behavior:**
- `compose_email()` creates draft
- `send_email_reply()` creates draft
- No way to manage drafts after creation

**Desired behavior:**
```python
list_drafts(max_results=10)  # List all drafts
get_draft(draft_id="...")  # Get draft content
update_draft(draft_id="...", body="...", subject="...")  # Edit draft
delete_draft(draft_id="...")  # Delete draft
```

**Implementation:**
- New file: `gmail_mcp/mcp/tools/email_drafts.py`
- Uses Gmail API `drafts()` resource
- Functions:
  - `list_drafts(max_results: int = 10) -> Dict`
  - `get_draft(draft_id: str) -> Dict`
  - `update_draft(draft_id: str, to: str = None, subject: str = None, body: str = None) -> Dict`
  - `delete_draft(draft_id: str) -> Dict`

**Files:**
- `gmail_mcp/mcp/tools/email_drafts.py` (new)
- `tests/test_email_drafts.py` (new)

**Estimated scope:** ~150 lines code, ~80 lines tests

---

### 13. Scheduled Send
**Priority:** High
**Issue:** Can't schedule emails to send later.

**Current behavior:**
- Emails send immediately after confirmation

**Desired behavior:**
```python
compose_email(to="...", subject="...", body="...", send_at="tomorrow 8am")
compose_email(to="...", subject="...", body="...", send_at="2026-01-25T09:00:00")
```

**Implementation:**
- Gmail API doesn't have native scheduled send via API
- **Workaround options:**
  1. Create draft + calendar reminder to send (hacky)
  2. Use Gmail's native schedule feature via SMTP (limited)
  3. Store locally and use cron/scheduler (requires persistent service)

- **Recommended approach:** Option 1 for now
  - Create draft
  - Create calendar event as reminder: "Send email: [subject]"
  - Include draft link in event description
  - User manually sends or Claude sends when reminded

- **Future:** If Gmail API adds scheduled send support, switch to native

**Files:**
- `gmail_mcp/mcp/tools/email_compose.py` (update compose_email)
- `gmail_mcp/mcp/tools/calendar.py` (helper to create send reminder)

**Estimated scope:** ~50 lines code (workaround approach)

---

### 21. Retention Labels & Automated Cleanup
**Priority:** Medium
**Issue:** No structured way to manage email retention policies.

**Concept:**
1. Create retention labels (e.g., `Retention/7-days`, `Retention/30-days`, `Retention/1-year`)
2. Apply to newsletters, notifications, receipts, etc.
3. Claude workflow to periodically delete emails past their retention window

**Implementation:**

**Phase 1: Label Setup**
```python
setup_retention_labels()
# Creates:
# - Retention/7-days
# - Retention/30-days
# - Retention/90-days
# - Retention/1-year
# - Retention/Forever (never auto-delete)
```

**Phase 2: Retention Enforcement**
```python
enforce_retention_policies(dry_run=True)
# Scans each retention label
# Finds emails older than retention period
# dry_run=True: Reports what would be deleted
# dry_run=False: Actually deletes (with confirmation)

# Returns:
{
  "7-days": {"count": 45, "oldest": "2026-01-10"},
  "30-days": {"count": 12, "oldest": "2025-12-15"},
  ...
}
```

**Phase 3: Filter Integration**
```python
create_retention_filter(
    from_address="notifications@github.com",
    retention="30-days",
    archive=True  # Skip inbox, apply retention label
)
```

**Claude Workflow:**
- Weekly prompt: "Run retention cleanup - show me what's expiring, confirm before delete"
- Can be added to `/daily` workflow as optional step

**Files:**
- `gmail_mcp/mcp/tools/email_retention.py` (new)
- `tests/test_email_retention.py` (new)

**Estimated scope:** ~150 lines code, ~60 lines tests

---

### 22. Unsubscribe Management
**Priority:** Medium
**Issue:** No systematic way to manage newsletters/subscriptions.

**Concept:**
1. Find emails with unsubscribe links (already have `find_unsubscribe_link`)
2. Create smart label for potential subscriptions
3. Workflow to triage: unsubscribe, junk, or retain

**Implementation:**

**Phase 1: Discovery**
```python
find_subscription_emails(max_results=100, unlabeled_only=True)
# Searches: has:unsubscribe -label:Subscription/*
# Returns list with sender, frequency, unsubscribe link

# Returns:
{
  "subscriptions": [
    {
      "from": "newsletter@techsite.com",
      "count": 15,
      "frequency": "daily",
      "unsubscribe_link": "https://...",
      "sample_subject": "Daily Tech Digest"
    },
    ...
  ]
}
```

**Phase 2: Triage Actions**
```python
# Option 1: Unsubscribe and archive existing
unsubscribe_and_cleanup(from_address="newsletter@spam.com")
# - Finds unsubscribe link
# - Returns link for user to click (or auto-request if simple)
# - Creates filter to auto-trash future emails
# - Archives existing emails from sender

# Option 2: Keep but organize
create_subscription_filter(
    from_address="newsletter@goodsite.com",
    action="retain",
    retention="30-days",  # Optional: auto-cleanup old ones
    skip_inbox=True
)
# Creates filter: apply Subscription/Retained label, archive

# Option 3: Mark as junk
mark_as_junk(from_address="spammer@bad.com")
# Creates filter to auto-trash
# Reports as spam
# Trashes existing emails
```

**Phase 3: Labels**
```python
setup_subscription_labels()
# Creates:
# - Subscription/Review (newly discovered)
# - Subscription/Retained (keeping)
# - Subscription/Unsubscribed (processed, filter created)
```

**Claude Workflow:**
- Weekly/monthly prompt: "Show me subscription emails I haven't triaged"
- For each: "Unsubscribe, junk, or keep? If keep, what retention?"

**Files:**
- `gmail_mcp/mcp/tools/email_subscriptions.py` (new)
- `tests/test_email_subscriptions.py` (new)

**Estimated scope:** ~200 lines code, ~80 lines tests

**Note:** Automatic unsubscription (HTTP request to unsubscribe link) is risky - some links confirm the email is active. Better to return the link for user to click manually.

---

### 14. Vacation Responder / Out of Office
**Priority:** Low
**Issue:** Can't set up auto-reply when away.

**Desired behavior:**
```python
set_vacation_responder(
    enabled=True,
    start_date="2026-02-01",
    end_date="2026-02-07",
    subject="Out of Office",
    message="I'm away until Feb 7. For urgent matters, contact...",
    contacts_only=False
)
get_vacation_responder()  # Check current status
disable_vacation_responder()
```

**Implementation:**
- Uses Gmail API `settings.updateVacation()`
- https://developers.google.com/gmail/api/reference/rest/v1/users.settings/updateVacation

**Files:**
- `gmail_mcp/mcp/tools/email_settings.py` (new)
- `tests/test_email_settings.py` (new)

**Estimated scope:** ~80 lines code, ~40 lines tests

---

## Calendar Features

### 15. Attendee Free/Busy Query
**Priority:** Medium
**Issue:** Can check own availability but not others'.

**Current behavior:**
- `find_free_time()` checks user's calendars only
- `suggest_meeting_times()` only considers user's schedule

**Desired behavior:**
```python
check_availability(
    attendees=["bob@company.com", "alice@company.com"],
    start="tomorrow",
    end="friday",
    duration="1 hour"
)
# Returns times when ALL attendees are free
```

**Implementation:**
- Uses Calendar API `freebusy.query()`
- https://developers.google.com/calendar/api/v3/reference/freebusy/query
- Note: Only works for attendees who share their calendar or are in same org

**Files:**
- `gmail_mcp/mcp/tools/conflict.py` (add check_availability)
- `tests/test_conflict.py`

**Estimated scope:** ~100 lines code, ~50 lines tests

---

### 16. Event Reminders/Notifications
**Priority:** Medium
**Issue:** Events use default reminder settings, can't customize per-event.

**Current behavior:**
```python
create_calendar_event(summary="...", start_time="...")  # Uses default reminders
```

**Desired behavior:**
```python
create_calendar_event(
    summary="...",
    start_time="...",
    reminders=[
        {"method": "popup", "minutes": 30},
        {"method": "email", "minutes": 1440}  # 1 day before
    ]
)
# Or NLP:
create_calendar_event(..., remind_me="30 minutes before and 1 day before by email")
```

**Implementation:**
- Add `reminders` parameter to `create_calendar_event()` and `update_calendar_event()`
- Parse NLP reminder strings: "30 minutes before", "1 hour before", "1 day before by email"
- Map to Google Calendar reminder format

**Files:**
- `gmail_mcp/mcp/tools/calendar.py`
- `gmail_mcp/utils/date_parser.py` (add parse_reminder)
- `tests/test_calendar_tools.py`

**Estimated scope:** ~80 lines code, ~40 lines tests

---

### 17. Travel Time Buffer
**Priority:** Low
**Issue:** No automatic travel time between events with locations.

**Desired behavior:**
```python
create_calendar_event(
    summary="Meeting at Client Office",
    start_time="tomorrow 2pm",
    location="123 Main St, Chicago",
    add_travel_time=True,  # Auto-adds buffer event before
    travel_from="Home"  # Or previous event location
)
```

**Implementation:**
- Complex - requires:
  - Location geocoding (Google Maps API)
  - Travel time estimation
  - Creating blocking event before main event
- **Simpler alternative:** Manual travel buffer
  ```python
  add_travel_buffer(event_id="...", minutes=30, label="Travel to meeting")
  ```

**Recommendation:** Start with simple manual buffer, skip auto-calculation for now.

**Files:**
- `gmail_mcp/mcp/tools/calendar.py`

**Estimated scope:** ~40 lines (simple version)

---

## Contact Integration

### 18. Contact Lookup
**Priority:** Medium
**Issue:** No access to Google Contacts.

**Desired behavior:**
```python
search_contacts(query="Bob Smith")  # Find contacts by name
get_contact(email="bob@company.com")  # Get contact details
list_contacts(max_results=50)  # List all contacts
```

**Returns:**
```json
{
  "name": "Bob Smith",
  "email": "bob@company.com",
  "phone": "+1-555-123-4567",
  "organization": "Acme Corp",
  "title": "Director of Engineering",
  "notes": "Met at conference 2025"
}
```

**Implementation:**
- Uses Google People API (not Gmail API)
- https://developers.google.com/people/api/rest
- Requires additional OAuth scope: `https://www.googleapis.com/auth/contacts.readonly`
- New service initialization in `services.py`

**Files:**
- `gmail_mcp/utils/services.py` (add People API service)
- `gmail_mcp/mcp/tools/contacts.py` (new)
- `gmail_mcp/auth/oauth.py` (add scope)
- `tests/test_contacts.py` (new)

**Estimated scope:** ~150 lines code, ~60 lines tests

---

## Low Priority / Polish

### 3. DST Transition Handling
**Priority:** Low
**Status:** Documented, not implemented

Edge case handling for daylight saving time transitions. Only affects ~2 hours per year.

---

### 9. Relative Email Count
**Priority:** Low
**Status:** Skip unless requested

`list_emails(count="last 10")` - Claude handles this naturally.

---

## Google Drive Integration (Future)

### 19. Drive Integration - Full Spec

**Priority:** Future (separate phase)
**Scope:** Large - effectively doubles the MCP functionality

#### 19.1 Core File Operations

```python
# List and search
list_drive_files(folder_id=None, query=None, max_results=20)
search_drive(query="quarterly report", file_type="document")
get_file_info(file_id="...")

# Upload and download
upload_file(local_path="/path/to/file.pdf", folder_id=None, name=None)
download_file(file_id="...", local_path="/path/to/save")

# Management
create_folder(name="Project X", parent_id=None)
move_file(file_id="...", new_parent_id="...")
rename_file(file_id="...", new_name="...")
delete_file(file_id="...")  # Moves to trash
permanently_delete_file(file_id="...")

# Sharing
share_file(file_id="...", email="bob@co.com", role="reader|writer|commenter")
get_sharing_settings(file_id="...")
remove_sharing(file_id="...", email="bob@co.com")
get_shareable_link(file_id="...", anyone_with_link=False)
```

#### 19.2 Google Docs

```python
# Creation
create_doc(title="Meeting Notes", content=None, folder_id=None)
create_doc_from_template(template_id="...", title="...", replacements={"{{NAME}}": "Mike"})

# Reading
get_doc_content(doc_id="...")  # Returns markdown or plain text
get_doc_outline(doc_id="...")  # Returns headers/structure

# Editing
append_to_doc(doc_id="...", content="New paragraph here")
insert_in_doc(doc_id="...", content="...", index=0)  # Insert at position
replace_in_doc(doc_id="...", find="old text", replace="new text")
update_doc(doc_id="...", content="Full new content")  # Replace all

# Export
export_doc(doc_id="...", format="pdf|docx|md|txt", local_path="...")
```

#### 19.3 Google Sheets

```python
# Creation
create_sheet(title="Budget 2026", folder_id=None)
create_sheet_from_template(template_id="...", title="...")

# Reading
get_sheet_data(sheet_id="...", range="Sheet1!A1:D10")
get_sheet_info(sheet_id="...")  # Metadata, sheet names, etc.
get_all_sheets(sheet_id="...")  # List tabs in spreadsheet

# Writing
update_sheet_cells(sheet_id="...", range="A1:B2", values=[["a", "b"], ["c", "d"]])
append_sheet_row(sheet_id="...", sheet_name="Sheet1", values=["col1", "col2", "col3"])
insert_sheet_row(sheet_id="...", row_index=5, values=[...])
delete_sheet_rows(sheet_id="...", start_row=5, end_row=10)

# Sheet management
add_sheet_tab(sheet_id="...", title="New Tab")
delete_sheet_tab(sheet_id="...", tab_id=123)
rename_sheet_tab(sheet_id="...", tab_id=123, new_name="...")

# Formatting (limited)
format_sheet_range(sheet_id="...", range="A1:D1", bold=True, background_color="#cccccc")

# Export
export_sheet(sheet_id="...", format="xlsx|csv|pdf", local_path="...")
```

#### 19.4 Google Slides (Lower Priority)

```python
create_presentation(title="Q1 Review")
get_presentation_outline(presentation_id="...")
add_slide(presentation_id="...", layout="TITLE_AND_BODY")
update_slide_text(presentation_id="...", slide_index=0, placeholder="TITLE", text="...")
export_presentation(presentation_id="...", format="pptx|pdf", local_path="...")
```

#### 19.5 Integration Features

```python
# Email + Drive
attach_drive_file(email_draft_id="...", file_id="...")  # Attach Drive file to email
save_attachment_to_drive(email_id="...", attachment_id="...", folder_id="...")

# Calendar + Drive
attach_file_to_event(event_id="...", file_id="...")
create_meeting_notes(event_id="...")  # Creates doc linked to event

# Cross-service search
search_all(query="quarterly report")  # Search emails, drive, calendar
```

#### Implementation Plan

**Phase 1: Core Drive (Est. 400 lines)**
- File listing, search, upload, download
- Folder operations
- Basic sharing

**Phase 2: Docs (Est. 300 lines)**
- Create, read, append, export
- Template support

**Phase 3: Sheets (Est. 400 lines)**
- Create, read, write cells
- Append rows, basic formatting
- Export

**Phase 4: Integration (Est. 200 lines)**
- Email attachments ↔ Drive
- Calendar ↔ Drive linking

**Phase 5: Slides (Est. 150 lines)**
- Basic creation and export
- Lower priority

**Total estimated scope:** ~1,500 lines code, ~500 lines tests

**New dependencies:**
- `google-api-python-client` (already have)
- Additional OAuth scopes:
  - `https://www.googleapis.com/auth/drive`
  - `https://www.googleapis.com/auth/documents`
  - `https://www.googleapis.com/auth/spreadsheets`
  - `https://www.googleapis.com/auth/presentations`

**New files:**
```
gmail_mcp/
├── drive/
│   ├── __init__.py
│   ├── files.py       # Core file operations
│   ├── docs.py        # Google Docs
│   ├── sheets.py      # Google Sheets
│   └── slides.py      # Google Slides
├── mcp/tools/
│   ├── drive_files.py
│   ├── drive_docs.py
│   ├── drive_sheets.py
│   └── drive_slides.py
tests/
├── test_drive_files.py
├── test_drive_docs.py
├── test_drive_sheets.py
└── test_drive_slides.py
```

**Recommendation:** Drive integration should be a separate project phase. Current Gmail+Calendar MCP is solid. Drive is a significant expansion that should be planned and executed as its own sprint.

---

## Completed

### ✅ NLP Date Parsing (2026-01-19)
- Added `dateparser` dependency
- Created centralized `date_parser.py`
- Updated all calendar functions to use NLP
- Added `recurrence_pattern` NLP for recurring events
- 50+ unit tests
- Updated README and docs

### ✅ Backlog Items 1,2,5,6,7,8,10 (2026-01-19)
- **#1 Week Range Handling**: `parse_week_range()` for "this week", "next week", "last week", "past N days"
- **#2 Better Error Messages**: `DATE_PARSING_HINT` constant with helpful examples in all date errors
- **#5 Past Date Preference**: `detect_date_direction()` auto-detects past/future based on keywords
- **#6 Working Hours Parsing**: `parse_working_hours()` supports "9-17", "9am-5pm", "9am to 5pm"
- **#7 Duration Parsing**: `parse_duration()` supports "1 hour", "90 minutes", "half hour"
- **#8 Email Search Date NLP**: `search_emails()` now accepts `after`, `before`, `date_range` NLP parameters
- **#10 Label Fuzzy Matching**: `apply_label()` and `remove_label()` accept `label` name parameter with case-insensitive matching

---

## Test Baseline

As of 2026-01-19 (post-backlog):
```
264 passed, 4 warnings
```

Warnings are dateparser deprecation notices (upstream issue, not actionable).
