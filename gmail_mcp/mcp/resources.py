"""
MCP Resources Module

This module defines all the resources available in the Gmail MCP server.
Resources are data that Claude can access to get context.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx

from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.token_manager import get_token_manager
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.gmail.processor import (
    parse_email_message,
    analyze_thread,
    get_sender_history,
    extract_email_metadata,
    extract_entities,
    find_related_emails,
    analyze_communication_patterns
)
from gmail_mcp.mcp.schemas import (
    EmailContextItem,
    ThreadContextItem,
    SenderContextItem
)

# Get logger
logger = get_logger(__name__)

# Get token manager singleton
token_manager = get_token_manager()


def setup_resources(mcp: FastMCP) -> None:
    """
    Set up all MCP resources on the FastMCP application.
    
    Args:
        mcp (FastMCP): The FastMCP application.
    """
    # Authentication resources
    @mcp.resource("auth://status")
    def auth_status() -> Dict[str, Any]:
        """
        Get the current authentication status.
        
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
                    "Call authenticate() to start the authentication process",
                    "The user will need to complete the authentication in their browser"
                ]
            }
        
        # Check if the credentials are expired
        if credentials.expired:
            try:
                # Try to refresh the token
                credentials.refresh(GoogleRequest())
                token_manager.store_token(credentials)
                
                # Get the user info
                response = httpx.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {credentials.token}"},
                )
                user_info = response.json()
                
                return {
                    "authenticated": True,
                    "email": user_info.get("email", "Unknown"),
                    "name": user_info.get("name", "Unknown"),
                    "picture": user_info.get("picture"),
                    "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                    "scopes": credentials.scopes,
                    "message": "Authentication is valid. Token was refreshed.",
                    "status": "refreshed"
                }
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                return {
                    "authenticated": False,
                    "message": f"Authentication expired and could not be refreshed: {e}",
                    "next_steps": [
                        "Call authenticate() to start a new authentication process",
                        "The user will need to complete the authentication in their browser"
                    ],
                    "status": "expired"
                }
        
        # Get the user info
        try:
            response = httpx.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            user_info = response.json()
            
            return {
                "authenticated": True,
                "email": user_info.get("email", "Unknown"),
                "name": user_info.get("name", "Unknown"),
                "picture": user_info.get("picture"),
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                "scopes": credentials.scopes,
                "message": "Authentication is valid.",
                "status": "valid"
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {
                "authenticated": True,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                "scopes": credentials.scopes,
                "message": f"Authentication is valid, but failed to get user info: {e}",
                "status": "valid_with_errors"
            }
    
    # Gmail resources
    @mcp.resource("gmail://status")
    def gmail_status() -> Dict[str, Any]:
        """
        Get the current status of the Gmail account.
        
        This resource provides information about the user's Gmail account,
        including authentication status, email address, and account statistics.
        
        Returns:
            Dict[str, Any]: The Gmail account status.
        """
        credentials = get_credentials()
        
        if not credentials:
            return {
                "authenticated": False,
                "message": "Not authenticated. Use the authenticate tool to start the authentication process.",
                "next_steps": [
                    "Check auth://status for authentication details",
                    "Call authenticate() to start the authentication process"
                ]
            }
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the profile information
            profile = service.users().getProfile(userId="me").execute()
            
            # Get labels to calculate counts
            labels = service.users().labels().list(userId="me").execute()
            
            # Extract label information
            label_info = {}
            for label in labels.get("labels", []):
                try:
                    label_details = service.users().labels().get(userId="me", id=label["id"]).execute()
                    label_info[label["name"]] = {
                        "total": label_details.get("messagesTotal", 0),
                        "unread": label_details.get("messagesUnread", 0)
                    }
                except Exception as e:
                    logger.error(f"Failed to get label details for {label['name']}: {e}")
            
            # Get the authentication status
            response = httpx.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            user_info = response.json()
            
            return {
                "authenticated": True,
                "email": profile.get("emailAddress", user_info.get("email", "Unknown")),
                "name": user_info.get("name", "Unknown"),
                "picture": user_info.get("picture"),
                "account_stats": {
                    "total_messages": profile.get("messagesTotal", 0),
                    "total_threads": profile.get("threadsTotal", 0),
                    "storage_used": profile.get("storageUsed", 0),
                    "storage_used_percent": round(int(profile.get("storageUsed", 0)) / (15 * 1024 * 1024 * 1024) * 100, 2)  # Assuming 15GB limit
                },
                "labels": label_info,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                "message": "Gmail account is accessible.",
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Failed to get Gmail status: {e}")
            return {
                "authenticated": True,
                "error": f"Failed to get Gmail status: {e}",
                "message": "Authentication is valid, but failed to get Gmail account information.",
                "next_steps": [
                    "Try again later",
                    "Check if the Gmail API is enabled in the Google Cloud Console",
                    "Check if the user has granted the necessary permissions"
                ],
                "status": "error"
            }
    
    # Email context resources
    @mcp.resource("email://{email_id}")
    def build_email_context(email_id: str) -> Dict[str, Any]:
        """
        Build context for email-related requests.
        
        This resource extracts information about the specified email
        and provides it as context for Claude to use.
        
        Args:
            email_id (str): The ID of the email to get context for.
            
        Returns:
            Dict[str, Any]: The email context.
        """
        credentials = get_credentials()
        if not credentials:
            logger.error("Not authenticated")
            return {"error": "Not authenticated"}
        
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the message
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            
            # Parse the message
            metadata, content = parse_email_message(message)
            
            # Extract entities from the email content
            entities = extract_entities(content.plain_text)
            
            # Find related emails
            related_emails = find_related_emails(email_id, max_results=5)
            
            # Generate a link to the email in Gmail web interface
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{metadata.thread_id}"
            
            # Create context item
            email_context = EmailContextItem(
                type="email",
                content={
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
                    "labels": metadata.labels,
                    "entities": entities,
                    "related_emails": related_emails,
                    "email_link": email_link
                }
            )
            
            return email_context.dict()
        
        except Exception as e:
            logger.error(f"Failed to build email context: {e}")
            return {"error": f"Failed to build email context: {e}"}
    
    @mcp.resource("thread://{thread_id}")
    def build_thread_context(thread_id: str) -> Dict[str, Any]:
        """
        Build context for thread-related requests.
        
        This resource extracts information about the specified thread
        and provides it as context for Claude to use.
        
        Args:
            thread_id (str): The ID of the thread to get context for.
            
        Returns:
            Dict[str, Any]: The thread context.
        """
        credentials = get_credentials()
        if not credentials:
            logger.error("Not authenticated")
            return {"error": "Not authenticated"}
            
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the thread
            thread_data = service.users().threads().get(userId="me", id=thread_id).execute()
            
            # Analyze the thread
            thread = analyze_thread(thread_id)
            if not thread:
                return {"error": "Thread not found or could not be analyzed"}
            
            # Generate a link to the thread in Gmail web interface
            thread_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"
            
            # Get all messages in the thread
            messages = []
            for message in thread_data.get("messages", []):
                msg_metadata, msg_content = parse_email_message(message)
                
                # Extract entities from each message
                entities = extract_entities(msg_content.plain_text)
                
                # Generate a link to the specific message
                message_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{msg_metadata.id}"
                
                messages.append({
                    "id": msg_metadata.id,
                    "subject": msg_metadata.subject,
                    "from": {
                        "email": msg_metadata.from_email,
                        "name": msg_metadata.from_name
                    },
                    "to": msg_metadata.to,
                    "date": msg_metadata.date.isoformat(),
                    "snippet": message.get("snippet", ""),
                    "entities": entities,
                    "email_link": message_link
                })
            
            # Sort messages by date
            messages.sort(key=lambda x: x["date"])
            
            # Analyze communication patterns between participants if there are at least 2 participants
            communication_patterns = {}
            if len(thread.participants) >= 2:
                # Get the user's email
                profile = service.users().getProfile(userId="me").execute()
                user_email = profile.get("emailAddress", "")
                
                # Analyze patterns with other participants
                for participant in thread.participants:
                    participant_email = participant.get("email", "")
                    if participant_email and participant_email != user_email:
                        patterns = analyze_communication_patterns(participant_email, user_email)
                        if patterns and "error" not in patterns:
                            communication_patterns[participant_email] = patterns
            
            # Create context item
            thread_context = ThreadContextItem(
                type="thread",
                content={
                    "id": thread.id,
                    "subject": thread.subject,
                    "message_count": thread.message_count,
                    "participants": thread.participants,
                    "last_message_date": thread.last_message_date.isoformat(),
                    "messages": messages,
                    "communication_patterns": communication_patterns,
                    "thread_link": thread_link
                }
            )
            
            return thread_context.dict()
        
        except Exception as e:
            logger.error(f"Failed to build thread context: {e}")
            return {"error": f"Failed to build thread context: {e}"}
    
    @mcp.resource("sender://{sender_email}")
    def build_sender_context(sender_email: str) -> Dict[str, Any]:
        """
        Build context for sender-related requests.
        
        This resource extracts information about the specified sender
        and provides it as context for Claude to use.
        
        Args:
            sender_email (str): The email address of the sender to get context for.
            
        Returns:
            Dict[str, Any]: The sender context.
        """
        credentials = get_credentials()
        if not credentials:
            logger.error("Not authenticated")
            return {"error": "Not authenticated"}
            
        try:
            # Build the Gmail API service
            service = build("gmail", "v1", credentials=credentials)
            
            # Get the user's email
            profile = service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")
            
            # Get sender history
            sender = get_sender_history(sender_email)
            if not sender:
                return {"error": "Sender not found or could not be analyzed"}
            
            # Analyze communication patterns
            communication_patterns = analyze_communication_patterns(sender_email, user_email)
            
            # Search for recent emails from this sender
            query = f"from:{sender_email}"
            result = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
            
            recent_emails = []
            for message_info in result.get("messages", []):
                message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
                metadata = extract_email_metadata(message)
                
                recent_emails.append({
                    "id": metadata.id,
                    "thread_id": metadata.thread_id,
                    "subject": metadata.subject,
                    "date": metadata.date.isoformat(),
                    "snippet": message.get("snippet", "")
                })
            
            # Create context item
            sender_context = SenderContextItem(
                type="sender",
                content={
                    "email": sender.email,
                    "name": sender.name,
                    "message_count": sender.message_count,
                    "first_message_date": sender.first_message_date.isoformat() if sender.first_message_date else None,
                    "last_message_date": sender.last_message_date.isoformat() if sender.last_message_date else None,
                    "common_topics": sender.common_topics,
                    "communication_patterns": communication_patterns,
                    "recent_emails": recent_emails
                }
            )
            
            return sender_context.dict()
        
        except Exception as e:
            logger.error(f"Failed to build sender context: {e}")
            return {"error": f"Failed to build sender context: {e}"}
    
    # Server resources
    @mcp.resource("server://info")
    def server_info() -> Dict[str, Any]:
        """
        Get information about the server.
        
        Returns:
            Dict[str, Any]: The server information.
        """
        config = get_config()
        
        return {
            "name": config.get("server_name", "Gmail MCP"),
            "version": config.get("server_version", "1.3.0"),
            "description": config.get("server_description", "A Model Context Protocol server for Gmail integration with Claude Desktop"),
            "host": config.get("host", "localhost"),
            "port": config.get("port", 8000),
        }
    
    @mcp.resource("server://config")
    def server_config() -> Dict[str, Any]:
        """
        Get the server configuration.
        
        Returns:
            Dict[str, Any]: The server configuration.
        """
        config = get_config()
        
        # Remove sensitive information
        safe_config = {k: v for k, v in config.items() if not any(sensitive in k for sensitive in ["secret", "password", "token", "key"])}
        
        return safe_config
    
    @mcp.resource("debug://help")
    def debug_help() -> Dict[str, Any]:
        """
        Get debugging help for the Gmail MCP server.
        
        This resource provides guidance on how to debug issues with the MCP server,
        particularly focusing on Claude Desktop integration problems.
        
        Returns:
            Dict[str, Any]: Debugging help information.
        """
        return {
            "title": "Gmail MCP Debugging Guide",
            "description": "This guide helps diagnose issues with the Gmail MCP server.",
            "common_issues": [
                {
                    "issue": "Claude Desktop is stuck in a polling loop",
                    "possible_causes": [
                        "Claude is not accessing resources",
                        "Claude is not calling tools",
                        "Claude is waiting for a response that never comes",
                        "The MCP server is not responding correctly"
                    ],
                    "solutions": [
                        "Simplify prompts and focus on direct tool calls",
                        "Use simple code examples without await/async",
                        "Check logs for errors or unexpected behavior",
                        "Restart the MCP server and Claude Desktop"
                    ]
                },
                {
                    "issue": "Authentication fails",
                    "possible_causes": [
                        "Invalid client ID or client secret",
                        "Redirect URI mismatch",
                        "Insufficient permissions",
                        "Token expired or invalid"
                    ],
                    "solutions": [
                        "Check Google Cloud Console configuration",
                        "Verify redirect URI matches exactly",
                        "Ensure all required scopes are included",
                        "Delete tokens.json and re-authenticate"
                    ]
                },
                {
                    "issue": "Gmail API calls fail",
                    "possible_causes": [
                        "Not authenticated",
                        "Insufficient permissions",
                        "API quota exceeded",
                        "Invalid request parameters"
                    ],
                    "solutions": [
                        "Check authentication status",
                        "Verify Gmail API is enabled in Google Cloud Console",
                        "Check for quota errors in logs",
                        "Verify request parameters are valid"
                    ]
                }
            ],
            "debugging_steps": [
                "1. Check logs for errors or unexpected behavior",
                "2. Verify authentication status using auth://status resource",
                "3. Try simple tool calls like get_email_count()",
                "4. Check if Claude Desktop is accessing resources",
                "5. Restart the MCP server and Claude Desktop",
                "6. Try using the MCP Inspector to verify functionality"
            ],
            "example_workflow": {
                "description": "A simple workflow to test basic functionality",
                "steps": [
                    "1. Access auth://status resource",
                    "2. If not authenticated, call authenticate()",
                    "3. Call get_email_count()",
                    "4. Call list_emails(max_results=3)"
                ],
                "code": """
# Check authentication
auth_status = mcp.resources.get("auth://status")
print(f"Authentication status: {auth_status}")

# Authenticate if needed
if not auth_status.get("authenticated", False):
    result = mcp.tools.authenticate()
    print(f"Authentication result: {result}")
    
    # Check authentication status again
    auth_status = mcp.resources.get("auth://status")
    print(f"Updated authentication status: {auth_status}")

# Get email count
email_count = mcp.tools.get_email_count()
print(f"Email count: {email_count}")

# List recent emails
emails = mcp.tools.list_emails(max_results=3)
print(f"Recent emails: {emails}")
"""
            }
        }
    
    @mcp.resource("server://status")
    def server_status() -> Dict[str, Any]:
        """
        Get the comprehensive server status, including authentication and Gmail status.
        
        This resource provides a one-stop overview of the server status, including
        authentication status, Gmail account information, and available functionality.
        
        Returns:
            Dict[str, Any]: The server status.
        """
        # Get credentials
        credentials = get_credentials()
        authenticated = credentials is not None
        
        # Basic status
        status = {
            "server": {
                "name": "Gmail MCP",
                "version": "1.3.0",
                "status": "running",
            },
            "authentication": {
                "authenticated": authenticated,
                "status": "authenticated" if authenticated else "not_authenticated",
            },
            "available_resources": [
                "auth://status",
                "gmail://status",
                "email://{email_id}",
                "thread://{thread_id}",
                "sender://{sender_email}",
                "server://info",
                "server://config",
                "server://status",
                "debug://help",
                "health://",
            ],
            "available_tools": [
                "authenticate()",
                "login_tool()",
                "process_auth_code_tool(code, state)",
                "logout()",
                "check_auth_status()",
                "get_email_count()",
                "list_emails(max_results=10, label='INBOX')",
                "get_email(email_id)",
                "search_emails(query, max_results=10)",
                "get_email_overview()",
            ],
            "available_prompts": [
                "gmail_welcome",
                "authenticate_gmail",
                "access_gmail_data",
            ],
            "next_steps": [],
        }
        
        # Add next steps based on authentication status
        if not authenticated:
            status["next_steps"] = [
                "Check authentication status: mcp.tools.check_auth_status()",
                "Start authentication: mcp.tools.authenticate()",
                "After authentication, verify status: mcp.tools.check_auth_status()",
            ]
        else:
            status["next_steps"] = [
                "Get email overview: mcp.tools.get_email_overview()",
                "Get email count: mcp.tools.get_email_count()",
                "List recent emails: mcp.tools.list_emails(max_results=5)",
                "Search for emails: mcp.tools.search_emails(query='is:unread')",
            ]
            
            # Add Gmail account information if authenticated
            try:
                # Build the Gmail API service
                service = build("gmail", "v1", credentials=credentials)
                
                # Get the profile information
                profile = service.users().getProfile(userId="me").execute()
                
                status["gmail"] = {
                    "email": profile.get("emailAddress", "Unknown"),
                    "total_messages": profile.get("messagesTotal", 0),
                    "total_threads": profile.get("threadsTotal", 0),
                    "storage_used": profile.get("storageUsed", 0),
                }
            except Exception as e:
                status["gmail"] = {
                    "status": "error",
                    "error": str(e),
                }
        
        return status
    
    # Health check resource
    @mcp.resource("health://")
    def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.
        
        Returns:
            Dict[str, Any]: The health check result.
        """
        return {"status": "healthy", "version": "1.3.0"} 