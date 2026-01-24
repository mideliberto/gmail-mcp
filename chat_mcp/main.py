#!/usr/bin/env python3
"""
Chat MCP Server

This module provides the main entry point for the Chat MCP server.
"""

import os
import sys
import traceback

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger, setup_logger
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.token_manager import get_token_manager

# Setup logger for chat_mcp
setup_logger("chat_mcp")
logger = get_logger("chat_mcp")

# Get configuration
config = get_config()

# Create FastMCP application
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "Chat MCP"),
)

# Import and setup tools after mcp is created
from chat_mcp.mcp.tools import setup_tools
from chat_mcp.mcp.resources import setup_resources

setup_tools(mcp)
setup_resources(mcp)


def get_chat_scopes() -> list:
    """
    Get the OAuth scopes required for Chat API.

    Returns:
        list: The list of OAuth scopes.
    """
    return [
        "https://www.googleapis.com/auth/chat.spaces",
        "https://www.googleapis.com/auth/chat.spaces.readonly",
        "https://www.googleapis.com/auth/chat.messages",
        "https://www.googleapis.com/auth/chat.messages.create",
        "https://www.googleapis.com/auth/chat.memberships",
        "https://www.googleapis.com/auth/chat.memberships.readonly",
        # User info scopes
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]


def check_authentication(max_attempts: int = 3, timeout: int = 300) -> bool:
    """
    Check if the user is authenticated with Chat scopes.

    This reuses the gmail-mcp token storage. If tokens exist and include
    Chat scopes, we're good. Otherwise, need to re-authenticate with
    combined scopes.

    Args:
        max_attempts: Maximum number of authentication attempts.
        timeout: Timeout for each authentication attempt in seconds.

    Returns:
        bool: True if authentication is successful, False otherwise.
    """
    token_manager = get_token_manager()

    # If tokens already exist, check if they have Chat scope
    if token_manager.tokens_exist():
        logger.info("Authentication tokens found, checking scopes")
        try:
            from gmail_mcp.auth.oauth import get_credentials
            credentials = get_credentials()
            if credentials:
                # Check if Chat scope is present
                if credentials.scopes and "https://www.googleapis.com/auth/chat.spaces" in credentials.scopes:
                    logger.info("Credentials include Chat scope")
                    return True
                else:
                    logger.warning("Credentials missing Chat scope, need to re-authenticate")
                    logger.info(f"Current scopes: {credentials.scopes}")
                    # Don't clear tokens - user may need them for gmail-mcp
                    # Just warn that Chat scope is missing
                    print("\n" + "=" * 80)
                    print("CHAT SCOPE MISSING")
                    print("=" * 80)
                    print("Your current authentication doesn't include Google Chat access.")
                    print("Please re-authenticate with Chat scopes enabled.")
                    print("You may need to update your config.yaml to include Chat scopes.")
                    print("\nNote: Chat API requires a Google Workspace account.")
                    print("Personal Gmail accounts do not have access to the Chat API.")
                    print("=" * 80 + "\n")
                    return False
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")
            return False

    # No tokens found
    logger.warning("No authentication tokens found")
    print("\n" + "=" * 80)
    print("NOT AUTHENTICATED")
    print("=" * 80)
    print("Please authenticate using gmail-mcp first, with Chat scopes enabled.")
    print("\nNote: Chat API requires a Google Workspace account.")
    print("Personal Gmail accounts do not have access to the Chat API.")
    print("=" * 80 + "\n")
    return False


def main() -> None:
    """
    Main entry point for the Chat MCP server.
    """
    try:
        # Check authentication
        if not check_authentication():
            logger.error("Authentication failed or missing Chat scope, exiting")
            sys.exit(1)

        # Run the MCP server
        logger.info("Starting Chat MCP server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
