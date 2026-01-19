# Gmail MCP Backlog

## Development Workflow

**Before any major work:**
1. `cd /Users/mike/gmail-mcp && source .venv/bin/activate`
2. `pytest tests/ -v --tb=short` - capture baseline (should be 241 passed)
3. Plan the changes (update this file or create issue)
4. Implement changes
5. `pytest tests/ -v --tb=short` - compare output
6. Fix any regressions
7. Update docs (`README.md`, `docs/overview.md`)
8. Update `_claude/gmail-mcp-test-plan.md` if needed
9. Commit and push

---

## NLP Improvements

### 1. Week Range Handling
**Priority:** Medium
**Issue:** "next week" and "this week" parse to single points, not ranges.

**Current behavior:**
- `time_min="next week"` → some arbitrary point
- `time_max="next week"` → same point

**Desired behavior:**
- For range parameters (`time_min`/`time_max`, `start_date`/`end_date`):
  - "this week" → Monday 00:00 to Friday 23:59 (or Sunday?)
  - "next week" → Next Monday to next Friday
  - "last week" → Previous Monday to previous Friday

**Implementation:**
- Add `parse_week_range()` function to `date_parser.py`
- Detect "this/next/last week" patterns
- Return tuple of (start, end) datetimes
- Update tools to use range parsing when appropriate

**Files:**
- `gmail_mcp/utils/date_parser.py`
- `gmail_mcp/mcp/tools/calendar.py` (list_calendar_events)
- `gmail_mcp/mcp/tools/conflict.py` (check_conflicts, find_free_time)
- `tests/test_date_parser.py`

---

### 2. Better Error Messages for Date Parsing
**Priority:** Medium
**Issue:** Generic "Could not parse date: X" doesn't help users.

**Current behavior:**
```json
{"success": false, "error": "Could not parse start time: blahblah"}
```

**Desired behavior:**
```json
{
  "success": false,
  "error": "Could not parse date: 'blahblah'",
  "hint": "Supported formats: 'tomorrow', 'next monday', 'in 3 days', '2026-01-20', 'next week at 2pm'"
}
```

**Implementation:**
- Add `DATE_PARSING_HINT` constant with examples
- Update all date parsing error responses to include hint
- Consider adding `suggest_similar()` for typos (e.g., "tomorow" → "Did you mean 'tomorrow'?")

**Files:**
- `gmail_mcp/utils/date_parser.py` (add hint constant)
- `gmail_mcp/mcp/tools/calendar.py`
- `gmail_mcp/mcp/tools/conflict.py`
- `gmail_mcp/calendar/processor.py`

---

### 3. DST Transition Handling
**Priority:** Low
**Issue:** "tomorrow at 2am" during DST spring-forward could fail or produce unexpected results.

**Edge cases:**
- Spring forward: 2am doesn't exist (skipped)
- Fall back: 2am exists twice (ambiguous)

**Implementation:**
- Add DST-aware handling in `parse_natural_date()`
- For spring forward: Round to 3am with warning log
- For fall back: Default to first occurrence (standard time)
- Add test cases for DST transitions

**Files:**
- `gmail_mcp/utils/date_parser.py`
- `tests/test_date_parser.py`

**Note:** Low priority because it only affects ~2 hours per year and user's timezone must be configured.

---

### 5. Past Date Preference for Historical Queries
**Priority:** Medium
**Issue:** `prefer_future=True` default can misinterpret historical queries.

**Problem scenario:**
- Today is Tuesday
- User: "show events from last monday"
- With `prefer_future=True`, might pick "this monday" (yesterday) instead of last week's Monday

**Implementation options:**

**Option A: Context-aware preference**
- Detect "last X" patterns and force `prefer_future=False`
- Already partially handled in `_parse_day_of_week_pattern()` but verify

**Option B: Explicit parameter**
- Add `prefer_past: bool` parameter to relevant tools
- Let Claude/user explicitly request past dates

**Option C: Smarter detection**
- If query contains "last", "ago", "previous", "before" → prefer past
- If query contains "next", "upcoming", "in", "after" → prefer future

**Recommendation:** Option C - transparent to users, handles most cases.

**Files:**
- `gmail_mcp/utils/date_parser.py`
- `tests/test_date_parser.py`

---

## Other NLP Opportunities

### 6. Working Hours Parsing
**Priority:** Low
**Issue:** `working_hours` parameter requires "9-17" format.

