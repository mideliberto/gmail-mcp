"""
Tests for mcp/tools.py - Label and attachment tools

Tests for label management and attachment handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


def create_mock_gmail_service():
    """Create a mock Gmail API service for labels and attachments."""
    service = MagicMock()

    # Mock users().labels().list()
    service.users().labels().list().execute.return_value = {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
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

    # Mock users().messages().modify() for apply/remove label
    service.users().messages().modify().execute.return_value = {
        "id": "msg001",
        "labelIds": ["INBOX", "Label_1"],
    }

    # Mock users().messages().get() for attachments
    service.users().messages().get().execute.return_value = {
        "id": "msg001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Email with attachment"},
            ],
            "parts": [
                {
                    "partId": "0",
                    "mimeType": "text/plain",
                    "body": {"data": "VGV4dCBib2R5"},
                },
                {
                    "partId": "1",
                    "filename": "document.pdf",
                    "mimeType": "application/pdf",
                    "body": {
                        "attachmentId": "att001",
                        "size": 12345,
                    },
                },
                {
                    "partId": "2",
                    "filename": "image.png",
                    "mimeType": "image/png",
                    "body": {
                        "attachmentId": "att002",
                        "size": 67890,
                    },
                },
            ],
        },
    }

    # Mock users().messages().attachments().get()
    service.users().messages().attachments().get().execute.return_value = {
        "data": "SGVsbG8gV29ybGQ=",  # "Hello World" base64 encoded
        "size": 11,
    }

    return service


class TestListLabels:
    """Tests for list_labels tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_list_labels_success(self, mock_build, mock_get_credentials):
        """Test successful label listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_labels = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_labels":
                list_labels = tool.fn
                break

        assert list_labels is not None

        result = list_labels()

        assert "error" not in result
        assert "labels" in result
        assert len(result["labels"]) == 4

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_list_labels_not_authenticated(self, mock_get_credentials):
        """Test list_labels when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        list_labels = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "list_labels":
                list_labels = tool.fn
                break

        result = list_labels()

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestCreateLabel:
    """Tests for create_label tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_create_label_success(self, mock_build, mock_get_credentials):
        """Test successful label creation."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_label":
                create_label = tool.fn
                break

        assert create_label is not None

        result = create_label(name="New Label")

        assert "error" not in result

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_create_label_not_authenticated(self, mock_get_credentials):
        """Test create_label when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        create_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "create_label":
                create_label = tool.fn
                break

        result = create_label(name="Test Label")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestApplyLabel:
    """Tests for apply_label tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_apply_label_success(self, mock_build, mock_get_credentials):
        """Test successful label application."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        apply_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "apply_label":
                apply_label = tool.fn
                break

        assert apply_label is not None

        result = apply_label(email_id="msg001", label_id="Label_1")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_apply_label_not_authenticated(self, mock_get_credentials):
        """Test apply_label when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        apply_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "apply_label":
                apply_label = tool.fn
                break

        result = apply_label(email_id="msg001", label_id="Label_1")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestRemoveLabel:
    """Tests for remove_label tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_remove_label_success(self, mock_build, mock_get_credentials):
        """Test successful label removal."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        remove_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "remove_label":
                remove_label = tool.fn
                break

        assert remove_label is not None

        result = remove_label(email_id="msg001", label_id="Label_1")

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_remove_label_not_authenticated(self, mock_get_credentials):
        """Test remove_label when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        remove_label = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "remove_label":
                remove_label = tool.fn
                break

        result = remove_label(email_id="msg001", label_id="Label_1")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestGetAttachments:
    """Tests for get_attachments tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_get_attachments_success(self, mock_build, mock_get_credentials):
        """Test successful attachment listing."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_attachments = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_attachments":
                get_attachments = tool.fn
                break

        assert get_attachments is not None

        result = get_attachments(email_id="msg001")

        assert "error" not in result
        assert "attachments" in result
        assert len(result["attachments"]) == 2  # Two attachments in mock

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_get_attachments_not_authenticated(self, mock_get_credentials):
        """Test get_attachments when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        get_attachments = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "get_attachments":
                get_attachments = tool.fn
                break

        result = get_attachments(email_id="msg001")

        assert "error" in result
        assert "Not authenticated" in result["error"]


class TestDownloadAttachment:
    """Tests for download_attachment tool."""

    @patch("gmail_mcp.mcp.tools.get_credentials")
    @patch("gmail_mcp.mcp.tools.build")
    def test_download_attachment_success(self, mock_build, mock_get_credentials, tmp_path):
        """Test successful attachment download."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials
        mock_build.return_value = create_mock_gmail_service()

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        download_attachment = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "download_attachment":
                download_attachment = tool.fn
                break

        assert download_attachment is not None

        save_path = str(tmp_path / "downloaded_file.pdf")
        result = download_attachment(
            email_id="msg001",
            attachment_id="att001",
            save_path=save_path
        )

        assert "error" not in result
        assert result.get("success", False)

    @patch("gmail_mcp.mcp.tools.get_credentials")
    def test_download_attachment_not_authenticated(self, mock_get_credentials, tmp_path):
        """Test download_attachment when not authenticated."""
        from gmail_mcp.mcp.tools import setup_tools
        from mcp.server.fastmcp import FastMCP

        mock_get_credentials.return_value = None

        mcp = FastMCP(name="Test")
        setup_tools(mcp)

        download_attachment = None
        for tool in mcp._tool_manager._tools.values():
            if tool.name == "download_attachment":
                download_attachment = tool.fn
                break

        result = download_attachment(
            email_id="msg001",
            attachment_id="att001",
            save_path=str(tmp_path / "file.pdf")
        )

        assert "error" in result
        assert "Not authenticated" in result["error"]
