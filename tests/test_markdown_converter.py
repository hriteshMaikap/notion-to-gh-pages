"""Test the Markdown converter."""

from src.notion.parser import BlockParser
from src.notion.converter import MarkdownConverter
from src.notion.models import (
    NotionBlock, ParagraphBlock, HeadingBlock, CodeBlock,
    RichText, TextContent, Annotations, EquationBlock, ImageBlock
)


def test_simple_paragraph():
    """Test converting simple paragraph."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="Hello world", link=None),
                    annotations=Annotations(),
                    plain_text="Hello world"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "Hello world\n\n"
    print("✓ Simple paragraph works")


def test_paragraph_with_bold():
    """Test paragraph with bold text."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="Bold text", link=None),
                    annotations=Annotations(bold=True),
                    plain_text="Bold text"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "**Bold text**\n\n"
    print("✓ Bold text works")


def test_mixed_annotations():
    """Test text with multiple annotations."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="Important", link=None),
                    annotations=Annotations(bold=True, italic=True),
                    plain_text="Important"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "***Important***\n\n"
    print("✓ Bold + italic works")


def test_inline_code():
    """Test inline code annotation."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="print('hello')", link=None),
                    annotations=Annotations(code=True),
                    plain_text="print('hello')"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "`print('hello')`\n\n"
    print("✓ Inline code works")


def test_link():
    """Test link conversion."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(
                        content="Click here",
                        link={"url": "https://example.com"}
                    ),
                    annotations=Annotations(),
                    plain_text="Click here"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "[Click here](https://example.com)\n\n"
    print("✓ Link works")


def test_bold_link():
    """Test bold link."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="paragraph",
        paragraph=ParagraphBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(
                        content="Click",
                        link={"url": "https://example.com"}
                    ),
                    annotations=Annotations(bold=True),
                    plain_text="Click"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "**[Click](https://example.com)**\n\n"
    print("✓ Bold link works")


def test_heading():
    """Test heading conversion."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="heading_1",
        heading_1=HeadingBlock(
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="Title", link=None),
                    annotations=Annotations(),
                    plain_text="Title"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert md == "# Title\n\n"
    print("✓ Heading works")


def test_code_block():
    """Test code block with language."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="code",
        code=CodeBlock(
            language="python",
            rich_text=[
                RichText(
                    type="text",
                    text=TextContent(content="print('hello')", link=None),
                    annotations=Annotations(),
                    plain_text="print('hello')"
                )
            ]
        )
    )
    
    md = converter.convert_block(block)
    assert "```python" in md
    assert "print('hello')" in md
    print("✓ Code block works")


def test_block_equation():
    """Test block-level equation."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="equation",
        equation=EquationBlock(expression="E = mc^2")
    )
    
    md = converter.convert_block(block)
    assert md == "$$\nE = mc^2\n$$\n\n"
    print("✓ Block equation works")


def test_divider():
    """Test divider."""
    converter = MarkdownConverter()
    
    block = NotionBlock(
        object="block",
        id="123",
        type="divider",
        divider={}
    )
    
    md = converter.convert_block(block)
    assert md == "---\n\n"
    print("✓ Divider works")


def test_real_content():
    """Test with real content1.json."""
    parser = BlockParser.from_file('src/content1.json')
    converter = MarkdownConverter()
    
    blocks = parser.get_processable_blocks()
    
    print(f"\n✓ Converting {len(blocks)} blocks...")
    
    markdown = converter.convert_blocks(blocks)
    
    # Basic checks
    assert "# " in markdown  # Has heading
    assert "```python" in markdown  # Has code
    assert "$$" in markdown  # Has equation
    assert "![" in markdown  # Has image
    
    print(f"✓ Generated {len(markdown)} characters of Markdown")
    
    # Save to file
    converter.convert_to_file(blocks, "test_output.md")
    print("✓ Saved to test_output.md")
    
    # Show preview
    lines = markdown.split('\n')
    print("\nFirst 20 lines of output:")
    print("=" * 60)
    for line in lines[:20]:
        print(line)
    print("=" * 60)


if __name__ == "__main__":
    print("Testing Markdown Converter...\n")
    
    test_simple_paragraph()
    test_paragraph_with_bold()
    test_mixed_annotations()
    test_inline_code()
    test_link()
    test_bold_link()
    test_heading()
    test_code_block()
    test_block_equation()
    test_divider()
    test_real_content()
    
    print("\n" + "=" * 60)
    print("✅ ALL CONVERTER TESTS PASSED!")
    print("=" * 60)
    print("\nCheck test_output.md to see the full conversion!")