"""
Authentication Tools Module

Handles OAuth login, logout, and authentication status checks.
"""

from typing import Dict, Any
import httpx

from mcp.server.fastmcp import FastMCP
from google.auth.transport.requests import Request as GoogleRequest

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.token_manager import get_token_manager
from typing import Optional, List
from gmail_mcp.auth.oauth import login, process_auth_code, start_oauth_process

logger = get_logger(__name__)
token_manager = get_token_manager()


def setup_auth_tools(mcp: FastMCP) -> None:
    """Set up authentication tools on the FastMCP application."""

    @mcp.tool()
    def login_tool() -> str:
        """
        Initiate the OAuth2 flow by providing a link to the Google authorization page.

        Returns:
            str: The authorization URL to redirect to.
        """
        return login()

    # Scope presets - groups of related scopes
    SCOPE_PRESETS = {
        "gmail": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.settings.basic",
        ],
        "calendar": [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        "contacts": [
            "https://www.googleapis.com/auth/contacts.readonly",
        ],
        "drive": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.labels",
            "https://www.googleapis.com/auth/drive.activity.readonly",
        ],
        "chat": [
            "https://www.googleapis.com/auth/chat.spaces",
            "https://www.googleapis.com/auth/chat.messages",
            "https://www.googleapis.com/auth/chat.memberships",
        ],
    }

    # Always included (user info)
    BASE_SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    @mcp.tool()
    def authenticate(services: Optional[str] = None) -> str:
        """
        Start the complete OAuth authentication process.

        This tool opens a browser window and starts a local server to handle the callback.

        Args:
            services (Optional[str]): Comma-separated list of services to request access for.
                Available: gmail, calendar, contacts, drive, chat
                Example: "gmail,calendar,contacts" (no chat or drive)
                If not provided, scopes are built from config (which may include all services).
                User info scopes are always included.

        Returns:
            str: A message indicating that the authentication process has started.
        """
        import threading

        # Build scope list from service presets
        scope_list: Optional[List[str]] = None
        if services:
            scope_list = list(BASE_SCOPES)  # Always include base scopes
            for service in services.split(","):
                service = service.strip().lower()
                if service in SCOPE_PRESETS:
                    scope_list.extend(SCOPE_PRESETS[service])
                else:
                    logger.warning(f"Unknown service preset: {service}")
            logger.info(f"Using services {services} with scopes: {scope_list}")

        thread = threading.Thread(
            target=start_oauth_process,
            kwargs={"scope_override": scope_list}
        )
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
        credentials = token_manager.get_token()

        if credentials:
            try:
                httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": credentials.token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
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
        credentials = token_manager.get_token()

        if not credentials:
            return {
                "authenticated": False,
                "message": "Not authenticated. Use the authenticate tool to start the authentication process.",
                "next_steps": [
                    "Call authenticate() to start the authentication process"
                ]
            }

        if credentials.expired:
            try:
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
