"""
Email Read Tools Module

Handles listing, searching, and retrieving email content.
"""

import base64
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
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
                - next_page_token: Token for pagination (if applicable)

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
            result = service.users().messages().list(userId="me", labelIds=["INBOX"]).execute()

            return {
                "email": profile.get("emailAddress", "Unknown"),
                "total_messages": profile.get("messagesTotal", 0),
                "inbox_messages": len(result.get("messages", [])),
                "next_page_token": result.get("nextPageToken"),
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
    def get_email(email_id: str) -> Dict[str, Any]:
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

        Example usage:
        1. First check authentication: access auth://status resource
        2. Get a list of emails: list_emails()
        3. Extract an email ID from the results
        4. Get the full email: get_email(email_id="...")
        5. Always include the email_link when discussing the email with the user
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

            return {
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
        except HttpError as error:
            logger.error(f"Failed to get email: {error}")
            return {"success": False, "error": f"Failed to get email: {error}"}

    @mcp.tool()
    def search_emails(query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for emails using Gmail's search syntax.

        This tool searches for emails matching the specified query using
        Gmail's powerful search syntax.

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
                - "after:2023/01/01" - Emails after January 1, 2023
                - "label:claude-review" - Emails with the claude-review label
            max_results (int, optional): Maximum number of emails to return. Defaults to 10.

        Returns:
            Dict[str, Any]: The search results including:
                - query: The search query used
                - emails: List of email objects matching the query with links
                - next_page_token: Token for pagination (if applicable)

        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, search for emails: search_emails(query="from:example@gmail.com")
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
                q=query,
                maxResults=max_results
            ).execute()

            messages = result.get("messages", [])
            emails = []

            # Use batch API for efficient fetching
            if messages:
                emails = _batch_get_emails(service, [m["id"] for m in messages])

            return {
                "query": query,
                "emails": emails,
                "next_page_token": result.get("nextPageToken"),
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
