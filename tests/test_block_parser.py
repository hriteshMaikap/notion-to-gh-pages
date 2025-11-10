"""Test the block parser."""

from src.notion.parser import BlockParser


def test_parser_from_file():
    """Test loading parser from file."""
    parser = BlockParser.from_file(filepath='src/content1.json')
    
    assert len(parser.blocks) == 66
    print(f"✓ Loaded {len(parser.blocks)} blocks from file")


def test_get_processable_blocks():
    """Test filtering logic."""
    parser = BlockParser.from_file('src/content1.json')
    
    # Get all processable blocks
    processable = parser.get_processable_blocks()
    
    # Should filter out archived, trashed, children, unsupported
    assert all(not b.archived for b in processable)
    assert all(not b.in_trash for b in processable)
    assert all(not b.has_children for b in processable)
    assert all(b.type in parser.SUPPORTED_TYPES for b in processable)
    
    print(f"✓ Filtered to {len(processable)} processable blocks")


def test_get_blocks_by_type():
    """Test getting blocks by type."""
    parser = BlockParser.from_file('src/content1.json')
    
    paragraphs = parser.get_blocks_by_type("paragraph")
    headings = parser.get_blocks_by_type("heading_1")
    equations = parser.get_blocks_by_type("equation")
    
    print(f"✓ Found {len(paragraphs)} paragraphs")
    print(f"✓ Found {len(headings)} heading_1s")
    print(f"✓ Found {len(equations)} equations")
    
    assert len(paragraphs) > 0
    assert len(headings) > 0


def test_text_vs_standalone():
    """Test separating text blocks from standalone blocks."""
    parser = BlockParser.from_file('src/content1.json')
    
    text_blocks = parser.get_text_blocks()
    standalone_blocks = parser.get_standalone_blocks()
    
    print(f"✓ {len(text_blocks)} text blocks (have rich_text)")
    print(f"✓ {len(standalone_blocks)} standalone blocks (no rich_text)")
    
    # Verify text blocks have rich_text
    for block in text_blocks:
        content = parser.get_block_content(block)
        if content and hasattr(content, 'rich_text'):
            assert isinstance(content.rich_text, list)


def test_get_block_content():
    """Test extracting block content."""
    parser = BlockParser.from_file('src/content1.json')
    
    # Get first paragraph
    para_block = next(b for b in parser.blocks if b.type == "paragraph")
    content = parser.get_block_content(para_block)
    
    assert content is not None
    assert hasattr(content, 'rich_text')
    assert len(content.rich_text) > 0
    
    first_text = content.rich_text[0].plain_text
    print(f"✓ First paragraph text: {first_text[:50]}...")
    
    # Get first equation (block-level)
    eq_block = next(b for b in parser.blocks if b.type == "equation")
    eq_content = parser.get_block_content(eq_block)
    
    assert eq_content is not None
    assert hasattr(eq_content, 'expression')
    print(f"✓ First equation: {eq_content.expression[:50]}...")


def test_summary():
    """Test summary generation."""
    parser = BlockParser.from_file('src/content1.json')
    
    summary = parser.get_summary()
    
    assert summary['total_blocks'] == 66
    assert 'type_counts' in summary
    assert 'processable_blocks' in summary
    
    print("\n" + "=" * 60)
    parser.print_summary()


def test_rich_text_access():
    """Test accessing rich text with annotations."""
    parser = BlockParser.from_file('src/content1.json')
    
    # Find a paragraph with bold text
    found = False
    for block in parser.get_blocks_by_type("paragraph"):
        content = parser.get_block_content(block)
        if content:
            for rt in content.rich_text:
                if rt.annotations.bold:
                    print(f"\n✓ Found bold text: \"{rt.plain_text}\"")
                    print(f"  Annotations: bold={rt.annotations.bold}, "
                          f"italic={rt.annotations.italic}, "
                          f"code={rt.annotations.code}")
                    found = True
                    break
        if found:
            break
    
    if not found:
        print("\n✓ No bold text found in content")


def test_code_block_language():
    """Test accessing code block language."""
    parser = BlockParser.from_file('src/content1.json')
    
    code_blocks = parser.get_blocks_by_type("code")
    
    if code_blocks:
        for i, block in enumerate(code_blocks[:3]):  # First 3
            content = parser.get_block_content(block)
            print(f"\n✓ Code block {i+1}:")
            print(f"  Language: {content.language}")
            if content.rich_text:
                code_text = content.rich_text[0].plain_text[:50]
                print(f"  Code: {code_text}...")


def test_image_block():
    """Test accessing image block."""
    parser = BlockParser.from_file('src/content1.json')
    
    image_blocks = parser.get_blocks_by_type("image")
    
    if image_blocks:
        block = image_blocks[0]
        content = parser.get_block_content(block)
        
        print(f"\n✓ Image block:")
        print(f"  Type: {content.type}")
        if content.file:
            print(f"  URL: {content.file.url[:50]}...")
            print(f"  Expires: {content.file.expiry_time}")


if __name__ == "__main__":
    print("Testing Block Parser...\n")
    
    test_parser_from_file()
    test_get_processable_blocks()
    test_get_blocks_by_type()
    test_text_vs_standalone()
    test_get_block_content()
    test_rich_text_access()
    test_code_block_language()
    test_image_block()
    test_summary()
    
    print("\n" + "=" * 60)
    print("✅ ALL PARSER TESTS PASSED!")
    print("=" * 60)