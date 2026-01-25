"""
Configuration Utility Module

This module provides functions for loading and accessing application configuration.
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

# Default configuration file path
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", "config.yaml")

# Cached configuration
_config_cache: Optional[Dict[str, Any]] = None


def load_yaml_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Returns:
        Dict[str, Any]: Configuration dictionary from YAML file or empty dict if file not found.
    """
    try:
        config_path = Path(CONFIG_FILE_PATH)
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        else:
            logging.warning(f"Configuration file not found: {CONFIG_FILE_PATH}")
            return {}
    except Exception as e:
        logging.error(f"Error loading configuration file: {e}")
        return {}


def get_config() -> Dict[str, Any]:
    """
    Get the application configuration from YAML file and environment variables.
    Environment variables for sensitive data (set in Claude Desktop config) take precedence.

    Configuration is cached after first load for performance.

    Returns:
        Dict[str, Any]: A dictionary containing the application configuration.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    # Load configuration from YAML file
    yaml_config = load_yaml_config()

    # Extract nested values from YAML config
    server_config = yaml_config.get("server", {})
    mcp_config = yaml_config.get("mcp", {})
    google_config = yaml_config.get("google", {})
    gmail_config = yaml_config.get("gmail", {})
    calendar_config = yaml_config.get("calendar", {})
    contacts_config = yaml_config.get("contacts", {})
    drive_config = yaml_config.get("drive", {})
    chat_config = yaml_config.get("chat", {})
    tokens_config = yaml_config.get("tokens", {})
    vault_config = yaml_config.get("vault", {})
    claude_review_config = yaml_config.get("claude_review", {})
    
    # Helper function to safely split strings
    def safe_split(value: Optional[str], delimiter: str = ",") -> List[str]:
        """Split a string safely, returning an empty list if the value is None."""
        if value:
            return value.split(delimiter)
        return []
    
    # Create configuration dictionary with environment variables from Claude Desktop config
    # taking precedence for sensitive data
    config = {
        # Server configuration (from YAML)
        "host": server_config.get("host", "localhost"),
        "port": int(server_config.get("port", 8000)),
        "debug": str(server_config.get("debug", False)).lower() == "true",
        "log_level": server_config.get("log_level", "INFO"),
        
        # MCP configuration (from YAML)
        "mcp_version": mcp_config.get("version", "2025-03-07"),
        "mcp_server_name": mcp_config.get("name", "Gmail MCP"),
        "mcp_server_description": mcp_config.get("description", 
                                               "A Model Context Protocol server for Gmail integration with Claude Desktop"),
        
        # Google OAuth configuration (sensitive data from env vars set in Claude Desktop config, rest from YAML)
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "google_redirect_uri": google_config.get("redirect_uri", "http://localhost:8000/auth/callback"),
        "google_auth_scopes": safe_split(google_config.get("auth_scopes", "")),
        
        # Gmail API configuration (from YAML)
        "gmail_api_scopes": safe_split(gmail_config.get("scopes", "https://www.googleapis.com/auth/gmail.readonly,"
                                           "https://www.googleapis.com/auth/gmail.send,"
                                           "https://www.googleapis.com/auth/gmail.labels,"
                                           "https://www.googleapis.com/auth/gmail.modify")),
        
        # Calendar API configuration (from YAML)
        "calendar_api_enabled": calendar_config.get("enabled", False),
        "calendar_api_scopes": safe_split(calendar_config.get("scopes", "https://www.googleapis.com/auth/calendar.readonly,"
                                                "https://www.googleapis.com/auth/calendar.events")),

        # Contacts API configuration (from YAML)
        "contacts_api_enabled": contacts_config.get("enabled", False),
        "contacts_api_scopes": safe_split(contacts_config.get("scopes", "https://www.googleapis.com/auth/contacts.readonly")),

        # Drive API configuration (from YAML)
        "drive_api_enabled": drive_config.get("enabled", False),
        "drive_api_scopes": safe_split(drive_config.get("scopes", "https://www.googleapis.com/auth/drive,"
                                                "https://www.googleapis.com/auth/drive.labels,"
                                                "https://www.googleapis.com/auth/drive.activity.readonly")),

        # Chat API configuration (from YAML)
        "chat_api_enabled": chat_config.get("enabled", False),
        "chat_api_scopes": safe_split(chat_config.get("scopes", "https://www.googleapis.com/auth/chat.spaces,"
                                                "https://www.googleapis.com/auth/chat.messages,"
                                                "https://www.googleapis.com/auth/chat.memberships")),

        # Token storage configuration (path from YAML, encryption key from env vars)
        "token_storage_path": tokens_config.get("storage_path", "./tokens.json"),
        "token_encryption_key": os.getenv("TOKEN_ENCRYPTION_KEY", ""),

        # Vault integration configuration
        "vault_path": vault_config.get("path") or os.getenv("VAULT_PATH", ""),
        "vault_inbox_folder": vault_config.get("inbox_folder", "0-inbox"),
        "vault_attachment_folder": vault_config.get("attachment_folder", "attachments"),

        # Claude review labels configuration
        "claude_review_labels": claude_review_config.get("labels", []),
    }

    # Cache the config
    _config_cache = config
    return config


def get_config_value(key: str, default: Optional[Any] = None) -> Any:
    """
    Get a specific configuration value.

    Args:
        key (str): The configuration key to retrieve.
        default (Optional[Any], optional): The default value if the key is not found. Defaults to None.

    Returns:
        Any: The configuration value.
    """
    config = get_config()
    return config.get(key, default) 