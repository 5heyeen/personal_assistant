"""Notion API integration for personal assistant."""

from typing import Dict, List, Optional, Any
from notion_client import Client
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class NotionIntegration:
    """Handles all Notion API interactions."""

    def __init__(self):
        """Initialize Notion client."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.client = Client(auth=self.config.notion_token)
        self.assistant_page_id = self.config.notion_assistant_page_id

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a Notion page.

        Args:
            page_id: Notion page ID

        Returns:
            Page data

        Raises:
            Exception: If page not found or API error
        """
        try:
            self.logger.debug(f"Fetching page: {page_id}")
            return self.client.pages.retrieve(page_id)
        except Exception as e:
            self.logger.error(f"Error fetching page {page_id}: {e}")
            raise

    def get_page_content(self, page_id: str) -> List[Dict[str, Any]]:
        """Retrieve page content (blocks).

        Args:
            page_id: Notion page ID

        Returns:
            List of blocks
        """
        try:
            self.logger.debug(f"Fetching blocks for page: {page_id}")
            response = self.client.blocks.children.list(page_id)
            return response.get('results', [])
        except Exception as e:
            self.logger.error(f"Error fetching blocks for {page_id}: {e}")
            raise

    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Retrieve database schema.

        Args:
            database_id: Notion database ID

        Returns:
            Database schema
        """
        try:
            self.logger.debug(f"Fetching database: {database_id}")
            return self.client.databases.retrieve(database_id)
        except Exception as e:
            self.logger.error(f"Error fetching database {database_id}: {e}")
            raise

    def query_database(
        self,
        database_id: str,
        filter_dict: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Query a Notion database.

        Args:
            database_id: Notion database ID
            filter_dict: Optional filter criteria
            sorts: Optional sort criteria
            page_size: Number of results per page

        Returns:
            List of database entries
        """
        try:
            self.logger.debug(f"Querying database: {database_id}")

            query_params = {"page_size": page_size}
            if filter_dict:
                query_params["filter"] = filter_dict
            if sorts:
                query_params["sorts"] = sorts

            response = self.client.databases.query(database_id, **query_params)
            results = response.get('results', [])

            # Handle pagination
            while response.get('has_more'):
                query_params['start_cursor'] = response.get('next_cursor')
                response = self.client.databases.query(database_id, **query_params)
                results.extend(response.get('results', []))

            self.logger.info(f"Retrieved {len(results)} entries from database {database_id}")
            return results

        except Exception as e:
            self.logger.error(f"Error querying database {database_id}: {e}")
            raise

    def create_page(
        self,
        parent_id: str,
        properties: Dict[str, Any],
        children: Optional[List[Dict[str, Any]]] = None,
        parent_type: str = "page_id"
    ) -> Dict[str, Any]:
        """Create a new page in Notion.

        Args:
            parent_id: Parent page or database ID
            properties: Page properties
            children: Optional page content (blocks)
            parent_type: 'page_id' or 'database_id'

        Returns:
            Created page data
        """
        try:
            parent = {
                "type": parent_type,
                parent_type: parent_id
            }

            page_data = {
                "parent": parent,
                "properties": properties
            }

            if children:
                page_data["children"] = children

            self.logger.debug(f"Creating page in {parent_id}")
            result = self.client.pages.create(**page_data)
            self.logger.info(f"Created page: {result['id']}")
            return result

        except Exception as e:
            self.logger.error(f"Error creating page: {e}")
            raise

    def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a Notion page's properties.

        Args:
            page_id: Page ID to update
            properties: Properties to update

        Returns:
            Updated page data
        """
        try:
            self.logger.debug(f"Updating page: {page_id}")
            result = self.client.pages.update(page_id, properties=properties)
            self.logger.info(f"Updated page: {page_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error updating page {page_id}: {e}")
            raise

    def append_block_children(
        self,
        block_id: str,
        children: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Append blocks to a page or block.

        Args:
            block_id: Parent block/page ID
            children: Blocks to append

        Returns:
            Response with appended blocks
        """
        try:
            self.logger.debug(f"Appending blocks to: {block_id}")
            result = self.client.blocks.children.append(block_id, children=children)
            self.logger.info(f"Appended {len(children)} blocks to {block_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error appending blocks to {block_id}: {e}")
            raise

    def search(
        self,
        query: str,
        filter_type: Optional[str] = None,
        sort_direction: str = "descending"
    ) -> List[Dict[str, Any]]:
        """Search Notion workspace.

        Args:
            query: Search query
            filter_type: Optional filter ('page' or 'database')
            sort_direction: Sort direction ('ascending' or 'descending')

        Returns:
            List of search results
        """
        try:
            self.logger.debug(f"Searching for: {query}")

            search_params = {
                "query": query,
                "sort": {"direction": sort_direction, "timestamp": "last_edited_time"}
            }

            if filter_type:
                search_params["filter"] = {"value": filter_type, "property": "object"}

            response = self.client.search(**search_params)
            results = response.get('results', [])
            self.logger.info(f"Found {len(results)} results for '{query}'")
            return results

        except Exception as e:
            self.logger.error(f"Error searching for '{query}': {e}")
            raise

    def add_memory(
        self,
        category: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Add a memory to the appropriate memory page.

        Args:
            category: Memory category (personal, work, finance, ai_usage)
            content: Memory content
            metadata: Optional additional metadata

        Returns:
            Created page/block or None if category page not configured
        """
        # Map categories to page IDs
        category_page_ids = {
            'personal': self.config.get('notion.referenced_pages.personal_topics'),
            'work': self.config.get('notion.referenced_pages.work_topics'),
            'finance': self.config.get('notion.referenced_pages.finance'),
            'ai_usage': self.config.get('notion.referenced_pages.ai_usage')
        }

        page_id = category_page_ids.get(category)
        if not page_id:
            self.logger.warning(f"No page ID configured for category: {category}")
            return None

        try:
            # Create a block with the memory content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"[{timestamp}] {content}"}
                    }]
                }
            }

            result = self.append_block_children(page_id, [block])
            self.logger.info(f"Added memory to {category}: {content[:50]}...")
            return result

        except Exception as e:
            self.logger.error(f"Error adding memory to {category}: {e}")
            return None

    def get_assistant_config(self) -> Dict[str, Any]:
        """Retrieve the Personal Assistant configuration page.

        Returns:
            Assistant configuration data
        """
        try:
            page = self.get_page(self.assistant_page_id)
            blocks = self.get_page_content(self.assistant_page_id)
            return {
                'page': page,
                'blocks': blocks
            }
        except Exception as e:
            self.logger.error(f"Error retrieving assistant config: {e}")
            raise
