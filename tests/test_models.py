"""Tests for Notion URL validation and parsing (Feature 1.2)."""

import pytest
from pydantic import ValidationError
from src.models import NotionPagesRequest

# Add src/ to sys.path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

class TestURLValidation:
    """Test URL format validation."""
    
    def test_valid_url_with_hyphens(self):
        """Test URL with hyphenated UUID is valid."""
        url = "https://www.notion.so/Page-Title-243d7db3-8544-80bc-a2b6-f823a7f0ad82"
        request = NotionPagesRequest(url=url)
        
        assert request.url == url
        assert request.block_id is not None
    
    def test_valid_url_without_hyphens(self):
        """Test URL with non-hyphenated UUID is valid."""
        url = "https://www.notion.so/Central-Limit-Theorem-<you-page-id>"
        request = NotionPagesRequest(url=url)
        
        assert request.url == url
        assert request.block_id is not None
    
    def test_valid_url_without_www(self):
        """Test URL without 'www' subdomain is valid."""
        url = "https://notion.so/Page-<you-page-id>"
        request = NotionPagesRequest(url=url)
        
        assert request.url == url
    
    def test_empty_url_raises_error(self):
        """Test that empty URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            NotionPagesRequest(url="")
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_whitespace_url_raises_error(self):
        """Test that whitespace-only URL raises error."""
        with pytest.raises(ValidationError):
            NotionPagesRequest(url="   ")
    
    def test_invalid_domain_raises_error(self):
        """Test that non-Notion URL raises error."""
        with pytest.raises(ValidationError) as exc_info:
            NotionPagesRequest(url="https://google.com/page-<you-page-id>")
        
        assert "notion" in str(exc_info.value).lower()
    
    def test_notion_url_without_uuid_raises_error(self):
        """Test that Notion URL without UUID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            NotionPagesRequest(url="https://www.notion.so/Invalid-Page")
        
        assert "page id" in str(exc_info.value).lower()
    
    def test_url_with_invalid_uuid_format_raises_error(self):
        """Test that URL with malformed UUID raises error."""
        with pytest.raises(ValidationError):
            NotionPagesRequest(url="https://www.notion.so/Page-xyz123")


class TestBlockIDExtraction:
    """Test block_id extraction from URL."""
    
    def test_extracts_hyphenated_uuid(self):
        """Test extraction of UUID with hyphens."""
        url = "https://www.notion.so/Page-243d7db3-8544-80bc-a2b6-f823a7f0ad82"
        request = NotionPagesRequest(url=url)
        
        # Should extract and normalize (remove hyphens)
        assert request.block_id == "<you-page-id>"
        assert "-" not in request.block_id
    
    def test_extracts_non_hyphenated_uuid(self):
        """Test extraction of UUID without hyphens."""
        url = "https://www.notion.so/Page-<you-page-id>"
        request = NotionPagesRequest(url=url)
        
        assert request.block_id == "<you-page-id>"
    
    def test_normalizes_uuid_removes_hyphens(self):
        """Test that hyphens are removed from block_id."""
        url = "https://www.notion.so/Page-243d7db3-8544-80bc-a2b6-f823a7f0ad82"
        request = NotionPagesRequest(url=url)
        
        # Original UUID has hyphens, but block_id should not
        assert "-" not in request.block_id
        assert len(request.block_id) == 32  # UUID without hyphens is 32 chars
    
    def test_block_id_is_lowercase(self):
        """Test that block_id is lowercase (UUIDs should be lowercase)."""
        url = "https://www.notion.so/Page-<you-page-id>"
        request = NotionPagesRequest(url=url)
        
        assert request.block_id.islower()


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_url_with_query_parameters(self):
        """Test URL with query parameters is handled."""
        url = "https://www.notion.so/Page-<you-page-id>?v=123"
        request = NotionPagesRequest(url=url)
        
        # Should still extract UUID correctly
        assert request.block_id == "<you-page-id>"
    
    def test_url_with_hash_fragment(self):
        """Test URL with hash fragment is handled."""
        url = "https://www.notion.so/Page-<you-page-id>#section"
        request = NotionPagesRequest(url=url)
        
        assert request.block_id == "<you-page-id>"