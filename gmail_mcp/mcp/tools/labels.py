"""
Label Management Tools Module

Handles Gmail label operations: list, create, apply, remove.
"""

from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.utils.config import get_config

logger = get_logger(__name__)


def _resolve_label(service, label_name: str) -> Dict[str, Any]:
    """
    Resolve a label name to its ID using case-insensitive matching.

    Args:
        service: Gmail API service instance
        label_name: The label name to search for (case-insensitive)

    Returns:
        Dict with 'id', 'name' if found, or 'error', 'suggestions' if not found
    """
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    # Try exact match first (case-insensitive)
    label_name_lower = label_name.lower()
    for label in labels:
        if label["name"].lower() == label_name_lower:
            return {"id": label["id"], "name": label["name"]}

    # Try partial match (contains)
    partial_matches = []
    for label in labels:
        if label_name_lower in label["name"].lower():
            partial_matches.append(label)

    if len(partial_matches) == 1:
        # Unique partial match
        return {"id": partial_matches[0]["id"], "name": partial_matches[0]["name"]}
    elif len(partial_matches) > 1:
        # Ambiguous - multiple matches
        return {
            "error": f"Ambiguous label name '{label_name}' matches multiple labels",
            "suggestions": [l["name"] for l in partial_matches[:5]]
        }

    # No match found - suggest similar labels
    suggestions = []
    for label in labels:
        # Simple similarity: shares common words
        label_words = set(label["name"].lower().split())
        search_words = set(label_name_lower.split())
        if label_words & search_words:  # Has common words
            suggestions.append(label["name"])

    return {
        "error": f"Label '{label_name}' not found",
        "suggestions": suggestions[:5] if suggestions else [l["name"] for l in labels[:5]]
    }


