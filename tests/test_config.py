"""
Tests for utils/config.py - Configuration loading and caching
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestConfigCaching:
    """Tests for configuration caching."""

    def test_config_is_cached(self):
        """Test that config is cached after first load."""
        import gmail_mcp.utils.config as config_module

        # Reset cache
        config_module._config_cache = None

        with patch.object(config_module, "load_yaml_config", return_value={}) as mock_load:
            # First call loads config
            config1 = config_module.get_config()
            assert mock_load.call_count == 1

            # Second call uses cache
            config2 = config_module.get_config()
            assert mock_load.call_count == 1  # Still 1, not 2

            # Same object returned
            assert config1 is config2

    def test_config_returns_dict(self):
        """Test that get_config returns a dictionary."""
        import gmail_mcp.utils.config as config_module

        config_module._config_cache = None

        with patch.object(config_module, "load_yaml_config", return_value={}):
            config = config_module.get_config()
            assert isinstance(config, dict)

    def test_config_includes_expected_keys(self):
        """Test that config includes expected keys."""
        import gmail_mcp.utils.config as config_module

        config_module._config_cache = None

        with patch.object(config_module, "load_yaml_config", return_value={}):
            config = config_module.get_config()

            # Check for expected keys from the config structure
            expected_keys = [
                "gmail_api_scopes",
                "calendar_api_enabled",
                "calendar_api_scopes",
                "token_storage_path",
                "google_client_id",
            ]
            for key in expected_keys:
                assert key in config, f"Missing expected key: {key}"


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_returns_value_if_exists(self):
        """Test returns value if key exists."""
        import gmail_mcp.utils.config as config_module

        config_module._config_cache = {"test_key": "test_value"}

        result = config_module.get_config_value("test_key")
        assert result == "test_value"

    def test_returns_default_if_not_exists(self):
        """Test returns default if key doesn't exist."""
        import gmail_mcp.utils.config as config_module

        config_module._config_cache = {}

        result = config_module.get_config_value("nonexistent_key", default="default_val")
        assert result == "default_val"

    def test_returns_none_if_no_default(self):
        """Test returns None if key doesn't exist and no default."""
        import gmail_mcp.utils.config as config_module

        config_module._config_cache = {}

        result = config_module.get_config_value("nonexistent_key")
        assert result is None


class TestLoadYamlConfig:
    """Tests for load_yaml_config function."""

    def test_returns_empty_dict_if_file_not_found(self):
        """Test returns empty dict if config file not found."""
        from gmail_mcp.utils.config import load_yaml_config

        with patch("gmail_mcp.utils.config.CONFIG_FILE_PATH", "/nonexistent/config.yaml"):
            result = load_yaml_config()
            assert result == {}

    def test_loads_yaml_file(self, tmp_path):
        """Test loads YAML config file."""
        from gmail_mcp.utils.config import load_yaml_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("server:\n  host: localhost\n  port: 8080\n")

        with patch("gmail_mcp.utils.config.CONFIG_FILE_PATH", str(config_file)):
            result = load_yaml_config()
            assert result["server"]["host"] == "localhost"
            assert result["server"]["port"] == 8080


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_env_vars_override_yaml(self):
        """Test that environment variables override YAML config."""
        import gmail_mcp.utils.config as config_module
        import os

        config_module._config_cache = None

        with patch.object(config_module, "load_yaml_config", return_value={}):
            with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "env_client_id"}):
                config = config_module.get_config()
                assert config["google_client_id"] == "env_client_id"
