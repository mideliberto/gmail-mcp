"""
Attachment Tools Module

Handles listing and downloading email attachments.
"""

import base64
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_attachment_tools(mcp: FastMCP) -> None:
    """Set up attachment tools on the FastMCP application."""

    @mcp.tool()
    def get_attachments(email_id: str) -> Dict[str, Any]:
        """
        List all attachments in an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: List of attachments with metadata
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            attachments = []

            def find_attachments(parts):
                for part in parts:
                    if part.get("filename"):
                        attachments.append({
                            "attachment_id": part["body"].get("attachmentId"),
                            "filename": part["filename"],
                            "mime_type": part["mimeType"],
                            "size": part["body"].get("size", 0)
                        })
                    if "parts" in part:
                        find_attachments(part["parts"])

            if "parts" in msg["payload"]:
                find_attachments(msg["payload"]["parts"])

            return {
                "success": True,
                "email_id": email_id,
                "attachments": attachments,
                "count": len(attachments)
            }

        except Exception as e:
            logger.error(f"Failed to get attachments: {e}")
            return {"success": False, "error": f"Failed to get attachments: {e}"}

    @mcp.tool()
    def download_attachment(email_id: str, attachment_id: str, save_path: str) -> Dict[str, Any]:
        """
        Download an attachment from an email.

        Args:
            email_id (str): The ID of the email
            attachment_id (str): The attachment ID (from get_attachments)
            save_path (str): Full path where to save the file

        Returns:
            Dict[str, Any]: Result including the saved file path
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=email_id,
                id=attachment_id
            ).execute()

            data = base64.urlsafe_b64decode(attachment["data"])

            with open(save_path, "wb") as f:
                f.write(data)

            return {
                "success": True,
                "message": f"Attachment saved to {save_path}",
                "file_path": save_path,
                "size_bytes": len(data)
            }

        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            return {"success": False, "error": f"Failed to download attachment: {e}"}
