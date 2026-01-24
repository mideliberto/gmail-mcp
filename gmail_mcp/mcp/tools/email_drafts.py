"""
Email Drafts Tools Module

Handles draft management: list, get, update, delete.
"""

import base64
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def _parse_draft_message(draft: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a draft message into a simplified structure.

    Args:
        draft: Raw draft object from Gmail API

    Returns:
        Parsed draft with id, message details, and metadata
    """
    message = draft.get("message", {})
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    # Extract body
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
            elif part.get("mimeType") == "text/html" and "data" in part.get("body", {}) and not body:
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    elif "body" in payload and "data" in payload.get("body", {}):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return {
        "draft_id": draft.get("id"),
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "bcc": headers.get("bcc", ""),
        "subject": headers.get("subject", "(No Subject)"),
        "from": headers.get("from", ""),
        "date": headers.get("date", ""),
        "body": body,
        "snippet": message.get("snippet", ""),
        "labels": message.get("labelIds", [])
    }


def setup_email_draft_tools(mcp: FastMCP) -> None:
    """Set up email draft management tools on the FastMCP application."""

    @mcp.tool()
    def list_drafts(max_results: int = 10) -> Dict[str, Any]:
        """
        List all drafts in the user's Gmail account.

        Args:
            max_results (int): Maximum number of drafts to return (default: 10, max: 100)

        Returns:
            Dict[str, Any]: List of drafts with basic info including:
                - drafts: List of draft objects with id, to, subject, snippet
                - total_drafts: Total number of drafts in account

        Example usage:
        1. List recent drafts: list_drafts()
        2. List more drafts: list_drafts(max_results=50)
        3. Get full draft content: get_draft(draft_id="...")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_results = min(max_results, 100)

            # List drafts
            result = service.users().drafts().list(
                userId="me",
                maxResults=max_results
            ).execute()

            drafts = result.get("drafts", [])

            if not drafts:
                return {
                    "success": True,
                    "drafts": [],
                    "total_drafts": 0,
                    "message": "No drafts found."
                }

            # Get basic info for each draft
            draft_list = []
            for draft in drafts:
                # Fetch draft info - drafts.get doesn't support metadataHeaders
                # so we use format="full" and parse what we need
                draft_detail = service.users().drafts().get(
                    userId="me",
                    id=draft["id"],
                    format="full"
                ).execute()

                message = draft_detail.get("message", {})
                payload = message.get("payload", {})
                headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

                draft_list.append({
                    "draft_id": draft["id"],
                    "message_id": message.get("id"),
                    "to": headers.get("to", "(No recipient)"),
                    "subject": headers.get("subject", "(No Subject)"),
                    "snippet": message.get("snippet", ""),
                    "date": headers.get("date", "")
                })

            return {
                "success": True,
                "drafts": draft_list,
                "total_drafts": result.get("resultSizeEstimate", len(drafts)),
                "next_page_token": result.get("nextPageToken")
            }

        except Exception as e:
            logger.error(f"Failed to list drafts: {e}")
            return {"success": False, "error": f"Failed to list drafts: {e}"}

    @mcp.tool()
    def get_draft(draft_id: str) -> Dict[str, Any]:
        """
        Get the full content of a draft.

        Args:
            draft_id (str): The ID of the draft to retrieve (from list_drafts)

        Returns:
            Dict[str, Any]: Full draft details including:
                - draft_id: The draft ID
                - message_id: The underlying message ID
                - to: Recipients
                - cc: CC recipients
                - bcc: BCC recipients
                - subject: Email subject
                - body: Full body content
                - snippet: Short preview

        Example usage:
        1. List drafts: drafts = list_drafts()
        2. Get specific draft: get_draft(draft_id=drafts["drafts"][0]["draft_id"])
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            draft = service.users().drafts().get(
                userId="me",
                id=draft_id,
                format="full"
            ).execute()

            parsed = _parse_draft_message(draft)

            return {
                "success": True,
                **parsed
            }

        except Exception as e:
            logger.error(f"Failed to get draft: {e}")
            return {"success": False, "error": f"Failed to get draft: {e}"}

    @mcp.tool()
    def update_draft(
        draft_id: str,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing draft.

        Only provided fields will be updated. Omitted fields retain their current values.

        Args:
            draft_id (str): The ID of the draft to update
            to (str, optional): New recipient(s), comma-separated
            subject (str, optional): New subject line
            body (str, optional): New body content
            cc (str, optional): New CC recipients, comma-separated
            bcc (str, optional): New BCC recipients, comma-separated

        Returns:
            Dict[str, Any]: Updated draft details

        Example usage:
        1. Update subject: update_draft(draft_id="...", subject="New Subject")
        2. Update body: update_draft(draft_id="...", body="New content here")
        3. Update multiple fields: update_draft(draft_id="...", to="new@email.com", subject="Updated")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Get current draft to preserve unchanged fields
            current = service.users().drafts().get(
                userId="me",
                id=draft_id,
                format="full"
            ).execute()

            parsed = _parse_draft_message(current)

            # Use new values or fall back to current
            new_to = to if to is not None else parsed["to"]
            new_subject = subject if subject is not None else parsed["subject"]
            new_body = body if body is not None else parsed["body"]
            new_cc = cc if cc is not None else parsed["cc"]
            new_bcc = bcc if bcc is not None else parsed["bcc"]

            # Build new message
            message = MIMEMultipart()
            message["to"] = new_to
            message["subject"] = new_subject
            if new_cc:
                message["cc"] = new_cc
            if new_bcc:
                message["bcc"] = new_bcc

            message.attach(MIMEText(new_body, "plain"))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            # Update the draft
            updated = service.users().drafts().update(
                userId="me",
                id=draft_id,
                body={"message": {"raw": raw}}
            ).execute()

            # Fetch the updated draft to return current state
            refreshed = service.users().drafts().get(
                userId="me",
                id=updated["id"],
                format="full"
            ).execute()

            parsed_updated = _parse_draft_message(refreshed)

            return {
                "success": True,
                "message": "Draft updated successfully.",
                **parsed_updated
            }

        except Exception as e:
            logger.error(f"Failed to update draft: {e}")
            return {"success": False, "error": f"Failed to update draft: {e}"}

    @mcp.tool()
    def delete_draft(draft_id: str) -> Dict[str, Any]:
        """
        Permanently delete a draft.

        WARNING: This action cannot be undone. The draft will be permanently deleted,
        not moved to trash.

        Args:
            draft_id (str): The ID of the draft to delete

        Returns:
            Dict[str, Any]: Result of the deletion

        Example usage:
        1. Delete a draft: delete_draft(draft_id="...")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Delete the draft
            service.users().drafts().delete(
                userId="me",
                id=draft_id
            ).execute()

            return {
                "success": True,
                "message": f"Draft {draft_id} deleted permanently.",
                "draft_id": draft_id
            }

        except Exception as e:
            logger.error(f"Failed to delete draft: {e}")
            return {"success": False, "error": f"Failed to delete draft: {e}"}
