"""
Bulk Operations Tools Module

Handles bulk email operations: archive, label, trash with batch API support.
"""

import re
import base64
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def _fetch_messages_with_pagination(
    service,
    query: str,
    max_messages: int
) -> List[Dict[str, Any]]:
    """
    Fetch messages matching a query with pagination support.

    Continues fetching pages until we have max_messages or no more results.

    Args:
        service: Gmail API service instance
        query: Gmail search query
        max_messages: Maximum number of messages to fetch

    Returns:
        List of message dicts with 'id' keys
    """
    messages = []
    page_token: Optional[str] = None
    page_count = 0

    logger.info(f"Starting pagination fetch for query='{query}', max={max_messages}")

    while len(messages) < max_messages:
        # Request only what we still need (up to 100 per page, API limit)
        remaining = max_messages - len(messages)
        page_size = min(remaining, 100)

        request_params = {
            "userId": "me",
            "q": query,
            "maxResults": page_size
        }
        if page_token:
            request_params["pageToken"] = page_token

        result = service.users().messages().list(**request_params).execute()

        page_messages = result.get("messages", [])
        page_count += 1
        logger.info(f"Page {page_count}: got {len(page_messages)} messages, total so far: {len(messages) + len(page_messages)}")

        if not page_messages:
            break

        messages.extend(page_messages)

        # Check if there are more pages
        page_token = result.get("nextPageToken")
        if not page_token:
            logger.info("No more pages available")
            break

    logger.info(f"Pagination complete: returning {len(messages[:max_messages])} messages")
    # Return only up to max_messages (in case last page pushed us over)
    return messages[:max_messages]


def setup_bulk_tools(mcp: FastMCP) -> None:
    """Set up bulk operation tools on the FastMCP application."""

    @mcp.tool()
    def bulk_archive(query: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Archive all emails matching a search query.

        Uses Gmail's batch API for efficient processing.

        Args:
            query (str): Gmail search query (e.g., "from:newsletter@example.com")
            max_emails (int): Maximum number of emails to archive (default 50, max 500)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 500)

            # Use pagination to fetch up to max_emails
            messages = _fetch_messages_with_pagination(service, query, max_emails)

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
            max_emails (int): Maximum number of emails to label (default 50, max 500)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 500)

            # Use pagination to fetch up to max_emails
            messages = _fetch_messages_with_pagination(service, query, max_emails)

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
            max_emails (int): Maximum number of emails to trash (default 50, max 500)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails = min(max_emails, 500)

            # Use pagination to fetch up to max_emails
            messages = _fetch_messages_with_pagination(service, query, max_emails)

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
            max_emails (int): Maximum number of emails to process (default: 100, max 500)

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
            max_emails = min(max_emails, 500)

            # Build query with age filter
            full_query = f"{query} older_than:{days_old}d"

            # Use pagination to fetch up to max_emails
            messages = _fetch_messages_with_pagination(service, full_query, max_emails)

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
    Batch modify emails using Gmail's native batchModify endpoint.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to modify
        add_labels: Labels to add
        remove_labels: Labels to remove

    Returns:
        tuple: (success_count, failure_count)
    """
    logger.info(f"Batch modify: {len(message_ids)} messages, add={add_labels}, remove={remove_labels}")

    # Gmail's batchModify endpoint handles up to 1000 IDs per call
    batch_size = 1000
    total_success = 0
    total_failed = 0

    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]

        body = {"ids": batch_ids}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels

        try:
            service.users().messages().batchModify(userId="me", body=body).execute()
            total_success += len(batch_ids)
            logger.info(f"Batch {i // batch_size + 1}: modified {len(batch_ids)} messages")
        except Exception as e:
            total_failed += len(batch_ids)
            logger.error(f"Batch {i // batch_size + 1} failed: {e}")

    logger.info(f"Batch modify complete: success={total_success}, failed={total_failed}")
    return total_success, total_failed


def _batch_trash_emails(service, message_ids: List[str]) -> tuple:
    """
    Batch trash emails using Gmail's native batchModify endpoint.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to trash

    Returns:
        tuple: (success_count, failure_count)
    """
    # Use batchModify to add TRASH label - same efficient endpoint
    return _batch_modify_emails(
        service,
        message_ids,
        add_labels=["TRASH"],
        remove_labels=["INBOX"]
    )
