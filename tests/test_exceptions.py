"""Tests for custom exception hierarchy (Feature 1.3)."""

import pytest
from src.exceptions import (
    NotionAPIError,
    NotionAuthenticationError,
    NotionAccessError,
    NotionRateLimitError,
    NotionServerError
)

# Add src/ to sys.path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

class TestExceptionHierarchy:
    """Test exception inheritance and hierarchy."""
    
    def test_specific_exceptions_inherit_from_base(self):
        """Test that specific exceptions inherit from NotionAPIError."""
        assert issubclass(NotionAuthenticationError, NotionAPIError)
        assert issubclass(NotionAccessError, NotionAPIError)
        assert issubclass(NotionRateLimitError, NotionAPIError)
        assert issubclass(NotionServerError, NotionAPIError)
    
    def test_base_exception_inherits_from_exception(self):
        """Test that NotionAPIError inherits from Exception."""
        assert issubclass(NotionAPIError, Exception)
    
    def test_can_catch_specific_as_base_type(self):
        """Test that specific exceptions can be caught as base type."""
        try:
            raise NotionAuthenticationError("Test error", status_code=401)
        except NotionAPIError as e:
            # Should catch as NotionAPIError
            assert isinstance(e, NotionAuthenticationError)
            assert isinstance(e, NotionAPIError)


class TestNotionAPIError:
    """Test base NotionAPIError exception."""
    
    def test_stores_message(self):
        """Test that exception stores error message."""
        error = NotionAPIError("Test message")
        
        assert error.message == "Test message"
        assert str(error) == "Test message"
    
    def test_stores_status_code(self):
        """Test that exception stores HTTP status code."""
        error = NotionAPIError("Error", status_code=500)
        
        assert error.status_code == 500
    
    def test_status_code_optional(self):
        """Test that status_code is optional."""
        error = NotionAPIError("Error")
        
        assert error.status_code is None
    
    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(NotionAPIError) as exc_info:
            raise NotionAPIError("Test", status_code=400)
        
        assert exc_info.value.message == "Test"
        assert exc_info.value.status_code == 400


class TestSpecificExceptions:
    """Test specific exception types."""
    
    def test_authentication_error(self):
        """Test NotionAuthenticationError."""
        error = NotionAuthenticationError("Bad token", status_code=401)
        
        assert error.message == "Bad token"
        assert error.status_code == 401
        assert isinstance(error, NotionAPIError)
    
    def test_access_error(self):
        """Test NotionAccessError."""
        error = NotionAccessError("No permission", status_code=403)
        
        assert error.message == "No permission"
        assert error.status_code == 403
    
    def test_rate_limit_error(self):
        """Test NotionRateLimitError."""
        error = NotionRateLimitError("Too many requests", status_code=429)
        
        assert error.message == "Too many requests"
        assert error.status_code == 429
    
    def test_server_error(self):
        """Test NotionServerError."""
        error = NotionServerError("Server down", status_code=503)
        
        assert error.message == "Server down"
        assert error.status_code == 503


class TestExceptionUsage:
    """Test practical exception usage scenarios."""
    
    def test_catch_specific_exception(self):
        """Test catching a specific exception type."""
        with pytest.raises(NotionAuthenticationError):
            raise NotionAuthenticationError("Invalid token")
    
    def test_catch_any_notion_error(self):
        """Test catching any Notion error with base type."""
        try:
            raise NotionRateLimitError("Rate limited", status_code=429)
        except NotionAPIError as e:
            # Should be caught as NotionAPIError
            assert e.status_code == 429
    
    def test_different_exceptions_distinguishable(self):
        """Test that different exception types are distinguishable."""
        auth_error = NotionAuthenticationError("Auth")
        access_error = NotionAccessError("Access")
        
        assert type(auth_error) != type(access_error)
        assert isinstance(auth_error, NotionAuthenticationError)
        assert isinstance(access_error, NotionAccessError)