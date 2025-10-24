from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    NOTION_API_TOKEN: str = Field(description="API Key for the Notion Integration")
    NOTION_BLOCK_ID: str | None = None # user will provide URL then extract the Block ID
    API_VERSION: str = "2022-06-28" # sensible default
    ENVIRONMENT: str = "development"

    @field_validator('NOTION_API_TOKEN')
    @classmethod
    def validate_notion_api_key(cls, value: str) -> str:
        # Strip whitespace FIRST
        value = value.strip()
        
        if not value:
            raise ValueError("NOTION API TOKEN cannot be empty!")
        
        if not value.startswith("ntn_"):
            raise ValueError("NOTION API TOKEN is Invalid!")
    
        return value

settings = Settings()