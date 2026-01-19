"""
Tests for gmail/helpers.py
"""

import pytest
from gmail_mcp.gmail.helpers import extract_email_info, extract_headers


class TestExtractHeaders:
    """Tests for extract_headers function."""

    def test_extract_headers_basic(self):
        """Test basic header extraction."""
        msg = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                ]
            }
        }
        headers = extract_headers(msg)

        assert headers["subject"] == "Test Subject"
        assert headers["from"] == "sender@example.com"
        assert headers["to"] == "recipient@example.com"

    def test_extract_headers_lowercase_keys(self):
        """Test that header names are lowercased."""
        msg = {
            "payload": {
                "headers": [
                    {"name": "X-Custom-Header", "value": "custom value"},
                    {"name": "CONTENT-TYPE", "value": "text/plain"},
                ]
            }
        }
        headers = extract_headers(msg)

        assert "x-custom-header" in headers
        assert "content-type" in headers
        assert headers["x-custom-header"] == "custom value"

    def test_extract_headers_empty(self):
        """Test extraction with no headers."""
        msg = {"payload": {"headers": []}}
        headers = extract_headers(msg)
        assert headers == {}

    def test_extract_headers_missing_payload(self):
        """Test extraction with missing payload."""
        msg = {}
        headers = extract_headers(msg)
        assert headers == {}


class TestExtractEmailInfo:
    """Tests for extract_email_info function."""

    def test_extract_email_info_full(self):
        """Test full email info extraction."""
        msg = {
            "id": "msg123",
            "threadId": "thread456",
            "snippet": "This is a preview...",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Meeting Tomorrow"},
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Cc", "value": "charlie@example.com"},
                    {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 -0800"},
                ]
            }
        }

        info = extract_email_info(msg)

        assert info["id"] == "msg123"
        assert info["thread_id"] == "thread456"
        assert info["subject"] == "Meeting Tomorrow"
        assert info["from"] == "alice@example.com"
        assert info["to"] == "bob@example.com"
        assert info["cc"] == "charlie@example.com"
        assert info["date"] == "Mon, 15 Jan 2024 10:00:00 -0800"
        assert info["snippet"] == "This is a preview..."
        assert info["labels"] == ["INBOX", "UNREAD"]
        assert info["email_link"] == "https://mail.google.com/mail/u/0/#inbox/thread456"

    def test_extract_email_info_missing_headers(self):
        """Test email info extraction with missing headers."""
        msg = {
            "id": "msg123",
            "threadId": "thread456",
            "snippet": "Preview text",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Only Subject"},
                ]
            }
        }

        info = extract_email_info(msg)

        assert info["id"] == "msg123"
        assert info["subject"] == "Only Subject"
        assert info["from"] == "Unknown"
        assert info["to"] == "Unknown"
        assert info["cc"] == ""
        assert info["date"] == "Unknown"

    def test_extract_email_info_no_subject(self):
        """Test email info extraction with no subject."""
        msg = {
            "id": "msg123",
            "threadId": "thread456",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                ]
            }
        }

        info = extract_email_info(msg)
        assert info["subject"] == "No Subject"

    def test_extract_email_info_no_labels(self):
        """Test email info extraction with no labels."""
        msg = {
            "id": "msg123",
            "threadId": "thread456",
            "payload": {"headers": []}
        }

        info = extract_email_info(msg)
        assert info["labels"] == []

    def test_extract_email_info_no_snippet(self):
        """Test email info extraction with no snippet."""
        msg = {
            "id": "msg123",
            "threadId": "thread456",
            "payload": {"headers": []}
        }

        info = extract_email_info(msg)
        assert info["snippet"] == ""

    def test_extract_email_info_link_format(self):
        """Test that email link is correctly formatted."""
        msg = {
            "id": "abc123xyz",
            "threadId": "thread789def",
            "payload": {"headers": []}
        }

        info = extract_email_info(msg)
        assert info["email_link"] == "https://mail.google.com/mail/u/0/#inbox/thread789def"
