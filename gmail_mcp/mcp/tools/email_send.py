"""
Email Send Tools Module

Handles composing, replying, forwarding, and sending emails.
"""

import base64
from typing import Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.gmail.processor import parse_email_message, extract_entities
from gmail_mcp.gmail.processor import (
    analyze_thread,
    get_sender_history,
    analyze_communication_patterns,
    find_related_emails
)

logger = get_logger(__name__)


def setup_email_send_tools(mcp: FastMCP) -> None:
    """Set up email send tools on the FastMCP application."""

    @mcp.tool()
    def prepare_email_reply(email_id: str) -> Dict[str, Any]:
        """
        Prepare a context-rich reply to an email.

        This tool gathers comprehensive context for replying to an email,
        including the original email, thread history, sender information,
        communication patterns, and related emails.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - You need an email ID, which can be obtained from list_emails() or search_emails()

        Args:
            email_id (str): The ID of the email to reply to.

        Returns:
            Dict[str, Any]: Comprehensive context for generating a reply, including:
                - original_email: The email being replied to
                - thread_context: Information about the thread
                - sender_context: Information about the sender
                - communication_patterns: Analysis of communication patterns
                - entities: Entities extracted from the email
                - related_emails: Related emails for context

        Example usage:
        1. First check authentication: access auth://status resource
        2. Get a list of emails: list_emails()
        3. Extract an email ID from the results
        4. Prepare a reply: prepare_email_reply(email_id="...")
        5. Use the returned context to craft a personalized reply
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)
            profile = service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")

            entities = extract_entities(content.plain_text)

            thread_context = None
            if metadata.thread_id:
                thread = analyze_thread(metadata.thread_id)
                if thread:
                    thread_context = {
                        "id": thread.id,
                        "subject": thread.subject,
                        "message_count": thread.message_count,
                        "participants": thread.participants,
                        "last_message_date": thread.last_message_date.isoformat()
                    }

            sender_context = None
            if metadata.from_email:
                sender = get_sender_history(metadata.from_email)
                if sender:
                    sender_context = {
                        "email": sender.email,
                        "name": sender.name,
                        "message_count": sender.message_count,
                        "first_message_date": sender.first_message_date.isoformat() if sender.first_message_date else None,
                        "last_message_date": sender.last_message_date.isoformat() if sender.last_message_date else None,
                        "common_topics": sender.common_topics
                    }

            communication_patterns = None
            if metadata.from_email:
                patterns = analyze_communication_patterns(metadata.from_email, user_email)
                if patterns and "error" not in patterns:
                    communication_patterns = patterns

            related_emails = find_related_emails(email_id, max_results=5)

            original_email = {
                "id": metadata.id,
                "thread_id": metadata.thread_id,
                "subject": metadata.subject,
                "from": {
                    "email": metadata.from_email,
                    "name": metadata.from_name
                },
                "to": metadata.to,
                "cc": metadata.cc,
                "date": metadata.date.isoformat(),
                "body": content.plain_text,
                "has_attachments": metadata.has_attachments,
                "labels": metadata.labels
            }

            return {
                "original_email": original_email,
                "thread_context": thread_context,
                "sender_context": sender_context,
                "communication_patterns": communication_patterns,
                "entities": entities,
                "related_emails": related_emails,
                "user_email": user_email
            }

        except Exception as e:
            logger.error(f"Failed to prepare email reply: {e}")
            return {"success": False, "error": f"Failed to prepare email reply: {e}"}

    @mcp.tool()
    def send_email_reply(email_id: str, reply_text: str, include_original: bool = True) -> Dict[str, Any]:
        """
        Create a draft reply to an email.

        This tool creates a draft reply to the specified email with the provided text.
        The draft is saved but NOT sent automatically - user confirmation is required.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - You need an email ID, which can be obtained from list_emails() or search_emails()
        - You should use prepare_email_reply() first to get context for crafting a personalized reply

        Args:
            email_id (str): The ID of the email to reply to.
            reply_text (str): The text of the reply.
            include_original (bool, optional): Whether to include the original email in the reply. Defaults to True.

        Returns:
            Dict[str, Any]: The result of the operation, including:
                - success: Whether the operation was successful
                - message: A message describing the result
                - draft_id: The ID of the created draft
                - confirmation_required: Always True to indicate user confirmation is needed

        Example usage:
        1. First check authentication: access auth://status resource
        2. Get a list of emails: list_emails()
        3. Extract an email ID from the results
        4. Prepare a reply: prepare_email_reply(email_id="...")
        5. Create a draft reply: send_email_reply(email_id="...", reply_text="...")
        6. IMPORTANT: Always ask for user confirmation before sending
        7. After user confirms, use confirm_send_email(draft_id='...')

        IMPORTANT: You must ALWAYS ask for user confirmation before sending any email.
        Never assume the email should be sent automatically.
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)

            headers = {}
            for header in message["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            reply_headers = {
                "In-Reply-To": headers.get("message-id", ""),
                "References": headers.get("message-id", ""),
                "Subject": f"Re: {metadata.subject}" if not metadata.subject.startswith("Re:") else metadata.subject
            }

            reply_body = reply_text

            if include_original:
                reply_body += f"\n\nOn {metadata.date.strftime('%a, %d %b %Y %H:%M:%S')}, {metadata.from_name} <{metadata.from_email}> wrote:\n"
                for line in content.plain_text.split("\n"):
                    reply_body += f"> {line}\n"

            msg = MIMEMultipart()
            msg["to"] = metadata.from_email
            msg["subject"] = reply_headers["Subject"]
            msg["In-Reply-To"] = reply_headers["In-Reply-To"]
            msg["References"] = reply_headers["References"]

            if metadata.cc:
                msg["cc"] = ", ".join(metadata.cc)

            msg.attach(MIMEText(reply_body, "plain"))

            encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            body = {
                "raw": encoded_message,
                "threadId": metadata.thread_id
            }

            draft = service.users().drafts().create(userId="me", body={"message": body}).execute()

            email_link = f"https://mail.google.com/mail/u/0/#inbox/{metadata.thread_id}"

            return {
                "success": True,
                "message": "Draft reply created successfully. Please confirm to send.",
                "draft_id": draft["id"],
                "thread_id": metadata.thread_id,
                "email_link": email_link,
                "confirmation_required": True,
                "next_steps": [
                    "Review the draft reply",
                    f"If satisfied, call confirm_send_email(draft_id='{draft['id']}')",
                    "If changes are needed, create a new draft"
                ]
            }

        except Exception as e:
            logger.error(f"Failed to create draft reply: {e}")
            return {
                "success": False,
                "error": f"Failed to create draft reply: {e}"
            }

    @mcp.tool()
    def confirm_send_email(draft_id: str) -> Dict[str, Any]:
        """
        Send a draft email after user confirmation.

        This tool sends a previously created draft email. It should ONLY be used
        after explicit user confirmation to send the email.

        Prerequisites:
        - The user must be authenticated
        - You need a draft_id from send_email_reply()
        - You MUST have explicit user confirmation to send the email

        Args:
            draft_id (str): The ID of the draft to send.

        Returns:
            Dict[str, Any]: The result of the operation, including:
                - success: Whether the operation was successful
                - message: A message describing the result
                - email_id: The ID of the sent email (if successful)

        Example usage:
        1. Create a draft: send_email_reply(email_id="...", reply_text="...")
        2. Ask for user confirmation: "Would you like me to send this email?"
        3. ONLY after user confirms: confirm_send_email(draft_id="...")

        IMPORTANT: Never call this function without explicit user confirmation.
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            sent_message = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()

            return {
                "success": True,
                "message": "Email sent successfully.",
                "email_id": sent_message.get("id", ""),
                "thread_id": sent_message.get("threadId", "")
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": f"Failed to send email: {e}"
            }

    @mcp.tool()
    def compose_email(to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Compose and send a new email (not a reply).

        This tool creates a draft email and requires user confirmation before sending.

        Args:
            to (str): Recipient email address(es), comma-separated for multiple
            subject (str): Email subject line
            body (str): Email body text
            cc (str, optional): CC recipients, comma-separated
            bcc (str, optional): BCC recipients, comma-separated

        Returns:
            Dict[str, Any]: Result including draft_id for confirmation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject

            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc

            message.attach(MIMEText(body, "plain"))

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            draft = service.users().drafts().create(
                userId="me",
                body={"message": {"raw": encoded_message}}
            ).execute()

            return {
                "success": True,
                "message": "Draft created. Call confirm_send_email to send.",
                "draft_id": draft["id"],
                "to": to,
                "subject": subject,
                "confirmation_required": True
            }

        except Exception as e:
            logger.error(f"Failed to compose email: {e}")
            return {"success": False, "error": f"Failed to compose email: {e}"}

    @mcp.tool()
    def forward_email(email_id: str, to: str, additional_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Forward an existing email to another recipient.

        Args:
            email_id (str): The ID of the email to forward
            to (str): Recipient email address(es)
            additional_message (str, optional): Message to include above forwarded content

        Returns:
            Dict[str, Any]: Result including draft_id for confirmation
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            original = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            headers = {}
            for header in original["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            body = ""
            if "parts" in original["payload"]:
                for part in original["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
            elif "body" in original["payload"] and "data" in original["payload"]["body"]:
                body = base64.urlsafe_b64decode(original["payload"]["body"]["data"]).decode("utf-8")

            fwd_body = ""
            if additional_message:
                fwd_body = additional_message + "\n\n"

            fwd_body += "---------- Forwarded message ----------\n"
            fwd_body += f"From: {headers.get('from', 'Unknown')}\n"
            fwd_body += f"Date: {headers.get('date', 'Unknown')}\n"
            fwd_body += f"Subject: {headers.get('subject', 'No Subject')}\n"
            fwd_body += f"To: {headers.get('to', 'Unknown')}\n\n"
            fwd_body += body

            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = f"Fwd: {headers.get('subject', 'No Subject')}"
            message.attach(MIMEText(fwd_body, "plain"))

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            draft = service.users().drafts().create(
                userId="me",
                body={"message": {"raw": encoded_message}}
            ).execute()

            return {
                "success": True,
                "message": "Forward draft created. Call confirm_send_email to send.",
                "draft_id": draft["id"],
                "to": to,
                "original_subject": headers.get('subject', 'No Subject'),
                "confirmation_required": True
            }

        except Exception as e:
            logger.error(f"Failed to forward email: {e}")
            return {"success": False, "error": f"Failed to forward email: {e}"}
