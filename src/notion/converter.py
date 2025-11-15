"""
Convert Notion blocks to Markdown format. 
Notion Blocks converted to markdown
"""

from typing import List, Optional
from src.notion.models import NotionBlock, RichText, Annotations

class MarkdownConverter:
    """
    The converter handles:
    - Rich text with annotations (bold, italic, code, strikethrough)
    - Links (inline and with annotations)
    - Headings (h1, h2, h3)
    - Lists (bulleted, numbered)
    - Code blocks with syntax highlighting
    - Equations (inline and block-level)
    - Images, dividers, quotes
    """

    def __init__(self):
        pass

    def convert_block(self, block: NotionBlock) -> str:
        """
        Convert a single Notion block to Markdown.
        
        Args:
            block: NotionBlock to convert
            
        Returns:
            Markdown string for this block
        """
        # Dispatch to specific converter based on block type
        converter_method = f"_convert_{block.type}"
        
        if hasattr(self, converter_method):
            return getattr(self, converter_method)(block)
        else:
            # Unsupported block type - return empty or warning
            return f"<!-- Unsupported block type: {block.type} -->\n\n"
        
    
    def convert_blocks(self, blocks: List[NotionBlock]) -> str:
        """
        Convert multiple blocks to Markdown.
        
        Args:
            blocks: List of NotionBlocks
            
        Returns:
            Combined Markdown string
        """
        markdown_parts = []
        
        for block in blocks:
            md = self.convert_block(block)
            if md:  # Skip empty blocks
                markdown_parts.append(md)
        
        return "".join(markdown_parts)
    
    def convert_to_file(self, blocks: List[NotionBlock], filepath: str) -> None:
        """
        Convert blocks and save to Markdown file.
        
        Args:
            blocks: List of NotionBlocks
            filepath: Output file path
        """
        markdown = self.convert_blocks(blocks)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

    # Main Logic to convert Rich Text
    def _convert_rich_text_array(self, rich_texts: List[RichText]) -> str:
        """
        Convert array of RichText objects to Markdown string.
        
        This is the CORE conversion logic. Each rich_text object is:
        1. Extracted for its plain_text
        2. Wrapped in link syntax if it has a link
        3. Wrapped with annotation syntax (bold, italic, etc.)
        4. Combined into final string
        
        Args:
            rich_texts: List of RichText objects
            
        Returns:
            Formatted Markdown string
            
        Example:
            Input: [
                RichText(plain_text="Hello ", annotations=Annotations(bold=False)),
                RichText(plain_text="world", annotations=Annotations(bold=True))
            ]
            Output: "Hello **world**"
        """
        if not rich_texts:
            return ""
        
        markdown_parts = []
        
        for rt in rich_texts:
            # Step 1: Get the base text
            if rt.type == "text":
                text = rt.plain_text
            elif rt.type == "equation":
                # ✅ FIX: Inline equation uses single $
                text = f"${rt.equation.expression}$"
            else:
                text = rt.plain_text
            
            if rt.type == "text" and rt.text and rt.text.link:
                url = rt.text.link.get("url", "")
                text = f"[{text}]({url})"
            elif rt.href:  # Alternative href field
                text = f"[{text}]({rt.href})"
            
            text = self._apply_annotations(text, rt.annotations)
            
            markdown_parts.append(text)
        
        # Step 4: Combine all parts
        return "".join(markdown_parts)
    
    def _apply_annotations(self, text: str, annotations: Annotations) -> str:
        """
        Apply Markdown formatting based on annotations.
        
        Order matters! We apply in this order:
        1. Code (innermost - highest priority)
        2. Bold
        3. Italic
        4. Strikethrough (outermost)
        
        This ensures proper nesting: ~~***`text`***~~
        
        Args:
            text: Plain text to format
            annotations: Annotations object
            
        Returns:
            Formatted text
            
        Example:
            >>> _apply_annotations("text", Annotations(bold=True, italic=True))
            "***text***"
        """
        is_link = text.startswith("[") and "](" in text
        
        if annotations.code and not is_link:
            # Inline code: `text`
            text = f"`{text}`"
        
        if annotations.bold:
            text = f"**{text}**"
        
        if annotations.italic:
            text = f"*{text}*"
        
        if annotations.strikethrough:
            text = f"~~{text}~~"
        
        # We'll use HTML <u> tags
        if annotations.underline:
            text = f"<u>{text}</u>"
        
        return text
    
    # Block Type Converters
    def _convert_paragraph(self, block: NotionBlock) -> str:
        """
        Convert paragraph block.
        
        Format: {text}\n\n
        
        Example:
            This is a paragraph with **bold** text.
            
        """
        content = block.paragraph
        if not content or not content.rich_text:
            return "\n"  # Empty paragraph
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"{text}\n\n"

    def _convert_heading_1(self, block: NotionBlock) -> str:
        """
        Convert heading 1 block.
        
        Format: # {text}\n\n
        """
        content = block.heading_1
        if not content or not content.rich_text:
            return ""
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"# {text}\n\n"
    
    def _convert_heading_2(self, block: NotionBlock) -> str:
        """
        Convert heading 2 block.
        
        Format: ## {text}\n\n
        """
        content = block.heading_2
        if not content or not content.rich_text:
            return ""
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"## {text}\n\n"
    
    def _convert_heading_3(self, block: NotionBlock) -> str:
        """
        Convert heading 3 block.
        
        Format: ### {text}\n\n
        """
        content = block.heading_3
        if not content or not content.rich_text:
            return ""
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"### {text}\n\n"
    
    def _convert_bulleted_list_item(self, block: NotionBlock) -> str:
        """
        Convert bulleted list item.
        
        Format: - {text}\n
        
        Note: No extra newline - lists are continuous
        """
        content = block.bulleted_list_item
        if not content or not content.rich_text:
            return "- \n"
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"- {text}\n"
    
    def _convert_numbered_list_item(self, block: NotionBlock) -> str:
        """
        Convert numbered list item.
        
        Format: 1. {text}\n
        
        Note: Markdown auto-numbers, so we always use "1."
        """
        content = block.numbered_list_item
        if not content or not content.rich_text:
            return "1. \n"
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"1. {text}\n"
    
    def _convert_quote(self, block: NotionBlock) -> str:
        """
        Convert quote block.
        
        Format: > {text}\n\n
        """
        content = block.quote
        if not content or not content.rich_text:
            return ""
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"> {text}\n\n"
    
    def _convert_code(self, block: NotionBlock) -> str:
        """
        Convert code block.
        
        Format:
        ```language
        code here
        ```
        
        Extracts language and code content.
        """
        content = block.code
        if not content:
            return ""
        
        language = content.language or "text"
        
        # Get code content from rich_text
        code = self._convert_rich_text_array(content.rich_text)
        
        # Remove trailing newlines from code
        code = code.rstrip()
        
        return f"```{language}\n{code}\n```\n\n"
    
    def _convert_to_do(self, block: NotionBlock) -> str:
        """
        Convert to-do/checkbox item.
        
        Format: - [ ] {text}\n  or  - [x] {text}\n
        """
        content = block.to_do
        if not content or not content.rich_text:
            return ""
        
        checkbox = "[x]" if content.checked else "[ ]"
        text = self._convert_rich_text_array(content.rich_text)
        return f"- {checkbox} {text}\n"
    
    def _convert_toggle(self, block: NotionBlock) -> str:
        """
        Convert toggle/collapsible block.
        
        Format: <details><summary>{text}</summary></details>
        
        Note: Uses HTML since Markdown doesn't have native toggles
        """
        content = block.toggle
        if not content or not content.rich_text:
            return ""
        
        text = self._convert_rich_text_array(content.rich_text)
        return f"<details>\n<summary>{text}</summary>\n\n</details>\n\n"

    def _convert_equation(self, block: NotionBlock) -> str:
        """
        Convert block-level equation.
        
        ✅ FIX: Use $$ for display math (Kramdown/Jekyll compatible)
        
        Format:
        $$
        expression
        $$
        
        This is different from inline equations ($expr$)
        """
        content = block.equation
        if not content:
            return ""
        
        expression = content.expression
        return f"$$\n{expression}\n$$\n\n"
    
    def _convert_divider(self, block: NotionBlock) -> str:
        """
        Convert divider block.
        
        Format: ---\n\n
        """
        return "---\n\n"
    
    def _convert_image(self, block: NotionBlock) -> str:
        """
        Convert image block.
        
        Format: ![caption](url)
        
        Note: Notion image URLs expire! 
        Images will be downloaded and URLs replaced by deployer.
        """
        content = block.image
        if not content:
            return ""
        
        url = ""
        if content.type == "file" and content.file:
            url = content.file.url
        elif content.type == "external" and content.external:
            url = content.external.url
        
        caption = ""
        if content.caption:
            caption = self._convert_rich_text_array(content.caption)
        
        if not url:
            return ""
        
        # ✅ No warning comment - deployer will handle image download
        return f"![{caption}]({url})\n\n"
    
    def _convert_table_of_contents(self, block: NotionBlock) -> str:
        """
        Convert table of contents.
        
        For now, we'll just add a placeholder.
        TODO: Generate actual TOC from headings
        """
        return "<!-- Table of Contents -->\n\n"
    
    def _convert_bookmark(self, block: NotionBlock) -> str:
        """
        Convert bookmark block.
        
        Format: [caption](url)
        """
        content = block.bookmark
        if not content:
            return ""
        
        url = content.url
        caption = ""
        if content.caption:
            caption = self._convert_rich_text_array(content.caption)
        
        if not caption:
            caption = url
        
        return f"[{caption}]({url})\n\n"
    
    def _convert_embed(self, block: NotionBlock) -> str:
        """
        Convert embed block.
        
        Format: [Embedded content](url)
        
        Note: Markdown doesn't support embeds, so we link
        """
        content = block.embed
        if not content:
            return ""
        
        return f"[Embedded content]({content.url})\n\n"
    
    def _convert_file(self, block: NotionBlock) -> str:
        """
        Convert file attachment.
        
        Format: [Filename](url)
        """
        content = block.file
        if not content:
            return ""
        
        url = ""
        if content.type == "file" and content.file:
            url = content.file.url
        elif content.type == "external" and content.external:
            url = content.external.get("url", "")
        
        caption = ""
        if content.caption:
            caption = self._convert_rich_text_array(content.caption)
        
        if not caption:
            caption = "File attachment"
        
        return f"[{caption}]({url})\n\n"



