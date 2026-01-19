"""
Tests for mcp/tools.py - Gmail tools

These tests mock the Gmail API to verify tool functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# Sample Gmail API response data
SAMPLE_MESSAGE = {
    "id": "msg001",
    "threadId": "thread001",
    "snippet": "Hello, this is a test email...",
    "labelIds": ["INBOX", "UNREAD"],
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Test Email"},
            {"name": "From", "value": "sender@example.com"},
            {"name": "To", "value": "recipient@example.com"},
            {"name": "Cc", "value": "cc@example.com"},
            {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
        ],
        "body": {"data": "SGVsbG8gV29ybGQ="},  # "Hello World" base64 encoded
    }
}

SAMPLE_MESSAGE_2 = {
    "id": "msg002",
    "threadId": "thread002",
    "snippet": "Another test email...",
    "labelIds": ["INBOX"],
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Second Email"},
            {"name": "From", "value": "other@example.com"},
            {"name": "To", "value": "recipient@example.com"},
            {"name": "Date", "value": "Tue, 16 Jan 2024 11:00:00 -0800"},
        ],
        "body": {"data": "VGVzdCBib2R5"},
    }
}

SAMPLE_PROFILE = {
    "emailAddress": "user@example.com",
    "messagesTotal": 1000,
    "threadsTotal": 500,
    "historyId": "12345",
}

SAMPLE_LABELS = {
    "labels": [
        {"id": "INBOX", "name": "INBOX", "type": "system"},
        {"id": "SENT", "name": "SENT", "type": "system"},
        {"id": "UNREAD", "name": "UNREAD", "type": "system"},
        {"id": "DRAFT", "name": "DRAFT", "type": "system"},
        {"id": "SPAM", "name": "SPAM", "type": "system"},
        {"id": "TRASH", "name": "TRASH", "type": "system"},
    ]
}

SAMPLE_LABEL_DETAIL = {
    "messagesTotal": 50,
    "messagesUnread": 10,
}


def create_mock_gmail_service():
    """Create a mock Gmail API service."""
    service = MagicMock()

    # Mock users().messages().list()
    service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg001"}, {"id": "msg002"}],
        "nextPageToken": "token123",
    }

    # Mock users().messages().get()
    def mock_get_message(userId, id, format=None):
        mock = MagicMock()
        if id == "msg001":
            mock.execute.return_value = SAMPLE_MESSAGE
        elif id == "msg002":
            mock.execute.return_value = SAMPLE_MESSAGE_2
        else:
            mock.execute.return_value = SAMPLE_MESSAGE
        return mock

    service.users().messages().get = mock_get_message

    # Mock users().getProfile()
    service.users().getProfile().execute.return_value = SAMPLE_PROFILE

    # Mock users().labels().list()
    service.users().labels().list().execute.return_value = SAMPLE_LABELS

    # Mock users().labels().get()
    service.users().labels().get().execute.return_value = SAMPLE_LABEL_DETAIL

    return service


class TestListEmails:
    """Tests for list_emails tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_list_emails_success(self, mock_build, mock_get_credentials):
        """Test successful email listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        # Setup mocks
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        # Create MCP and setup tools
        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        # Get the list_emails tool
        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        assert list_emails is not None, "list_emails tool not found"

        # Call the tool
        result = list_emails(max_results=10, label="INBOX")

        # Verify result
        assert "error" not in result
        assert "emails" in result
        assert len(result["emails"]) == 2
        assert result["next_page_token"] == "token123"

        # Verify email structure
        email = result["emails"][0]
        assert email["id"] == "msg001"
        assert email["thread_id"] == "thread001"
        assert email["subject"] == "Test Email"
        assert email["from"] == "sender@example.com"
        assert "email_link" in email

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_list_emails_not_authenticated(self, mock_get_credentials):
        """Test list_emails when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        result = list_emails(max_results=10, label="INBOX")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestSearchEmails:
    """Tests for search_emails tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_search_emails_success(self, mock_build, mock_get_credentials):
        """Test successful email search."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        assert search_emails is not None

        result = search_emails(query="from:sender@example.com", max_results=10)

        assert "error" not in result
        assert "emails" in result
        assert "query" in result
        assert result["query"] == "from:sender@example.com"
        assert len(result["emails"]) == 2

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_search_emails_not_authenticated(self, mock_get_credentials):
        """Test search_emails when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        result = search_emails(query="test", max_results=10)

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetEmail:
    """Tests for get_email tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_get_email_success(self, mock_build, mock_get_credentials):
        """Test successful email retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email":
                get_email = tool.fn
                break

        assert get_email is not None

        result = get_email(email_id="msg001")

        assert "error" not in result
        assert result["id"] == "msg001"
        assert result["thread_id"] == "thread001"
        assert result["subject"] == "Test Email"
        assert result["from"] == "sender@example.com"
        assert "email_link" in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_get_email_not_authenticated(self, mock_get_credentials):
        """Test get_email when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email":
                get_email = tool.fn
                break

        result = get_email(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetEmailOverview:
    """Tests for get_email_overview tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_get_email_overview_success(self, mock_build, mock_get_credentials):
        """Test successful email overview retrieval."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_service = create_mock_gmail_service()
        mock_build.return_value = mock_service

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email_overview = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email_overview":
                get_email_overview = tool.fn
                break

        assert get_email_overview is not None

        result = get_email_overview()

        assert "error" not in result
        assert "account" in result
        assert "counts" in result
        assert "recent_emails" in result

        # Verify account info
        assert result["account"]["email"] == "user@example.com"
        assert result["account"]["total_messages"] == 1000

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_get_email_overview_not_authenticated(self, mock_get_credentials):
        """Test get_email_overview when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_email_overview = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_email_overview":
                get_email_overview = tool.fn
                break

        result = get_email_overview()

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestExtractEmailInfoIntegration:
    """Integration tests verifying extract_email_info is used correctly."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_list_emails_uses_helper(self, mock_build, mock_get_credentials):
        """Verify list_emails uses extract_email_info helper."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_emails":
                list_emails = tool.fn
                break

        result = list_emails(max_results=10, label="INBOX")

        # Verify the email structure matches extract_email_info output
        email = result["emails"][0]
        expected_keys = ["id", "thread_id", "subject", "from", "to", "cc", "date", "snippet", "labels", "email_link"]
        for key in expected_keys:
            assert key in email, f"Missing key: {key}"

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_search_emails_uses_helper(self, mock_build, mock_get_credentials):
        """Verify search_emails uses extract_email_info helper."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        search_emails = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "search_emails":
                search_emails = tool.fn
                break

        result = search_emails(query="test", max_results=10)

        # Verify the email structure matches extract_email_info output
        email = result["emails"][0]
        expected_keys = ["id", "thread_id", "subject", "from", "to", "cc", "date", "snippet", "labels", "email_link"]
        for key in expected_keys:
            assert key in email, f"Missing key: {key}"
