"""
Email Read Tools Module

Handles listing, searching, and retrieving email content.
"""

import base64
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.utils.date_parser import parse_natural_date, parse_week_range, DATE_PARSING_HINT
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.gmail.helpers import extract_email_info

logger = get_logger(__name__)


def setup_email_read_tools(mcp: FastMCP) -> None:
    """Set up email read tools on the FastMCP application."""

    @mcp.tool()
    def get_email_count() -> Dict[str, Any]:
        """
        Get the count of emails in the user's inbox.

        This tool retrieves the total number of messages in the user's Gmail account
        and the number of messages in the inbox.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.

        Returns:
            Dict[str, Any]: The email count information including:
                - email: The user's email address
                - total_messages: Total number of messages in the account
                - inbox_messages: Number of messages in the inbox
                - inbox_unread: Number of unread messages in the inbox

        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, call get_email_count()
        3. If not authenticated, guide user to authenticate first
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            profile = service.users().getProfile(userId="me").execute()
            # Use label metadata for accurate counts (not paginated)
            inbox_label = service.users().labels().get(userId="me", id="INBOX").execute()

            return {
                "email": profile.get("emailAddress", "Unknown"),
                "total_messages": profile.get("messagesTotal", 0),
                "inbox_messages": inbox_label.get("messagesTotal", 0),
                "inbox_unread": inbox_label.get("messagesUnread", 0),
            }
        except HttpError as error:
            logger.error(f"Failed to get email count: {error}")
            return {"success": False, "error": f"Failed to get email count: {error}"}

    @mcp.tool()
    def list_emails(max_results: int = 10, label: str = "INBOX") -> Dict[str, Any]:
        """
        List emails from the user's mailbox.

        This tool retrieves a list of emails from the specified label in the user's
        Gmail account, with basic information about each email.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.

        Args:
            max_results (int, optional): Maximum number of emails to return. Defaults to 10.
            label (str, optional): The label to filter by. Defaults to "INBOX".
                Common labels: "INBOX", "SENT", "DRAFT", "TRASH", "SPAM", "STARRED"

        Returns:
            Dict[str, Any]: The list of emails including:
                - emails: List of email objects with basic information and links
                - next_page_token: Token for pagination (if applicable)

        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, call list_emails(max_results=5, label="INBOX")
        3. If not authenticated, guide user to authenticate first
        4. Always include the email_link when discussing specific emails with the user
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            result = service.users().messages().list(
                userId="me",
                labelIds=[label],
                maxResults=max_results
            ).execute()

            messages = result.get("messages", [])
            emails = []

            # Use batch API for efficient fetching
            if messages:
                emails = _batch_get_emails(service, [m["id"] for m in messages])

            return {
                "emails": emails,
                "next_page_token": result.get("nextPageToken"),
            }
        except HttpError as error:
            logger.error(f"Failed to list emails: {error}")
            return {"success": False, "error": f"Failed to list emails: {error}"}

    @mcp.tool()
    def get_email(email_id: str, include_thread: bool = False) -> Dict[str, Any]:
        """
        Get a specific email by ID.

        This tool retrieves the full details of a specific email, including
        the body content, headers, and other metadata.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - You need an email ID, which can be obtained from list_emails() or search_emails()

        Args:
            email_id (str): The ID of the email to retrieve. This ID comes from the
                            list_emails() or search_emails() results.
            include_thread (bool): If True, also fetches the full thread context.
                                   Defaults to False for backward compatibility.

        Returns:
            Dict[str, Any]: The email details including:
                - id: Email ID
                - thread_id: Thread ID
                - subject: Email subject
                - from: Sender information
                - to: Recipient information
                - cc: CC recipients
                - date: Email date
                - body: Email body content
                - snippet: Short snippet of the email
                - labels: Email labels
                - email_link: Direct link to the email in Gmail web interface
                - thread: (only if include_thread=True) Full thread context with:
                    - message_count: Number of messages in thread
                    - participants: List of unique email addresses
                    - messages: All messages in chronological order

        Example usage:
        1. First check authentication: access auth://status resource
        2. Get a list of emails: list_emails()
        3. Extract an email ID from the results
        4. Get the full email: get_email(email_id="...")
        5. Get email with thread context: get_email(email_id="...", include_thread=True)
        6. Always include the email_link when discussing the email with the user
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            headers = {}
            for header in msg["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = part["body"]["data"]
                        break
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = msg["payload"]["body"]["data"]

            if body:
                body = base64.urlsafe_b64decode(body.encode("ASCII")).decode("utf-8")

            thread_id = msg["threadId"]
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{email_id}"

            result = {
                "id": msg["id"],
                "thread_id": thread_id,
                "subject": headers.get("subject", "No Subject"),
                "from": headers.get("from", "Unknown"),
                "to": headers.get("to", "Unknown"),
                "cc": headers.get("cc", ""),
                "date": headers.get("date", "Unknown"),
                "body": body,
                "snippet": msg["snippet"],
                "labels": msg["labelIds"],
                "email_link": email_link
            }

            # Optionally include thread context
            if include_thread:
                thread_data = _get_thread_context(service, thread_id)
                if thread_data:
                    result["thread"] = thread_data

            return result
        except HttpError as error:
            logger.error(f"Failed to get email: {error}")
            return {"success": False, "error": f"Failed to get email: {error}"}

    @mcp.tool()
    def search_emails(
        query: str,
        max_results: int = 10,
        after: Optional[str] = None,
        before: Optional[str] = None,
        date_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for emails using Gmail's search syntax.

        This tool searches for emails matching the specified query using
        Gmail's powerful search syntax. Date filtering supports natural language.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.

        Args:
            query (str): The search query using Gmail's search syntax.
                Examples:
                - "from:example@gmail.com" - Emails from a specific sender
                - "to:example@gmail.com" - Emails to a specific recipient
                - "subject:meeting" - Emails with "meeting" in the subject
                - "has:attachment" - Emails with attachments
                - "is:unread" - Unread emails
                - "label:claude-review" - Emails with the claude-review label
            max_results (int, optional): Maximum number of emails to return. Defaults to 10.
            after (str, optional): Only include emails after this date. Supports natural language
                (e.g., "last monday", "3 days ago", "2026-01-15").
            before (str, optional): Only include emails before this date. Supports natural language
                (e.g., "today", "yesterday", "2026-01-20").
            date_range (str, optional): Date range in natural language (e.g., "last week",
                "past 7 days", "this month"). Overrides after/before if provided.

        Returns:
            Dict[str, Any]: The search results including:
                - query: The search query used
                - emails: List of email objects matching the query with links
                - next_page_token: Token for pagination (if applicable)

        Example usage:
        1. Search with date range:
           search_emails(query="from:boss@company.com", date_range="last week")
        2. Search with specific dates:
           search_emails(query="invoices", after="last monday", before="today")
        3. Search recent emails:
           search_emails(query="is:unread", date_range="past 3 days")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            # Build the final query with date filters
            final_query = query

            # Handle date_range (overrides after/before)
            if date_range:
                start_dt, end_dt = parse_week_range(date_range)
                if start_dt:
                    final_query += f" after:{start_dt.strftime('%Y/%m/%d')}"
                if end_dt:
                    final_query += f" before:{end_dt.strftime('%Y/%m/%d')}"
            else:
                # Handle individual after/before parameters
                if after:
                    after_dt = parse_natural_date(after, prefer_future=False)
                    if after_dt:
                        final_query += f" after:{after_dt.strftime('%Y/%m/%d')}"
                    else:
                        return {
                            "success": False,
                            "error": f"Could not parse 'after' date: {after}",
                            "hint": DATE_PARSING_HINT
                        }

                if before:
                    before_dt = parse_natural_date(before, prefer_future=False)
                    if before_dt:
                        final_query += f" before:{before_dt.strftime('%Y/%m/%d')}"
                    else:
                        return {
                            "success": False,
                            "error": f"Could not parse 'before' date: {before}",
                            "hint": DATE_PARSING_HINT
                        }

            service = get_gmail_service(credentials)
            result = service.users().messages().list(
                userId="me",
                q=final_query,
                maxResults=max_results
            ).execute()

            messages = result.get("messages", [])
            emails = []

            # Use batch API for efficient fetching
            if messages:
                emails = _batch_get_emails(service, [m["id"] for m in messages])

            return {
                "query": query,
                "final_query": final_query,
                "emails": emails,
                "next_page_token": result.get("nextPageToken"),
                "date_filters": {
                    "after": after,
                    "before": before,
                    "date_range": date_range
                } if (after or before or date_range) else None
            }
        except HttpError as error:
            logger.error(f"Failed to search emails: {error}")
            return {"success": False, "error": f"Failed to search emails: {error}"}

    @mcp.tool()
    def get_email_overview() -> Dict[str, Any]:
        """
        Get a simple overview of the user's emails.

        This tool provides a quick summary of the user's Gmail account,
        including counts and recent emails, all in one call.

        Returns:
            Dict[str, Any]: The email overview including:
                - account: Account information
                - counts: Email counts by label
                - recent_emails: List of recent emails with links
                - unread_count: Number of unread emails

        Note: Always include the email_link when discussing specific emails with the user.
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            profile = service.users().getProfile(userId="me").execute()
            inbox_result = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=5).execute()
            unread_result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=5).execute()
            labels_result = service.users().labels().list(userId="me").execute()

            recent_emails = []
            if "messages" in inbox_result:
                recent_emails = _batch_get_emails(service, [m["id"] for m in inbox_result["messages"][:5]])

            label_counts = {}
            for label in labels_result.get("labels", []):
                if label["type"] == "system":
                    label_detail = service.users().labels().get(userId="me", id=label["id"]).execute()
                    label_counts[label["name"]] = {
                        "total": label_detail.get("messagesTotal", 0),
                        "unread": label_detail.get("messagesUnread", 0)
                    }

            return {
                "account": {
                    "email": profile.get("emailAddress", "Unknown"),
                    "total_messages": profile.get("messagesTotal", 0),
                    "total_threads": profile.get("threadsTotal", 0),
                },
                "counts": {
                    "inbox": label_counts.get("INBOX", {}).get("total", 0),
                    "unread": label_counts.get("UNREAD", {}).get("total", 0),
                    "sent": label_counts.get("SENT", {}).get("total", 0),
                    "draft": label_counts.get("DRAFT", {}).get("total", 0),
                    "spam": label_counts.get("SPAM", {}).get("total", 0),
                    "trash": label_counts.get("TRASH", {}).get("total", 0),
                },
                "recent_emails": recent_emails,
                "unread_count": len(unread_result.get("messages", [])),
            }
        except Exception as e:
            logger.error(f"Failed to get email overview: {e}")
            return {"success": False, "error": f"Failed to get email overview: {e}"}


