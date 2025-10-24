"""Tests for configuration management (Feature 1.1)."""

import pytest
from pydantic import ValidationError
from src.config import Settings

# Add src/ to sys.path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


class TestSettingsValidation:
    """Test Settings class validation."""
    
    def test_valid_token_loads_successfully(self):
        """Test that valid token format is accepted."""
        settings = Settings(
            NOTION_API_TOKEN="ntn_123456789012345678901234567890",
            API_VERSION="2022-06-28"
        )
        
        assert settings.NOTION_API_TOKEN.startswith("ntn_")
        assert settings.API_VERSION == "2022-06-28"
    
    def test_empty_token_raises_error(self):
        """Test that empty token raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(NOTION_API_TOKEN="")
        
        # Check error message contains our custom message
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_whitespace_token_raises_error(self):
        """Test that whitespace-only token raises error."""
        with pytest.raises(ValidationError):
            Settings(NOTION_API_TOKEN="   ")
    
    def test_invalid_token_prefix_raises_error(self):
        """Test that token without 'ntn_' prefix raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(NOTION_API_TOKEN="abc_123456789012345678901234567890")
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_token_stripped_of_whitespace(self):
        """Test that token is stripped of leading/trailing whitespace."""
        settings = Settings(
            NOTION_API_TOKEN="  ntn_123456789012345678901234567890  "
        )
        
        # Should be stripped
        assert settings.NOTION_API_TOKEN == "ntn_123456789012345678901234567890"
        assert not settings.NOTION_API_TOKEN.startswith(" ")
        assert not settings.NOTION_API_TOKEN.endswith(" ")


class TestSettingsDefaults:
    """Test Settings class default values."""
    
    def test_optional_fields_have_defaults(self):
        """Test that optional fields use default values."""
        settings = Settings(
            NOTION_API_TOKEN="ntn_123456789012345678901234567890",
            _env_file=None  # Don't load from .env file
        )
        
        # Check defaults
        assert settings.NOTION_BLOCK_ID is None
        assert settings.API_VERSION == "2022-06-28"
        assert settings.ENVIRONMENT == "development"
    
    def test_optional_fields_can_be_overridden(self):
        """Test that optional fields can be set."""
        settings = Settings(
            NOTION_API_TOKEN="ntn_123456789012345678901234567890",
            NOTION_BLOCK_ID="abc123",
            ENVIRONMENT="production"
        )
        
        assert settings.NOTION_BLOCK_ID == "abc123"
        assert settings.ENVIRONMENT == "production"


class TestSettingsFromEnv:
    """Test Settings loads from environment variables."""
    
    def test_loads_from_dotenv_file(self, monkeypatch, tmp_path):
        """Test that Settings loads from .env file."""
        # Create temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "NOTION_API_TOKEN=ntn_test_token_123456789012\n"
            "ENVIRONMENT=testing\n"
        )
        
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        
        # Load settings
        settings = Settings(_env_file=str(env_file))
        
        assert settings.NOTION_API_TOKEN == "ntn_test_token_123456789012"
        assert settings.ENVIRONMENT == "testing"