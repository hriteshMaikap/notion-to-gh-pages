import httpx
from src.config import settings
from src.exceptions import (
    NotionAPIError,
    NotionAuthenticationError,
    NotionAccessError,
    NotionRateLimitError,
    NotionServerError
)

class NotionClient:
    """Client that interacts with Notion API"""

    def __init__(self, api_token: str, api_version: str = "2022-06-28"):
        """
        Initialize Notion API client.
        
        Args:
            api_token: Notion integration API token
            api_version: Notion API version to use
        """

        self.api_token = api_token
        self.api_version = api_version
        self.base_url = "https://api.notion.com/v1"

        self.client = httpx.AsyncClient(headers=self._get_headers(), timeout=30.0)  # Reuses TCP connections (connection pooling)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json"
        }
    
    async def close(self):
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_block_children(self, block_id: str, start_cursor: str | None = None, page_size = 100) -> dict:
        """
        Fetch the children blocks of the page

        Args:
            block_id
            start_cursor
            page_size

        Returns
            results
            has_more
            next_cursor

        Raises 
            Custom NotionAPIErrors
        """

        # Step 1: Build the URL
        url = f"{self.base_url}/blocks/{block_id}/children"

        # Step 2: Build Query Params
        params = {
            "page_size":page_size
        }
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        # Step 3: Make request
        response = await self.client.get(url, params=params)

        # Step 4: Handle Requests
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 403:
            raise NotionAccessError(
                "Access Denied to this Notion Page.",
                status_code=403
            )
    
        elif response.status_code == 401:
            raise NotionAuthenticationError(
                "Invalid Notion API token",
                status_code=401
            )

        elif response.status_code == 404:
            raise NotionAccessError(  # ✅ Use NotionAccessError
                "Notion page not found or integration not granted access",
                status_code=404
            )
        
        elif response.status_code == 429:
            raise NotionRateLimitError(
                "Notion API rate limit exceeded. Please try again later.",
                status_code=429
            )
        
        elif response.status_code >= 500:
            raise NotionServerError(
                f"Notion API server error: {response.status_code}",
                status_code=response.status_code
            )
        
        else:
            raise NotionAPIError(
                f"Notion API error: {response.status_code} - {response.text}",
                status_code=response.status_code
            )
        
    async def get_all_block_children(self, block_id: str) -> list: 
        """Handle Paginated Responses"""
    
        all_res = []
        cursor = None

        while True:
            data = await self.get_block_children(
                block_id=block_id,
                start_cursor=cursor
            )

            all_res.extend(data['results']) #extend merges the list, while append will append it as a single list

            if not data['has_more']:
                break

            cursor = data['next_cursor']
        
        return all_res
