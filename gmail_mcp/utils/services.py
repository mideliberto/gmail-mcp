"""
Service Caching Module

This module provides cached instances of Gmail and Calendar services to avoid
recreating service objects on every API call.
"""

from typing import Optional
from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

from gmail_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Cached service instances
_gmail_service: Optional[Resource] = None
_calendar_service: Optional[Resource] = None
_credentials_hash: Optional[int] = None


def _get_credentials_hash(credentials: Credentials) -> int:
    """
    Get a hash of the credentials token for cache invalidation.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        int: A hash of the credentials token.
    """
    return hash((credentials.token, credentials.refresh_token))


def get_gmail_service(credentials: Credentials) -> Resource:
    """
    Get a cached Gmail API service instance.

    The service is cached and reused across calls. If the credentials change
    (different token), a new service is created.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        Resource: The Gmail API service instance.
    """
    global _gmail_service, _credentials_hash

    cred_hash = _get_credentials_hash(credentials)
    if _gmail_service is None or _credentials_hash != cred_hash:
        logger.debug("Creating new Gmail service instance")
        _gmail_service = build("gmail", "v1", credentials=credentials)
        _credentials_hash = cred_hash

    return _gmail_service


def get_calendar_service(credentials: Credentials) -> Resource:
    """
    Get a cached Calendar API service instance.

    The service is cached and reused across calls. If the credentials change
    (different token), a new service is created.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        Resource: The Calendar API service instance.
    """
    global _calendar_service, _credentials_hash

    cred_hash = _get_credentials_hash(credentials)
    if _calendar_service is None or _credentials_hash != cred_hash:
        logger.debug("Creating new Calendar service instance")
        _calendar_service = build("calendar", "v3", credentials=credentials)
        _credentials_hash = cred_hash

    return _calendar_service


def clear_service_cache() -> None:
    """
    Clear all cached service instances.

    This should be called when logging out or when credentials are invalidated.
    """
    global _gmail_service, _calendar_service, _credentials_hash
    _gmail_service = None
    _calendar_service = None
    _credentials_hash = None
    logger.debug("Cleared service cache")
