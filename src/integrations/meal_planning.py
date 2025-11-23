"""Meal planning integration using Notion database."""

from typing import List, Dict, Optional, Any
from datetime import datetime, date

from ..utils.config import get_config
from ..utils.logger import get_logger
from .notion import NotionIntegration


class MealPlanningIntegration:
    """Handles meal planning from Notion database."""

    def __init__(self):
        """Initialize meal planning integration."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.notion = NotionIntegration()

        # Get meal planning database ID from config
        self.meal_db_id = self.config.get('notion.referenced_pages.meal_planning')

    def is_available(self) -> bool:
        """Check if meal planning is available.

        Returns:
            True if database ID is configured
        """
        return self.meal_db_id is not None

    def get_todays_meals(self) -> List[Dict[str, Any]]:
        """Get meals planned for today.

        Returns:
            List of meal dictionaries
        """
        if not self.is_available():
            self.logger.warning("Meal planning database not configured")
            return []

        try:
            # Get today's day name (e.g., "Monday")
            today_name = datetime.now().strftime('%A')

            # Query database for meals with today in "When to Cook"
            # Note: This queries all recipes and filters client-side
            # For better performance, you could use Notion API filters
            all_meals = self.notion.query_database(self.meal_db_id, page_size=100)

            todays_meals = []

            for meal in all_meals:
                props = meal.get('properties', {})

                # Check "When to Cook" field
                when_to_cook = props.get('When to Cook', {})
                if when_to_cook.get('type') == 'select':
                    selected = when_to_cook.get('select')
                    if selected and today_name.lower() in selected.get('name', '').lower():
                        todays_meals.append(self._format_meal(meal))

            self.logger.info(f"Found {len(todays_meals)} meals for {today_name}")
            return todays_meals

        except Exception as e:
            self.logger.error(f"Error getting today's meals: {e}")
            return []

    def get_meals_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get meals for a specific date.

        Args:
            target_date: Date to query

        Returns:
            List of meal dictionaries
        """
        if not self.is_available():
            return []

        try:
            # Get day name for target date
            day_name = target_date.strftime('%A')

            all_meals = self.notion.query_database(self.meal_db_id, page_size=100)

            meals = []
            for meal in all_meals:
                props = meal.get('properties', {})

                when_to_cook = props.get('When to Cook', {})
                if when_to_cook.get('type') == 'select':
                    selected = when_to_cook.get('select')
                    if selected and day_name.lower() in selected.get('name', '').lower():
                        meals.append(self._format_meal(meal))

            return meals

        except Exception as e:
            self.logger.error(f"Error getting meals for {target_date}: {e}")
            return []

    def _format_meal(self, meal: Dict) -> Dict[str, Any]:
        """Format meal data from Notion.

        Args:
            meal: Raw meal entry from Notion

        Returns:
            Formatted meal dictionary
        """
        props = meal.get('properties', {})

        # Extract recipe name
        title_prop = props.get('Recipe Name', {})
        title = ''
        if title_prop.get('type') == 'title':
            title_items = title_prop.get('title', [])
            if title_items:
                title = title_items[0].get('plain_text', 'Untitled')

        # Extract category
        categories = []
        category_prop = props.get('Category', {})
        if category_prop.get('type') == 'multi_select':
            for cat in category_prop.get('multi_select', []):
                categories.append(cat.get('name', ''))

        # Extract servings
        servings_prop = props.get('Servings', {})
        servings = servings_prop.get('number') if servings_prop.get('type') == 'number' else None

        # Extract URL
        url_prop = props.get('URL', {})
        url = url_prop.get('url') if url_prop.get('type') == 'url' else None

        return {
            'name': title,
            'categories': categories,
            'servings': servings,
            'url': url,
            'notion_id': meal.get('id')
        }

    def format_meal_summary(self, meal: Dict[str, Any]) -> str:
        """Format a meal into a readable summary.

        Args:
            meal: Formatted meal dictionary

        Returns:
            Formatted meal string
        """
        parts = [meal.get('name', 'Untitled')]

        if meal.get('categories'):
            category_str = ', '.join(meal['categories'])
            parts.append(f"({category_str})")

        if meal.get('servings'):
            parts.append(f"- {meal['servings']} servings")

        return ' '.join(parts)
