"""
Pydantic models for Notion API blocks and rich text.

Structure (from smallest to largest):
1. Annotations - text styling (bold, italic, etc.)
2. RichText - a single formatted text unit
3. BlockContent - type-specific block data
4. NotionBlock - complete block with metadata
"""

from typing import Literal, Optional, Any, List
from pydantic import BaseModel, Field

# Level 1- Annotation (Samllest)
class Annotations(BaseModel):
    """
    {
        "bold": true,
        "italic": false,
        "strikethrough": false,
        "underline": false,
        "code": false,
        "color": "default"
    }
    """
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    code: bool = False
    color: str = "default"

# Level 2: Rich Text Content Types

class TextContent(BaseModel):
    "Content for rich_text with type = 'text'"
    content: str
    link: Optional[dict] = None

class EquationContent(BaseModel):
    "Content for rich_text with type = 'equation'"
    expression: str

class MentionContent(BaseModel):
    "Content for rich_text with type = 'mention'"
    type: str  # "page", "user", "database", etc.

# Level 3: Rich Text 
class RichText(BaseModel):
    """
    {
        "type": "text",
        "text": {"content": "Hello", "link": null},
        "annotations": {"bold": true, ...},
        "plain_text": "Hello",
        "href": null
    }
    """
    type: Literal["text","equation","mention"]
    text: Optional[TextContent] = None
    equation: Optional[EquationContent] = None
    mention: Optional[MentionContent] = None
    annotations: Annotations
    plain_text: str
    href: Optional[str] = None

# LEVEL 4: Block-Specific Content (WITH rich_text)
class ParagraphBlock(BaseModel):
    """Paragraph block content."""
    rich_text: List[RichText]
    color: str = "default"


class HeadingBlock(BaseModel):
    """Heading block content (h1, h2, h3)."""
    rich_text: List[RichText]
    color: str = "default"
    is_toggleable: bool = False


class BulletedListItemBlock(BaseModel):
    """Bulleted list item content."""
    rich_text: List[RichText]
    color: str = "default"


class NumberedListItemBlock(BaseModel):
    """Numbered list item content."""
    rich_text: List[RichText]
    color: str = "default"


class QuoteBlock(BaseModel):
    """Quote block content."""
    rich_text: List[RichText]
    color: str = "default"


class CodeBlock(BaseModel):
    """Code block content."""
    rich_text: List[RichText]
    language: str = "plain text"
    caption: List[RichText] = Field(default_factory=list)

# LEVEL 5: Block-Specific Content (NO rich_text)

class EquationBlock(BaseModel):
    """Block-level equation (LaTeX)."""
    expression: str


class DividerBlock(BaseModel):
    """Horizontal divider - no content."""
    pass


class TableOfContentsBlock(BaseModel):
    """Table of contents block."""
    color: str = "default"


class ImageBlock(BaseModel):
    """Image block content."""
    
    class FileInfo(BaseModel):
        """File information for hosted images."""
        url: str
        expiry_time: Optional[str] = None
    
    class ExternalInfo(BaseModel):
        """External image URL."""
        url: str
    
    type: Literal["file", "external"]
    file: Optional[FileInfo] = None
    external: Optional[ExternalInfo] = None
    caption: List[RichText] = Field(default_factory=list)

# Main Notion Block
class NotionBlock(BaseModel):
    """
    A complete Notion block.
    
    Structure:
    {
        "object": "block",
        "id": "...",
        "type": "paragraph",
        "paragraph": { ... },  # Type-specific content
        "has_children": false,
        "archived": false,
        "in_trash": false
    }
    """
    
    object: Literal["block"]
    id: str
    type: str
    
    parent: Optional[dict] = None
    
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None
    
    created_by: Optional[dict] = None
    last_edited_by: Optional[dict] = None
    
    has_children: bool = False
    archived: bool = False
    in_trash: bool = False
    
    # ===== Blocks WITH rich_text =====
    paragraph: Optional[ParagraphBlock] = None
    heading_1: Optional[HeadingBlock] = None
    heading_2: Optional[HeadingBlock] = None
    heading_3: Optional[HeadingBlock] = None
    bulleted_list_item: Optional[BulletedListItemBlock] = None
    numbered_list_item: Optional[NumberedListItemBlock] = None
    quote: Optional[QuoteBlock] = None
    code: Optional[CodeBlock] = None
    
    # ===== Blocks WITHOUT rich_text =====
    equation: Optional[EquationBlock] = None
    divider: Optional[DividerBlock] = None
    table_of_contents: Optional[TableOfContentsBlock] = None
    image: Optional[ImageBlock] = None
    
    # Allow extra fields for block types I don't handle yet
    class Config:
        extra = "allow"


# LEVEL 7: API Response

class BlocksResponse(BaseModel):
    """Response from Notion blocks API."""
    object: Literal["list"]
    results: List[NotionBlock]
    has_more: bool
    next_cursor: Optional[str] = None
    type: str = "block"
    
    class Config:
        extra = "allow" 
