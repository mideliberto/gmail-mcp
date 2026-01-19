"""
Bulk Operations Tools Module

Handles bulk email operations: archive, label, trash with batch API support.
"""

import re
import base64
from typing import Dict, Any, List

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_bulk_tools(mcp: FastMCP) -> None:
    """Set up bulk operation tools on the FastMCP application."""

    @mcp.tool()
    def bulk_archive(query: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Archive all emails matching a search query.

        Uses Gmail's batch API for efficient processing.

        Args:
            query (str): Gmail search query (e.g., "from:newsletter@example.com")
            max_emails (int): Maximum number of emails to archive (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])

            if not messages:
                return {
                    "success": True,
                    "message": "No emails found matching query.",
                    "archived": 0,
                    "failed": 0,
                    "query": query
                }

            # Use batch API for efficient processing
            archived, failed = _batch_modify_emails(
                service,
                [m["id"] for m in messages],
                remove_labels=["INBOX"]
            )

            return {
                "success": True,
                "message": f"Archived {archived} emails.",
                "archived": archived,
                "failed": failed,
                "query": query
            }

        except Exception as e:
            logger.error(f"Failed to bulk archive: {e}")
            return {"success": False, "error": f"Failed to bulk archive: {e}"}

    @mcp.tool()
    def bulk_label(query: str, label_id: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Apply a label to all emails matching a search query.

        Uses Gmail's batch API for efficient processing.

        Args:
            query (str): Gmail search query
            label_id (str): The label ID to apply
            max_emails (int): Maximum number of emails to label (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])

            if not messages:
                return {
                    "success": True,
                    "message": "No emails found matching query.",
                    "labeled": 0,
                    "failed": 0,
                    "query": query,
                    "label_id": label_id
                }

            # Use batch API for efficient processing
            labeled, failed = _batch_modify_emails(
                service,
                [m["id"] for m in messages],
                add_labels=[label_id]
            )

            return {
                "success": True,
                "message": f"Labeled {labeled} emails.",
                "labeled": labeled,
                "failed": failed,
                "query": query,
                "label_id": label_id
            }

        except Exception as e:
            logger.error(f"Failed to bulk label: {e}")
            return {"success": False, "error": f"Failed to bulk label: {e}"}

    @mcp.tool()
    def bulk_trash(query: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Move all emails matching a search query to trash.

        Uses Gmail's batch API for efficient processing.

        Args:
            query (str): Gmail search query
            max_emails (int): Maximum number of emails to trash (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])

            if not messages:
                return {
                    "success": True,
                    "message": "No emails found matching query.",
                    "trashed": 0,
                    "failed": 0,
                    "query": query
                }

            # Use batch API for trash operations
            trashed, failed = _batch_trash_emails(service, [m["id"] for m in messages])

            return {
                "success": True,
                "message": f"Trashed {trashed} emails.",
                "trashed": trashed,
                "failed": failed,
                "query": query
            }

        except Exception as e:
            logger.error(f"Failed to bulk trash: {e}")
            return {"success": False, "error": f"Failed to bulk trash: {e}"}

    @mcp.tool()
    def find_unsubscribe_link(email_id: str) -> Dict[str, Any]:
        """
        Find unsubscribe link in an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Unsubscribe link if found
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

            unsubscribe_header = headers.get("list-unsubscribe", "")

            body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/html" and "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
                    elif part["mimeType"] == "text/plain" and "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")

            unsubscribe_patterns = [
                r'https?://[^\s<>"]+unsubscribe[^\s<>"]*',
                r'https?://[^\s<>"]+optout[^\s<>"]*',
                r'https?://[^\s<>"]+opt-out[^\s<>"]*',
                r'https?://[^\s<>"]+remove[^\s<>"]*',
            ]

            found_links = []

            if unsubscribe_header:
                header_links = re.findall(r'<(https?://[^>]+)>', unsubscribe_header)
                found_links.extend(header_links)
                mailto_links = re.findall(r'<(mailto:[^>]+)>', unsubscribe_header)
                found_links.extend(mailto_links)

            for pattern in unsubscribe_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                found_links.extend(matches)

            found_links = list(set(found_links))

            return {
                "success": True,
                "email_id": email_id,
                "unsubscribe_links": found_links[:5],
                "has_list_unsubscribe_header": bool(unsubscribe_header),
                "from": headers.get("from", "Unknown")
            }

        except Exception as e:
            logger.error(f"Failed to find unsubscribe link: {e}")
            return {"success": False, "error": f"Failed to find unsubscribe link: {e}"}

    @mcp.tool()
    def cleanup_old_emails(
        query: str,
        days_old: int = 30,
        action: str = "archive",
        max_emails: int = 100
    ) -> Dict[str, Any]:
        """
        Clean up old emails matching criteria.

        Useful for batch cleanup workflows - archive or trash emails older than
        a specified number of days that match a query.

        Args:
            query (str): Base Gmail search query (e.g., "from:newsletter@example.com")
            days_old (int): Only process emails older than this many days (default: 30)
            action (str): Action to take - "archive" or "trash" (default: "archive")
            max_emails (int): Maximum number of emails to process (default: 100)

        Returns:
            Dict[str, Any]: Results of the cleanup operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        if action not in ["archive", "trash"]:
            return {"success": False, "error": "Action must be 'archive' or 'trash'"}

        try:
            service = get_gmail_service(credentials)

            # Build query with age filter
            full_query = f"{query} older_than:{days_old}d"

            result = service.users().messages().list(
                userId="me",
                q=full_query,
                maxResults=min(max_emails, 100)
            ).execute()

            messages = result.get("messages", [])

            if not messages:
                return {
                    "success": True,
                    "message": f"No emails found older than {days_old} days matching query.",
                    "processed": 0,
                    "failed": 0,
                    "query": full_query,
                    "action": action
                }

            message_ids = [m["id"] for m in messages]

            if action == "archive":
                processed, failed = _batch_modify_emails(
                    service,
                    message_ids,
                    remove_labels=["INBOX"]
                )
            else:  # trash
                processed, failed = _batch_trash_emails(service, message_ids)

            return {
                "success": True,
                "message": f"{'Archived' if action == 'archive' else 'Trashed'} {processed} emails older than {days_old} days.",
                "processed": processed,
                "failed": failed,
                "query": full_query,
                "action": action
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old emails: {e}")
            return {"success": False, "error": f"Failed to cleanup old emails: {e}"}


def _batch_modify_emails(
    service,
    message_ids: List[str],
    add_labels: List[str] = None,
    remove_labels: List[str] = None
) -> tuple:
    """
    Batch modify emails using Gmail's batch API.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to modify
        add_labels: Labels to add
        remove_labels: Labels to remove

    Returns:
        tuple: (success_count, failure_count)
    """
    success = 0
    failed = 0

    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels

    # Process in batches of 100 (Gmail batch API limit)
    batch_size = 100
    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]

        batch = service.new_batch_http_request()

        def callback(request_id, response, exception):
            nonlocal success, failed
            if exception is not None:
                failed += 1
                logger.error(f"Batch modify failed for {request_id}: {exception}")
            else:
                success += 1

        for msg_id in batch_ids:
            batch.add(
                service.users().messages().modify(userId="me", id=msg_id, body=body),
                callback=callback
            )

        batch.execute()

    return success, failed


def _batch_trash_emails(service, message_ids: List[str]) -> tuple:
    """
    Batch trash emails using Gmail's batch API.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to trash

    Returns:
        tuple: (success_count, failure_count)
    """
    success = 0
    failed = 0

    batch_size = 100
    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]

        batch = service.new_batch_http_request()

        def callback(request_id, response, exception):
            nonlocal success, failed
            if exception is not None:
                failed += 1
                logger.error(f"Batch trash failed for {request_id}: {exception}")
            else:
                success += 1

        for msg_id in batch_ids:
            batch.add(
                service.users().messages().trash(userId="me", id=msg_id),
                callback=callback
            )

        batch.execute()

    return success, failed
