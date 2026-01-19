"""
Tests for utils/services.py - Service caching
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGetGmailService:
    """Tests for get_gmail_service function."""

    @patch("gmail_mcp.utils.services.build")
    def test_creates_service_on_first_call(self, mock_build):
        """Test that service is created on first call."""
        import gmail_mcp.utils.services as services_module

        # Reset cache
        services_module._gmail_service = None
        services_module._credentials_hash = None

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"

        result = services_module.get_gmail_service(mock_creds)

        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
        assert result == mock_service

    @patch("gmail_mcp.utils.services.build")
    def test_returns_cached_service(self, mock_build):
        """Test that cached service is returned on subsequent calls."""
        import gmail_mcp.utils.services as services_module

        # Reset cache
        services_module._gmail_service = None
        services_module._credentials_hash = None

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"

        # First call
        result1 = services_module.get_gmail_service(mock_creds)
        # Second call with same credentials
        result2 = services_module.get_gmail_service(mock_creds)

        # Build should only be called once
        assert mock_build.call_count == 1
        # Same service returned
        assert result1 is result2

    @patch("gmail_mcp.utils.services.build")
    def test_creates_new_service_when_credentials_change(self, mock_build):
        """Test that new service is created when credentials change."""
        import gmail_mcp.utils.services as services_module

        # Reset cache
        services_module._gmail_service = None
        services_module._credentials_hash = None

        mock_service1 = MagicMock()
        mock_service2 = MagicMock()
        mock_build.side_effect = [mock_service1, mock_service2]

        mock_creds1 = MagicMock()
        mock_creds1.token = "token_1"
        mock_creds1.refresh_token = "refresh_1"

        mock_creds2 = MagicMock()
        mock_creds2.token = "token_2"
        mock_creds2.refresh_token = "refresh_2"

        # First call with creds1
        result1 = services_module.get_gmail_service(mock_creds1)
        # Second call with different creds
        result2 = services_module.get_gmail_service(mock_creds2)

        # Build should be called twice
        assert mock_build.call_count == 2
        # Different services returned
        assert result1 == mock_service1
        assert result2 == mock_service2


class TestGetCalendarService:
    """Tests for get_calendar_service function."""

    @patch("gmail_mcp.utils.services.build")
    def test_creates_calendar_service(self, mock_build):
        """Test that calendar service is created."""
        import gmail_mcp.utils.services as services_module

        # Reset cache
        services_module._calendar_service = None
        services_module._credentials_hash = None

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"

        result = services_module.get_calendar_service(mock_creds)

        mock_build.assert_called_once_with("calendar", "v3", credentials=mock_creds)
        assert result == mock_service

    @patch("gmail_mcp.utils.services.build")
    def test_returns_cached_calendar_service(self, mock_build):
        """Test that cached calendar service is returned."""
        import gmail_mcp.utils.services as services_module

        # Reset cache
        services_module._calendar_service = None
        services_module._credentials_hash = None

        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"

        # First call
        result1 = services_module.get_calendar_service(mock_creds)
        # Second call
        result2 = services_module.get_calendar_service(mock_creds)

        # Build should only be called once
        assert mock_build.call_count == 1
        assert result1 is result2


class TestClearServiceCache:
    """Tests for clear_service_cache function."""

    def test_clears_all_caches(self):
        """Test that clear_service_cache clears all cached services."""
        import gmail_mcp.utils.services as services_module

        # Set some cache values
        services_module._gmail_service = MagicMock()
        services_module._calendar_service = MagicMock()
        services_module._credentials_hash = 12345

        # Clear cache
        services_module.clear_service_cache()

        # All should be None
        assert services_module._gmail_service is None
        assert services_module._calendar_service is None
        assert services_module._credentials_hash is None

    @patch("gmail_mcp.utils.services.build")
    def test_new_service_created_after_clear(self, mock_build):
        """Test that new service is created after cache is cleared."""
        import gmail_mcp.utils.services as services_module

        mock_service1 = MagicMock()
        mock_service2 = MagicMock()
        mock_build.side_effect = [mock_service1, mock_service2]

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"

        # Reset and first call
        services_module._gmail_service = None
        services_module._credentials_hash = None
        result1 = services_module.get_gmail_service(mock_creds)

        # Clear cache
        services_module.clear_service_cache()

        # Second call should create new service
        result2 = services_module.get_gmail_service(mock_creds)

        assert mock_build.call_count == 2
        assert result1 == mock_service1
        assert result2 == mock_service2


class TestCredentialsHash:
    """Tests for credentials hashing."""

    def test_same_credentials_same_hash(self):
        """Test that same credentials produce same hash."""
        from gmail_mcp.utils.services import _get_credentials_hash

        mock_creds = MagicMock()
        mock_creds.token = "token_abc"
        mock_creds.refresh_token = "refresh_xyz"

        hash1 = _get_credentials_hash(mock_creds)
        hash2 = _get_credentials_hash(mock_creds)

        assert hash1 == hash2

    def test_different_tokens_different_hash(self):
        """Test that different tokens produce different hash."""
        from gmail_mcp.utils.services import _get_credentials_hash

        mock_creds1 = MagicMock()
        mock_creds1.token = "token_1"
        mock_creds1.refresh_token = "refresh_1"

        mock_creds2 = MagicMock()
        mock_creds2.token = "token_2"
        mock_creds2.refresh_token = "refresh_2"

        hash1 = _get_credentials_hash(mock_creds1)
        hash2 = _get_credentials_hash(mock_creds2)

        assert hash1 != hash2
