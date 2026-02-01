# Google MCP - Project Instructions

> **Location:** ~/dev/google-mcp/
> **Language:** Python
> **Purpose:** Gmail, Calendar, Drive, Docs, Chat MCPs

**Read first:** `~/dev/CLAUDE.md` for universal standards (DEVLOG, error handling, workflow).

---

## Project-Specific

### Key Paths
- Tools: `gmail_mcp/mcp/tools/`, `drive_mcp/mcp/tools/`, etc.
- Auth: `gmail_mcp/auth/token_manager.py`
- Tokens: `~/gmail_mcp_tokens_personal/`, `~/gmail_mcp_tokens_pwp/`

### Testing
- Syntax check: `python -m py_compile <file>`
- Import check: `python -c "from gmail_mcp.mcp.tools.calendar import *"`

### Patterns
- All tools use `@mcp.tool()` decorator
- Calendar tools: `calendar_id: str = "primary"` parameter pattern
- Processor classes handle API calls, tools handle MCP interface

---

*See ~/dev/CLAUDE.md for error handling, DEVLOG requirements, and workflow rules.*
