"""
Tests for auth/token_manager.py - Token management and security
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestSingletonPattern:
    """Tests for TokenManager singleton pattern."""

    def test_get_token_manager_returns_same_instance(self):
        """Test that get_token_manager returns the same instance."""
        from gmail_mcp.auth.token_manager import get_token_manager, _instance

        # Reset singleton for clean test
        import gmail_mcp.auth.token_manager as tm_module
        tm_module._instance = None

        tm1 = get_token_manager()
        tm2 = get_token_manager()

        assert tm1 is tm2

    def test_singleton_persists_state(self):
        """Test that singleton maintains state across calls."""
        from gmail_mcp.auth.token_manager import get_token_manager

        import gmail_mcp.auth.token_manager as tm_module
        tm_module._instance = None

        tm1 = get_token_manager()
        tm1.store_state("test_state_123")

        tm2 = get_token_manager()
        assert tm2.verify_state("test_state_123")


class TestPBKDF2KeyDerivation:
    """Tests for PBKDF2 encryption key derivation."""

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_key_derivation_with_encryption_key(self, mock_get_config):
        """Test that PBKDF2 derives a proper key from encryption key."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "/tmp/test_tokens.json",
            "token_encryption_key": "my_secret_key",
        }

        tm = TokenManager()

        # Key should be derived and not None
        assert tm.encryption_key is not None
        # Key should be 44 bytes (32 bytes base64 encoded)
        assert len(tm.encryption_key) == 44
        # Fernet should be initialized
        assert tm.fernet is not None

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_no_encryption_without_key(self, mock_get_config):
        """Test that encryption is disabled without key."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "/tmp/test_tokens.json",
            "token_encryption_key": "",
        }

        tm = TokenManager()

        assert tm.encryption_key is None
        assert tm.fernet is None

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_same_key_produces_same_derived_key(self, mock_get_config):
        """Test that same input key produces same derived key."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "/tmp/test_tokens.json",
            "token_encryption_key": "consistent_key",
        }

        tm1 = TokenManager()
        tm2 = TokenManager()

        assert tm1.encryption_key == tm2.encryption_key

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_different_keys_produce_different_derived_keys(self, mock_get_config):
        """Test that different input keys produce different derived keys."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "/tmp/test_tokens.json",
            "token_encryption_key": "key_one",
        }
        tm1 = TokenManager()

        mock_get_config.return_value = {
            "token_storage_path": "/tmp/test_tokens.json",
            "token_encryption_key": "key_two",
        }
        tm2 = TokenManager()

        assert tm1.encryption_key != tm2.encryption_key


class TestTokenStorage:
    """Tests for token storage and retrieval."""

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_store_and_retrieve_token_unencrypted(self, mock_get_config, tmp_path):
        """Test storing and retrieving token without encryption."""
        from gmail_mcp.auth.token_manager import TokenManager

        token_file = tmp_path / "tokens.json"
        mock_get_config.return_value = {
            "token_storage_path": str(token_file),
            "token_encryption_key": "",
        }

        tm = TokenManager()

        # Create mock credentials
        mock_creds = Mock()
        mock_creds.token = "access_token_123"
        mock_creds.refresh_token = "refresh_token_456"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "client_id"
        mock_creds.client_secret = "client_secret"
        mock_creds.scopes = ["scope1", "scope2"]
        mock_creds.expiry = datetime.now() + timedelta(hours=1)

        # Store token
        tm.store_token(mock_creds)

        # Verify file exists
        assert token_file.exists()

        # Verify content is valid JSON (unencrypted)
        with open(token_file) as f:
            data = json.load(f)
        assert data["token"] == "access_token_123"
        assert data["refresh_token"] == "refresh_token_456"

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_store_and_retrieve_token_encrypted(self, mock_get_config, tmp_path):
        """Test storing and retrieving token with encryption."""
        from gmail_mcp.auth.token_manager import TokenManager

        token_file = tmp_path / "tokens.json"
        mock_get_config.return_value = {
            "token_storage_path": str(token_file),
            "token_encryption_key": "my_encryption_key",
        }

        tm = TokenManager()

        # Create mock credentials
        mock_creds = Mock()
        mock_creds.token = "access_token_123"
        mock_creds.refresh_token = "refresh_token_456"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "client_id"
        mock_creds.client_secret = "client_secret"
        mock_creds.scopes = ["scope1", "scope2"]
        mock_creds.expiry = datetime.now() + timedelta(hours=1)

        # Store token
        tm.store_token(mock_creds)

        # Verify file exists
        assert token_file.exists()

        # Verify content is NOT valid JSON (encrypted)
        with open(token_file) as f:
            content = f.read()
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)

        # But we can retrieve it
        retrieved = tm.get_token()
        assert retrieved is not None
        assert retrieved.token == "access_token_123"
        assert retrieved.refresh_token == "refresh_token_456"

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_get_token_returns_none_if_not_exists(self, mock_get_config, tmp_path):
        """Test get_token returns None if file doesn't exist."""
        from gmail_mcp.auth.token_manager import TokenManager

        token_file = tmp_path / "nonexistent.json"
        mock_get_config.return_value = {
            "token_storage_path": str(token_file),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        result = tm.get_token()

        assert result is None

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_clear_token(self, mock_get_config, tmp_path):
        """Test clearing stored token."""
        from gmail_mcp.auth.token_manager import TokenManager

        token_file = tmp_path / "tokens.json"
        token_file.write_text('{"test": "data"}')

        mock_get_config.return_value = {
            "token_storage_path": str(token_file),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        assert token_file.exists()

        tm.clear_token()
        assert not token_file.exists()

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_tokens_exist(self, mock_get_config, tmp_path):
        """Test tokens_exist method."""
        from gmail_mcp.auth.token_manager import TokenManager

        token_file = tmp_path / "tokens.json"
        mock_get_config.return_value = {
            "token_storage_path": str(token_file),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        assert not tm.tokens_exist()

        token_file.write_text('{"test": "data"}')
        assert tm.tokens_exist()


class TestOAuthStateVerification:
    """Tests for OAuth state parameter verification."""

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_store_and_verify_state(self, mock_get_config, tmp_path):
        """Test storing and verifying OAuth state."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": str(tmp_path / "tokens.json"),
            "token_encryption_key": "",
        }

        tm = TokenManager()

        # Store state
        tm.store_state("state_abc123")

        # Verify correct state
        assert tm.verify_state("state_abc123") is True

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_verify_wrong_state_fails(self, mock_get_config, tmp_path):
        """Test verifying wrong state fails."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": str(tmp_path / "tokens.json"),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        tm.store_state("correct_state")

        assert tm.verify_state("wrong_state") is False

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_verify_state_without_stored_state_fails(self, mock_get_config, tmp_path):
        """Test verifying state without stored state fails."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": str(tmp_path / "tokens.json"),
            "token_encryption_key": "",
        }

        tm = TokenManager()

        assert tm.verify_state("any_state") is False

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_verify_state_clears_after_success(self, mock_get_config, tmp_path):
        """Test that state is cleared after successful verification (one-time use)."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": str(tmp_path / "tokens.json"),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        tm.store_state("one_time_state")

        # First verification succeeds
        assert tm.verify_state("one_time_state") is True

        # Second verification fails (state was cleared)
        assert tm.verify_state("one_time_state") is False

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_verify_empty_state_fails(self, mock_get_config, tmp_path):
        """Test verifying empty state fails."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": str(tmp_path / "tokens.json"),
            "token_encryption_key": "",
        }

        tm = TokenManager()
        tm.store_state("valid_state")

        assert tm.verify_state("") is False
        assert tm.verify_state(None) is False


class TestTokenPath:
    """Tests for token storage path configuration."""

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_default_token_path(self, mock_get_config):
        """Test default token path is ~/.gmail-mcp/tokens.json."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "",
            "token_encryption_key": "",
        }

        tm = TokenManager()

        expected = Path.home() / ".gmail-mcp" / "tokens.json"
        assert tm.token_path == expected

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_custom_token_path(self, mock_get_config):
        """Test custom token path is respected."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "/custom/path/tokens.json",
            "token_encryption_key": "",
        }

        tm = TokenManager()

        assert tm.token_path == Path("/custom/path/tokens.json")

    @patch("gmail_mcp.auth.token_manager.get_config")
    def test_tilde_expansion(self, mock_get_config):
        """Test tilde is expanded in token path."""
        from gmail_mcp.auth.token_manager import TokenManager

        mock_get_config.return_value = {
            "token_storage_path": "~/my_tokens/tokens.json",
            "token_encryption_key": "",
        }

        tm = TokenManager()

        assert "~" not in str(tm.token_path)
        assert str(Path.home()) in str(tm.token_path)
