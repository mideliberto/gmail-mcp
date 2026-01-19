"""
Gmail Filter Management Tools Module

Handles Gmail filter operations: list, create, update, delete.
Requires the gmail.settings.basic scope.
"""

from typing import Dict, Any, Optional, List

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_filter_tools(mcp: FastMCP) -> None:
    """Set up Gmail filter management tools on the FastMCP application."""

    @mcp.tool()
    def list_filters() -> Dict[str, Any]:
        """
        List all Gmail filters in the user's account.

        Returns:
            Dict[str, Any]: List of filters with their criteria and actions
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            results = service.users().settings().filters().list(userId="me").execute()
            filters = results.get("filter", [])

            formatted_filters = []
            for f in filters:
                criteria = f.get("criteria", {})
                action = f.get("action", {})

                formatted_filters.append({
                    "id": f.get("id"),
                    "criteria": {
                        "from": criteria.get("from"),
                        "to": criteria.get("to"),
                        "subject": criteria.get("subject"),
                        "query": criteria.get("query"),
                        "negatedQuery": criteria.get("negatedQuery"),
                        "hasAttachment": criteria.get("hasAttachment"),
                        "excludeChats": criteria.get("excludeChats"),
                        "size": criteria.get("size"),
                        "sizeComparison": criteria.get("sizeComparison"),
                    },
                    "action": {
                        "addLabelIds": action.get("addLabelIds", []),
                        "removeLabelIds": action.get("removeLabelIds", []),
                        "forward": action.get("forward"),
                    }
                })

            return {
                "success": True,
                "count": len(formatted_filters),
                "filters": formatted_filters
            }

        except Exception as e:
            logger.error(f"Failed to list filters: {e}")
            return {"success": False, "error": f"Failed to list filters: {e}"}

    @mcp.tool()
    def create_filter(
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        subject: Optional[str] = None,
        query: Optional[str] = None,
        has_attachment: Optional[bool] = None,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
        archive: bool = False,
        mark_read: bool = False,
        star: bool = False,
        forward_to: Optional[str] = None,
        never_spam: bool = False,
        mark_important: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Create a new Gmail filter.

        At least one criteria (from_address, to_address, subject, query, or has_attachment)
        must be provided. At least one action (add_label_ids, remove_label_ids, archive,
        mark_read, star, forward_to, never_spam, or mark_important) must be provided.

        Args:
            from_address (str, optional): Filter emails from this address
            to_address (str, optional): Filter emails to this address
            subject (str, optional): Filter emails with this subject
            query (str, optional): Gmail search query for matching
            has_attachment (bool, optional): Filter emails with attachments
            add_label_ids (List[str], optional): Label IDs to add (use list_labels to get IDs)
            remove_label_ids (List[str], optional): Label IDs to remove
            archive (bool): Archive matching emails (skip inbox)
            mark_read (bool): Mark matching emails as read
            star (bool): Star matching emails
            forward_to (str, optional): Forward to this email address
            never_spam (bool): Never send to spam
            mark_important (bool, optional): Mark as important (True) or not important (False)

        Returns:
            Dict[str, Any]: The created filter details

        Example usage:
        1. Filter newsletters to a label and archive:
           create_filter(
               from_address="newsletter@example.com",
               add_label_ids=["Label_123"],
               archive=True
           )

        2. Flag emails for Claude review:
           create_filter(
               from_address="important@company.com",
               add_label_ids=["Label_ClaudeReview"]
           )

        3. Filter by subject and mark as important:
           create_filter(
               subject="urgent",
               mark_important=True,
               star=True
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        # Validate at least one criteria
        if not any([from_address, to_address, subject, query, has_attachment is not None]):
            return {
                "success": False,
                "error": "At least one filter criteria must be provided (from_address, to_address, subject, query, or has_attachment)"
            }

        # Validate at least one action
        if not any([add_label_ids, remove_label_ids, archive, mark_read, star, forward_to, never_spam, mark_important is not None]):
            return {
                "success": False,
                "error": "At least one action must be provided"
            }

        try:
            service = get_gmail_service(credentials)

            # Build criteria
            criteria = {}
            if from_address:
                criteria["from"] = from_address
            if to_address:
                criteria["to"] = to_address
            if subject:
                criteria["subject"] = subject
            if query:
                criteria["query"] = query
            if has_attachment is not None:
                criteria["hasAttachment"] = has_attachment

            # Build action
            action = {}
            if add_label_ids:
                action["addLabelIds"] = add_label_ids
            if remove_label_ids:
                action["removeLabelIds"] = remove_label_ids

            # Archive = remove INBOX label
            if archive:
                if "removeLabelIds" not in action:
                    action["removeLabelIds"] = []
                if "INBOX" not in action["removeLabelIds"]:
                    action["removeLabelIds"].append("INBOX")

            # Mark as read = remove UNREAD label
            if mark_read:
                if "removeLabelIds" not in action:
                    action["removeLabelIds"] = []
                if "UNREAD" not in action["removeLabelIds"]:
                    action["removeLabelIds"].append("UNREAD")

            # Star = add STARRED label
            if star:
                if "addLabelIds" not in action:
                    action["addLabelIds"] = []
                if "STARRED" not in action["addLabelIds"]:
                    action["addLabelIds"].append("STARRED")

            # Forward
            if forward_to:
                action["forward"] = forward_to

            # Never spam = add to important, remove from spam
            if never_spam:
                if "removeLabelIds" not in action:
                    action["removeLabelIds"] = []
                if "SPAM" not in action["removeLabelIds"]:
                    action["removeLabelIds"].append("SPAM")

            # Mark important
            if mark_important is True:
                if "addLabelIds" not in action:
                    action["addLabelIds"] = []
                if "IMPORTANT" not in action["addLabelIds"]:
                    action["addLabelIds"].append("IMPORTANT")
            elif mark_important is False:
                if "removeLabelIds" not in action:
                    action["removeLabelIds"] = []
                if "IMPORTANT" not in action["removeLabelIds"]:
                    action["removeLabelIds"].append("IMPORTANT")

            filter_body = {
                "criteria": criteria,
                "action": action
            }

            created_filter = service.users().settings().filters().create(
                userId="me",
                body=filter_body
            ).execute()

            return {
                "success": True,
                "message": "Filter created successfully.",
                "filter_id": created_filter.get("id"),
                "criteria": criteria,
                "action": action
            }

        except Exception as e:
            logger.error(f"Failed to create filter: {e}")
            return {"success": False, "error": f"Failed to create filter: {e}"}

    @mcp.tool()
    def delete_filter(filter_id: str) -> Dict[str, Any]:
        """
        Delete a Gmail filter.

        Args:
            filter_id (str): The ID of the filter to delete (from list_filters)

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            service.users().settings().filters().delete(
                userId="me",
                id=filter_id
            ).execute()

            return {
                "success": True,
                "message": "Filter deleted successfully.",
                "filter_id": filter_id
            }

        except Exception as e:
            logger.error(f"Failed to delete filter: {e}")
            return {"success": False, "error": f"Failed to delete filter: {e}"}

    @mcp.tool()
    def get_filter(filter_id: str) -> Dict[str, Any]:
        """
        Get details of a specific Gmail filter.

        Args:
            filter_id (str): The ID of the filter

        Returns:
            Dict[str, Any]: The filter details
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            f = service.users().settings().filters().get(
                userId="me",
                id=filter_id
            ).execute()

            criteria = f.get("criteria", {})
            action = f.get("action", {})

            return {
                "success": True,
                "filter": {
                    "id": f.get("id"),
                    "criteria": {
                        "from": criteria.get("from"),
                        "to": criteria.get("to"),
                        "subject": criteria.get("subject"),
                        "query": criteria.get("query"),
                        "negatedQuery": criteria.get("negatedQuery"),
                        "hasAttachment": criteria.get("hasAttachment"),
                        "excludeChats": criteria.get("excludeChats"),
                        "size": criteria.get("size"),
                        "sizeComparison": criteria.get("sizeComparison"),
                    },
                    "action": {
                        "addLabelIds": action.get("addLabelIds", []),
                        "removeLabelIds": action.get("removeLabelIds", []),
                        "forward": action.get("forward"),
                    }
                }
            }

        except Exception as e:
            logger.error(f"Failed to get filter: {e}")
            return {"success": False, "error": f"Failed to get filter: {e}"}

    @mcp.tool()
    def create_claude_review_filter(
        from_address: Optional[str] = None,
        subject_contains: Optional[str] = None,
        query: Optional[str] = None,
        review_type: str = "Review"
    ) -> Dict[str, Any]:
        """
        Create a filter to automatically flag emails for Claude review.

        This is a convenience tool that creates a filter applying one of the
        Claude review labels. Run setup_claude_review_labels() first to ensure
        the labels exist.

        Args:
            from_address (str, optional): Filter emails from this address
            subject_contains (str, optional): Filter emails with this in the subject
            query (str, optional): Gmail search query for matching
            review_type (str): Type of review - "Review", "Urgent", "Reply-Needed",
                              "Summarize", or "Action-Required" (default: "Review")

        Returns:
            Dict[str, Any]: The created filter details

        Example usage:
        1. Flag all emails from a VIP for urgent review:
           create_claude_review_filter(
               from_address="ceo@company.com",
               review_type="Urgent"
           )

        2. Flag emails with "invoice" in subject for action:
           create_claude_review_filter(
               subject_contains="invoice",
               review_type="Action-Required"
           )
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        # Validate review type
        valid_types = ["Review", "Urgent", "Reply-Needed", "Summarize", "Action-Required"]
        if review_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid review_type. Must be one of: {', '.join(valid_types)}"
            }

        # Validate at least one criteria
        if not any([from_address, subject_contains, query]):
            return {
                "success": False,
                "error": "At least one criteria must be provided (from_address, subject_contains, or query)"
            }

        try:
            service = get_gmail_service(credentials)

            # Find the Claude review label
            label_name = f"Claude/{review_type}"
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

            # Build criteria
            criteria = {}
            if from_address:
                criteria["from"] = from_address
            if subject_contains:
                criteria["subject"] = subject_contains
            if query:
                criteria["query"] = query

            # Build action
            action = {
                "addLabelIds": [label_id]
            }

            filter_body = {
                "criteria": criteria,
                "action": action
            }

            created_filter = service.users().settings().filters().create(
                userId="me",
                body=filter_body
            ).execute()

            return {
                "success": True,
                "message": f"Filter created to flag emails for Claude/{review_type}.",
                "filter_id": created_filter.get("id"),
                "label_name": label_name,
                "label_id": label_id,
                "criteria": criteria
            }

        except Exception as e:
            logger.error(f"Failed to create Claude review filter: {e}")
            return {"success": False, "error": f"Failed to create Claude review filter: {e}"}
