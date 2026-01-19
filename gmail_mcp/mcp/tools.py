"""
MCP Tools Module

This module defines all the tools available in the Gmail MCP server.
Tools are functions that Claude can call to perform actions.
"""

import os
import json
import logging
import base64
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta, timezone
import httpx
import dateutil.parser as parser

from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleRequest

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.token_manager import get_token_manager
from gmail_mcp.auth.oauth import get_credentials, login, process_auth_code, start_oauth_process
from gmail_mcp.gmail.processor import (
    parse_email_message,
    analyze_thread,
    get_sender_history,
    extract_entities,
    analyze_communication_patterns,
    find_related_emails
)
from gmail_mcp.gmail.helpers import extract_email_info

from gmail_mcp.calendar.processor import (
    get_user_timezone,
    create_calendar_event_object,
    get_color_id_from_name
)

# Get logger
logger = get_logger(__name__)

# Get token manager singleton
token_manager = get_token_manager()


def setup_tools(mcp: FastMCP) -> None:
    """
    Set up all MCP tools on the FastMCP application.
    
    Args:
        mcp (FastMCP): The FastMCP application.
    """
    # Authentication tools
    @mcp.tool()
    def login_tool() -> str:
        """
        Initiate the OAuth2 flow by providing a link to the Google authorization page.
        
        Returns:
            str: The authorization URL to redirect to.
        """
        return login()
    
    @mcp.tool()
    def authenticate() -> str:
        """
        Start the complete OAuth authentication process.
        
        This tool opens a browser window and starts a local server to handle the callback.
        
        Returns:
            str: A message indicating that the authentication process has started.
        """
        # Start the OAuth process in a separate thread
        import threading
        thread = threading.Thread(target=start_oauth_process)
        thread.daemon = True
        thread.start()
        
        return "Authentication process started. Please check your browser to complete the process."
    
    @mcp.tool()
    def process_auth_code_tool(code: str, state: str) -> str:
        """
        Process the OAuth2 authorization code and state.
        
        Args:
            code (str): The authorization code from Google.
            state (str): The state parameter from Google.
            
        Returns:
            str: A success or error message.
        """
        return process_auth_code(code, state)
    
    @mcp.tool()
    def logout() -> str:
        """
        Log out by revoking the access token and clearing the stored credentials.
        
        Returns:
            str: A success or error message.
        """
        # Get the credentials
        credentials = token_manager.get_token()
        
        if credentials:
            try:
                # Revoke the access token
                httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": credentials.token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
                
                # Clear the stored credentials
                token_manager.clear_token()
                
                return "Logged out successfully."
            except Exception as e:
                logger.error(f"Failed to revoke token: {e}")
                return f"Error: Failed to revoke token: {e}"
        else:
            return "No active session to log out from."
    
    @mcp.tool()
    def check_auth_status() -> Dict[str, Any]:
        """
        Check the current authentication status.
        
        This tool provides a direct way to check if the user is authenticated
        without having to access the auth://status resource.
        
        Returns:
            Dict[str, Any]: The authentication status.
        """
        # Get the credentials
        credentials = token_manager.get_token()
        
        if not credentials:
            return {
                "authenticated": False,
                "message": "Not authenticated. Use the authenticate tool to start the authentication process.",
                "next_steps": [
                    "Call authenticate() to start the authentication process"
                ]
            }
        
        # Check if the credentials are expired
        if credentials.expired:
            try:
                # Try to refresh the token
                credentials.refresh(GoogleRequest())
                token_manager.store_token(credentials)
                
                return {
                    "authenticated": True,
                    "message": "Authentication is valid. Token was refreshed.",
                    "status": "refreshed"
                }
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return {
                    "authenticated": False,
                    "message": f"Authentication expired and could not be refreshed: {e}",
                    "next_steps": [
                        "Call authenticate() to start a new authentication process"
                    ],
                    "status": "expired"
                }
        
        return {
            "authenticated": True,
            "message": "Authentication is valid.",
            "status": "valid"
        }
    
    # Gmail tools
    @mcp.tool()
    def get_email_count() -> Dict[str, Any]:
        """
        Get the count of emails in the user's inbox.
        
        This tool retrieves the total number of messages in the user's Gmail account
        and the number of messages in the inbox.
        
        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.
        
        Returns:
            Dict[str, Any]: The email count information including:
                - email: The user's email address
                - total_messages: Total number of messages in the account
                - inbox_messages: Number of messages in the inbox
                - next_page_token: Token for pagination (if applicable)
                
        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, call get_email_count()
        3. If not authenticated, guide user to authenticate first
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the profile information
            profile = service.users().getProfile(userId="me").execute()
            
            # Get the inbox messages
            result = service.users().messages().list(userId="me", labelIds=["INBOX"]).execute()
            
            return {
                "email": profile.get("emailAddress", "Unknown"),
                "total_messages": profile.get("messagesTotal", 0),
                "inbox_messages": len(result.get("messages", [])),
                "next_page_token": result.get("nextPageToken"),
            }
        except HttpError as error:
            logger.error(f"Failed to get email count: {error}")
            return {"error": f"Failed to get email count: {error}"}
    
    @mcp.tool()
    def list_emails(max_results: int = 10, label: str = "INBOX") -> Dict[str, Any]:
        """
        List emails from the user's mailbox.
        
        This tool retrieves a list of emails from the specified label in the user's
        Gmail account, with basic information about each email.
        
        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.
        
        Args:
            max_results (int, optional): Maximum number of emails to return. Defaults to 10.
            label (str, optional): The label to filter by. Defaults to "INBOX".
                Common labels: "INBOX", "SENT", "DRAFT", "TRASH", "SPAM", "STARRED"
            
        Returns:
            Dict[str, Any]: The list of emails including:
                - emails: List of email objects with basic information and links
                - next_page_token: Token for pagination (if applicable)
                
        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, call list_emails(max_results=5, label="INBOX")
        3. If not authenticated, guide user to authenticate first
        4. Always include the email_link when discussing specific emails with the user
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the messages
            result = service.users().messages().list(
                userId="me", 
                labelIds=[label], 
                maxResults=max_results
            ).execute()
            
            messages = result.get("messages", [])
            emails = []

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                emails.append(extract_email_info(msg))

            return {
                "emails": emails,
                "next_page_token": result.get("nextPageToken"),
            }
        except HttpError as error:
            logger.error(f"Failed to list emails: {error}")
            return {"error": f"Failed to list emails: {error}"}

    @mcp.tool()
    def get_email(email_id: str) -> Dict[str, Any]:
        """
        Get a specific email by ID.
        
        This tool retrieves the full details of a specific email, including
        the body content, headers, and other metadata.
        
        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - You need an email ID, which can be obtained from list_emails() or search_emails()
        
        Args:
            email_id (str): The ID of the email to retrieve. This ID comes from the
                            list_emails() or search_emails() results.
            
        Returns:
            Dict[str, Any]: The email details including:
                - id: Email ID
                - thread_id: Thread ID
                - subject: Email subject
                - from: Sender information
                - to: Recipient information
                - cc: CC recipients
                - date: Email date
                - body: Email body content
                - snippet: Short snippet of the email
                - labels: Email labels
                - email_link: Direct link to the email in Gmail web interface
                
        Example usage:
        1. First check authentication: access auth://status resource
        2. Get a list of emails: list_emails()
        3. Extract an email ID from the results
        4. Get the full email: get_email(email_id="...")
        5. Always include the email_link when discussing the email with the user
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the message
            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            
            # Extract headers
            headers = {}
            for header in msg["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]
            
            # Extract body
            body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = part["body"]["data"]
                        break
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = msg["payload"]["body"]["data"]
            
            # Decode body if needed (base64url encoded)
            if body:
                body = base64.urlsafe_b64decode(body.encode("ASCII")).decode("utf-8")
            
            # Generate a link to the email in Gmail web interface
            thread_id = msg["threadId"]
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{email_id}"
            
            return {
                "id": msg["id"],
                "thread_id": thread_id,
                "subject": headers.get("subject", "No Subject"),
                "from": headers.get("from", "Unknown"),
                "to": headers.get("to", "Unknown"),
                "cc": headers.get("cc", ""),
                "date": headers.get("date", "Unknown"),
                "body": body,
                "snippet": msg["snippet"],
                "labels": msg["labelIds"],
                "email_link": email_link
            }
        except HttpError as error:
            logger.error(f"Failed to get email: {error}")
            return {"error": f"Failed to get email: {error}"}
    
    @mcp.tool()
    def search_emails(query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for emails using Gmail's search syntax.
        
        This tool searches for emails matching the specified query using
        Gmail's powerful search syntax.
        
        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - If not authenticated, guide the user through the authentication process.
        
        Args:
            query (str): The search query using Gmail's search syntax.
                Examples:
                - "from:example@gmail.com" - Emails from a specific sender
                - "to:example@gmail.com" - Emails to a specific recipient
                - "subject:meeting" - Emails with "meeting" in the subject
                - "has:attachment" - Emails with attachments
                - "is:unread" - Unread emails
                - "after:2023/01/01" - Emails after January 1, 2023
            max_results (int, optional): Maximum number of emails to return. Defaults to 10.
            
        Returns:
            Dict[str, Any]: The search results including:
                - query: The search query used
                - emails: List of email objects matching the query with links
                - next_page_token: Token for pagination (if applicable)
                
        Example usage:
        1. First check authentication: access auth://status resource
        2. If authenticated, search for emails: search_emails(query="from:example@gmail.com")
        3. If not authenticated, guide user to authenticate first
        4. Always include the email_link when discussing specific emails with the user
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Search for messages
            result = service.users().messages().list(
                userId="me", 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = result.get("messages", [])
            emails = []

            for message in messages:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                emails.append(extract_email_info(msg))

            return {
                "query": query,
                "emails": emails,
                "next_page_token": result.get("nextPageToken"),
            }
        except HttpError as error:
            logger.error(f"Failed to search emails: {error}")
            return {"error": f"Failed to search emails: {error}"}

    @mcp.tool()
    def get_email_overview() -> Dict[str, Any]:
        """
        Get a simple overview of the user's emails.
        
        This tool provides a quick summary of the user's Gmail account,
        including counts and recent emails, all in one call.
        
        Returns:
            Dict[str, Any]: The email overview including:
                - account: Account information
                - counts: Email counts by label
                - recent_emails: List of recent emails with links
                - unread_count: Number of unread emails
                
        Note: Always include the email_link when discussing specific emails with the user.
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the profile information
            profile = service.users().getProfile(userId="me").execute()
            
            # Get the inbox messages
            inbox_result = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=5).execute()
            
            # Get unread messages
            unread_result = service.users().messages().list(userId="me", labelIds=["UNREAD"], maxResults=5).execute()
            
            # Get labels
            labels_result = service.users().labels().list(userId="me").execute()
            
            # Process recent emails
            recent_emails = []
            if "messages" in inbox_result:
                for message in inbox_result["messages"][:5]:  # Limit to 5 emails
                    msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                    recent_emails.append(extract_email_info(msg))

            # Count emails by label
            label_counts = {}
            for label in labels_result.get("labels", []):
                if label["type"] == "system":
                    label_detail = service.users().labels().get(userId="me", id=label["id"]).execute()
                    label_counts[label["name"]] = {
                        "total": label_detail.get("messagesTotal", 0),
                        "unread": label_detail.get("messagesUnread", 0)
                    }
            
            return {
                "account": {
                    "email": profile.get("emailAddress", "Unknown"),
                    "total_messages": profile.get("messagesTotal", 0),
                    "total_threads": profile.get("threadsTotal", 0),
                },
                "counts": {
                    "inbox": label_counts.get("INBOX", {}).get("total", 0),
                    "unread": label_counts.get("UNREAD", {}).get("total", 0),
                    "sent": label_counts.get("SENT", {}).get("total", 0),
                    "draft": label_counts.get("DRAFT", {}).get("total", 0),
                    "spam": label_counts.get("SPAM", {}).get("total", 0),
                    "trash": label_counts.get("TRASH", {}).get("total", 0),
                },
                "recent_emails": recent_emails,
                "unread_count": len(unread_result.get("messages", [])),
            }
        except Exception as e:
            logger.error(f"Failed to get email overview: {e}")
            return {"error": f"Failed to get email overview: {e}"}
    
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
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the original email
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)
            
            # Get the user's email
            profile = service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")
            
            # Extract entities from the email content
            entities = extract_entities(content.plain_text)
            
            # Get thread context
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
            
            # Get sender context
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
            
            # Analyze communication patterns
            communication_patterns = None
            if metadata.from_email:
                patterns = analyze_communication_patterns(metadata.from_email, user_email)
                if patterns and "error" not in patterns:
                    communication_patterns = patterns
            
            # Find related emails
            related_emails = find_related_emails(email_id, max_results=5)
            
            # Create original email object
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
            
            # Create reply context
            reply_context = {
                "original_email": original_email,
                "thread_context": thread_context,
                "sender_context": sender_context,
                "communication_patterns": communication_patterns,
                "entities": entities,
                "related_emails": related_emails,
                "user_email": user_email
            }
            
            return reply_context
        
        except Exception as e:
            logger.error(f"Failed to prepare email reply: {e}")
            return {"error": f"Failed to prepare email reply: {e}"}
    
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
        7. After user confirms, use confirm_send_email(draft_id='" + draft["id"] + "')
        
        IMPORTANT: You must ALWAYS ask for user confirmation before sending any email.
        Never assume the email should be sent automatically.
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the original email
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)
            
            # Extract headers
            headers = {}
            for header in message["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]
            
            # Create reply headers
            reply_headers = {
                "In-Reply-To": headers.get("message-id", ""),
                "References": headers.get("message-id", ""),
                "Subject": f"Re: {metadata.subject}" if not metadata.subject.startswith("Re:") else metadata.subject
            }
            
            # Create reply body
            reply_body = reply_text
            
            if include_original:
                reply_body += f"\n\nOn {metadata.date.strftime('%a, %d %b %Y %H:%M:%S')}, {metadata.from_name} <{metadata.from_email}> wrote:\n"
                
                # Add original email with > prefix
                for line in content.plain_text.split("\n"):
                    reply_body += f"> {line}\n"
            
            # Create message
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import base64
            
            message = MIMEMultipart()
            message["to"] = metadata.from_email
            message["subject"] = reply_headers["Subject"]
            message["In-Reply-To"] = reply_headers["In-Reply-To"]
            message["References"] = reply_headers["References"]
            
            # Add CC recipients if any
            if metadata.cc:
                message["cc"] = ", ".join(metadata.cc)
            
            # Add message body
            message.attach(MIMEText(reply_body, "plain"))
            
            # Encode message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create the draft message body
            body = {
                "raw": encoded_message,
                "threadId": metadata.thread_id
            }
            
            # Create the draft
            draft = service.users().drafts().create(userId="me", body={"message": body}).execute()
            
            # Generate a link to the email in Gmail web interface
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
                    "If satisfied, call confirm_send_email(draft_id='" + draft["id"] + "')",
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
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Send the draft
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
    
    # Calendar tools
    @mcp.tool()
    def create_calendar_event(summary: str, start_time: str, end_time: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None, attendees: Optional[List[str]] = None, color_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new event in the user's Google Calendar.
        
        This tool creates a new calendar event with the specified details.
        
        Prerequisites:
        - The user must be authenticated with Google Calendar access
        
        Args:
            summary (str): The title/summary of the event
            start_time (str): The start time of the event in ISO format (YYYY-MM-DDTHH:MM:SS) or simple date/time format ("5pm", "tomorrow 3pm")
            end_time (str, optional): The end time of the event. If not provided, you should ask the user for this information.
            description (str, optional): Description or notes for the event. If not provided, leave it blank.
            location (str, optional): Location of the event. If not provided, leave it blank.
            attendees (List[str], optional): List of email addresses of attendees. The current user will always be added automatically.
            color_name (str, optional): Color name for the event (e.g., "red", "blue", "green", "purple", "yellow", "orange")
            
        Returns:
            Dict[str, Any]: The result of the operation, including:
                - success: Whether the operation was successful
                - message: A message describing the result
                - event_id: The ID of the created event
                - event_link: Direct link to the event in Google Calendar
                - missing_info: List of missing information that should be asked from the user
                
        Example usage:
        1. Create a simple event:
           create_calendar_event(summary="Team Meeting", start_time="2023-12-01T14:00:00")
           
        2. Create a detailed event:
           create_calendar_event(
               summary="Project Kickoff",
               start_time="next monday at 10am",
               end_time="next monday at 11:30am",
               description="Initial meeting to discuss project scope",
               location="Conference Room A",
               attendees=["colleague@example.com", "manager@example.com"],
               color_id="2"
           )
        """
        # Check if the user is authenticated
        credentials = get_credentials()
        if not credentials:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first.",
                "missing_info": []
            }
        
        try:
            # Build the Calendar API service
            service = build("calendar", "v3", credentials=credentials)
            
            # Convert color name to color ID if needed
            if color_name:
                color_id = get_color_id_from_name(color_name)
            else:
                # Default to blue (1) if no color specified
                color_id = "1"
            
            # Use the calendar processor to create the event object with proper date/time handling
            event_body = create_calendar_event_object(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                color_id=color_id
            )
            
            # Check if there was an error parsing the dates
            if "error" in event_body:
                missing_info = []
                if not end_time:
                    missing_info.append("end_time")
                
                return {
                    "success": False,
                    "error": event_body["error"],
                    "parsed_start": event_body.get("parsed_start"),
                    "parsed_end": event_body.get("parsed_end"),
                    "current_datetime": event_body.get("current_datetime"),
                    "missing_info": missing_info
                }
            
            # Create the event
            created_event = service.events().insert(calendarId="primary", body=event_body).execute()
            
            # Get the event ID and link
            event_id = created_event.get("id", "")
            event_link = created_event.get("htmlLink", "")
            
            return {
                "success": True,
                "message": "Event created successfully.",
                "event_id": event_id,
                "event_link": event_link,
                "event_details": {
                    "summary": summary,
                    "start": event_body.get("start", {}),
                    "end": event_body.get("end", {}),
                    "timezone": event_body.get("_parsed", {}).get("timezone", "UTC"),
                    "all_day": event_body.get("_parsed", {}).get("all_day", False),
                    "current_datetime": event_body.get("_parsed", {}).get("current_datetime", "")
                },
                "missing_info": []
            }
        
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            missing_info = []
            if not end_time:
                missing_info.append("end_time")
            
            return {
                "success": False,
                "error": f"Failed to create calendar event: {e}",
                "missing_info": missing_info
            }
    
    @mcp.tool()
    def detect_events_from_email(email_id: str) -> Dict[str, Any]:
        """
        Detect potential calendar events from an email.
        
        This tool analyzes an email to identify potential calendar events
        based on dates, times, and contextual clues.
        
        Prerequisites:
        - The user must be authenticated
        - You need an email ID from list_emails() or search_emails()
        
        Args:
            email_id (str): The ID of the email to analyze for events
            
        Returns:
            Dict[str, Any]: The detected events including:
                - success: Whether the operation was successful
                - events: List of potential events with details
                - email_link: Link to the original email
                
        Example usage:
        1. Get an email: email = get_email(email_id="...")
        2. Detect events: events = detect_events_from_email(email_id="...")
        3. Ask the user if they want to add the events to their calendar
        4. Ask the user for any missing information (end time, location, description, attendees)
        5. If confirmed, create the events using create_calendar_event()
        
        Important:
        - Always ask for user confirmation before creating calendar events
        - Always ask for missing information like end time, location, description, and attendees
        - Never use default values without user input
        - Always include the event_link when discussing events with the user
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the email
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)
            
            # Extract entities from the email content
            entities = extract_entities(content.plain_text)
            
            # Generate a link to the email in Gmail web interface
            thread_id = message["threadId"]
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{email_id}"
            
            # Detect potential events
            potential_events = []
            
            # Look for date and time combinations
            dates = entities.get("dates", [])
            times = entities.get("times", [])
            
            # Extract potential event details from the email
            # First, try to find explicit event patterns
            event_patterns = [
                r'(?i)(?:meeting|call|conference|appointment|event|webinar|seminar|workshop|session|interview)\s+(?:on|at|for)\s+([^.,:;!?]+)',
                r'(?i)(?:schedule|scheduled|plan|planning|organize|organizing|host|hosting)\s+(?:a|an)\s+([^.,:;!?]+)',
                r'(?i)(?:invite|invitation|inviting)\s+(?:you|everyone|all)\s+(?:to|for)\s+([^.,:;!?]+)'
            ]

            event_titles = []
            for pattern in event_patterns:
                matches = re.findall(pattern, content.plain_text)
                event_titles.extend(matches)
            
            # Process dates and times
            parsed_datetimes = []
            
            # Try to parse complete datetime expressions first
            datetime_patterns = [
                r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:tomorrow|today|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b'
            ]
            
            for pattern in datetime_patterns:
                matches = re.findall(pattern, content.plain_text)
                for match in matches:
                    try:
                        dt = parser.parse(match)
                        parsed_datetimes.append(dt)
                    except (ValueError, TypeError):
                        pass
            
            # If no complete datetime expressions, try combining dates and times
            if not parsed_datetimes and dates and times:
                for date_str in dates:
                    for time_str in times:
                        try:
                            dt = parser.parse(f"{date_str} {time_str}")
                            parsed_datetimes.append(dt)
                        except (ValueError, TypeError):
                            pass
            
            # Extract attendees - look for email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            potential_attendees = list(set(re.findall(email_pattern, content.plain_text)))
            
            # Extract location - look for location indicators
            location_patterns = [
                r'(?i)(?:at|in|location|place|venue):\s*([^.,:;!?]+)',
                r'(?i)(?:at|in)\s+the\s+([^.,:;!?]+)',
                r'(?i)(?:meet|meeting)\s+(?:at|in)\s+([^.,:;!?]+)'
            ]
            
            potential_location = None
            for pattern in location_patterns:
                matches = re.findall(pattern, content.plain_text)
                if matches:
                    potential_location = matches[0].strip()
                    break
            
            # Create potential events
            for i, dt in enumerate(parsed_datetimes):
                # Default event duration is 1 hour
                end_dt = dt + timedelta(hours=1)
                
                # Try to find a title
                title = f"Event from email"
                if i < len(event_titles):
                    title = event_titles[i]
                elif metadata.subject:
                    title = f"Re: {metadata.subject}"
                
                # Add to potential events
                potential_events.append({
                    "summary": title,
                    "start_time": dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "description": f"Detected from email: {metadata.subject}",
                    "location": potential_location,
                    "attendees": potential_attendees,
                    "confidence": "medium",
                    "source_text": content.plain_text[:200] + "..." if len(content.plain_text) > 200 else content.plain_text
                })
            
            return {
                "success": True,
                "events": potential_events,
                "email_id": email_id,
                "email_link": email_link,
                "subject": metadata.subject,
                "from": {
                    "email": metadata.from_email,
                    "name": metadata.from_name
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to detect events from email: {e}")
            return {
                "success": False,
                "error": f"Failed to detect events from email: {e}"
            }
    
    @mcp.tool()
    def list_calendar_events(max_results: int = 10, time_min: Optional[str] = None, time_max: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
        """
        List events from the user's Google Calendar.
        
        This tool retrieves a list of upcoming events from the user's calendar.
        
        Prerequisites:
        - The user must be authenticated with Google Calendar access
        
        Args:
            max_results (int, optional): Maximum number of events to return. Defaults to 10.
            time_min (str, optional): Start time for the search in ISO format or natural language.
                                     Defaults to now.
            time_max (str, optional): End time for the search in ISO format or natural language.
                                     Defaults to unlimited.
            query (str, optional): Free text search terms to find events that match.
            
        Returns:
            Dict[str, Any]: The list of events including:
                - events: List of calendar events with details and links
                - next_page_token: Token for pagination (if applicable)
                
        Example usage:
        1. List upcoming events:
           list_calendar_events()
           
        2. List events for a specific time range:
           list_calendar_events(time_min="tomorrow", time_max="tomorrow at 11:59pm")
           
        3. Search for specific events:
           list_calendar_events(query="meeting")
           
        Important:
        - Always include the event_link when discussing specific events with the user
        - The event_link allows users to directly access their events in Google Calendar
        - When listing multiple events, include the event_link for each event
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Build the Calendar API service
            service = build("calendar", "v3", credentials=credentials)
            
            # Parse time parameters using dateutil.parser
            # Set default time_min to now if not provided
            if not time_min:
                time_min_dt = datetime.now(timezone.utc)
            else:
                try:
                    time_min_dt = parser.parse(time_min, fuzzy=True)
                    # If the parsed date is in the past and no explicit year was mentioned, assume next occurrence
                    if time_min_dt < datetime.now() and "year" not in time_min.lower():
                        # If it's a day of week reference, find next occurrence
                        if any(day in time_min.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                            # Find the next occurrence of this day
                            current_datetime = datetime.now()
                            days_ahead = (time_min_dt.weekday() - current_datetime.weekday()) % 7
                            if days_ahead == 0:  # Same day of week
                                days_ahead = 7  # Go to next week
                            time_min_dt = current_datetime + timedelta(days=days_ahead)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not parse start time: {time_min}",
                        "message": "Please provide a clearer date and time format for the start time."
                    }
            
            # Format time_min for API
            time_min_formatted = time_min_dt.isoformat() + 'Z'  # 'Z' indicates UTC time
            
            # Parse time_max if provided
            time_max_formatted = None
            if time_max:
                try:
                    time_max_dt = parser.parse(time_max, fuzzy=True)
                    # If the parsed date is in the past and no explicit year was mentioned, assume next occurrence
                    if time_max_dt < datetime.now() and "year" not in time_max.lower():
                        # If it's a day of week reference, find next occurrence
                        if any(day in time_max.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                            # Find the next occurrence of this day
                            current_datetime = datetime.now()
                            days_ahead = (time_max_dt.weekday() - current_datetime.weekday()) % 7
                            if days_ahead == 0:  # Same day of week
                                days_ahead = 7  # Go to next week
                            time_max_dt = current_datetime + timedelta(days=days_ahead)
                    # Format time_max for API
                    time_max_formatted = time_max_dt.isoformat() + 'Z'  # 'Z' indicates UTC time
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not parse end time: {time_max}",
                        "message": "Please provide a clearer date and time format for the end time."
                    }
            
            # Get user's timezone
            user_timezone = get_user_timezone()
            
            # Prepare parameters for the API call
            params = {
                'calendarId': 'primary',
                'timeMin': time_min_formatted,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
                'timeZone': user_timezone
            }
            
            # Add optional parameters if provided
            if time_max_formatted:
                params['timeMax'] = time_max_formatted
            
            if query:
                params['q'] = query
            
            # Get events
            events_result = service.events().list(**params).execute()
            events = events_result.get('items', [])
            
            # Process events
            processed_events = []
            for event in events:
                # Get start and end times
                start = event.get('start', {})
                end = event.get('end', {})
                
                # Determine if this is an all-day event
                is_all_day = 'date' in start and 'date' in end
                
                # Format start and end times for display
                if is_all_day:
                    start_display = start.get('date', '')
                    end_display = end.get('date', '')
                    time_display = "All day"
                else:
                    # Parse the datetime strings
                    try:
                        start_dt = parser.parse(start.get('dateTime', ''))
                        end_dt = parser.parse(end.get('dateTime', ''))
                        
                        # Format for display
                        start_display = start_dt.strftime("%Y-%m-%d %I:%M %p")
                        end_display = end_dt.strftime("%I:%M %p") if start_dt.date() == end_dt.date() else end_dt.strftime("%Y-%m-%d %I:%M %p")
                        time_display = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
                    except Exception:
                        start_display = start.get('dateTime', '')
                        end_display = end.get('dateTime', '')
                        time_display = "Unknown time"
                
                # Generate event link
                event_id = event['id']
                event_link = f"https://calendar.google.com/calendar/event?eid={event_id}"
                
                # Add to processed events
                processed_events.append({
                    "id": event_id,
                    "summary": event.get('summary', 'Untitled Event'),
                    "start": start,
                    "end": end,
                    "start_display": start_display,
                    "end_display": end_display,
                    "time_display": time_display,
                    "is_all_day": is_all_day,
                    "location": event.get('location', ''),
                    "description": event.get('description', ''),
                    "attendees": event.get('attendees', []),
                    "event_link": event_link
                })
            
            return {
                "success": True,
                "events": processed_events,
                "next_page_token": events_result.get('nextPageToken'),
                "timezone": user_timezone,
                "query_parameters": {
                    "time_min": time_min,
                    "time_max": time_max,
                    "query": query
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return {
                "success": False,
                "error": f"Failed to list calendar events: {e}"
            }
    
    @mcp.tool()
    def suggest_meeting_times(start_date: str, end_date: str, duration_minutes: int = 60, working_hours: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest available meeting times within a date range.
        
        This tool analyzes the user's calendar and suggests available time slots
        for scheduling meetings based on their existing calendar events.
        
        Prerequisites:
        - The user must be authenticated with Google Calendar access
        
        Args:
            start_date (str): The start date of the range to check (can be natural language like "tomorrow")
            end_date (str): The end date of the range to check (can be natural language like "next friday")
            duration_minutes (int, optional): The desired meeting duration in minutes. Defaults to 60.
            working_hours (str, optional): Working hours in format "9-17" (9am to 5pm). Defaults to 9am-5pm.
            
        Returns:
            Dict[str, Any]: The suggested meeting times including:
                - success: Whether the operation was successful
                - suggestions: List of suggested meeting times with formatted date/time
                - message: A message describing the result
                
        Example usage:
        1. Find meeting times for tomorrow:
           suggest_meeting_times(start_date="tomorrow", end_date="tomorrow")
           
        2. Find meeting times for next week with custom duration:
           suggest_meeting_times(
               start_date="next monday", 
               end_date="next friday", 
               duration_minutes=30
           )
           
        3. Find meeting times with custom working hours:
           suggest_meeting_times(
               start_date="tomorrow", 
               end_date="friday", 
               working_hours="10-16"
           )
           
        Important:
        - The tool respects the user's existing calendar events
        - Suggestions are limited to working hours (default 9am-5pm)
        - Weekends are excluded by default
        - The tool will return at most 10 suggestions
        """
        credentials = get_credentials()
        
        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}
        
        try:
            # Parse working hours if provided
            work_start_hour = 9  # Default 9am
            work_end_hour = 17   # Default 5pm
            
            if working_hours:
                try:
                    hours_parts = working_hours.split("-")
                    if len(hours_parts) == 2:
                        work_start_hour = int(hours_parts[0])
                        work_end_hour = int(hours_parts[1])
                except Exception as e:
                    logger.warning(f"Failed to parse working hours: {e}")
            
            # Use the calendar processor to suggest meeting times
            from gmail_mcp.calendar.processor import suggest_meeting_times as processor_suggest_times
            
            suggestions = processor_suggest_times(
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                working_hours=(work_start_hour, work_end_hour)
            )
            
            # Check if there was an error
            if suggestions and "error" in suggestions[0]:
                return {
                    "success": False,
                    "error": suggestions[0]["error"],
                    "message": "Could not suggest meeting times. Please check your date range."
                }
            
            # Format the response
            return {
                "success": True,
                "suggestions": suggestions,
                "message": f"Found {len(suggestions)} available time slots.",
                "parameters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_minutes": duration_minutes,
                    "working_hours": f"{work_start_hour}-{work_end_hour}"
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to suggest meeting times: {e}")
            return {
                "success": False,
                "error": f"Failed to suggest meeting times: {e}"
            }

    # ========== NEW EMAIL TOOLS ==========

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
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            service = build("gmail", "v1", credentials=credentials)

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
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            service = build("gmail", "v1", credentials=credentials)

            # Get the original email
            original = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            # Extract headers
            headers = {}
            for header in original["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            # Extract body
            body = ""
            if "parts" in original["payload"]:
                for part in original["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
            elif "body" in original["payload"] and "data" in original["payload"]["body"]:
                body = base64.urlsafe_b64decode(original["payload"]["body"]["data"]).decode("utf-8")

            # Build forwarded message
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

    @mcp.tool()
    def archive_email(email_id: str) -> Dict[str, Any]:
        """
        Archive an email (remove from inbox but keep in All Mail).

        Args:
            email_id (str): The ID of the email to archive

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["INBOX"]}
            ).execute()

            return {
                "success": True,
                "message": "Email archived successfully.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to archive email: {e}")
            return {"success": False, "error": f"Failed to archive email: {e}"}

    @mcp.tool()
    def trash_email(email_id: str) -> Dict[str, Any]:
        """
        Move an email to trash.

        Args:
            email_id (str): The ID of the email to trash

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().trash(userId="me", id=email_id).execute()

            return {
                "success": True,
                "message": "Email moved to trash.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to trash email: {e}")
            return {"success": False, "error": f"Failed to trash email: {e}"}

    @mcp.tool()
    def delete_email(email_id: str) -> Dict[str, Any]:
        """
        Permanently delete an email. THIS CANNOT BE UNDONE.

        Args:
            email_id (str): The ID of the email to delete permanently

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().delete(userId="me", id=email_id).execute()

            return {
                "success": True,
                "message": "Email permanently deleted.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to delete email: {e}")
            return {"success": False, "error": f"Failed to delete email: {e}"}

    @mcp.tool()
    def list_labels() -> Dict[str, Any]:
        """
        List all labels in the user's Gmail account.

        Returns:
            Dict[str, Any]: List of labels with IDs and names
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            return {
                "success": True,
                "labels": [
                    {
                        "id": label["id"],
                        "name": label["name"],
                        "type": label.get("type", "user")
                    }
                    for label in labels
                ]
            }

        except Exception as e:
            logger.error(f"Failed to list labels: {e}")
            return {"success": False, "error": f"Failed to list labels: {e}"}

    @mcp.tool()
    def create_label(name: str, background_color: Optional[str] = None, text_color: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new label.

        Args:
            name (str): Name for the new label
            background_color (str, optional): Background color in hex (e.g., "#16a765")
            text_color (str, optional): Text color in hex (e.g., "#ffffff")

        Returns:
            Dict[str, Any]: The created label details
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            label_body = {
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show"
            }

            if background_color or text_color:
                label_body["color"] = {}
                if background_color:
                    label_body["color"]["backgroundColor"] = background_color
                if text_color:
                    label_body["color"]["textColor"] = text_color

            label = service.users().labels().create(userId="me", body=label_body).execute()

            return {
                "success": True,
                "message": f"Label '{name}' created.",
                "label": {
                    "id": label["id"],
                    "name": label["name"]
                }
            }

        except Exception as e:
            logger.error(f"Failed to create label: {e}")
            return {"success": False, "error": f"Failed to create label: {e}"}

    @mcp.tool()
    def apply_label(email_id: str, label_id: str) -> Dict[str, Any]:
        """
        Apply a label to an email.

        Args:
            email_id (str): The ID of the email
            label_id (str): The ID of the label to apply (use list_labels to find IDs)

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [label_id]}
            ).execute()

            return {
                "success": True,
                "message": "Label applied.",
                "email_id": email_id,
                "label_id": label_id
            }

        except Exception as e:
            logger.error(f"Failed to apply label: {e}")
            return {"success": False, "error": f"Failed to apply label: {e}"}

    @mcp.tool()
    def remove_label(email_id: str, label_id: str) -> Dict[str, Any]:
        """
        Remove a label from an email.

        Args:
            email_id (str): The ID of the email
            label_id (str): The ID of the label to remove

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": [label_id]}
            ).execute()

            return {
                "success": True,
                "message": "Label removed.",
                "email_id": email_id,
                "label_id": label_id
            }

        except Exception as e:
            logger.error(f"Failed to remove label: {e}")
            return {"success": False, "error": f"Failed to remove label: {e}"}

    @mcp.tool()
    def mark_as_read(email_id: str) -> Dict[str, Any]:
        """
        Mark an email as read.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()

            return {
                "success": True,
                "message": "Email marked as read.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return {"success": False, "error": f"Failed to mark as read: {e}"}

    @mcp.tool()
    def mark_as_unread(email_id: str) -> Dict[str, Any]:
        """
        Mark an email as unread.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": ["UNREAD"]}
            ).execute()

            return {
                "success": True,
                "message": "Email marked as unread.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to mark as unread: {e}")
            return {"success": False, "error": f"Failed to mark as unread: {e}"}

    @mcp.tool()
    def star_email(email_id: str) -> Dict[str, Any]:
        """
        Star an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": ["STARRED"]}
            ).execute()

            return {
                "success": True,
                "message": "Email starred.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to star email: {e}")
            return {"success": False, "error": f"Failed to star email: {e}"}

    @mcp.tool()
    def unstar_email(email_id: str) -> Dict[str, Any]:
        """
        Remove star from an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["STARRED"]}
            ).execute()

            return {
                "success": True,
                "message": "Star removed.",
                "email_id": email_id
            }

        except Exception as e:
            logger.error(f"Failed to unstar email: {e}")
            return {"success": False, "error": f"Failed to unstar email: {e}"}

    @mcp.tool()
    def get_attachments(email_id: str) -> Dict[str, Any]:
        """
        List all attachments in an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: List of attachments with metadata
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            attachments = []

            def find_attachments(parts):
                for part in parts:
                    if part.get("filename"):
                        attachments.append({
                            "attachment_id": part["body"].get("attachmentId"),
                            "filename": part["filename"],
                            "mime_type": part["mimeType"],
                            "size": part["body"].get("size", 0)
                        })
                    if "parts" in part:
                        find_attachments(part["parts"])

            if "parts" in msg["payload"]:
                find_attachments(msg["payload"]["parts"])

            return {
                "success": True,
                "email_id": email_id,
                "attachments": attachments,
                "count": len(attachments)
            }

        except Exception as e:
            logger.error(f"Failed to get attachments: {e}")
            return {"success": False, "error": f"Failed to get attachments: {e}"}

    @mcp.tool()
    def download_attachment(email_id: str, attachment_id: str, save_path: str) -> Dict[str, Any]:
        """
        Download an attachment from an email.

        Args:
            email_id (str): The ID of the email
            attachment_id (str): The attachment ID (from get_attachments)
            save_path (str): Full path where to save the file

        Returns:
            Dict[str, Any]: Result including the saved file path
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=email_id,
                id=attachment_id
            ).execute()

            data = base64.urlsafe_b64decode(attachment["data"])

            with open(save_path, "wb") as f:
                f.write(data)

            return {
                "success": True,
                "message": f"Attachment saved to {save_path}",
                "file_path": save_path,
                "size_bytes": len(data)
            }

        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            return {"success": False, "error": f"Failed to download attachment: {e}"}

    @mcp.tool()
    def bulk_archive(query: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Archive all emails matching a search query.

        Args:
            query (str): Gmail search query (e.g., "from:newsletter@example.com")
            max_emails (int): Maximum number of emails to archive (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])
            archived = 0
            failed = 0

            for msg in messages:
                try:
                    service.users().messages().modify(
                        userId="me",
                        id=msg["id"],
                        body={"removeLabelIds": ["INBOX"]}
                    ).execute()
                    archived += 1
                except Exception:
                    failed += 1

            return {
                "success": True,
                "message": f"Archived {archived} emails.",
                "archived": archived,
                "failed": failed,
                "query": query
            }

        except Exception as e:
            logger.error(f"Failed to bulk archive: {e}")
            return {"success": False, "error": f"Failed to bulk archive: {e}"}

    @mcp.tool()
    def bulk_label(query: str, label_id: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Apply a label to all emails matching a search query.

        Args:
            query (str): Gmail search query
            label_id (str): The label ID to apply
            max_emails (int): Maximum number of emails to label (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])
            labeled = 0
            failed = 0

            for msg in messages:
                try:
                    service.users().messages().modify(
                        userId="me",
                        id=msg["id"],
                        body={"addLabelIds": [label_id]}
                    ).execute()
                    labeled += 1
                except Exception:
                    failed += 1

            return {
                "success": True,
                "message": f"Labeled {labeled} emails.",
                "labeled": labeled,
                "failed": failed,
                "query": query,
                "label_id": label_id
            }

        except Exception as e:
            logger.error(f"Failed to bulk label: {e}")
            return {"success": False, "error": f"Failed to bulk label: {e}"}

    @mcp.tool()
    def bulk_trash(query: str, max_emails: int = 50) -> Dict[str, Any]:
        """
        Move all emails matching a search query to trash.

        Args:
            query (str): Gmail search query
            max_emails (int): Maximum number of emails to trash (default 50, max 100)

        Returns:
            Dict[str, Any]: Results of the bulk operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            max_emails = min(max_emails, 100)

            result = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get("messages", [])
            trashed = 0
            failed = 0

            for msg in messages:
                try:
                    service.users().messages().trash(userId="me", id=msg["id"]).execute()
                    trashed += 1
                except Exception:
                    failed += 1

            return {
                "success": True,
                "message": f"Trashed {trashed} emails.",
                "trashed": trashed,
                "failed": failed,
                "query": query
            }

        except Exception as e:
            logger.error(f"Failed to bulk trash: {e}")
            return {"success": False, "error": f"Failed to bulk trash: {e}"}

    @mcp.tool()
    def find_unsubscribe_link(email_id: str) -> Dict[str, Any]:
        """
        Find unsubscribe link in an email.

        Args:
            email_id (str): The ID of the email

        Returns:
            Dict[str, Any]: Unsubscribe link if found
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("gmail", "v1", credentials=credentials)

            msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()

            # Check headers for List-Unsubscribe
            headers = {}
            for header in msg["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]

            unsubscribe_header = headers.get("list-unsubscribe", "")

            # Extract body
            body = ""
            if "parts" in msg["payload"]:
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/html" and "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                        break
                    elif part["mimeType"] == "text/plain" and "data" in part["body"]:
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
                body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")

            # Find unsubscribe links in body
            unsubscribe_patterns = [
                r'https?://[^\s<>"]+unsubscribe[^\s<>"]*',
                r'https?://[^\s<>"]+optout[^\s<>"]*',
                r'https?://[^\s<>"]+opt-out[^\s<>"]*',
                r'https?://[^\s<>"]+remove[^\s<>"]*',
            ]

            found_links = []

            # Extract from header
            if unsubscribe_header:
                header_links = re.findall(r'<(https?://[^>]+)>', unsubscribe_header)
                found_links.extend(header_links)
                mailto_links = re.findall(r'<(mailto:[^>]+)>', unsubscribe_header)
                found_links.extend(mailto_links)

            # Extract from body
            for pattern in unsubscribe_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                found_links.extend(matches)

            # Deduplicate
            found_links = list(set(found_links))

            return {
                "success": True,
                "email_id": email_id,
                "unsubscribe_links": found_links[:5],  # Limit to 5
                "has_list_unsubscribe_header": bool(unsubscribe_header),
                "from": headers.get("from", "Unknown")
            }

        except Exception as e:
            logger.error(f"Failed to find unsubscribe link: {e}")
            return {"success": False, "error": f"Failed to find unsubscribe link: {e}"}

    # ========== CALENDAR UPDATE/DELETE TOOLS ==========

    @mcp.tool()
    def update_calendar_event(event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id (str): The ID of the event to update
            summary (str, optional): New title for the event
            start_time (str, optional): New start time
            end_time (str, optional): New end time
            description (str, optional): New description
            location (str, optional): New location

        Returns:
            Dict[str, Any]: Updated event details
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("calendar", "v3", credentials=credentials)

            # Get existing event
            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            # Update fields if provided
            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if location:
                event["location"] = location

            if start_time:
                try:
                    start_dt = parser.parse(start_time, fuzzy=True)
                    event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": get_user_timezone()}
                except Exception:
                    return {"success": False, "error": f"Could not parse start time: {start_time}"}

            if end_time:
                try:
                    end_dt = parser.parse(end_time, fuzzy=True)
                    event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": get_user_timezone()}
                except Exception:
                    return {"success": False, "error": f"Could not parse end time: {end_time}"}

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": "Event updated successfully.",
                "event_id": updated_event["id"],
                "event_link": updated_event.get("htmlLink", ""),
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return {"success": False, "error": f"Failed to update calendar event: {e}"}

    @mcp.tool()
    def delete_calendar_event(event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event.

        Args:
            event_id (str): The ID of the event to delete

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = build("calendar", "v3", credentials=credentials)

            service.events().delete(calendarId="primary", eventId=event_id).execute()

            return {
                "success": True,
                "message": "Event deleted successfully.",
                "event_id": event_id
            }

        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return {"success": False, "error": f"Failed to delete calendar event: {e}"}

    @mcp.tool()
    def rsvp_event(event_id: str, response: str) -> Dict[str, Any]:
        """
        Respond to a calendar event invitation.

        Args:
            event_id (str): The ID of the event
            response (str): Response status - "accepted", "declined", or "tentative"

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        if response not in ["accepted", "declined", "tentative"]:
            return {"success": False, "error": "Response must be 'accepted', 'declined', or 'tentative'"}

        try:
            service = build("calendar", "v3", credentials=credentials)

            # Get the event
            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            # Get user's email
            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")

            # Update attendee response
            attendees = event.get("attendees", [])
            for attendee in attendees:
                if attendee.get("email", "").lower() == user_email.lower():
                    attendee["responseStatus"] = response
                    break

            event["attendees"] = attendees

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": f"RSVP updated to '{response}'.",
                "event_id": event_id,
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to RSVP: {e}")
            return {"success": False, "error": f"Failed to RSVP: {e}"} 