"""
MCP Prompts Module

This module defines all prompts available in the Gmail MCP server.
Prompts are templated messages and workflows for users.
"""

import logging
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger

# Get logger
logger = get_logger(__name__)


def setup_prompts(mcp: FastMCP) -> None:
    """
    Set up all prompts for the Gmail MCP server.
    
    Args:
        mcp (FastMCP): The FastMCP application.
    """
    @mcp.prompt("gmail://quickstart")
    def quickstart_prompt() -> Dict[str, Any]:
        """
        Quick Start Guide for Gmail MCP
        
        This prompt provides a simple guide to get started with the Gmail MCP.
        It includes basic instructions for authentication and common operations.
        """
        return {
            "title": "Gmail MCP Quick Start Guide",
            "description": "Get started with Gmail integration in Claude Desktop",
            "content": """
# Gmail MCP Quick Start Guide

Welcome to the Gmail MCP for Claude Desktop! This integration allows Claude to access and work with your Gmail account and Google Calendar, providing context-aware assistance for your email and scheduling needs.

## Getting Started

1. **Authentication**: First, you need to authenticate with your Google account.
   - Check your authentication status with `check_auth_status()`
   - If not authenticated, use `authenticate()` to start the process
   - A browser window will open for you to sign in and grant permissions
   - Authentication completes automatically via callback

2. **Email Operations**:
   - Get an overview of your inbox with `get_email_overview()`
   - List recent emails with `list_emails(max_results=10, label="INBOX")`
   - Search for specific emails with `search_emails(query="from:example@gmail.com")`
   - View a specific email with `get_email(email_id="...")`

3. **Context-Aware Email Replies**:
   - Prepare a context-rich reply with `prepare_email_reply(email_id="...")`
   - Create a draft reply with `send_email_reply(email_id="...", reply_text="...", include_original=True)`
   - After reviewing and confirming, send the email with `confirm_send_email(draft_id="...")`

4. **Calendar Integration**:
   - Create calendar events with `create_calendar_event(summary="...", start_time="...")`
   - Detect events from emails with `detect_events_from_email(email_id="...")`
   - List upcoming calendar events with `list_calendar_events(max_results=10)`

5. **Troubleshooting**:
   - If you encounter any issues, check the debug help resource: `debug://help`
   - You can also check the server status with `server://status`
   - For authentication issues, see the authentication guide: `gmail://authentication_guide`

## Example Workflows

### Email Workflow

1. Check authentication status:
   ```
   check_auth_status()
   ```

2. If not authenticated, start the authentication process:
   ```
   authenticate()
   ```

3. Get an overview of your inbox:
   ```
   get_email_overview()
   ```

4. Search for emails from a specific sender:
   ```
   search_emails(query="from:example@gmail.com")
   ```

5. View a specific email (replace with an actual email ID):
   ```
   get_email(email_id="18abc123def456")
   ```

6. Prepare a context-aware reply:
   ```
   prepare_email_reply(email_id="18abc123def456")
   ```

7. Create a draft reply:
   ```
   send_email_reply(email_id="18abc123def456", reply_text="Thanks for your email. I'll review this and get back to you soon.")
   ```

8. After user confirmation, send the email:
   ```
   confirm_send_email(draft_id="draft_id_from_previous_step")
   ```

### Calendar Workflow

1. List upcoming calendar events:
   ```
   list_calendar_events(max_results=5)
   ```

2. Create a new calendar event:
   ```
   create_calendar_event(
       summary="Team Meeting",
       start_time="tomorrow at 2pm",
       end_time="tomorrow at 3pm",
       description="Weekly team sync",
       location="Conference Room A",
       attendees=["colleague@example.com"]
   )
   ```

3. Detect potential events from an email:
   ```
   detect_events_from_email(email_id="18abc123def456")
   ```

## Advanced Search Syntax

When using `search_emails()`, you can leverage Gmail's powerful search syntax:

- `from:example@gmail.com` - Emails from a specific sender
- `to:example@gmail.com` - Emails to a specific recipient
- `subject:meeting` - Emails with "meeting" in the subject
- `has:attachment` - Emails with attachments
- `is:unread` - Unread emails
- `after:2023/01/01` - Emails after January 1, 2023

For more search options, see the search guide: `gmail://search_guide`

## Available Resources

- `auth://status` - Authentication status
- `gmail://status` - Gmail account status
- `email://{email_id}` - Detailed context for a specific email
- `thread://{thread_id}` - Context for an entire email thread
- `sender://{sender_email}` - Context about a specific sender
- `server://info` - Server information
- `server://status` - Server status
- `debug://help` - Debugging help

## Need Help?

If you need more information, check the following resources:
- `gmail://authentication_guide` - Guide to authentication
- `gmail://search_guide` - Guide to Gmail's search syntax
- `gmail://reply_guide` - Guide to context-aware email replies
- `gmail://debug_guide` - Troubleshooting guide
            """
        }
    
    @mcp.prompt("gmail://search_guide")
    def search_guide_prompt() -> Dict[str, Any]:
        """
        Gmail Search Syntax Guide
        
        This prompt provides a guide to Gmail's search syntax for use with the search_emails tool.
        """
        return {
            "title": "Gmail Search Syntax Guide",
            "description": "Learn how to use Gmail's powerful search syntax",
            "content": """
# Gmail Search Syntax Guide

When using the `search_emails()` tool, you can leverage Gmail's powerful search syntax to find exactly what you're looking for.

## Basic Search Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `from:` | Emails from a specific sender | `from:example@gmail.com` |
| `to:` | Emails to a specific recipient | `to:example@gmail.com` |
| `subject:` | Emails with specific text in the subject | `subject:meeting` |
| `has:attachment` | Emails with attachments | `has:attachment` |
| `filename:` | Emails with specific attachment types | `filename:pdf` |
| `in:` | Emails in a specific location | `in:inbox`, `in:trash` |
| `is:` | Emails with a specific status | `is:unread`, `is:starred` |
| `after:` | Emails after a date | `after:2023/01/01` |
| `before:` | Emails before a date | `before:2023/12/31` |
| `older:` | Emails older than a time period | `older:1d` (1 day) |
| `newer:` | Emails newer than a time period | `newer:1w` (1 week) |

## Combining Operators

You can combine multiple operators to create more specific searches:

- `from:example@gmail.com has:attachment` - Emails from example@gmail.com with attachments
- `subject:report is:unread` - Unread emails with "report" in the subject
- `after:2023/01/01 before:2023/01/31 from:example@gmail.com` - Emails from example@gmail.com in January 2023

## Advanced Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `OR` | Match either term | `from:alice OR from:bob` |
| `-` | Exclude matches | `-from:example@gmail.com` |
| `( )` | Group operators | `(from:alice OR from:bob) has:attachment` |
| `"..."` | Exact phrase | `"quarterly report"` |
| `{ }` | Find messages with only one of the terms | `{project meeting}` |

## Date Formats

- YYYY/MM/DD: `after:2023/01/01`
- Relative: `newer:2d` (2 days), `older:1w` (1 week), `newer:3m` (3 months), `older:1y` (1 year)

## Examples

1. Find unread emails with attachments:
   ```
   is:unread has:attachment
   ```

2. Find emails from a specific domain in the last week:
   ```
   from:@example.com newer:1w
   ```

3. Find emails with "report" in the subject that are starred:
   ```
   subject:report is:starred
   ```

4. Find emails from Alice or Bob with PDF attachments:
   ```
   (from:alice OR from:bob) filename:pdf
   ```

5. Find emails with "urgent" in the subject that are unread:
   ```
   subject:urgent is:unread
   ```
            """
        }
    
    @mcp.prompt("gmail://authentication_guide")
    def authentication_guide_prompt() -> Dict[str, Any]:
        """
        Gmail Authentication Guide
        
        This prompt provides a guide to the authentication process for the Gmail MCP.
        """
        return {
            "title": "Gmail Authentication Guide",
            "description": "Learn how to authenticate with your Google account",
            "content": """
# Gmail Authentication Guide

To use the Gmail MCP with Claude Desktop, you need to authenticate with your Google account. This guide explains the authentication process and how to troubleshoot common issues.

## Authentication Process

1. **Check Authentication Status**
   First, check if you're already authenticated:
   ```
   check_auth_status()
   ```

2. **Start Authentication**
   If not authenticated, start the process:
   ```
   authenticate()
   ```

3. **Complete Authentication**
   - A browser window will open with Google's login page
   - Sign in with your Google account and grant the requested permissions
   - Authentication completes automatically via secure callback
   - Your tokens are encrypted and stored securely

4. **Verify Authentication**
   Check that authentication was successful:
   ```
   check_auth_status()
   ```

## Authentication Troubleshooting

### Common Issues

1. **Browser Doesn't Open**
   - The authentication URL will be displayed in Claude's response
   - Copy and paste the URL into your browser manually

2. **Callback Failed**
   - Ensure no other application is using port 8000
   - Check that your firewall isn't blocking local connections
   - Try logging out with `logout()` and authenticating again

3. **Permission Denied**
   - Ensure you grant all requested permissions
   - If you denied permissions, start again with `authenticate()`

4. **Already Authenticated**
   - If you want to switch accounts, first log out:
     ```
     logout()
     ```
   - Then start the authentication process again

5. **Token Expired**
   - Tokens automatically refresh, but if you encounter issues:
     ```
     authenticate()
     ```

## Security Information

- The Gmail MCP uses OAuth 2.0 for secure authentication
- OAuth state verification protects against CSRF attacks
- Your tokens are encrypted at rest using Fernet encryption with PBKDF2 key derivation
- You can revoke access at any time through your Google Account settings or by using the `logout()` tool
- The MCP only requests the minimum permissions needed to function

## Need Help?

If you encounter any authentication issues:
- Check the `auth://status` resource for detailed information
- Check the `debug://help` resource for troubleshooting guidance
- Try the `logout()` tool followed by `authenticate()` to restart the process
            """
        }
    
    @mcp.prompt("gmail://debug_guide")
    def debug_guide_prompt() -> Dict[str, Any]:
        """
        Gmail MCP Debugging Guide
        
        This prompt provides a guide to debugging common issues with the Gmail MCP.
        """
        return {
            "title": "Gmail MCP Debugging Guide",
            "description": "Troubleshoot common issues with the Gmail MCP",
            "content": """
# Gmail MCP Debugging Guide

This guide helps you troubleshoot common issues with the Gmail MCP integration in Claude Desktop.

## Quick Diagnostic Steps

1. **Check Server Status**
   ```
   server://status
   ```

2. **Check Authentication Status**
   ```
   check_auth_status()
   ```

3. **Check Gmail Status**
   ```
   gmail://status
   ```

4. **Check Health**
   ```
   health://check
   ```

## Common Issues and Solutions

### Authentication Issues

**Symptoms:**
- "Not authenticated" errors
- Unable to access Gmail data
- Authentication loops

**Solutions:**
1. Check authentication status:
   ```
   check_auth_status()
   ```

2. If not authenticated, start the process:
   ```
   authenticate()
   ```

3. If authentication fails repeatedly:
   - Log out and try again:
     ```
     logout()
     authenticate()
     ```
   - Check that you're granting all requested permissions
   - Try using a different browser

### API Rate Limiting

**Symptoms:**
- "Rate limit exceeded" errors
- Operations fail after many requests

**Solutions:**
1. Wait a few minutes before trying again
2. Reduce the frequency of requests
3. Use batch operations when possible

### Connection Issues

**Symptoms:**
- Timeout errors
- "Failed to connect" messages

**Solutions:**
1. Check your internet connection
2. Verify the server is running:
   ```
   server://status
   ```
3. Restart the MCP server if necessary

### Permission Issues

**Symptoms:**
- "Insufficient permissions" errors
- Unable to access certain Gmail features

**Solutions:**
1. Log out and re-authenticate to grant all permissions:
   ```
   logout()
   authenticate()
   ```
2. Make sure you're using the correct Google account

### Data Not Updating

**Symptoms:**
- Stale or outdated email information
- New emails not appearing

**Solutions:**
1. Refresh the data by making a new request
2. Check for pagination tokens if listing many emails
3. Verify the correct query parameters are being used

## Advanced Debugging

### Check Debug Logs

Access detailed debug information:
```
debug://help
```

### Server Information

Get information about the server configuration:
```
server://info
server://config
```

### Health Check

Perform a comprehensive health check:
```
health://check
```

## Still Having Issues?

If you continue to experience problems:

1. Try restarting the MCP server
2. Check for any error messages in the server logs
3. Verify that your Google account has not revoked access
4. Ensure you're using the latest version of the Gmail MCP
            """
        }
    
    @mcp.prompt("gmail://reply_guide")
    def reply_guide_prompt() -> Dict[str, Any]:
        """
        Email Reply Guide
        
        This prompt provides a guide to using the context-aware email reply system.
        """
        return {
            "title": "Context-Aware Email Reply Guide",
            "description": "Learn how to craft personalized, context-aware email replies",
            "content": """
# Context-Aware Email Reply Guide

The Gmail MCP provides powerful tools for crafting personalized, context-aware email replies. This guide explains how to use these tools to create replies that consider the full context of your communication history.

## Understanding Context-Aware Replies

Context-aware replies take into account:

- The content of the original email
- The history of the conversation thread
- Your relationship with the sender
- Communication patterns between you and the sender
- Related emails and topics
- Entities mentioned in the email (dates, times, action items, etc.)

## Reply Workflow

### 1. Find the Email to Reply To

First, find the email you want to reply to:

```
# Get recent emails
list_emails(max_results=10, label="INBOX")

# Or search for a specific email
search_emails(query="from:example@gmail.com")
```

### 2. Prepare the Reply Context

Use the `prepare_email_reply` tool to gather comprehensive context:

```
# Replace with the actual email ID
reply_context = prepare_email_reply(email_id="18abc123def456")
```

### 3. Analyze the Context

The reply context includes:

- **Original Email**: The email you're replying to
- **Thread Context**: Information about the conversation thread
- **Sender Context**: Information about the sender and your history with them
- **Communication Patterns**: Analysis of how you and the sender typically communicate
- **Entities**: Important information extracted from the email (dates, times, action items)
- **Related Emails**: Other emails that provide additional context

### 4. Craft a Personalized Reply

Based on the context, craft a reply that:

- Matches the formality level of your previous communications
- Addresses all action items or questions
- References relevant history or related emails
- Maintains your typical response style with this sender

### 5. Create a Draft Reply

Use the `send_email_reply` tool to create a draft reply:

```
# Replace with the actual email ID and your reply text
draft_result = send_email_reply(
    email_id="18abc123def456",
    reply_text="Your personalized reply here...",
    include_original=True  # Whether to include the original email in the reply
)
```

### 6. ALWAYS Ask for User Confirmation

⚠️ **CRITICAL STEP** ⚠️

You must ALWAYS ask for the user's explicit confirmation before sending any email. This is a mandatory step:

```
# After creating the draft, show it to the user and ask:
"Here's the draft reply I've created. Would you like me to send it? If yes, I'll send it. If you'd like to make changes, please let me know."
```

### 7. Send Only After Explicit Confirmation

Only after receiving explicit confirmation from the user, send the email:

```
# Only after user confirms:
confirm_send_email(draft_id=draft_result["draft_id"])
```

## Always Include Email Links

When discussing or referencing emails, always include the direct link to the email in Gmail's web interface. These links are automatically included in the context:

- Email context includes `email_link`
- Thread context includes `thread_link`
- Each message in a thread includes its own `email_link`

Always display these links when discussing specific emails to allow the user to easily access them.

## Example: Analyzing Communication Patterns

The communication patterns analysis provides insights like:

- **Frequency**: How often you communicate with this sender
- **Response Time**: Your typical response time to this sender
- **Formality**: Whether your communications are typically formal or informal
- **Message Length**: Typical length of messages between you and the sender
- **Common Topics**: Topics that frequently appear in your communications

Use these insights to maintain consistency in your communication style.

## Example: Entity Extraction

The entity extraction identifies important information like:

- **Dates**: Mentioned dates that might indicate deadlines or events
- **Times**: Specific times mentioned in the email
- **Action Items**: Tasks or requests that require your attention
- **URLs**: Links that you might need to reference
- **Email Addresses**: Other people mentioned in the conversation

Address these entities explicitly in your reply to ensure a complete response.

## Tips for Effective Replies

1. **Match Tone and Style**: Use the communication patterns analysis to match your previous tone
2. **Address All Points**: Use the entity extraction to ensure you address all questions and action items
3. **Reference History**: When relevant, reference previous communications from the thread context
4. **Provide Context**: If referencing related emails, provide enough context for clarity
5. **Be Concise**: While being comprehensive, keep your reply as concise as possible
6. **Include Links**: Always include the email link when discussing a specific email
7. **Always Get Confirmation**: Never send an email without explicit user confirmation

## Important Reminders

1. **NEVER send an email without explicit user confirmation**
2. **ALWAYS include email links when referencing specific emails**
3. **Use the full context to craft personalized, relevant replies**
            """
        } 