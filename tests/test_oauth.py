"""
Tests for auth/oauth.py - OAuth authentication
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGetScopes:
    """Tests for get_scopes function."""

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_returns_list(self, mock_get_config):
        """Test that get_scopes returns a list."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "calendar_api_enabled": False,
        }

        scopes = get_scopes()
        assert isinstance(scopes, list)

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_includes_gmail_scopes(self, mock_get_config):
        """Test that Gmail scopes are included."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
            ],
            "calendar_api_enabled": False,
        }

        scopes = get_scopes()
        assert "https://www.googleapis.com/auth/gmail.readonly" in scopes
        assert "https://www.googleapis.com/auth/gmail.send" in scopes

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_includes_calendar_scopes_when_enabled(self, mock_get_config):
        """Test that Calendar scopes are included when enabled."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "calendar_api_enabled": True,
            "calendar_api_scopes": [
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/calendar.events",
            ],
        }

        scopes = get_scopes()
        assert "https://www.googleapis.com/auth/calendar.readonly" in scopes
        assert "https://www.googleapis.com/auth/calendar.events" in scopes

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_excludes_calendar_scopes_when_disabled(self, mock_get_config):
        """Test that Calendar scopes are excluded when disabled."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "calendar_api_enabled": False,
            "calendar_api_scopes": [
                "https://www.googleapis.com/auth/calendar.readonly",
            ],
        }

        scopes = get_scopes()
        assert "https://www.googleapis.com/auth/calendar.readonly" not in scopes

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_always_includes_userinfo_scopes(self, mock_get_config):
        """Test that user info scopes are always included."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "calendar_api_enabled": False,
        }

        scopes = get_scopes()
        assert "https://www.googleapis.com/auth/userinfo.email" in scopes
        assert "https://www.googleapis.com/auth/userinfo.profile" in scopes
        assert "openid" in scopes

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_no_duplicate_scopes(self, mock_get_config):
        """Test that scopes are not duplicated."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/userinfo.email",  # Already in user info
            ],
            "calendar_api_enabled": False,
        }

        scopes = get_scopes()
        # Count occurrences
        email_count = scopes.count("https://www.googleapis.com/auth/userinfo.email")
        assert email_count == 1

    @patch("gmail_mcp.auth.oauth.get_config")
    def test_returns_new_list_each_call(self, mock_get_config):
        """Test that get_scopes returns a new list each call (no mutation)."""
        from gmail_mcp.auth.oauth import get_scopes

        mock_get_config.return_value = {
            "gmail_api_scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "calendar_api_enabled": False,
        }

        scopes1 = get_scopes()
        scopes1.append("modified")

        scopes2 = get_scopes()
        assert "modified" not in scopes2


class TestLogin:
    """Tests for login function."""

    @patch("gmail_mcp.auth.oauth.token_manager")
    @patch("gmail_mcp.auth.oauth.InstalledAppFlow")
    @patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test_client_id",
        "GOOGLE_CLIENT_SECRET": "test_client_secret",
    })
    def test_login_returns_auth_url(self, mock_flow_class, mock_token_manager):
        """Test that login returns an authorization URL."""
        from gmail_mcp.auth.oauth import login

        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?...",
            "state_abc123"
        )
        mock_flow_class.from_client_config.return_value = mock_flow

        result = login()

        assert "https://accounts.google.com" in result
        assert not result.startswith("Error:")

    @patch("gmail_mcp.auth.oauth.token_manager")
    @patch("gmail_mcp.auth.oauth.InstalledAppFlow")
    @patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test_client_id",
        "GOOGLE_CLIENT_SECRET": "test_client_secret",
    })
    def test_login_stores_state(self, mock_flow_class, mock_token_manager):
        """Test that login stores the OAuth state."""
        from gmail_mcp.auth.oauth import login

        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?...",
            "state_xyz789"
        )
        mock_flow_class.from_client_config.return_value = mock_flow

        login()

        mock_token_manager.store_state.assert_called_once_with("state_xyz789")

    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}, clear=True)
    def test_login_returns_error_without_credentials(self):
        """Test that login returns error without OAuth credentials."""
        from gmail_mcp.auth.oauth import login

        # Clear env vars
        import os
        os.environ.pop("GOOGLE_CLIENT_ID", None)
        os.environ.pop("GOOGLE_CLIENT_SECRET", None)

        result = login()

        assert result.startswith("Error:")
        assert "Missing Google OAuth credentials" in result


class TestProcessAuthCode:
    """Tests for process_auth_code function."""

    @patch("gmail_mcp.auth.oauth.token_manager")
    @patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test_client_id",
        "GOOGLE_CLIENT_SECRET": "test_client_secret",
    })
    def test_rejects_invalid_state(self, mock_token_manager):
        """Test that process_auth_code rejects invalid state (CSRF protection)."""
        from gmail_mcp.auth.oauth import process_auth_code

        mock_token_manager.verify_state.return_value = False

        result = process_auth_code(code="auth_code_123", state="invalid_state")

        assert "Error:" in result
        assert "Invalid state parameter" in result

    @patch("gmail_mcp.auth.oauth.token_manager")
    @patch("gmail_mcp.auth.oauth.InstalledAppFlow")
    @patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test_client_id",
        "GOOGLE_CLIENT_SECRET": "test_client_secret",
    })
    def test_accepts_valid_state(self, mock_flow_class, mock_token_manager):
        """Test that process_auth_code accepts valid state."""
        from gmail_mcp.auth.oauth import process_auth_code

        mock_token_manager.verify_state.return_value = True

        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_config.return_value = mock_flow

        result = process_auth_code(code="valid_code", state="valid_state")

        assert "Error:" not in result or "Invalid state" not in result

    @patch("gmail_mcp.auth.oauth.token_manager")
    @patch("gmail_mcp.auth.oauth.InstalledAppFlow")
    @patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test_client_id",
        "GOOGLE_CLIENT_SECRET": "test_client_secret",
    })
    def test_stores_token_on_success(self, mock_flow_class, mock_token_manager):
        """Test that credentials are stored on successful auth."""
        from gmail_mcp.auth.oauth import process_auth_code

        mock_token_manager.verify_state.return_value = True

        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_config.return_value = mock_flow

        process_auth_code(code="valid_code", state="valid_state")

        mock_token_manager.store_token.assert_called_once_with(mock_credentials)

    @patch("gmail_mcp.auth.oauth.token_manager")
    def test_state_verified_before_token_exchange(self, mock_token_manager):
        """Test that state is verified BEFORE any token exchange."""
        from gmail_mcp.auth.oauth import process_auth_code

        mock_token_manager.verify_state.return_value = False

        # This should fail at state verification, never reaching token exchange
        result = process_auth_code(code="code", state="bad_state")

        # Verify state was checked
        mock_token_manager.verify_state.assert_called_once_with("bad_state")
        # Verify token was NOT stored (auth rejected)
        mock_token_manager.store_token.assert_not_called()


class TestGetCredentials:
    """Tests for get_credentials function."""

    @patch("gmail_mcp.auth.oauth.token_manager")
    def test_returns_none_if_no_tokens(self, mock_token_manager):
        """Test returns None if no tokens exist."""
        from gmail_mcp.auth.oauth import get_credentials

        mock_token_manager.tokens_exist.return_value = False

        result = get_credentials()

        assert result is None

    @patch("gmail_mcp.auth.oauth.token_manager")
    def test_returns_credentials_if_valid(self, mock_token_manager):
        """Test returns credentials if tokens are valid."""
        from gmail_mcp.auth.oauth import get_credentials

        mock_token_manager.tokens_exist.return_value = True
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_token_manager.get_token.return_value = mock_creds

        result = get_credentials()

        assert result == mock_creds

    @patch("gmail_mcp.auth.oauth.GoogleRequest")
    @patch("gmail_mcp.auth.oauth.token_manager")
    def test_refreshes_expired_token(self, mock_token_manager, mock_request):
        """Test that expired tokens are refreshed."""
        from gmail_mcp.auth.oauth import get_credentials

        mock_token_manager.tokens_exist.return_value = True
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_token_manager.get_token.return_value = mock_creds

        get_credentials()

        # Token should be refreshed
        mock_creds.refresh.assert_called_once()
        # New token should be stored
        mock_token_manager.store_token.assert_called_once_with(mock_creds)