def _get_thread_context(service, thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Get thread context for an email.

    Args:
        service: Gmail API service instance
        thread_id: The thread ID to fetch

    Returns:
        Dict with thread context or None on error
    """
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="full"
        ).execute()

        messages = thread.get("messages", [])

        if not messages:
            return None

        # Extract messages
        extracted_messages = []
        participants = set()

        for msg in messages:
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Extract body
            body = ""
            payload = msg.get("payload", {})
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
            elif "body" in payload and "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

            extracted_messages.append({
                "id": msg["id"],
                "from": headers.get("from", "Unknown"),
                "to": headers.get("to", "Unknown"),
                "cc": headers.get("cc", ""),
                "date": headers.get("date", "Unknown"),
                "subject": headers.get("subject", "No Subject"),
                "snippet": msg.get("snippet", ""),
                "body": body
            })

            # Collect participants
            for field in ["from", "to", "cc"]:
                value = headers.get(field, "")
                if value:
                    for addr in value.split(","):
                        addr = addr.strip()
                        if "<" in addr and ">" in addr:
                            addr = addr[addr.index("<") + 1:addr.index(">")]
                        if addr and "@" in addr:
                            participants.add(addr.lower())

        return {
            "message_count": len(extracted_messages),
            "participants": sorted(list(participants)),
            "messages": extracted_messages
        }

    except Exception as e:
        logger.error(f"Failed to get thread context: {e}")
        return None


def _batch_get_emails(service, message_ids: list) -> list:
    """
    Batch fetch multiple emails efficiently using Gmail's batch API.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to fetch

    Returns:
        list: List of email info dictionaries
    """
    if not message_ids:
        return []

    emails = []

    # Gmail batch API allows up to 100 requests per batch
    batch_size = 100
    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]

        # Create batch request
        batch = service.new_batch_http_request()

        def callback(request_id, response, exception):
            if exception is not None:
                logger.error(f"Batch request failed for {request_id}: {exception}")
            else:
                emails.append(extract_email_info(response))

        for msg_id in batch_ids:
            batch.add(
                service.users().messages().get(userId="me", id=msg_id),
                callback=callback
            )

        batch.execute()

    return emails
