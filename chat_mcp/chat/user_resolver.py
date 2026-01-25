"""
User Resolver Module

Resolves Chat API user IDs to display names and emails using the People API
Directory endpoint (for Google Workspace domains).
"""

import threading
from typing import Any, Dict, Optional

from googleapiclient.discovery import build

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger("chat_mcp.user_resolver")

# Thread-safe singleton instance
_resolver_instance: Optional["UserResolver"] = None
_resolver_lock = threading.Lock()


class UserResolver:
    """
    Resolves Chat API user IDs to display names and emails.

    Uses the People API listDirectoryPeople endpoint to fetch all domain users
    and builds a cache for fast lookups.
    """

    def __init__(self) -> None:
        """Initialize the user resolver."""
        self._cache: Dict[str, Dict[str, str]] = {}
        self._cache_lock = threading.Lock()
        self._cache_populated = False
        self._service = None
        self._service_lock = threading.Lock()
        self._last_error: Optional[str] = None

    def _get_service(self) -> Any:
        """
        Get the People API service.

        Returns:
            Any: The People API service.
        """
        with self._service_lock:
            if self._service is None:
                credentials = get_credentials()
                if not credentials:
                    raise RuntimeError("Not authenticated with Google")
                self._service = build("people", "v1", credentials=credentials)
            return self._service

    def _populate_cache(self) -> None:
        """
        Populate the cache with all directory users.

        Fetches all users from the Google Workspace directory using the
        People API listDirectoryPeople endpoint.
        """
        with self._cache_lock:
            if self._cache_populated:
                return

            try:
                service = self._get_service()
                page_token = None

                while True:
                    # List directory people (Workspace users)
                    request_params = {
                        "readMask": "names,emailAddresses,metadata",
                        "sources": ["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"],
                        "pageSize": 100,
                    }
                    if page_token:
                        request_params["pageToken"] = page_token

                    result = service.people().listDirectoryPeople(
                        **request_params
                    ).execute()

                    for person in result.get("people", []):
                        self._process_person(person)

                    page_token = result.get("nextPageToken")
                    if not page_token:
                        break

                self._cache_populated = True
                logger.info(f"User cache populated with {len(self._cache)} users")

            except Exception as e:
                self._last_error = str(e)
                logger.warning(f"Failed to populate user cache: {e}")
                # Don't mark as populated so we retry next time

    def _process_person(self, person: Dict[str, Any]) -> None:
        """
        Process a person resource and add to cache.

        Args:
            person: The person resource from People API.
        """
        # Get the user ID from metadata
        metadata = person.get("metadata", {})
        sources = metadata.get("sources", [])

        user_id = None
        for source in sources:
            if source.get("type") == "PROFILE":
                user_id = source.get("id")
                break

        if not user_id:
            return

        # Get display name
        names = person.get("names", [])
        display_name = ""
        if names:
            display_name = names[0].get("displayName", "")

        # Get email
        emails = person.get("emailAddresses", [])
        email = ""
        if emails:
            email = emails[0].get("value", "")

        # Store in cache with the full user resource name format
        self._cache[f"users/{user_id}"] = {
            "displayName": display_name,
            "email": email,
            "id": user_id,
        }

    def resolve(self, user_name: str) -> Dict[str, str]:
        """
        Resolve a user ID to display name and email.

        Args:
            user_name: The user resource name (e.g., "users/123456").

        Returns:
            Dict with displayName, email, and id. Returns empty strings if not found.
        """
        # Populate cache on first use
        if not self._cache_populated:
            self._populate_cache()

        with self._cache_lock:
            if user_name in self._cache:
                return self._cache[user_name]

        # Not found - return empty
        return {
            "displayName": "",
            "email": "",
            "id": user_name.replace("users/", "") if user_name.startswith("users/") else user_name,
        }

    def resolve_many(self, user_names: list) -> Dict[str, Dict[str, str]]:
        """
        Resolve multiple user IDs at once.

        Args:
            user_names: List of user resource names.

        Returns:
            Dict mapping user_name -> resolved info.
        """
        # Populate cache on first use
        if not self._cache_populated:
            self._populate_cache()

        results = {}
        with self._cache_lock:
            for user_name in user_names:
                if user_name in self._cache:
                    results[user_name] = self._cache[user_name]
                else:
                    results[user_name] = {
                        "displayName": "",
                        "email": "",
                        "id": user_name.replace("users/", "") if user_name.startswith("users/") else user_name,
                    }
        return results

    def clear_cache(self) -> None:
        """Clear the user cache to force refresh on next lookup."""
        with self._cache_lock:
            self._cache.clear()
            self._cache_populated = False
            logger.info("User cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "populated": self._cache_populated,
                "user_count": len(self._cache),
                "last_error": self._last_error,
            }


def get_user_resolver() -> UserResolver:
    """
    Get the singleton UserResolver instance (thread-safe).

    Returns:
        UserResolver: The singleton instance.
    """
    global _resolver_instance
    with _resolver_lock:
        if _resolver_instance is None:
            _resolver_instance = UserResolver()
        return _resolver_instance
