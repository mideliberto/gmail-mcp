"""
Tests for mcp/tools.py - Bulk operations and email reply tools

Tests for bulk archive/label/trash and email reply functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


def create_mock_gmail_service():
    """Create a mock Gmail API service for bulk ops and replies."""
    service = MagicMock()

    # Mock users().messages().list() for bulk operations
    service.users().messages().list().execute.return_value = {
        "messages": [
            {"id": "msg001"},
            {"id": "msg002"},
            {"id": "msg003"},
        ],
    }

    # Mock users().messages().modify() for bulk label/archive
    service.users().messages().modify().execute.return_value = {
        "id": "msg001",
        "labelIds": ["Label_1"],
    }

    # Mock users().messages().trash() for bulk trash
    service.users().messages().trash().execute.return_value = {
        "id": "msg001",
        "labelIds": ["TRASH"],
    }

    # Mock users().messages().get() for reply context
    service.users().messages().get().execute.return_value = {
        "id": "msg001",
        "threadId": "thread001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Re: Original Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Message-ID", "value": "<original@example.com>"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
            ],
            "body": {"data": "T3JpZ2luYWwgbWVzc2FnZQ=="},  # "Original message"
        },
        "snippet": "Original message snippet...",
    }

    # Mock users().threads().get() for thread context
    service.users().threads().get().execute.return_value = {
        "id": "thread001",
        "messages": [
            {
                "id": "msg001",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Original Subject"},
                        {"name": "From", "value": "sender@example.com"},
                    ],
                },
            },
        ],
    }

    # Mock users().drafts().create() for reply draft
    service.users().drafts().create().execute.return_value = {
        "id": "draft001",
        "message": {"id": "msg_draft001", "threadId": "thread001"},
    }

    # Mock users().drafts().send()
    service.users().drafts().send().execute.return_value = {
        "id": "sent001",
        "threadId": "thread001",
        "labelIds": ["SENT"],
    }

    # Mock users().getProfile() for sender info
    service.users().getProfile().execute.return_value = {
        "emailAddress": "user@example.com",
    }

    return service


class TestBulkArchive:
    """Tests for bulk_archive tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_bulk_archive_success(self, mock_build, mock_get_credentials):
        """Test successful bulk archive."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_archive = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_archive":
                bulk_archive = tool.fn
                break

        assert bulk_archive is not None

        result = bulk_archive(query="from:newsletter@example.com")

        assert "error" not in result
        assert result.get("success", False) or "archived" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_bulk_archive_not_authenticated(self, mock_get_credentials):
        """Test bulk_archive when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_archive = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_archive":
                bulk_archive = tool.fn
                break

        result = bulk_archive(query="from:test@example.com")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestBulkLabel:
    """Tests for bulk_label tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_bulk_label_success(self, mock_build, mock_get_credentials):
        """Test successful bulk labeling."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_label":
                bulk_label = tool.fn
                break

        assert bulk_label is not None

        result = bulk_label(query="from:work@example.com", label_id="Label_1")

        assert "error" not in result
        assert result.get("success", False) or "labeled" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_bulk_label_not_authenticated(self, mock_get_credentials):
        """Test bulk_label when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_label":
                bulk_label = tool.fn
                break

        result = bulk_label(query="test", label_id="Label_1")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestBulkTrash:
    """Tests for bulk_trash tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_bulk_trash_success(self, mock_build, mock_get_credentials):
        """Test successful bulk trash."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_trash = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_trash":
                bulk_trash = tool.fn
                break

        assert bulk_trash is not None

        result = bulk_trash(query="older_than:30d is:unread")

        assert "error" not in result
        assert result.get("success", False) or "trashed" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_bulk_trash_not_authenticated(self, mock_get_credentials):
        """Test bulk_trash when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        bulk_trash = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "bulk_trash":
                bulk_trash = tool.fn
                break

        result = bulk_trash(query="test")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestPrepareEmailReply:
    """Tests for prepare_email_reply tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_prepare_reply_success(self, mock_build, mock_get_credentials):
        """Test successful reply preparation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        prepare_email_reply = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "prepare_email_reply":
                prepare_email_reply = tool.fn
                break

        assert prepare_email_reply is not None

        result = prepare_email_reply(email_id="msg001")

        assert "error" not in result
        assert "original_email" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_prepare_reply_not_authenticated(self, mock_get_credentials):
        """Test prepare_email_reply when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        prepare_email_reply = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "prepare_email_reply":
                prepare_email_reply = tool.fn
                break

        result = prepare_email_reply(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestSendEmailReply:
    """Tests for send_email_reply tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_send_reply_creates_draft(self, mock_build, mock_get_credentials):
        """Test that send_email_reply creates a draft (requires confirmation)."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        send_email_reply = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "send_email_reply":
                send_email_reply = tool.fn
                break

        assert send_email_reply is not None

        result = send_email_reply(
            email_id="msg001",
            reply_text="Thank you for your message."
        )

        assert "error" not in result
        # Should create draft, not send directly
        assert "draft_id" in result
        assert result.get("confirmation_required", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_send_reply_not_authenticated(self, mock_get_credentials):
        """Test send_email_reply when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        send_email_reply = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "send_email_reply":
                send_email_reply = tool.fn
                break

        result = send_email_reply(
            email_id="msg001",
            reply_text="Reply text"
        )

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestConfirmSendEmail:
    """Tests for confirm_send_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_confirm_send_success(self, mock_build, mock_get_credentials):
        """Test successful email sending after confirmation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        confirm_send_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "confirm_send_email":
                confirm_send_email = tool.fn
                break

        assert confirm_send_email is not None

        result = confirm_send_email(draft_id="draft001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_confirm_send_not_authenticated(self, mock_get_credentials):
        """Test confirm_send_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        confirm_send_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "confirm_send_email":
                confirm_send_email = tool.fn
                break

        result = confirm_send_email(draft_id="draft001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestFindUnsubscribeLink:
    """Tests for find_unsubscribe_link tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_find_unsubscribe_success(self, mock_build, mock_get_credentials):
        """Test successful unsubscribe link finding."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        mock_service = create_mock_gmail_service()
        # Add List-Unsubscribe header
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Newsletter"},
                    {"name": "List-Unsubscribe", "value": "<https://example.com/unsubscribe>"},
                ],
            },
        }
        mock_build.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        find_unsubscribe_link = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "find_unsubscribe_link":
                find_unsubscribe_link = tool.fn
                break

        assert find_unsubscribe_link is not None

        result = find_unsubscribe_link(email_id="msg001")

        assert "error" not in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_find_unsubscribe_not_authenticated(self, mock_get_credentials):
        """Test find_unsubscribe_link when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        find_unsubscribe_link = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "find_unsubscribe_link":
                find_unsubscribe_link = tool.fn
                break

        result = find_unsubscribe_link(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]
