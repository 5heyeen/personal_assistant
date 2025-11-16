"""TickTick integration for task management."""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
from pathlib import Path
import json

from ..utils.config import get_config
from ..utils.logger import get_logger


class TickTickIntegration:
    """Handles TickTick API interactions for task management."""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize TickTick integration.

        Args:
            username: TickTick username (email)
            password: TickTick password
        """
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Get credentials from config or parameters
        self.username = username or self.config.get_env('TICKTICK_USERNAME')
        self.password = password or self.config.get_env('TICKTICK_PASSWORD')

        if not self.username or not self.password:
            self.logger.warning("TickTick credentials not configured")
            self.client = None
            return

        # Try to import ticktick-py library
        try:
            from ticktick.oauth2 import OAuth2
            from ticktick.api import TickTickClient

            # Initialize client
            self.auth_client = OAuth2(
                username=self.username,
                password=self.password
            )

            self.client = TickTickClient(
                username=self.username,
                password=self.password,
                oauth=self.auth_client
            )

            self.logger.info("TickTick integration initialized")

        except ImportError:
            self.logger.error("ticktick-py library not installed. Run: pip install ticktick-py")
            self.client = None
        except Exception as e:
            self.logger.error(f"Error initializing TickTick: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if TickTick integration is available.

        Returns:
            True if client is initialized, False otherwise
        """
        return self.client is not None

    def get_today_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks due today.

        Returns:
            List of task dictionaries
        """
        if not self.is_available():
            return []

        try:
            today = datetime.now().date()
            tasks = []

            # Get all tasks
            all_tasks = self.client.task.get_from_project()

            for task in all_tasks:
                # Check if task is due today
                if hasattr(task, 'due_date'):
                    due_date = task.due_date
                    if due_date and due_date.date() == today:
                        tasks.append(self._format_task(task))

            self.logger.debug(f"Retrieved {len(tasks)} tasks for today")
            return tasks

        except Exception as e:
            self.logger.error(f"Error getting today's tasks: {e}")
            return []

    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get overdue tasks.

        Returns:
            List of overdue task dictionaries
        """
        if not self.is_available():
            return []

        try:
            today = datetime.now().date()
            tasks = []

            all_tasks = self.client.task.get_from_project()

            for task in all_tasks:
                if hasattr(task, 'due_date') and task.due_date:
                    if task.due_date.date() < today and not task.is_completed:
                        tasks.append(self._format_task(task))

            self.logger.debug(f"Retrieved {len(tasks)} overdue tasks")
            return tasks

        except Exception as e:
            self.logger.error(f"Error getting overdue tasks: {e}")
            return []

    def get_upcoming_tasks(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get tasks due in the next N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of upcoming task dictionaries
        """
        if not self.is_available():
            return []

        try:
            today = datetime.now().date()
            end_date = today + timedelta(days=days)
            tasks = []

            all_tasks = self.client.task.get_from_project()

            for task in all_tasks:
                if hasattr(task, 'due_date') and task.due_date:
                    due_date = task.due_date.date()
                    if today <= due_date <= end_date and not task.is_completed:
                        tasks.append(self._format_task(task))

            # Sort by due date
            tasks.sort(key=lambda x: x.get('due_date', datetime.max))

            self.logger.debug(f"Retrieved {len(tasks)} upcoming tasks")
            return tasks

        except Exception as e:
            self.logger.error(f"Error getting upcoming tasks: {e}")
            return []

    def get_tasks_by_priority(self, priority: int = 5) -> List[Dict[str, Any]]:
        """Get tasks by priority level.

        Args:
            priority: Priority level (0=None, 1=Low, 3=Medium, 5=High)

        Returns:
            List of task dictionaries
        """
        if not self.is_available():
            return []

        try:
            tasks = []
            all_tasks = self.client.task.get_from_project()

            for task in all_tasks:
                if hasattr(task, 'priority') and task.priority == priority:
                    if not task.is_completed:
                        tasks.append(self._format_task(task))

            self.logger.debug(f"Retrieved {len(tasks)} tasks with priority {priority}")
            return tasks

        except Exception as e:
            self.logger.error(f"Error getting tasks by priority: {e}")
            return []

    def get_tasks_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get tasks with a specific tag.

        Args:
            tag: Tag name

        Returns:
            List of task dictionaries
        """
        if not self.is_available():
            return []

        try:
            tasks = []
            all_tasks = self.client.task.get_from_project()

            for task in all_tasks:
                if hasattr(task, 'tags') and tag in task.tags:
                    tasks.append(self._format_task(task))

            self.logger.debug(f"Retrieved {len(tasks)} tasks with tag '{tag}'")
            return tasks

        except Exception as e:
            self.logger.error(f"Error getting tasks by tag: {e}")
            return []

    def create_task(
        self,
        title: str,
        due_date: Optional[datetime] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        content: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new task.

        Args:
            title: Task title
            due_date: Due date/time
            priority: Priority (0=None, 1=Low, 3=Medium, 5=High)
            tags: List of tags
            content: Task description
            project_id: Project/list ID

        Returns:
            Created task dictionary or None
        """
        if not self.is_available():
            return None

        try:
            task = self.client.task.builder(
                title=title,
                priority=priority
            )

            if due_date:
                task.set_due_date(due_date)

            if tags:
                task.set_tags(tags)

            if content:
                task.set_content(content)

            if project_id:
                task.set_project_id(project_id)

            created = task.create()
            self.logger.info(f"Created task: {title}")
            return self._format_task(created)

        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            return None

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Task ID

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            self.client.task.complete(task_id)
            self.logger.info(f"Completed task: {task_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error completing task: {e}")
            return False

    def get_task_statistics(self) -> Dict[str, int]:
        """Get task completion statistics.

        Returns:
            Dictionary with task stats
        """
        if not self.is_available():
            return {
                'total': 0,
                'completed_today': 0,
                'overdue': 0,
                'due_today': 0,
                'high_priority': 0
            }

        try:
            all_tasks = self.client.task.get_from_project()
            today = datetime.now().date()

            stats = {
                'total': 0,
                'completed_today': 0,
                'overdue': 0,
                'due_today': 0,
                'high_priority': 0
            }

            for task in all_tasks:
                stats['total'] += 1

                # Completed today
                if task.is_completed and hasattr(task, 'completed_time'):
                    if task.completed_time and task.completed_time.date() == today:
                        stats['completed_today'] += 1

                # Overdue
                if hasattr(task, 'due_date') and task.due_date:
                    if task.due_date.date() < today and not task.is_completed:
                        stats['overdue'] += 1
                    elif task.due_date.date() == today and not task.is_completed:
                        stats['due_today'] += 1

                # High priority
                if hasattr(task, 'priority') and task.priority == 5 and not task.is_completed:
                    stats['high_priority'] += 1

            return stats

        except Exception as e:
            self.logger.error(f"Error getting task statistics: {e}")
            return {}

    def _format_task(self, task) -> Dict[str, Any]:
        """Format a TickTick task object into a dictionary.

        Args:
            task: TickTick task object

        Returns:
            Formatted task dictionary
        """
        formatted = {
            'id': task.id,
            'title': task.title,
            'completed': task.is_completed,
        }

        # Optional fields
        if hasattr(task, 'due_date') and task.due_date:
            formatted['due_date'] = task.due_date

        if hasattr(task, 'priority'):
            formatted['priority'] = task.priority
            formatted['priority_name'] = self._priority_name(task.priority)

        if hasattr(task, 'tags'):
            formatted['tags'] = task.tags

        if hasattr(task, 'content'):
            formatted['content'] = task.content

        if hasattr(task, 'project_id'):
            formatted['project_id'] = task.project_id

        return formatted

    def _priority_name(self, priority: int) -> str:
        """Convert priority number to name.

        Args:
            priority: Priority number

        Returns:
            Priority name
        """
        priority_map = {
            0: 'None',
            1: 'Low',
            3: 'Medium',
            5: 'High'
        }
        return priority_map.get(priority, 'Unknown')

    def format_task_summary(self, task: Dict[str, Any]) -> str:
        """Format a task into a readable summary.

        Args:
            task: Task dictionary

        Returns:
            Formatted task summary
        """
        parts = []

        # Priority indicator
        priority = task.get('priority', 0)
        if priority == 5:
            parts.append('🔴')
        elif priority == 3:
            parts.append('🟡')
        elif priority == 1:
            parts.append('🔵')

        # Title
        parts.append(task.get('title', 'Untitled'))

        # Due date
        if 'due_date' in task:
            due = task['due_date']
            if isinstance(due, datetime):
                parts.append(f"(due {due.strftime('%I:%M %p')})")

        # Tags
        if task.get('tags'):
            tags_str = ' '.join(f"#{tag}" for tag in task['tags'])
            parts.append(f"[{tags_str}]")

        return ' '.join(parts)
