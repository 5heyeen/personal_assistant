#!/usr/bin/env python3
"""Analyze the Notion data and extract key information."""

import json
from collections import defaultdict

def extract_text_from_rich_text(rich_text_array):
    """Extract plain text from Notion rich_text array."""
    return ''.join([item.get('plain_text', '') for item in rich_text_array])

def analyze_blocks(blocks, depth=0):
    """Recursively analyze blocks and extract structure."""
    structure = []

    for block in blocks.get('results', []):
        block_type = block.get('type')

        if block_type == 'heading_1':
            text = extract_text_from_rich_text(block['heading_1']['rich_text'])
            structure.append(('h1', text, depth))
        elif block_type == 'heading_2':
            text = extract_text_from_rich_text(block['heading_2']['rich_text'])
            structure.append(('h2', text, depth))
        elif block_type == 'heading_3':
            text = extract_text_from_rich_text(block['heading_3']['rich_text'])
            structure.append(('h3', text, depth))
        elif block_type == 'paragraph':
            text = extract_text_from_rich_text(block['paragraph']['rich_text'])
            if text.strip():
                structure.append(('p', text, depth))
        elif block_type == 'bulleted_list_item':
            text = extract_text_from_rich_text(block['bulleted_list_item']['rich_text'])
            structure.append(('bullet', text, depth))
        elif block_type == 'child_database':
            structure.append(('database', block.get('id'), depth))

    return structure

def find_page_mentions(blocks):
    """Find all page mentions in blocks."""
    mentions = []

    for block in blocks.get('results', []):
        block_type = block.get('type')

        if block_type in ['paragraph', 'bulleted_list_item', 'numbered_list_item']:
            rich_text = block.get(block_type, {}).get('rich_text', [])

            for item in rich_text:
                if item.get('type') == 'mention':
                    mention_type = item['mention'].get('type')
                    if mention_type == 'page':
                        page_id = item['mention']['page'].get('id')
                        mentions.append({
                            'page_id': page_id,
                            'context': extract_text_from_rich_text(rich_text)
                        })
                    elif mention_type == 'database':
                        db_id = item['mention']['database'].get('id')
                        mentions.append({
                            'database_id': db_id,
                            'context': extract_text_from_rich_text(rich_text)
                        })

    return mentions

def main():
    with open('notion_data.json', 'r') as f:
        data = json.load(f)

    print("="*80)
    print("PERSONAL ASSISTANT CONFIGURATION SUMMARY")
    print("="*80)

    # Analyze structure
    structure = analyze_blocks(data['blocks'])

    current_section = None
    sections = defaultdict(list)

    for item_type, text, depth in structure:
        if item_type in ['h1', 'h2']:
            current_section = text
            sections[current_section] = []
        elif current_section:
            sections[current_section].append((item_type, text))

    # Print organized sections
    for section_name, items in sections.items():
        print(f"\n## {section_name}")
        print("-" * 80)
        for item_type, text in items:
            if item_type == 'bullet':
                print(f"  • {text}")
            elif item_type == 'p':
                print(f"  {text}")
            elif item_type == 'database':
                print(f"  [DATABASE: {text}]")

    # Find all mentions
    print("\n" + "="*80)
    print("REFERENCED PAGES AND DATABASES")
    print("="*80)
    mentions = find_page_mentions(data['blocks'])

    page_refs = [m for m in mentions if 'page_id' in m]
    db_refs = [m for m in mentions if 'database_id' in m]

    print(f"\nFound {len(page_refs)} page reference(s):")
    for ref in page_refs:
        print(f"  • Page ID: {ref['page_id']}")
        print(f"    Context: {ref['context']}")

    print(f"\nFound {len(db_refs)} database reference(s):")
    for ref in db_refs:
        print(f"  • Database ID: {ref['database_id']}")
        print(f"    Context: {ref['context']}")

    # Database schemas
    print("\n" + "="*80)
    print("DATABASE SCHEMAS")
    print("="*80)
    for db_id, db_data in data.get('databases', {}).items():
        print(f"\nDatabase: {db_data.get('title', [{}])[0].get('plain_text', 'Untitled')}")
        print(f"ID: {db_id}")
        print(f"Properties:")
        for prop_name, prop_data in db_data.get('properties', {}).items():
            print(f"  • {prop_name}: {prop_data.get('type')}")

    # Save summary
    summary = {
        'sections': dict(sections),
        'page_references': page_refs,
        'database_references': db_refs,
        'database_ids': list(data.get('databases', {}).keys())
    }

    with open('assistant_config_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*80)
    print("Summary saved to assistant_config_summary.json")
    print("="*80)

if __name__ == '__main__':
    main()
