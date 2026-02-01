# Development Log

> **Purpose:** Durable record of development tasks, decisions, and outcomes.
> **Maintainer:** Appended by Claude Code after each task completion.
> **Format:** Reverse chronological (newest first within each date).

---

## 2026-02-01

### rsvp_event calendar_id parameter
**Origin:** Consistency fix (found during calendar_id work)
**Task:** Add calendar_id parameter to rsvp_event for full consistency
**Changes:**
- Added calendar_id: str = "primary" to rsvp_event
- Updated API calls at lines 902, 917
**Commits:** 1204a52
**Status:** Complete
**Notes:** Commit also included pending changes from 2026-01-31 session (timezone fixes, doc deletions)

### calendar_id parameter consistency (Issue #12)
**Origin:** Issue #12
**Task:** Add calendar_id parameter to all calendar tools
**Changes:**
- Added calendar_id to: create_calendar_event, create_recurring_event, list_calendar_events, update_calendar_event, delete_calendar_event, add_travel_buffer
- Updated docs/gmail-mcp.md with parameter documentation and examples
**Commits:** 8679109, a1d08b6
**Status:** Complete
**Notes:** None

---

## 2026-01-31

### Documentation cleanup and reorganization
**Origin:** Chat design session - MCP standardization
**Task:** Consolidate and clean up documentation structure
**Changes:**
- Deleted obsolete docs: overview.md, structure.md, setup.md, google-docs-api-lists.md
- Content merged into README.md and per-server docs
- Updated tool counts and removed references to deleted code
**Commits:** (included in 1204a52)
**Status:** Complete
**Notes:** Changes were staged but not committed separately; picked up in next day's commit

### Dead code removal
**Origin:** Code review findings
**Task:** Remove harmful and dead code identified in review
**Changes:**
- Deleted detect_events_from_email (created garbage calendar invites)
- Deleted create_formatted_doc, debug_doc_structure, test_gdocs_render from drive_mcp
- Deleted gdocs_builder.py, gdocs_test.py, test_docs_formatter.py
- Deleted duplicate find_unsubscribe_link from bulk.py
**Commits:** (included in 1204a52)
**Status:** Complete
**Notes:** Should have been committed same day; got bundled into later commit

---

