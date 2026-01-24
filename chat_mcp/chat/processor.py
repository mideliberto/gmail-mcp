"""
Chat Processor Module

This module provides functionality for interacting with the Google Chat API.
"""

import threading
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger("chat_mcp.processor")

# Thread-safe singleton instance (Issue #8 prevention)
_processor_instance: Optional["ChatProcessor"] = None
_processor_lock = threading.Lock()


class ChatProcessor:
    """
    Processor for Google Chat operations.
    """

    def __init__(self) -> None:
        """Initialize the Chat processor."""
        self._service = None
        self._service_lock = threading.Lock()  # Issue #8: thread safety

    def _get_service(self) -> Any:
        """
        Get the Google Chat API service.

        Thread-safe lazy initialization of the service.

        Returns:
            Any: The Google Chat API service.

        Raises:
            RuntimeError: If authentication fails.
        """
        with self._service_lock:
            if self._service is None:
                credentials = get_credentials()
                if not credentials:
                    raise RuntimeError("Not authenticated with Google")
                self._service = build("chat", "v1", credentials=credentials)
            return self._service

    # =========================================================================
    # Space Operations
    # =========================================================================

    def list_spaces(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List spaces the user is a member of.

        Args:
            page_size: Maximum number of spaces to return.
            page_token: Token for pagination.
            filter_str: Filter string (e.g., "spaceType = 'SPACE'").

        Returns:
            Dict containing spaces list and nextPageToken if available.
        """
        service = self._get_service()

        request_params: Dict[str, Any] = {
            "pageSize": page_size,
        }

        if page_token:
            request_params["pageToken"] = page_token
        if filter_str:
            request_params["filter"] = filter_str

        result = service.spaces().list(**request_params).execute()

        return {
            "spaces": result.get("spaces", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_space(self, space_name: str) -> Dict[str, Any]:
        """
        Get details of a specific space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").

        Returns:
            Dict containing space details.
        """
        service = self._get_service()
        result = service.spaces().get(name=space_name).execute()
        return result

    def create_space(
        self,
        display_name: str,
        space_type: str = "SPACE",
        external_user_allowed: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new space.

        Args:
            display_name: Display name for the space.
            space_type: Type of space - "SPACE" or "GROUP_CHAT".
            external_user_allowed: Whether external users can join.

        Returns:
            Dict containing the created space.
        """
        service = self._get_service()

        space_body = {
            "displayName": display_name,
            "spaceType": space_type,
            "externalUserAllowed": external_user_allowed,
        }

        result = service.spaces().create(body=space_body).execute()
        return result

    def update_space(
        self,
        space_name: str,
        display_name: Optional[str] = None,
        space_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a space.

        Args:
            space_name: The resource name of the space.
            display_name: New display name.
            space_type: New space type.

        Returns:
            Dict containing the updated space.
        """
        service = self._get_service()

        space_body: Dict[str, Any] = {}
        update_mask_fields = []

        if display_name is not None:
            space_body["displayName"] = display_name
            update_mask_fields.append("displayName")
        if space_type is not None:
            space_body["spaceType"] = space_type
            update_mask_fields.append("spaceType")

        if not update_mask_fields:
            return {"error": "No fields to update"}

        result = service.spaces().patch(
            name=space_name,
            body=space_body,
            updateMask=",".join(update_mask_fields),
        ).execute()

        return result

    def delete_space(self, space_name: str) -> Dict[str, Any]:
        """
        Delete a space.

        Args:
            space_name: The resource name of the space.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()
        service.spaces().delete(name=space_name).execute()
        return {"success": True, "message": f"Space {space_name} deleted"}

    def find_direct_message(self, user_name: str) -> Dict[str, Any]:
        """
        Find an existing direct message space with a user.

        Args:
            user_name: The resource name of the user (e.g., "users/123456").

        Returns:
            Dict containing the DM space if found.
        """
        service = self._get_service()

        try:
            result = service.spaces().findDirectMessage(name=user_name).execute()
            return result
        except Exception as e:
            return {"error": str(e), "message": "Direct message not found"}

    def setup_space(
        self,
        display_name: str,
        member_emails: List[str],
        space_type: str = "SPACE",
    ) -> Dict[str, Any]:
        """
        Create a space and add members in one operation.

        Args:
            display_name: Display name for the space.
            member_emails: List of email addresses to add.
            space_type: Type of space.

        Returns:
            Dict containing the created space and membership results.
        """
        service = self._get_service()

        # Create the space with initial members
        space_body = {
            "displayName": display_name,
            "spaceType": space_type,
        }

        memberships = [
            {"member": {"name": f"users/{email}", "type": "HUMAN"}}
            for email in member_emails
        ]

        result = service.spaces().setup(
            body={
                "space": space_body,
                "memberships": memberships,
            }
        ).execute()

        return result

    def search_spaces(
        self,
        query: str,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for spaces (admin only).

        Args:
            query: Search query string.
            page_size: Maximum number of spaces to return.
            page_token: Token for pagination.

        Returns:
            Dict containing matching spaces.
        """
        service = self._get_service()

        request_params: Dict[str, Any] = {
            "query": query,
            "pageSize": page_size,
        }

        if page_token:
            request_params["pageToken"] = page_token

        try:
            result = service.spaces().search(**request_params).execute()
            return {
                "spaces": result.get("spaces", []),
                "nextPageToken": result.get("nextPageToken"),
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Search failed. This may require admin permissions.",
                "spaces": [],
            }

    # =========================================================================
    # Message Operations
    # =========================================================================

    def list_messages(
        self,
        space_name: str,
        page_size: int = 25,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
        order_by: Optional[str] = None,
        show_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List messages in a space.

        Args:
            space_name: The resource name of the space.
            page_size: Maximum number of messages to return.
            page_token: Token for pagination.
            filter_str: Filter string for messages.
            order_by: Order by string (e.g., "createTime desc").
            show_deleted: Whether to include deleted messages.

        Returns:
            Dict containing messages list and nextPageToken.
        """
        service = self._get_service()

        request_params: Dict[str, Any] = {
            "parent": space_name,
            "pageSize": page_size,
            "showDeleted": show_deleted,
        }

        if page_token:
            request_params["pageToken"] = page_token
        if filter_str:
            request_params["filter"] = filter_str
        if order_by:
            request_params["orderBy"] = order_by

        result = service.spaces().messages().list(**request_params).execute()

        return {
            "messages": result.get("messages", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_message(self, message_name: str) -> Dict[str, Any]:
        """
        Get a specific message.

        Args:
            message_name: The resource name of the message.

        Returns:
            Dict containing the message.
        """
        service = self._get_service()
        result = service.spaces().messages().get(name=message_name).execute()
        return result

    def send_message(
        self,
        space_name: str,
        text: str,
        thread_key: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a text message to a space.

        Args:
            space_name: The resource name of the space.
            text: The message text.
            thread_key: Optional thread key to reply to a thread.
            request_id: Optional request ID for idempotency.

        Returns:
            Dict containing the sent message.
        """
        service = self._get_service()

        message_body: Dict[str, Any] = {
            "text": text,
        }

        if thread_key:
            message_body["thread"] = {"threadKey": thread_key}

        request_params: Dict[str, Any] = {
            "parent": space_name,
            "body": message_body,
        }

        if request_id:
            request_params["requestId"] = request_id
        if thread_key:
            request_params["messageReplyOption"] = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"

        result = service.spaces().messages().create(**request_params).execute()
        return result

    def update_message(
        self,
        message_name: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Update a message's text.

        Args:
            message_name: The resource name of the message.
            text: New message text.

        Returns:
            Dict containing the updated message.
        """
        service = self._get_service()

        message_body = {
            "text": text,
        }

        result = service.spaces().messages().patch(
            name=message_name,
            body=message_body,
            updateMask="text",
        ).execute()

        return result

    def delete_message(self, message_name: str) -> Dict[str, Any]:
        """
        Delete a message.

        Args:
            message_name: The resource name of the message.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()
        service.spaces().messages().delete(name=message_name).execute()
        return {"success": True, "message": f"Message {message_name} deleted"}

    def send_card_message(
        self,
        space_name: str,
        cards: List[Dict[str, Any]],
        text: Optional[str] = None,
        thread_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a rich card message.

        Args:
            space_name: The resource name of the space.
            cards: List of card definitions.
            text: Optional fallback text.
            thread_key: Optional thread key.

        Returns:
            Dict containing the sent message.
        """
        service = self._get_service()

        message_body: Dict[str, Any] = {
            "cardsV2": cards,
        }

        if text:
            message_body["text"] = text
        if thread_key:
            message_body["thread"] = {"threadKey": thread_key}

        request_params: Dict[str, Any] = {
            "parent": space_name,
            "body": message_body,
        }

        if thread_key:
            request_params["messageReplyOption"] = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"

        result = service.spaces().messages().create(**request_params).execute()
        return result

    # =========================================================================
    # Member Operations
    # =========================================================================

    def list_members(
        self,
        space_name: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
        show_groups: bool = False,
        show_invited: bool = False,
    ) -> Dict[str, Any]:
        """
        List members of a space.

        Args:
            space_name: The resource name of the space.
            page_size: Maximum number of members to return.
            page_token: Token for pagination.
            filter_str: Filter string for members.
            show_groups: Whether to include group members.
            show_invited: Whether to include invited members.

        Returns:
            Dict containing members list and nextPageToken.
        """
        service = self._get_service()

        request_params: Dict[str, Any] = {
            "parent": space_name,
            "pageSize": page_size,
            "showGroups": show_groups,
            "showInvited": show_invited,
        }

        if page_token:
            request_params["pageToken"] = page_token
        if filter_str:
            request_params["filter"] = filter_str

        result = service.spaces().members().list(**request_params).execute()

        return {
            "members": result.get("memberships", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_member(self, member_name: str) -> Dict[str, Any]:
        """
        Get details of a specific member.

        Args:
            member_name: The resource name of the membership.

        Returns:
            Dict containing member details.
        """
        service = self._get_service()
        result = service.spaces().members().get(name=member_name).execute()
        return result

    def add_member(
        self,
        space_name: str,
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Add a member to a space.

        Args:
            space_name: The resource name of the space.
            user_email: Email address of the user to add.

        Returns:
            Dict containing the created membership.
        """
        service = self._get_service()

        membership_body = {
            "member": {
                "name": f"users/{user_email}",
                "type": "HUMAN",
            }
        }

        result = service.spaces().members().create(
            parent=space_name,
            body=membership_body,
        ).execute()

        return result

    def update_member(
        self,
        member_name: str,
        role: str,
    ) -> Dict[str, Any]:
        """
        Update a member's role.

        Args:
            member_name: The resource name of the membership.
            role: New role - "ROLE_MEMBER" or "ROLE_MANAGER".

        Returns:
            Dict containing the updated membership.
        """
        service = self._get_service()

        membership_body = {
            "role": role,
        }

        result = service.spaces().members().patch(
            name=member_name,
            body=membership_body,
            updateMask="role",
        ).execute()

        return result

    def remove_member(self, member_name: str) -> Dict[str, Any]:
        """
        Remove a member from a space.

        Args:
            member_name: The resource name of the membership.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()
        service.spaces().members().delete(name=member_name).execute()
        return {"success": True, "message": f"Member {member_name} removed"}

    # =========================================================================
    # Reaction Operations
    # =========================================================================

    def list_reactions(
        self,
        message_name: str,
        page_size: int = 25,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List reactions on a message.

        Args:
            message_name: The resource name of the message.
            page_size: Maximum number of reactions to return.
            page_token: Token for pagination.
            filter_str: Filter string for reactions.

        Returns:
            Dict containing reactions list and nextPageToken.
        """
        service = self._get_service()

        request_params: Dict[str, Any] = {
            "parent": message_name,
            "pageSize": page_size,
        }

        if page_token:
            request_params["pageToken"] = page_token
        if filter_str:
            request_params["filter"] = filter_str

        result = service.spaces().messages().reactions().list(**request_params).execute()

        return {
            "reactions": result.get("reactions", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def add_reaction(
        self,
        message_name: str,
        emoji_unicode: str,
    ) -> Dict[str, Any]:
        """
        Add a reaction to a message.

        Args:
            message_name: The resource name of the message.
            emoji_unicode: Unicode emoji character.

        Returns:
            Dict containing the created reaction.
        """
        service = self._get_service()

        reaction_body = {
            "emoji": {
                "unicode": emoji_unicode,
            }
        }

        result = service.spaces().messages().reactions().create(
            parent=message_name,
            body=reaction_body,
        ).execute()

        return result

    def remove_reaction(self, reaction_name: str) -> Dict[str, Any]:
        """
        Remove a reaction from a message.

        Args:
            reaction_name: The resource name of the reaction.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()
        service.spaces().messages().reactions().delete(name=reaction_name).execute()
        return {"success": True, "message": f"Reaction {reaction_name} removed"}

    # =========================================================================
    # Attachment Operations
    # =========================================================================

    def get_attachment(self, attachment_name: str) -> Dict[str, Any]:
        """
        Get attachment metadata.

        Args:
            attachment_name: The resource name of the attachment.

        Returns:
            Dict containing attachment metadata.
        """
        service = self._get_service()

        # Attachments are accessed via the media endpoint
        result = service.media().download(resourceName=attachment_name).execute()
        return result

    # =========================================================================
    # Utility Operations
    # =========================================================================

    def check_auth(self) -> Dict[str, Any]:
        """
        Verify Chat API authentication works.

        Returns:
            Dict containing auth status.
        """
        try:
            # Try to list spaces to verify authentication
            result = self.list_spaces(page_size=1)

            if "error" in result:
                return {
                    "authenticated": False,
                    "message": f"Authentication error: {result['error']}",
                }

            return {
                "authenticated": True,
                "message": "Successfully authenticated with Google Chat API",
                "space_count": len(result.get("spaces", [])),
            }
        except Exception as e:
            return {
                "authenticated": False,
                "message": f"Authentication failed: {e}",
            }


def get_chat_processor() -> ChatProcessor:
    """
    Get the singleton ChatProcessor instance (thread-safe).

    Returns:
        ChatProcessor: The singleton instance.
    """
    global _processor_instance
    with _processor_lock:
        if _processor_instance is None:
            _processor_instance = ChatProcessor()
        return _processor_instance
