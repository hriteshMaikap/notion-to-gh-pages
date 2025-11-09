"""Complete test for all Notion models."""

import json
from src.notion.models import (
    Annotations, RichText, TextContent, EquationContent,
    ParagraphBlock, HeadingBlock, CodeBlock, ImageBlock,
    EquationBlock, DividerBlock, NotionBlock, BlocksResponse
)
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

def test_annotations():
    """Test annotations model."""
    ann = Annotations(bold=True, italic=True)
    assert ann.bold == True
    assert ann.strikethrough == False  # Default
    print("✓ Annotations work")


def test_rich_text():
    """Test rich text parsing."""
    data = {
        "type": "text",
        "text": {
            "content": "Hello World",
            "link": None
        },
        "annotations": {
            "bold": True,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        },
        "plain_text": "Hello World",
        "href": None
    }
    
    rt = RichText(**data)
    assert rt.type == "text"
    assert rt.text.content == "Hello World"
    assert rt.annotations.bold == True
    print("✓ RichText works")


def test_inline_equation():
    """Test inline equation in rich text."""
    data = {
        "type": "equation",
        "equation": {
            "expression": "E = mc^2"
        },
        "annotations": {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        },
        "plain_text": "E = mc^2",
        "href": None
    }
    
    rt = RichText(**data)
    assert rt.type == "equation"
    assert rt.equation.expression == "E = mc^2"
    print("✓ Inline equation works")


def test_paragraph_block():
    """Test paragraph block."""
    data = {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": "Test", "link": None},
                "annotations": {
                    "bold": False, "italic": False, "strikethrough": False,
                    "underline": False, "code": False, "color": "default"
                },
                "plain_text": "Test",
                "href": None
            }
        ],
        "color": "default"
    }
    
    para = ParagraphBlock(**data)
    assert len(para.rich_text) == 1
    assert para.rich_text[0].plain_text == "Test"
    print("✓ ParagraphBlock works")


def test_block_level_equation():
    """Test block-level equation (no rich_text)."""
    data = {
        "expression": "\\bar{X} = \\frac{1}{n} \\sum_{i=1}^{n} X_i"
    }
    
    eq = EquationBlock(**data)
    assert "\\bar{X}" in eq.expression
    print("✓ EquationBlock works")


def test_image_block():
    """Test image block."""
    data = {
        "type": "file",
        "file": {
            "url": "https://example.com/image.png",
            "expiry_time": "2025-11-09T14:22:27.700Z"
        },
        "caption": []
    }
    
    img = ImageBlock(**data)
    assert img.type == "file"
    assert img.file.url == "https://example.com/image.png"
    print("✓ ImageBlock works")


def test_divider_block():
    """Test divider block (empty)."""
    div = DividerBlock()
    print("✓ DividerBlock works")


def test_complete_block():
    """Test complete NotionBlock."""
    data = {
        "object": "block",
        "id": "123",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": "Hello", "link": None},
                    "annotations": {
                        "bold": False, "italic": False, "strikethrough": False,
                        "underline": False, "code": False, "color": "default"
                    },
                    "plain_text": "Hello",
                    "href": None
                }
            ],
            "color": "default"
        },
        "has_children": False,
        "archived": False,
        "in_trash": False
    }
    
    block = NotionBlock(**data)
    assert block.type == "paragraph"
    assert block.paragraph.rich_text[0].plain_text == "Hello"
    print("✓ NotionBlock works")


def test_parse_real_json():
    """Test parsing your actual content1.json."""
    with open('src/content1.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    response = BlocksResponse(**data)
    
    print(f"\n✓ Parsed {len(response.results)} blocks from content1.json")
    
    # Check types
    types = {}
    for block in response.results:
        types[block.type] = types.get(block.type, 0) + 1
    
    print("\nBlock types found:")
    for block_type, count in sorted(types.items()):
        print(f"  {block_type}: {count}")
    
    # Test accessing specific blocks
    first_para = next((b for b in response.results if b.type == "paragraph"), None)
    if first_para and first_para.paragraph:
        print(f"\nFirst paragraph text: {first_para.paragraph.rich_text[0].plain_text[:50]}...")
    
    first_eq = next((b for b in response.results if b.type == "equation"), None)
    if first_eq and first_eq.equation:
        print(f"First equation: {first_eq.equation.expression[:50]}...")


if __name__ == "__main__":
    test_annotations()
    test_rich_text()
    test_inline_equation()
    test_paragraph_block()
    test_block_level_equation()
    test_image_block()
    test_divider_block()
    test_complete_block()
    test_parse_real_json()
    
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED!")
    print("="*50)