"""
Token Manager Module

This module provides functionality for securely storing and managing OAuth tokens.
"""

import os
import json
import base64
from typing import Any, Optional
from pathlib import Path
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from google.oauth2.credentials import Credentials

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.config import get_config

# Get logger
logger = get_logger(__name__)

# Singleton instance
_instance: Optional["TokenManager"] = None


def get_token_manager() -> "TokenManager":
    """
    Get the singleton TokenManager instance.

    Returns:
        TokenManager: The singleton TokenManager instance.
    """
    global _instance
    if _instance is None:
        _instance = TokenManager()
    return _instance


class TokenManager:
    """
    Class for securely storing and managing OAuth tokens.
    """

    def __init__(self) -> None:
        """Initialize the TokenManager."""
        self.config = get_config()

        # Single token location: configured path or default ~/.gmail-mcp/tokens.json
        token_path = self.config.get("token_storage_path", "")
        if not token_path:
            token_path = os.path.join(os.path.expanduser("~"), ".gmail-mcp", "tokens.json")
        elif token_path.startswith("~"):
            token_path = os.path.expanduser(token_path)

        self.token_path = Path(token_path)

        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key) if self.encryption_key else None
        self._state: Optional[str] = None

    def _get_encryption_key(self) -> Optional[bytes]:
        """
        Get the encryption key from the environment and derive a proper key using PBKDF2.

        Returns:
            Optional[bytes]: The derived encryption key, or None if not set.
        """
        key = self.config.get("token_encryption_key", "")

        if not key:
            logger.warning("No encryption key found, tokens will not be encrypted")
            return None

        # Derive a proper 32-byte key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"gmail-mcp-token-salt",  # Static salt is fine for this use case
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key.encode()))

    def store_token(self, credentials: Any) -> None:
        """
        Store the OAuth token securely.

        Args:
            credentials (Any): The OAuth credentials to store. This can be any type of credentials
                               that has the required attributes.
        """
        # Convert the credentials to a dictionary
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

        # Convert the dictionary to JSON
        token_json = json.dumps(token_data)

        # Encrypt the JSON if encryption is enabled
        if self.fernet:
            token_json = self.fernet.encrypt(token_json.encode()).decode()

        # Create the token directory if it doesn't exist
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the token to the file
        with open(self.token_path, "w") as f:
            f.write(token_json)

        logger.info(f"Stored token at {self.token_path}")

    def get_token(self) -> Optional[Credentials]:
        """
        Get the stored OAuth token.

        Returns:
            Optional[Credentials]: The OAuth credentials, or None if not found.
        """
        if not self.token_path.exists():
            logger.warning(f"No token found at {self.token_path}")
            return None

        try:
            # Read the token from the file
            with open(self.token_path, "r") as f:
                token_json = f.read()

            # Decrypt the JSON if encryption is enabled
            if self.fernet:
                token_json = self.fernet.decrypt(token_json.encode()).decode()

            # Parse the JSON
            token_data = json.loads(token_json)

            # Convert the expiry string to a datetime
            if token_data.get("expiry"):
                token_data["expiry"] = datetime.fromisoformat(token_data["expiry"])

            # Create the credentials
            credentials = Credentials(
                token=token_data["token"],
                refresh_token=token_data["refresh_token"],
                token_uri=token_data["token_uri"],
                client_id=token_data["client_id"],
                client_secret=token_data["client_secret"],
                scopes=token_data["scopes"],
            )

            # Set the expiry
            if token_data.get("expiry"):
                credentials.expiry = token_data["expiry"]

            return credentials
        except Exception as e:
            logger.error(f"Failed to get token from {self.token_path}: {e}")
            return None

    def clear_token(self) -> None:
        """Clear the stored OAuth token."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
                logger.info(f"Cleared token at {self.token_path}")
            except Exception as e:
                logger.error(f"Failed to clear token at {self.token_path}: {e}")

    def store_state(self, state: str) -> None:
        """
        Store the OAuth state parameter.

        Args:
            state (str): The state parameter.
        """
        self._state = state
        logger.info("Stored OAuth state parameter")

    def verify_state(self, state: str) -> bool:
        """
        Verify the OAuth state parameter.

        Args:
            state (str): The state parameter to verify.

        Returns:
            bool: True if the state parameter is valid, False otherwise.
        """
        if not self._state or not state or self._state != state:
            logger.warning("Invalid OAuth state parameter")
            return False

        # Clear state after successful verification (one-time use)
        self._state = None
        logger.info("Verified OAuth state parameter")
        return True

    def tokens_exist(self) -> bool:
        """
        Check if the token file exists.

        Returns:
            bool: True if the token file exists, False otherwise.
        """
        return self.token_path.exists()
