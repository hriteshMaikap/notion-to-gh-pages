from pydantic import BaseModel, field_validator, model_validator
from typing import ClassVar
import re
        

class NotionPagesRequest(BaseModel):
    """Model for validating URL given by user"""
    UUID_PATTERN: ClassVar[str] = r"[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12}"
    
    url: str
    block_id: str | None = None #optional

    
    @field_validator('url')
    @classmethod
    def validate_url(cls, value: str) -> str:

        if not value or value.strip()=="":
            raise ValueError("URL cannot be empty")
        
        if not (value.startswith("https://www.notion.so/")
                or value.startswith("https://notion.so/")):
            raise ValueError("URL must be a valid Notion URL")
        
        if not re.search(cls.UUID_PATTERN, value):
            raise ValueError("URL must contain Notion Page ID")
        
        return value

    # Field Validators cannot set other fields directly, so we use model validator    
    @model_validator(mode='after')
    def extract_block_id(self) -> 'NotionPagesRequest':
        """Exctract block id from validated URL"""
        # Since already validated no need to raise error again, this block will only extract
        match = re.search(self.UUID_PATTERN, self.url)
        if match:
            block_id = match.group()
            block_id = block_id.replace("-","").lower()  # normalize: remove hyphens and lowercase

            self.block_id = block_id
        
        return self
        