**Current behavior:**
```python
find_free_time(date="tomorrow", working_hours="9-17")
```

**Desired behavior:**
```python
find_free_time(date="tomorrow", working_hours="9am to 5pm")
find_free_time(date="tomorrow", working_hours="9:00-17:00")
find_free_time(date="tomorrow", working_hours="9am-5pm")
```

**Implementation:**
- Add `parse_working_hours()` function to `date_parser.py`
- Support formats: "9-17", "9:00-17:00", "9am-5pm", "9am to 5pm"
- Return tuple of (start_hour: int, end_hour: int)
- Fallback to 9-17 if parsing fails

**Files:**
- `gmail_mcp/utils/date_parser.py`
- `gmail_mcp/mcp/tools/conflict.py` (find_free_time)
- `gmail_mcp/mcp/tools/calendar.py` (suggest_meeting_times)
- `tests/test_date_parser.py`

---

### 7. Duration Parsing
**Priority:** Low
**Issue:** `duration_minutes` is integer-only, not user-friendly.

**Current behavior:**
```python
find_free_time(date="tomorrow", duration_minutes=60)
suggest_meeting_times(start_date="tomorrow", end_date="friday", duration_minutes=90)
```

**Desired behavior:**
```python
find_free_time(date="tomorrow", duration="1 hour")
find_free_time(date="tomorrow", duration="90 minutes")
find_free_time(date="tomorrow", duration="1.5 hours")
find_free_time(date="tomorrow", duration="30 min")
```

**Implementation:**
- Add `parse_duration()` function to `date_parser.py`
- Support patterns:
  - `"60"` → 60 minutes (backwards compatible)
  - `"1 hour"`, `"1 hr"` → 60 minutes
  - `"90 minutes"`, `"90 min"` → 90 minutes
  - `"1.5 hours"` → 90 minutes
  - `"1 hour 30 minutes"` → 90 minutes
- Add `duration` parameter alongside `duration_minutes` (deprecate old?)

**Files:**
- `gmail_mcp/utils/date_parser.py`
- `gmail_mcp/mcp/tools/calendar.py`
- `gmail_mcp/mcp/tools/conflict.py`
- `tests/test_date_parser.py`

---

### 8. Email Search Date NLP
**Priority:** Medium
**Issue:** Gmail search uses its own date syntax, not NLP.

**Current behavior:**
User must know Gmail syntax:
```python
search_emails(query="from:boss@company.com after:2026/01/13 before:2026/01/20")
```

**Desired behavior:**
NLP dates in search queries:
```python
search_emails(query="from:boss@company.com", date_range="last week")
search_emails(query="invoices", date_range="past 30 days")
search_emails(query="meeting notes", after="last monday", before="today")
```

**Implementation options:**

**Option A: Separate parameters**
- Add `after`, `before`, `date_range` parameters to `search_emails()`
- Parse with `parse_natural_date()`
- Inject into Gmail query as `after:YYYY/MM/DD before:YYYY/MM/DD`

**Option B: Query preprocessing**
- Detect NLP date patterns in query string
- Replace with Gmail syntax before API call
- e.g., "invoices from last week" → "invoices after:2026/01/13 before:2026/01/20"

**Recommendation:** Option A - cleaner, more explicit, easier to test.

**Files:**
- `gmail_mcp/mcp/tools/email_read.py` (search_emails, list_emails)
- `gmail_mcp/utils/date_parser.py` (helper to format Gmail date syntax)
- `tests/test_tools.py`

---

### 9. Relative Email Count
**Priority:** Low
**Issue:** `max_results` is integer-only.

**Current:** `list_emails(max_results=10)`
**Could support:** `list_emails(count="last 10")`, `list_emails(count="first 5")`

Not high value - Claude handles this naturally. Skip unless requested.

---

### 10. Label Name Fuzzy Matching
**Priority:** Low
**Issue:** Label operations require exact label_id.

**Current behavior:**
```python
apply_label(email_id="...", label_id="Label_123")  # Must know exact ID
```

**Desired behavior:**
```python
apply_label(email_id="...", label="Important")  # Fuzzy match by name
apply_label(email_id="...", label="work")  # Case-insensitive
```

**Implementation:**
- Add `label` parameter (string) alongside `label_id`
- If `label` provided, search labels for case-insensitive match
- Error if ambiguous (multiple matches)

**Files:**
- `gmail_mcp/mcp/tools/labels.py`
- `gmail_mcp/mcp/tools/email_manage.py`

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
