"""
Gmail Helper Functions

This module provides helper functions for processing Gmail API responses.
"""

from typing import Dict, Any, List


def extract_email_info(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract common email info from a Gmail API message.

    This helper function extracts the most commonly needed fields from a Gmail
    message response, reducing code duplication across list_emails, search_emails,
    and get_email_overview.

    Args:
        msg: The Gmail API message object (from messages.get()).

    Returns:
        Dict containing:
            - id: Email ID
            - thread_id: Thread ID
            - subject: Email subject
            - from: Sender
            - to: Recipient(s)
            - cc: CC recipients
            - date: Email date
            - snippet: Short snippet of email content
            - labels: List of label IDs
            - email_link: Direct link to email in Gmail web interface
    """
    # Extract headers into a lookup dict
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

    email_id = msg["id"]
    thread_id = msg["threadId"]

    return {
        "id": email_id,
        "thread_id": thread_id,
        "subject": headers.get("subject", "No Subject"),
        "from": headers.get("from", "Unknown"),
        "to": headers.get("to", "Unknown"),
        "cc": headers.get("cc", ""),
        "date": headers.get("date", "Unknown"),
        "snippet": msg.get("snippet", ""),
        "labels": msg.get("labelIds", []),
        "email_link": f"https://mail.google.com/mail/u/0/#inbox/{thread_id}",
    }


def extract_headers(msg: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract headers from a Gmail message into a dictionary.

    Args:
        msg: The Gmail API message object.

    Returns:
        Dict mapping lowercase header names to their values.
    """
    return {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
