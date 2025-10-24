"""Tests for Notion API client (Feature 1.4)."""

import pytest
import httpx
from src.notion_api import NotionClient
from src.exceptions import (
    NotionAuthenticationError,
    NotionAccessError,
    NotionRateLimitError,
    NotionServerError
)

# Add src/ to sys.path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

class TestClientInitialization:
    """Test NotionClient initialization."""
    
    def test_client_initializes_with_token(self):
        """Test that client initializes with API token."""
        client = NotionClient(api_token="ntn_test_token")
        
        assert client.api_token == "ntn_test_token"
        assert client.base_url == "https://api.notion.com/v1"
    
    def test_client_uses_default_api_version(self):
        """Test that client uses default API version."""
        client = NotionClient(api_token="ntn_test")
        
        assert client.api_version == "2022-06-28"
    
    def test_client_accepts_custom_api_version(self):
        """Test that client accepts custom API version."""
        client = NotionClient(api_token="ntn_test", api_version="2023-01-01")
        
        assert client.api_version == "2023-01-01"
    
    def test_headers_include_authorization(self):
        """Test that headers include Bearer token."""
        client = NotionClient(api_token="ntn_test_token_123")
        headers = client._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ntn_test_token_123"
        assert headers["Authorization"].startswith("Bearer ")
    
    def test_headers_include_notion_version(self):
        """Test that headers include Notion-Version."""
        client = NotionClient(api_token="ntn_test", api_version="2022-06-28")
        headers = client._get_headers()
        
        assert "Notion-Version" in headers
        assert headers["Notion-Version"] == "2022-06-28"
    
    def test_headers_include_content_type(self):
        """Test that headers include Content-Type."""
        client = NotionClient(api_token="ntn_test")
        headers = client._get_headers()
        
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
class TestGetBlockChildren:
    """Test get_block_children method."""
    
    async def test_successful_request_returns_data(self, httpx_mock):
        """Test that successful request returns JSON data."""
        # Mock successful API response
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_block_id/children?page_size=100",
            json={
                "object": "list",
                "results": [
                    {"type": "paragraph", "id": "block1"},
                    {"type": "heading_1", "id": "block2"}
                ],
                "has_more": False,
                "next_cursor": None
            }
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            data = await client.get_block_children("test_block_id")
        
        assert data["object"] == "list"
        assert len(data["results"]) == 2
        assert data["has_more"] is False
    
    async def test_401_raises_authentication_error(self, httpx_mock):
        """Test that 401 status raises NotionAuthenticationError."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            status_code=401
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            with pytest.raises(NotionAuthenticationError) as exc_info:
                await client.get_block_children("test_id")
            
            assert exc_info.value.status_code == 401
    
    async def test_403_raises_access_error(self, httpx_mock):
        """Test that 403 status raises NotionAccessError."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            status_code=403
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            with pytest.raises(NotionAccessError) as exc_info:
                await client.get_block_children("test_id")
            
            assert exc_info.value.status_code == 403
    
    async def test_404_raises_access_error(self, httpx_mock):
        """Test that 404 status raises NotionAccessError."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            status_code=404
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            with pytest.raises(NotionAccessError) as exc_info:
                await client.get_block_children("test_id")
            
            assert exc_info.value.status_code == 404
    
    async def test_429_raises_rate_limit_error(self, httpx_mock):
        """Test that 429 status raises NotionRateLimitError."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            status_code=429
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            with pytest.raises(NotionRateLimitError) as exc_info:
                await client.get_block_children("test_id")
            
            assert exc_info.value.status_code == 429
    
    async def test_500_raises_server_error(self, httpx_mock):
        """Test that 500+ status raises NotionServerError."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            status_code=503
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            with pytest.raises(NotionServerError) as exc_info:
                await client.get_block_children("test_id")
            
            assert exc_info.value.status_code == 503
    
    async def test_supports_pagination_parameters(self, httpx_mock):
        """Test that pagination parameters are passed correctly."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=50&start_cursor=cursor123",
            json={"object": "list", "results": [], "has_more": False}
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            await client.get_block_children(
                "test_id",
                start_cursor="cursor123",
                page_size=50
            )
        
        # If no exception, request was made correctly


@pytest.mark.asyncio
class TestPagination:
    """Test automatic pagination (get_all_children_block)."""
    
    async def test_single_page_returns_all_results(self, httpx_mock):
        """Test that single page scenario works."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            json={
                "object": "list",
                "results": [{"id": "1"}, {"id": "2"}],
                "has_more": False,
                "next_cursor": None
            }
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            results = await client.get_all_block_children("test_id")
        
        assert len(results) == 2
        assert results[0]["id"] == "1"
    
    async def test_multiple_pages_combined(self, httpx_mock):
        """Test that multiple pages are combined correctly."""
        # First page
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            json={
                "results": [{"id": "1"}, {"id": "2"}],
                "has_more": True,
                "next_cursor": "cursor_page2"
            }
        )
        
        # Second page
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100&start_cursor=cursor_page2",
            json={
                "results": [{"id": "3"}, {"id": "4"}],
                "has_more": True,
                "next_cursor": "cursor_page3"
            }
        )
        
        # Third page (final)
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100&start_cursor=cursor_page3",
            json={
                "results": [{"id": "5"}],
                "has_more": False,
                "next_cursor": None
            }
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            results = await client.get_all_block_children("test_id")
        
        # Should have combined all 3 pages
        assert len(results) == 5
        assert results[0]["id"] == "1"
        assert results[4]["id"] == "5"
    
    async def test_empty_results_returns_empty_list(self, httpx_mock):
        """Test that empty page returns empty list."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            json={
                "results": [],
                "has_more": False,
                "next_cursor": None
            }
        )
        
        async with NotionClient(api_token="ntn_test") as client:
            results = await client.get_all_block_children("test_id")
        
        assert results == []


@pytest.mark.asyncio
class TestContextManager:
    """Test async context manager support."""
    
    async def test_context_manager_closes_client(self, httpx_mock):
        """Test that context manager closes client on exit."""
        httpx_mock.add_response(
            url="https://api.notion.com/v1/blocks/test_id/children?page_size=100",
            json={"results": [], "has_more": False}
        )
        
        client = NotionClient(api_token="ntn_test")
        
        async with client as c:
            # Client should be usable
            await c.get_block_children("test_id")
        
        # After exiting, client should be closed
        assert client.client.is_closed
    
    async def test_can_manually_close_client(self):
        """Test that client can be manually closed."""
        client = NotionClient(api_token="ntn_test")
        
        await client.close()
        
        assert client.client.is_closed