"""
Tests for mcp/tools.py - Email management tools

Tests for compose, forward, archive, trash, delete, mark read/unread, star/unstar.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


def create_mock_gmail_service():
    """Create a mock Gmail API service for email management."""
    service = MagicMock()

    # Mock users().messages().modify() for archive, labels, read/unread, star
    service.users().messages().modify().execute.return_value = {
        "id": "msg001",
        "labelIds": ["INBOX"],
    }

    # Mock users().messages().trash()
    service.users().messages().trash().execute.return_value = {
        "id": "msg001",
        "labelIds": ["TRASH"],
    }

    # Mock users().messages().delete()
    service.users().messages().delete().execute.return_value = None

    # Mock users().messages().get() for forwarding
    service.users().messages().get().execute.return_value = {
        "id": "msg001",
        "threadId": "thread001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Original Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
            ],
            "body": {"data": "T3JpZ2luYWwgYm9keQ=="},  # "Original body"
        }
    }

    # Mock users().drafts().create()
    service.users().drafts().create().execute.return_value = {
        "id": "draft001",
        "message": {"id": "msg_draft001"},
    }

    # Mock users().drafts().send()
    service.users().drafts().send().execute.return_value = {
        "id": "sent001",
        "labelIds": ["SENT"],
    }

    # Mock users().labels().list()
    service.users().labels().list().execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "Label_1", "name": "Work", "type": "user"},
            {"id": "Label_2", "name": "Personal", "type": "user"},
        ]
    }

    # Mock users().labels().create()
    service.users().labels().create().execute.return_value = {
        "id": "Label_new",
        "name": "New Label",
        "type": "user",
    }

    return service


class TestComposeEmail:
    """Tests for compose_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_compose_email_success(self, mock_build, mock_get_credentials):
        """Test successful email composition."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        assert compose_email is not None

        result = compose_email(
            to="recipient@example.com",
            subject="Test Subject",
            body="Test body content"
        )

        assert "error" not in result
        assert "draft_id" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_compose_email_not_authenticated(self, mock_get_credentials):
        """Test compose_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        compose_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "compose_email":
                compose_email = tool.fn
                break

        result = compose_email(
            to="recipient@example.com",
            subject="Test",
            body="Body"
        )

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestForwardEmail:
    """Tests for forward_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_forward_email_success(self, mock_build, mock_get_credentials):
        """Test successful email forwarding."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        forward_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "forward_email":
                forward_email = tool.fn
                break

        assert forward_email is not None

        result = forward_email(
            email_id="msg001",
            to="forward@example.com"
        )

        assert "error" not in result
        assert "draft_id" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_forward_email_not_authenticated(self, mock_get_credentials):
        """Test forward_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        forward_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "forward_email":
                forward_email = tool.fn
                break

        result = forward_email(email_id="msg001", to="forward@example.com")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestArchiveEmail:
    """Tests for archive_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_archive_email_success(self, mock_build, mock_get_credentials):
        """Test successful email archiving."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        archive_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "archive_email":
                archive_email = tool.fn
                break

        assert archive_email is not None

        result = archive_email(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_archive_email_not_authenticated(self, mock_get_credentials):
        """Test archive_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        archive_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "archive_email":
                archive_email = tool.fn
                break

        result = archive_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestTrashEmail:
    """Tests for trash_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_trash_email_success(self, mock_build, mock_get_credentials):
        """Test successful email trashing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        trash_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "trash_email":
                trash_email = tool.fn
                break

        assert trash_email is not None

        result = trash_email(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_trash_email_not_authenticated(self, mock_get_credentials):
        """Test trash_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        trash_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "trash_email":
                trash_email = tool.fn
                break

        result = trash_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestDeleteEmail:
    """Tests for delete_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_delete_email_success(self, mock_build, mock_get_credentials):
        """Test successful email deletion."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_email":
                delete_email = tool.fn
                break

        assert delete_email is not None

        result = delete_email(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_delete_email_not_authenticated(self, mock_get_credentials):
        """Test delete_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        delete_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "delete_email":
                delete_email = tool.fn
                break

        result = delete_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestMarkAsRead:
    """Tests for mark_as_read tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_mark_as_read_success(self, mock_build, mock_get_credentials):
        """Test successful marking as read."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        mark_as_read = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "mark_as_read":
                mark_as_read = tool.fn
                break

        assert mark_as_read is not None

        result = mark_as_read(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_mark_as_read_not_authenticated(self, mock_get_credentials):
        """Test mark_as_read when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        mark_as_read = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "mark_as_read":
                mark_as_read = tool.fn
                break

        result = mark_as_read(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestMarkAsUnread:
    """Tests for mark_as_unread tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_mark_as_unread_success(self, mock_build, mock_get_credentials):
        """Test successful marking as unread."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        mark_as_unread = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "mark_as_unread":
                mark_as_unread = tool.fn
                break

        assert mark_as_unread is not None

        result = mark_as_unread(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_mark_as_unread_not_authenticated(self, mock_get_credentials):
        """Test mark_as_unread when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        mark_as_unread = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "mark_as_unread":
                mark_as_unread = tool.fn
                break

        result = mark_as_unread(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestStarEmail:
    """Tests for star_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_star_email_success(self, mock_build, mock_get_credentials):
        """Test successful starring email."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        star_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "star_email":
                star_email = tool.fn
                break

        assert star_email is not None

        result = star_email(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_star_email_not_authenticated(self, mock_get_credentials):
        """Test star_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        star_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "star_email":
                star_email = tool.fn
                break

        result = star_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestUnstarEmail:
    """Tests for unstar_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_unstar_email_success(self, mock_build, mock_get_credentials):
        """Test successful unstarring email."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        unstar_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "unstar_email":
                unstar_email = tool.fn
                break

        assert unstar_email is not None

        result = unstar_email(email_id="msg001")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_unstar_email_not_authenticated(self, mock_get_credentials):
        """Test unstar_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        unstar_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "unstar_email":
                unstar_email = tool.fn
                break

        result = unstar_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]
