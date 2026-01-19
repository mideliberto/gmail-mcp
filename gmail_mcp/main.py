#!/usr/bin/env python3
"""
Gmail MCP Server

This module provides the main entry point for the Gmail MCP server.
"""

import os
import sys
import traceback

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.token_manager import get_token_manager
from gmail_mcp.mcp.tools import setup_tools
from gmail_mcp.mcp.resources import setup_resources
from gmail_mcp.mcp.prompts import setup_prompts

# Get logger
logger = get_logger(__name__)

# Get configuration
config = get_config()

# Create FastMCP application
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "Gmail MCP"),
)

# Setup tools, resources, and prompts
setup_tools(mcp)
setup_resources(mcp)
setup_prompts(mcp)

def check_authentication(max_attempts: int = 3, timeout: int = 300) -> bool:
    """
    Check if the user is authenticated and prompt them to authenticate if not.
    
    Args:
        max_attempts (int, optional): Maximum number of authentication attempts. Defaults to 3.
        timeout (int, optional): Timeout for each authentication attempt in seconds. Defaults to 300 (5 minutes).
        
    Returns:
        bool: True if authentication is successful, False otherwise.
    """
    token_manager = get_token_manager()

    # If tokens already exist, we're good to go
    if token_manager.tokens_exist():
        logger.info("Authentication tokens found, user is authenticated")
        try:
            # Verify that the tokens are valid by checking if we can get credentials
            from gmail_mcp.auth.oauth import get_credentials
            credentials = get_credentials()
            if credentials:
                logger.info("Credentials are valid")
                return True
            else:
                logger.warning("Credentials are invalid, deleting tokens and starting authentication")
                token_manager.clear_token()
        except Exception as e:
            logger.error(f"Error checking credentials: {e}")
            logger.warning("Deleting tokens and starting authentication")
            token_manager.clear_token()
    
    # No tokens or invalid tokens, start authentication
    logger.info("No authentication tokens found, starting authentication")
    
    # Start authentication process
    from gmail_mcp.auth.oauth import start_oauth_process
    for attempt in range(max_attempts):
        logger.info(f"Authentication attempt {attempt + 1}/{max_attempts}")
        try:
            if start_oauth_process(timeout=timeout):
                logger.info("Authentication successful")
                return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            logger.error(traceback.format_exc())
    
    logger.error(f"Authentication failed after {max_attempts} attempts")
    return False


def main() -> None:
    """
    Main entry point for the Gmail MCP server.
    """
    try:
        # Check authentication
        if not check_authentication():
            logger.error("Authentication failed, exiting")
            sys.exit(1)
        
        # Run the MCP server
        logger.info("Starting MCP server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 