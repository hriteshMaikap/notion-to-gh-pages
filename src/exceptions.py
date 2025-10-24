"""Custom Notion API Errors"""

class NotionAPIError(Exception):
    """Base Exception for Notion API Errors"""
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotionAuthenticationError(NotionAPIError):
    pass
    # def __init__(self, message: str = "Invalid Notion API Token"):
    #     super().__init__(message, status_code=401)
    # Sample Customization

class NotionAccessError(NotionAPIError):
    pass

class NotionRateLimitError(NotionAPIError):
    pass

class NotionServerError(NotionAPIError):
    pass