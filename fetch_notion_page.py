#!/usr/bin/env python3
"""Fetch Personal Assistant page from Notion and extract database references."""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_VERSION = '2022-06-28'

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json'
}

def get_page(page_id):
    """Retrieve a Notion page."""
    url = f'https://api.notion.com/v1/pages/{page_id}'
    response = requests.get(url, headers=headers)
    return response.json()

def get_block_children(block_id):
    """Retrieve children blocks of a page or block."""
    url = f'https://api.notion.com/v1/blocks/{block_id}/children'
    response = requests.get(url, headers=headers)
    return response.json()

def extract_database_ids(blocks):
    """Extract all database IDs from blocks."""
    database_ids = []

    def process_block(block):
        if block.get('type') == 'child_database':
            db_id = block.get('id')
            if db_id:
                database_ids.append(db_id)

        # Check for linked databases in various block types
        if 'has_children' in block and block['has_children']:
            children = get_block_children(block['id'])
            if 'results' in children:
                for child in children['results']:
                    process_block(child)

    for block in blocks.get('results', []):
        process_block(block)

    return database_ids

def get_database(database_id):
    """Retrieve database schema."""
    url = f'https://api.notion.com/v1/databases/{database_id}'
    response = requests.get(url, headers=headers)
    return response.json()

def main():
    # Page ID from the URL
    page_id = '29664f44-8283-8098-ab98-e34380b5d96b'

    print("Fetching Personal Assistant page...")
    page = get_page(page_id)

    print("\n" + "="*80)
    print("PAGE DETAILS")
    print("="*80)
    print(json.dumps(page, indent=2))

    print("\n" + "="*80)
    print("FETCHING PAGE CONTENT (BLOCKS)")
    print("="*80)
    blocks = get_block_children(page_id)
    print(json.dumps(blocks, indent=2))

    # Extract database IDs
    print("\n" + "="*80)
    print("EXTRACTING DATABASE IDs")
    print("="*80)
    database_ids = extract_database_ids(blocks)

    if database_ids:
        print(f"Found {len(database_ids)} database(s):")
        for db_id in database_ids:
            print(f"  - {db_id}")
    else:
        print("No databases found in page blocks")

    # Fetch database schemas
    databases = {}
    for db_id in database_ids:
        print(f"\nFetching database schema for {db_id}...")
        db = get_database(db_id)
        databases[db_id] = db
        print(json.dumps(db, indent=2))

    # Save all data to file
    output = {
        'page': page,
        'blocks': blocks,
        'database_ids': database_ids,
        'databases': databases
    }

    with open('notion_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*80)
    print("Data saved to notion_data.json")
    print("="*80)

if __name__ == '__main__':
    main()
