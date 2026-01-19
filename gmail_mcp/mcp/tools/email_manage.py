"""
Email Management Tools Module

Handles email organization: archive, trash, delete, star, read/unread status.
"""

from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_email_manage_tools(mcp: FastMCP) -> None:
    """Set up email management tools on the FastMCP application."""

    @mcp.tool()
    def archive_email(email_id: str) -> Dict[str, Any]:
        """
        Archive an email (remove from inbox but keep in All Mail).

        Args:
            email_id (str): The ID of the email to archive

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()

            return {
                "success": True,
                "message": "Email archived successfully.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to archive email: {e}")
            return {"success": False, "error": f"Failed to archive email: {e}"}

    @mcp.tool()
    def trash_email(email_id: str) -> Dict[str, Any]:
        """
        Move an email to trash.

        Args:
            email_id (str): The ID of the email to trash

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().trash(userId="me", id=email_id).execute()

            return {
                "success": True,
                "message": "Email moved to trash.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to trash email: {e}")
            return {"success": False, "error": f"Failed to trash email: {e}"}

    @mcp.tool()
    def delete_email(email_id: str) -> Dict[str, Any]:
        """
        Permanently delete an email. THIS CANNOT BE UNDONE.

        Args:
            email_id (str): The ID of the email to delete permanently

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().delete(userId="me", id=email_id).execute()

            return {
                "success": True,
                "message": "Email permanently deleted.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to delete email: {e}")
            return {"success": False, "error": f"Failed to delete email: {e}"}

    @mcp.tool()
    def mark_as_read(email_id: str) -> Dict[str, Any]:
        """
        Mark an email as read.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            return {
                "success": True,
                "message": "Email marked as read.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return {"success": False, "error": f"Failed to mark as read: {e}"}

    @mcp.tool()
    def mark_as_unread(email_id: str) -> Dict[str, Any]:
        """
        Mark an email as unread.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": ["UNREAD"]}
            ).execute()

            return {
                "success": True,
                "message": "Email marked as unread.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to mark as unread: {e}")
            return {"success": False, "error": f"Failed to mark as unread: {e}"}

    @mcp.tool()
    def star_email(email_id: str) -> Dict[str, Any]:
        """
        Star an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": ["STARRED"]}
            ).execute()

            return {
                "success": True,
                "message": "Email starred.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to star email: {e}")
            return {"success": False, "error": f"Failed to star email: {e}"}

    @mcp.tool()
    def unstar_email(email_id: str) -> Dict[str, Any]:
        """
        Remove star from an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["STARRED"]}
            ).execute()

            return {
                "success": True,
                "message": "Star removed.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to unstar email: {e}")
            return {"success": False, "error": f"Failed to unstar email: {e}"}
