#!/usr/bin/env python3
"""Fetch all referenced pages and their databases."""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_VERSION = '2022-06-28'

headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json'
}

# Referenced page IDs from analysis
PAGE_IDS = [
    '27f64f44-8283-8152-8a1a-ed26e775f5f3',  # meal planning
    '29464f44-8283-80c4-bf65-dcbfd7e90205',  # memories main
    '29564f44-8283-808f-8cc2-d0d864298d86',  # personal topics
    '29664f44-8283-80a5-b782-c2af62a7dbbb',  # work topics
    '29564f44-8283-804f-a3a1-d5ae41013bb7',  # finance & investments
    '29564f44-8283-80d9-8d5c-ea630e2698a2',  # AI usage
]

def get_page(page_id):
    """Retrieve a Notion page."""
    url = f'https://api.notion.com/v1/pages/{page_id}'
    response = requests.get(url, headers=headers)
    return response.json()

def get_block_children(block_id):
    """Retrieve children blocks."""
    url = f'https://api.notion.com/v1/blocks/{block_id}/children'
    response = requests.get(url, headers=headers)
    return response.json()

def get_database(database_id):
    """Retrieve database schema."""
    url = f'https://api.notion.com/v1/databases/{database_id}'
    response = requests.get(url, headers=headers)
    return response.json()

def find_child_databases(block_id, collected_dbs=None):
    """Recursively find all child databases."""
    if collected_dbs is None:
        collected_dbs = []

    try:
        blocks = get_block_children(block_id)

        for block in blocks.get('results', []):
            if block.get('type') == 'child_database':
                db_id = block.get('id')
                if db_id and db_id not in collected_dbs:
                    collected_dbs.append(db_id)

            if block.get('has_children'):
                find_child_databases(block['id'], collected_dbs)

    except Exception as e:
        print(f"Error processing block {block_id}: {e}")

    return collected_dbs

def main():
    all_pages = {}
    all_databases = {}

    print("Fetching referenced pages...")

    for page_id in PAGE_IDS:
        print(f"\nFetching page: {page_id}")
        page = get_page(page_id)

        if page.get('object') == 'error':
            print(f"  ⚠️  Error: {page.get('message')}")
            print(f"  This page needs to be shared with your integration!")
            continue

        title = 'Untitled'
        if 'properties' in page and 'title' in page['properties']:
            title_array = page['properties']['title'].get('title', [])
            if title_array:
                title = title_array[0].get('plain_text', 'Untitled')

        print(f"  ✓ {title}")
        all_pages[page_id] = page

        # Find child databases
        print(f"  Searching for databases...")
        db_ids = find_child_databases(page_id)

        if db_ids:
            print(f"  Found {len(db_ids)} database(s)")
            for db_id in db_ids:
                if db_id not in all_databases:
                    db = get_database(db_id)
                    all_databases[db_id] = db

                    db_title = 'Untitled'
                    if 'title' in db and db['title']:
                        db_title = db['title'][0].get('plain_text', 'Untitled')

                    print(f"    • {db_title} ({db_id})")
        else:
            print(f"  No databases found")

    # Save results
    output = {
        'pages': all_pages,
        'databases': all_databases,
        'database_ids': list(all_databases.keys()),
        'page_ids': list(all_pages.keys())
    }

    with open('referenced_pages_data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Pages fetched: {len(all_pages)}/{len(PAGE_IDS)}")
    print(f"Databases found: {len(all_databases)}")
    print("\nDatabase IDs:")
    for db_id, db in all_databases.items():
        db_title = 'Untitled'
        if 'title' in db and db['title']:
            db_title = db['title'][0].get('plain_text', 'Untitled')
        print(f"  • {db_title}: {db_id}")

    print("\nData saved to referenced_pages_data.json")

if __name__ == '__main__':
    main()
