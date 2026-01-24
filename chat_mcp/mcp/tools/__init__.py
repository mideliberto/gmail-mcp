"""
MCP Tools for Chat MCP server.

This module provides all the tool definitions for the Chat MCP server.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from chat_mcp.chat.processor import get_chat_processor

logger = get_logger("chat_mcp.tools")


def setup_tools(mcp: FastMCP) -> None:
    """
    Set up all Chat MCP tools.

    Args:
        mcp: The FastMCP application instance.
    """

    # =========================================================================
    # Space Operations (8 tools)
    # =========================================================================

    @mcp.tool()
    def list_chat_spaces(
        max_results: int = 100,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List Google Chat spaces the user is a member of.

        Args:
            max_results: Maximum number of spaces to return (default: 100).
            page_token: Token for pagination to get next page of results.
            filter_str: Optional filter (e.g., "spaceType = 'SPACE'").

        Returns:
            Dict containing:
                - spaces: List of space objects
                - next_page_token: Token for getting next page (if more results exist)
        """
        processor = get_chat_processor()
        return processor.list_spaces(
            page_size=max_results,
            page_token=page_token,
            filter_str=filter_str,
        )

    @mcp.tool()
    def get_chat_space(space_name: str) -> Dict[str, Any]:
        """
        Get details of a specific Google Chat space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").

        Returns:
            Dict containing space details including:
                - name, displayName, type, spaceType
                - threaded, externalUserAllowed
        """
        processor = get_chat_processor()
        return processor.get_space(space_name)

    @mcp.tool()
    def create_chat_space(
        display_name: str,
        space_type: str = "SPACE",
        external_user_allowed: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new Google Chat space.

        Args:
            display_name: Display name for the space.
            space_type: Type of space - "SPACE" or "GROUP_CHAT" (default: "SPACE").
            external_user_allowed: Whether external users can join (default: False).

        Returns:
            Dict containing the created space.
        """
        processor = get_chat_processor()
        return processor.create_space(
            display_name=display_name,
            space_type=space_type,
            external_user_allowed=external_user_allowed,
        )

    @mcp.tool()
    def update_chat_space(
        space_name: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a Google Chat space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").
            display_name: New display name for the space.

        Returns:
            Dict containing the updated space.
        """
        processor = get_chat_processor()
        return processor.update_space(
            space_name=space_name,
            display_name=display_name,
        )

    @mcp.tool()
    def delete_chat_space(space_name: str) -> Dict[str, Any]:
        """
        Delete a Google Chat space.

        Args:
            space_name: The resource name of the space to delete.

        Returns:
            Dict containing the result.
        """
        processor = get_chat_processor()
        return processor.delete_space(space_name)

    @mcp.tool()
    def find_direct_message(user_id: str) -> Dict[str, Any]:
        """
        Find an existing direct message space with a user.

        Args:
            user_id: The user identifier (email or user ID).

        Returns:
            Dict containing the DM space if found.
        """
        processor = get_chat_processor()
        # Format as users/email if it looks like an email
        if "@" in user_id:
            user_name = f"users/{user_id}"
        else:
            user_name = user_id if user_id.startswith("users/") else f"users/{user_id}"
        return processor.find_direct_message(user_name)

    @mcp.tool()
    def setup_chat_space(
        display_name: str,
        member_emails: List[str],
        space_type: str = "SPACE",
    ) -> Dict[str, Any]:
        """
        Create a space and add members in one operation.

        Args:
            display_name: Display name for the space.
            member_emails: List of email addresses to add as members.
            space_type: Type of space - "SPACE" or "GROUP_CHAT" (default: "SPACE").

        Returns:
            Dict containing the created space and membership results.
        """
        processor = get_chat_processor()
        return processor.setup_space(
            display_name=display_name,
            member_emails=member_emails,
            space_type=space_type,
        )

    @mcp.tool()
    def search_chat_spaces(
        query: str,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for spaces (admin feature).

        Note: Requires admin permissions.

        Args:
            query: Search query string.
            max_results: Maximum number of spaces to return (default: 10).
            page_token: Token for pagination.

        Returns:
            Dict containing matching spaces.
        """
        processor = get_chat_processor()
        return processor.search_spaces(
            query=query,
            page_size=max_results,
            page_token=page_token,
        )

    # =========================================================================
    # Message Operations (6 tools)
    # =========================================================================

    @mcp.tool()
    def list_chat_messages(
        space_name: str,
        max_results: int = 25,
        page_token: Optional[str] = None,
        filter_str: Optional[str] = None,
        order_by: Optional[str] = None,
        show_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List messages in a Google Chat space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").
            max_results: Maximum number of messages to return (default: 25).
            page_token: Token for pagination.
            filter_str: Optional filter for messages.
            order_by: Order by string (e.g., "createTime desc").
            show_deleted: Whether to include deleted messages (default: False).

        Returns:
            Dict containing:
                - messages: List of message objects
                - next_page_token: Token for next page (if exists)
        """
        processor = get_chat_processor()
        return processor.list_messages(
            space_name=space_name,
            page_size=max_results,
            page_token=page_token,
            filter_str=filter_str,
            order_by=order_by,
            show_deleted=show_deleted,
        )

    @mcp.tool()
    def get_chat_message(message_name: str) -> Dict[str, Any]:
        """
        Get a specific Google Chat message.

        Args:
            message_name: The resource name of the message
                          (e.g., "spaces/AAAAA/messages/BBBBB").

        Returns:
            Dict containing the message with sender, text, createTime, etc.
        """
        processor = get_chat_processor()
        return processor.get_message(message_name)

    @mcp.tool()
    def send_chat_message(
        space_name: str,
        text: str,
        thread_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a text message to a Google Chat space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").
            text: The message text to send.
            thread_key: Optional thread key to reply in a specific thread.

        Returns:
            Dict containing the sent message.
        """
        processor = get_chat_processor()
        return processor.send_message(
            space_name=space_name,
            text=text,
            thread_key=thread_key,
        )

    @mcp.tool()
    def update_chat_message(
        message_name: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Update (edit) an existing Google Chat message.

        Args:
            message_name: The resource name of the message to update.
            text: New message text.

        Returns:
            Dict containing the updated message.
        """
        processor = get_chat_processor()
        return processor.update_message(
            message_name=message_name,
            text=text,
        )

    @mcp.tool()
    def delete_chat_message(message_name: str) -> Dict[str, Any]:
        """
        Delete a Google Chat message.

        Args:
            message_name: The resource name of the message to delete.

        Returns:
            Dict containing the result.
        """
        processor = get_chat_processor()
        return processor.delete_message(message_name)

    @mcp.tool()
    def send_card_message(
        space_name: str,
        card_header: str,
        card_sections: List[Dict[str, Any]],
        fallback_text: Optional[str] = None,
        thread_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a rich card message to a Google Chat space.

        Args:
            space_name: The resource name of the space.
            card_header: Title/header for the card.
            card_sections: List of section definitions with widgets.
            fallback_text: Optional fallback text for notifications.
            thread_key: Optional thread key to reply in a thread.

        Returns:
            Dict containing the sent message.

        Example card_sections:
            [{"widgets": [{"textParagraph": {"text": "Hello"}}]}]
        """
        processor = get_chat_processor()

        cards = [{
            "cardId": "card1",
            "card": {
                "header": {"title": card_header},
                "sections": card_sections,
            }
        }]

        return processor.send_card_message(
            space_name=space_name,
            cards=cards,
            text=fallback_text,
            thread_key=thread_key,
        )

    # =========================================================================
    # Member Operations (5 tools)
    # =========================================================================

    @mcp.tool()
    def list_chat_members(
        space_name: str,
        max_results: int = 100,
        page_token: Optional[str] = None,
        show_groups: bool = False,
        show_invited: bool = False,
    ) -> Dict[str, Any]:
        """
        List members of a Google Chat space.

        Args:
            space_name: The resource name of the space (e.g., "spaces/AAAAA").
            max_results: Maximum number of members to return (default: 100).
            page_token: Token for pagination.
            show_groups: Whether to include group members (default: False).
            show_invited: Whether to include invited members (default: False).

        Returns:
            Dict containing:
                - members: List of membership objects
                - next_page_token: Token for next page (if exists)
        """
        processor = get_chat_processor()
        return processor.list_members(
            space_name=space_name,
            page_size=max_results,
            page_token=page_token,
            show_groups=show_groups,
            show_invited=show_invited,
        )

    @mcp.tool()
    def get_chat_member(member_name: str) -> Dict[str, Any]:
        """
        Get details of a specific space member.

        Args:
            member_name: The resource name of the membership
                         (e.g., "spaces/AAAAA/members/BBBBB").

        Returns:
            Dict containing member details including role, state, member info.
        """
        processor = get_chat_processor()
        return processor.get_member(member_name)

    @mcp.tool()
    def add_chat_member(
        space_name: str,
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Add a member to a Google Chat space.

        Args:
            space_name: The resource name of the space.
            user_email: Email address of the user to add.

        Returns:
            Dict containing the created membership.
        """
        processor = get_chat_processor()
        return processor.add_member(
            space_name=space_name,
            user_email=user_email,
        )

    @mcp.tool()
    def update_chat_member(
        member_name: str,
        role: str,
    ) -> Dict[str, Any]:
        """
        Update a member's role in a Google Chat space.

        Args:
            member_name: The resource name of the membership.
            role: New role - "ROLE_MEMBER" or "ROLE_MANAGER".

        Returns:
            Dict containing the updated membership.
        """
        processor = get_chat_processor()
        return processor.update_member(
            member_name=member_name,
            role=role,
        )

    @mcp.tool()
    def remove_chat_member(member_name: str) -> Dict[str, Any]:
        """
        Remove a member from a Google Chat space.

        Args:
            member_name: The resource name of the membership to remove.

        Returns:
            Dict containing the result.
        """
        processor = get_chat_processor()
        return processor.remove_member(member_name)

    # =========================================================================
    # Reaction Operations (3 tools)
    # =========================================================================

    @mcp.tool()
    def list_chat_reactions(
        message_name: str,
        max_results: int = 25,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List reactions on a Google Chat message.

        Args:
            message_name: The resource name of the message.
            max_results: Maximum number of reactions to return (default: 25).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - reactions: List of reaction objects
                - next_page_token: Token for next page (if exists)
        """
        processor = get_chat_processor()
        return processor.list_reactions(
            message_name=message_name,
            page_size=max_results,
            page_token=page_token,
        )

    @mcp.tool()
    def add_chat_reaction(
        message_name: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Add an emoji reaction to a Google Chat message.

        Args:
            message_name: The resource name of the message.
            emoji: Unicode emoji character (e.g., thumbs up, heart, etc.).

        Returns:
            Dict containing the created reaction.
        """
        processor = get_chat_processor()
        return processor.add_reaction(
            message_name=message_name,
            emoji_unicode=emoji,
        )

    @mcp.tool()
    def remove_chat_reaction(reaction_name: str) -> Dict[str, Any]:
        """
        Remove a reaction from a Google Chat message.

        Args:
            reaction_name: The resource name of the reaction to remove.

        Returns:
            Dict containing the result.
        """
        processor = get_chat_processor()
        return processor.remove_reaction(reaction_name)

    # =========================================================================
    # Attachment Operations (1 tool)
    # =========================================================================

    @mcp.tool()
    def get_chat_attachment(attachment_name: str) -> Dict[str, Any]:
        """
        Get metadata for a Google Chat attachment.

        Args:
            attachment_name: The resource name of the attachment.

        Returns:
            Dict containing attachment metadata including contentType, downloadUri.
        """
        processor = get_chat_processor()
        return processor.get_attachment(attachment_name)

    # =========================================================================
    # Utility Operations (1 tool)
    # =========================================================================

    @mcp.tool()
    def check_chat_auth() -> Dict[str, Any]:
        """
        Verify Google Chat API authentication.

        Tests the connection to the Chat API by attempting to list spaces.

        Returns:
            Dict containing:
                - authenticated: Boolean indicating if auth works
                - message: Status message
                - space_count: Number of spaces accessible (if authenticated)
        """
        processor = get_chat_processor()
        return processor.check_auth()

    logger.info("Chat MCP tools registered successfully (24 tools)")
