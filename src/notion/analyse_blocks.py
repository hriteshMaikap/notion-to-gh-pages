import json
from collections import defaultdict, Counter

def analyse_json(filepath: str):

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    blocks = data.get('results', [])

    print("=====BLOCK ANALYSIS======")
    print("Total Blocks: ", len(blocks))

    block_types = Counter(block['type'] for block in blocks)
    print("=====Block Type Distribution=====")
    for block_type, count in sorted(block_types.items()):
        print(f" {block_type}: {count}")

    # Analyse the blocks that have rich text
    has_rich_text = []
    no_rich_text = []

    for block in blocks: 
        block_type = block['type']
        type_obj = block.get(block_type,{})

        if 'rich_text' in type_obj:
            has_rich_text.append(block_type)
        else:
            no_rich_text.append(block_type)

    print("Blocks with NO Rich Text: ")
    for bt in sorted(set(no_rich_text)):
        count = no_rich_text.count(bt)
        print(f" {bt}: {count}")

    print("Blocks with Rich Text: ")
    for bt in sorted(set(has_rich_text)):
        count = has_rich_text.count(bt)
        print(f" {bt}: {count}")

    print("\n=== Rich Text Object Types ===")
    
    rich_text_types = []
    
    for block in blocks:
        block_type = block['type']
        type_obj = block.get(block_type, {})
        rich_texts = type_obj.get('rich_text', [])
        
        for rt in rich_texts:
            rich_text_types.append(rt.get('type', 'unknown'))
    
    rt_counts = Counter(rich_text_types)
    for rt_type, count in sorted(rt_counts.items()):
        print(f"  {rt_type}: {count}")

if __name__ == "__main__":
    analyse_json('C:\\Users\\hrite\\OneDrive\\Documents\\notion-to-gh-pages\\src\\content1.json')