def setup_label_tools(mcp: FastMCP) -> None:
    """Set up label management tools on the FastMCP application."""

    @mcp.tool()
    def list_labels() -> Dict[str, Any]:
        """
        List all labels in the user's Gmail account.

        Returns:
            Dict[str, Any]: List of labels with IDs and names
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            return {
                "success": True,
                "labels": [
                    {
                        "id": label["id"],
                        "name": label["name"],
                        "type": label.get("type", "user")
                    }
                    for label in labels
                ]
            }

        except Exception as e:
            logger.error(f"Failed to list labels: {e}")
            return {"success": False, "error": f"Failed to list labels: {e}"}

    @mcp.tool()
    def create_label(name: str, background_color: Optional[str] = None, text_color: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new label.

        Args:
            name (str): Name for the new label
            background_color (str, optional): Background color in hex (e.g., "#16a765")
            text_color (str, optional): Text color in hex (e.g., "#ffffff")

        Returns:
            Dict[str, Any]: The created label details
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            label_body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show"
            }

            if background_color or text_color:
                label_body["color"] = {}
                if background_color:
                    label_body["color"]["backgroundColor"] = background_color
                if text_color:
                    label_body["color"]["textColor"] = text_color

            label = service.users().labels().create(userId="me", body=label_body).execute()

            return {
                "success": True,
                "message": f"Label '{name}' created.",
                "label": {
                    "id": label["id"],
                    "name": label["name"]
                }
            }

        except Exception as e:
            logger.error(f"Failed to create label: {e}")
            return {"success": False, "error": f"Failed to create label: {e}"}

    @mcp.tool()
    def delete_label(label_id: str) -> Dict[str, Any]:
        """
        Delete a label.

        Args:
            label_id (str): The ID of the label to delete

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().labels().delete(userId="me", id=label_id).execute()

            return {
                "success": True,
                "message": "Label deleted successfully.",
                "label_id": label_id
            }

        except Exception as e:
            logger.error(f"Failed to delete label: {e}")
            return {"success": False, "error": f"Failed to delete label: {e}"}

    @mcp.tool()
    def apply_label(
        email_id: str,
        label_id: Optional[str] = None,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a label to an email.

        Args:
            email_id (str): The ID of the email
            label_id (str, optional): The ID of the label to apply
            label (str, optional): The name of the label (case-insensitive fuzzy matching).
                                  Use this for convenience instead of label_id.

        Note: Either label_id or label must be provided. If both are provided, label_id takes precedence.

        Returns:
            Dict[str, Any]: Result of the operation

        Example usage:
        1. By label ID: apply_label(email_id="...", label_id="Label_123")
        2. By label name: apply_label(email_id="...", label="Important")
        3. Case-insensitive: apply_label(email_id="...", label="important")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        if not label_id and not label:
            return {"success": False, "error": "Either label_id or label name must be provided"}

        try:
            service = get_gmail_service(credentials)

            # Resolve label name to ID if needed
            resolved_label_id = label_id
            resolved_label_name = None

            if not label_id and label:
                resolved = _resolve_label(service, label)
                if "error" in resolved:
                    return {
                        "success": False,
                        "error": resolved["error"],
                        "suggestions": resolved.get("suggestions", [])
                    }
                resolved_label_id = resolved["id"]
                resolved_label_name = resolved["name"]

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [resolved_label_id]}
            ).execute()

            return {
                "success": True,
                "message": f"Label '{resolved_label_name or resolved_label_id}' applied.",
                "email_id": email_id,
                "label_id": resolved_label_id,
                "label_name": resolved_label_name
            }

        except Exception as e:
            logger.error(f"Failed to apply label: {e}")
            return {"success": False, "error": f"Failed to apply label: {e}"}

    @mcp.tool()
    def remove_label(
        email_id: str,
        label_id: Optional[str] = None,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove a label from an email.

        Args:
            email_id (str): The ID of the email
            label_id (str, optional): The ID of the label to remove
            label (str, optional): The name of the label (case-insensitive fuzzy matching).
                                  Use this for convenience instead of label_id.

        Note: Either label_id or label must be provided. If both are provided, label_id takes precedence.

        Returns:
            Dict[str, Any]: Result of the operation

        Example usage:
        1. By label ID: remove_label(email_id="...", label_id="Label_123")
        2. By label name: remove_label(email_id="...", label="Important")
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        if not label_id and not label:
            return {"success": False, "error": "Either label_id or label name must be provided"}

        try:
            service = get_gmail_service(credentials)

            # Resolve label name to ID if needed
            resolved_label_id = label_id
            resolved_label_name = None

            if not label_id and label:
                resolved = _resolve_label(service, label)
                if "error" in resolved:
                    return {
                        "success": False,
                        "error": resolved["error"],
                        "suggestions": resolved.get("suggestions", [])
                    }
                resolved_label_id = resolved["id"]
                resolved_label_name = resolved["name"]

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": [resolved_label_id]}
            ).execute()

            return {
                "success": True,
                "message": f"Label '{resolved_label_name or resolved_label_id}' removed.",
                "email_id": email_id,
                "label_id": resolved_label_id,
                "label_name": resolved_label_name
            }

        except Exception as e:
            logger.error(f"Failed to remove label: {e}")
            return {"success": False, "error": f"Failed to remove label: {e}"}

    @mcp.tool()
    def setup_claude_review_labels() -> Dict[str, Any]:
        """
        Set up Claude review labels for email triage.

        Creates a set of labels that can be used with Gmail filters to flag
        emails for Claude to review. These labels help organize emails that
        need AI assistance.

        Labels created:
        - Claude/Review - General review needed
        - Claude/Urgent - Urgent review needed
        - Claude/Reply-Needed - Needs a reply drafted
        - Claude/Summarize - Needs summarization
        - Claude/Action-Required - Has action items to extract

        Returns:
            Dict[str, Any]: Result including created labels
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Define Claude review labels with colors
            claude_labels = [
                {"name": "Claude/Review", "bg": "#4986e7", "text": "#ffffff"},
                {"name": "Claude/Urgent", "bg": "#cc3a21", "text": "#ffffff"},
                {"name": "Claude/Reply-Needed", "bg": "#16a765", "text": "#ffffff"},
                {"name": "Claude/Summarize", "bg": "#ffad47", "text": "#000000"},
                {"name": "Claude/Action-Required", "bg": "#a479e2", "text": "#ffffff"},
            ]

            created = []
            existing = []

            # Get existing labels
            results = service.users().labels().list(userId="me").execute()
            existing_names = {l["name"]: l["id"] for l in results.get("labels", [])}

            for label_def in claude_labels:
                if label_def["name"] in existing_names:
                    existing.append({
                        "name": label_def["name"],
                        "id": existing_names[label_def["name"]]
                    })
                else:
                    label_body = {
                        "name": label_def["name"],
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                        "color": {
                            "backgroundColor": label_def["bg"],
                            "textColor": label_def["text"]
                        }
                    }
                    label = service.users().labels().create(userId="me", body=label_body).execute()
                    created.append({
                        "name": label["name"],
                        "id": label["id"]
                    })

            return {
                "success": True,
                "message": f"Created {len(created)} labels, {len(existing)} already existed.",
                "created": created,
                "existing": existing,
                "usage": {
                    "description": "Apply these labels via Gmail filters to flag emails for Claude review",
                    "search_example": "label:Claude-Review is:unread",
                    "filter_tip": "Create Gmail filters to auto-apply these labels to specific senders or subjects"
                }
            }

        except Exception as e:
            logger.error(f"Failed to setup Claude review labels: {e}")
            return {"success": False, "error": f"Failed to setup Claude review labels: {e}"}

    @mcp.tool()
    def get_emails_for_claude_review(label_name: str = "Claude/Review", max_results: int = 10) -> Dict[str, Any]:
        """
        Get emails flagged for Claude review.

        Retrieves emails with the specified Claude review label.

        Args:
            label_name (str): The Claude review label to search for (default: "Claude/Review")
            max_results (int): Maximum number of emails to return (default: 10)

        Returns:
            Dict[str, Any]: List of emails needing review
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Find the label ID
            results = service.users().labels().list(userId="me").execute()
            label_id = None
            for label in results.get("labels", []):
                if label["name"] == label_name:
                    label_id = label["id"]
                    break

            if not label_id:
                return {
                    "success": False,
                    "error": f"Label '{label_name}' not found. Run setup_claude_review_labels() first."
                }

            # Get emails with this label
            result = service.users().messages().list(
                userId="me",
                labelIds=[label_id],
                maxResults=max_results
            ).execute()

            messages = result.get("messages", [])
            emails = []

            from gmail_mcp.gmail.helpers import extract_email_info

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                emails.append(extract_email_info(msg))

            return {
                "success": True,
                "label": label_name,
                "count": len(emails),
                "emails": emails,
                "next_page_token": result.get("nextPageToken")
            }

        except Exception as e:
            logger.error(f"Failed to get emails for Claude review: {e}")
            return {"success": False, "error": f"Failed to get emails for Claude review: {e}"}
