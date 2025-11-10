"""
Parse and filter Notion blocks from API response.

This module converts raw JSON from Notion API into typed,
validated Pydantic models and filters blocks for processing.
"""

from typing import List, Dict, Optional, Set
from pathlib import Path
import json

from src.notion.models import BlocksResponse, NotionBlock


class BlockParser:
    """
    Parse and filter Notion blocks.
    
    Usage:
        parser = BlockParser.from_file('content.json')
        blocks = parser.get_processable_blocks()
        
        for block in blocks:
            if block.type == "paragraph":
                print(block.paragraph.rich_text[0].plain_text)
    """
    
    # Block types we support in pilot version
    SUPPORTED_TYPES: Set[str] = {
        # Text-based blocks (have rich_text)
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "quote",
        "bulleted_list_item",
        "numbered_list_item",
        "code",
        "to_do",
        "toggle",
        "callout",
        
        # Standalone blocks (no rich_text)
        "equation",
        "image",
        "divider",
        "table_of_contents",
        "bookmark",
        "embed",
        "file",
    }
    
    def __init__(self, response: BlocksResponse):
        """
        Initialize parser with validated response.
        
        Args:
            response: Validated BlocksResponse from Pydantic
        """
        self.response = response
        self.blocks = response.results
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BlockParser':
        """
        Create parser from raw JSON dict.
        
        Args:
            data: Raw JSON response from Notion API
            
        Returns:
            BlockParser instance
            
        Raises:
            ValidationError: If JSON doesn't match expected structure
        """
        response = BlocksResponse(**data)
        return cls(response)
    
    @classmethod
    def from_file(cls, filepath: str) -> 'BlockParser':
        """
        Create parser from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            BlockParser instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_all_blocks(self) -> List[NotionBlock]:
        """Get all blocks (no filtering)."""
        return self.blocks
    
    def get_processable_blocks(
        self,
        skip_archived: bool = True,
        skip_trashed: bool = True,
        skip_children: bool = True,
        only_supported: bool = True,
    ) -> List[NotionBlock]:
        """
        Get blocks ready for processing with filters applied.
        
        Args:
            skip_archived: Skip archived blocks
            skip_trashed: Skip blocks in trash
            skip_children: Skip blocks with children (for now)
            only_supported: Only return supported block types
            
        Returns:
            List of filtered blocks
        """
        filtered = []
        
        for block in self.blocks:
            # Filter: Skip archived
            if skip_archived and block.archived:
                continue
            
            # Filter: Skip trashed
            if skip_trashed and block.in_trash:
                continue
            
            # Filter: Skip blocks with children (pilot version)
            if skip_children and block.has_children:
                # TODO: In future, fetch children recursively
                continue
            
            # Filter: Only supported types
            if only_supported and block.type not in self.SUPPORTED_TYPES:
                continue
            
            filtered.append(block)
        
        return filtered
    
    def get_blocks_by_type(self, block_type: str) -> List[NotionBlock]:
        """
        Get all blocks of a specific type.
        
        Args:
            block_type: Block type (e.g., "paragraph", "heading_1")
            
        Returns:
            List of blocks matching the type
        """
        return [b for b in self.blocks if b.type == block_type]
    
    def get_text_blocks(self) -> List[NotionBlock]:
        """
        Get blocks that contain rich_text arrays.
        
        Returns:
            List of text-based blocks
        """
        text_types = {
            "paragraph", "heading_1", "heading_2", "heading_3",
            "quote", "bulleted_list_item", "numbered_list_item",
            "code", "to_do", "toggle", "callout"
        }
        return [b for b in self.blocks if b.type in text_types]
    
    def get_standalone_blocks(self) -> List[NotionBlock]:
        """
        Get blocks that don't have rich_text (equation, image, etc.).
        
        Returns:
            List of standalone blocks
        """
        standalone_types = {
            "equation", "image", "divider", "table_of_contents",
            "bookmark", "embed", "file"
        }
        return [b for b in self.blocks if b.type in standalone_types]
    
    def get_block_content(self, block: NotionBlock) -> Optional[any]:
        """
        Extract type-specific content from a block.
        
        Args:
            block: NotionBlock instance
            
        Returns:
            Type-specific content object (e.g., ParagraphBlock, EquationBlock)
            or None if not found
            
        Example:
            content = parser.get_block_content(block)
            if block.type == "paragraph":
                for rt in content.rich_text:
                    print(rt.plain_text)
        """
        return getattr(block, block.type, None)
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get summary statistics of blocks.
        
        Returns:
            Dictionary with statistics
        """
        type_counts = {}
        for block in self.blocks:
            type_counts[block.type] = type_counts.get(block.type, 0) + 1
        
        processable = self.get_processable_blocks()
        
        return {
            "total_blocks": len(self.blocks),
            "archived": sum(1 for b in self.blocks if b.archived),
            "in_trash": sum(1 for b in self.blocks if b.in_trash),
            "has_children": sum(1 for b in self.blocks if b.has_children),
            "type_counts": type_counts,
            "supported_types": len([b for b in self.blocks if b.type in self.SUPPORTED_TYPES]),
            "processable_blocks": len(processable),
            "text_blocks": len(self.get_text_blocks()),
            "standalone_blocks": len(self.get_standalone_blocks()),
        }
    
    def print_summary(self) -> None:
        """Print formatted summary to console."""
        summary = self.get_summary()
        
        print("=" * 60)
        print("NOTION BLOCKS SUMMARY")
        print("=" * 60)
        print(f"\nTotal blocks: {summary['total_blocks']}")
        print(f"Processable blocks: {summary['processable_blocks']}")
        print(f"  - Text blocks: {summary['text_blocks']}")
        print(f"  - Standalone blocks: {summary['standalone_blocks']}")
        
        print(f"\nFiltered out:")
        print(f"  - Archived: {summary['archived']}")
        print(f"  - In trash: {summary['in_trash']}")
        print(f"  - Has children: {summary['has_children']}")
        print(f"  - Unsupported types: {summary['total_blocks'] - summary['supported_types']}")
        
        print(f"\nBlock type distribution:")
        for block_type, count in sorted(summary['type_counts'].items()):
            supported = "✓" if block_type in self.SUPPORTED_TYPES else "✗"
            print(f"  {supported} {block_type}: {count}")
        
        print("=" * 60)