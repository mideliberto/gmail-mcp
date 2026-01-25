"""
Tests for Chat MCP processor.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestChatProcessorSpaceOperations:
    """Tests for space operations."""

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_list_spaces_success(self, mock_creds, mock_build):
        """Test listing spaces."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().list().execute.return_value = {
            "spaces": [
                {"name": "spaces/AAA", "displayName": "Test Space", "type": "ROOM"},
                {"name": "spaces/BBB", "displayName": "Another Space", "type": "ROOM"},
            ],
            "nextPageToken": None,
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.list_spaces()

        assert "spaces" in result
        assert len(result["spaces"]) == 2

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_get_space_success(self, mock_creds, mock_build):
        """Test getting space details."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().get().execute.return_value = {
            "name": "spaces/AAA",
            "displayName": "Test Space",
            "type": "ROOM",
            "spaceType": "SPACE",
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.get_space("spaces/AAA")

        assert result["name"] == "spaces/AAA"
        assert result["displayName"] == "Test Space"

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_create_space_success(self, mock_creds, mock_build):
        """Test creating a space."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().create().execute.return_value = {
            "name": "spaces/CCC",
            "displayName": "New Space",
            "spaceType": "SPACE",
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.create_space("New Space")

        assert result["displayName"] == "New Space"

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_delete_space_success(self, mock_creds, mock_build):
        """Test deleting a space."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().delete().execute.return_value = {}

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.delete_space("spaces/AAA")

        assert result["success"] is True


class TestChatProcessorMessageOperations:
    """Tests for message operations."""

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_list_messages_success(self, mock_creds, mock_build):
        """Test listing messages."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().list().execute.return_value = {
            "messages": [
                {"name": "spaces/AAA/messages/111", "text": "Hello"},
                {"name": "spaces/AAA/messages/222", "text": "World"},
            ],
            "nextPageToken": None,
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.list_messages("spaces/AAA")

        assert "messages" in result
        assert len(result["messages"]) == 2

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_send_message_success(self, mock_creds, mock_build):
        """Test sending a message."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().create().execute.return_value = {
            "name": "spaces/AAA/messages/333",
            "text": "Test message",
            "createTime": "2026-01-24T10:00:00Z",
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.send_message("spaces/AAA", "Test message")

        assert result["text"] == "Test message"

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_get_message_success(self, mock_creds, mock_build):
        """Test getting a message."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().get().execute.return_value = {
            "name": "spaces/AAA/messages/111",
            "text": "Hello",
            "createTime": "2026-01-24T10:00:00Z",
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.get_message("spaces/AAA/messages/111")

        assert result["text"] == "Hello"

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_delete_message_success(self, mock_creds, mock_build):
        """Test deleting a message."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().delete().execute.return_value = {}

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.delete_message("spaces/AAA/messages/111")

        assert result["success"] is True


class TestChatProcessorMemberOperations:
    """Tests for member operations."""

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_list_members_success(self, mock_creds, mock_build):
        """Test listing members."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().members().list().execute.return_value = {
            "memberships": [
                {"name": "spaces/AAA/members/111", "role": "ROLE_MEMBER"},
                {"name": "spaces/AAA/members/222", "role": "ROLE_MANAGER"},
            ],
            "nextPageToken": None,
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.list_members("spaces/AAA")

        assert "members" in result
        assert len(result["members"]) == 2

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_add_member_success(self, mock_creds, mock_build):
        """Test adding a member."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().members().create().execute.return_value = {
            "name": "spaces/AAA/members/333",
            "role": "ROLE_MEMBER",
            "state": "JOINED",
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.add_member("spaces/AAA", "user@example.com")

        assert result["role"] == "ROLE_MEMBER"

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_remove_member_success(self, mock_creds, mock_build):
        """Test removing a member."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().members().delete().execute.return_value = {}

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.remove_member("spaces/AAA/members/111")

        assert result["success"] is True


class TestChatProcessorReactionOperations:
    """Tests for reaction operations."""

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_list_reactions_success(self, mock_creds, mock_build):
        """Test listing reactions."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().reactions().list().execute.return_value = {
            "reactions": [
                {"name": "spaces/AAA/messages/111/reactions/R1", "emoji": {"unicode": "👍"}},
            ],
            "nextPageToken": None,
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.list_reactions("spaces/AAA/messages/111")

        assert "reactions" in result
        assert len(result["reactions"]) == 1

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_add_reaction_success(self, mock_creds, mock_build):
        """Test adding a reaction."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().messages().reactions().create().execute.return_value = {
            "name": "spaces/AAA/messages/111/reactions/R2",
            "emoji": {"unicode": "❤️"},
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.add_reaction("spaces/AAA/messages/111", "❤️")

        assert "emoji" in result


class TestChatProcessorAuth:
    """Tests for authentication operations."""

    @patch("chat_mcp.chat.processor.build")
    @patch("chat_mcp.chat.processor.get_credentials")
    def test_check_auth_success(self, mock_creds, mock_build):
        """Test checking authentication."""
        mock_creds.return_value = Mock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.spaces().list().execute.return_value = {
            "spaces": [{"name": "spaces/AAA"}],
        }

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.check_auth()

        assert result["authenticated"] is True

    @patch("chat_mcp.chat.processor.get_credentials")
    def test_check_auth_no_credentials(self, mock_creds):
        """Test check_auth when not authenticated."""
        mock_creds.return_value = None

        from chat_mcp.chat.processor import ChatProcessor
        processor = ChatProcessor()

        result = processor.check_auth()

        assert result["authenticated"] is False


class TestChatMcpTools:
    """Tests for chat-mcp tool registration."""

    def test_tools_registered(self):
        """Test that all tools are registered."""
        from chat_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())

        # Verify expected tools exist
        expected_tools = [
            "list_chat_spaces",
            "get_chat_space",
            "create_chat_space",
            "send_chat_message",
            "list_chat_members",
            "add_chat_reaction",
            "check_chat_auth",
        ]

        for tool in expected_tools:
            assert tool in tools, f"Missing tool: {tool}"

    def test_tool_count(self):
        """Test that we have the expected number of tools."""
        from chat_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 25, f"Expected 25 tools, got {len(tools)}"
