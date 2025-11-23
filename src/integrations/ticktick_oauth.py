"""TickTick OAuth2 integration for task management."""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
import json
from pathlib import Path
from urllib.parse import urlencode
import webbrowser

from ..utils.config import get_config
from ..utils.logger import get_logger


class TickTickOAuth:
    """Handles TickTick OAuth2 authentication and API interactions."""

    # TickTick OAuth endpoints
    AUTH_URL = "https://ticktick.com/oauth/authorize"
    TOKEN_URL = "https://ticktick.com/oauth/token"
    API_BASE = "https://api.ticktick.com/open/v1"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """Initialize TickTick OAuth integration.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
        """
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Get credentials from config or parameters
        self.client_id = client_id or self.config.get_env('TICKTICK_CLIENT_ID')
        self.client_secret = client_secret or self.config.get_env('TICKTICK_CLIENT_SECRET')

        # Token storage
        self.token_file = self.config.base_dir / 'data' / 'ticktick_token.json'
        self.access_token = None
        self.refresh_token = None

        if not self.client_id or not self.client_secret:
            self.logger.warning("TickTick OAuth credentials not configured")
            return

        # Load existing token if available
        self._load_token()

    def is_available(self) -> bool:
        """Check if TickTick OAuth is available and authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.access_token is not None

    def _load_token(self) -> bool:
        """Load access token from file.

        Returns:
            True if token loaded, False otherwise
        """
        if not self.token_file.exists():
            return False

        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')

            self.logger.info("Loaded TickTick OAuth token")
            return True

        except Exception as e:
            self.logger.error(f"Error loading token: {e}")
            return False

    def _save_token(self, token_data: Dict[str, Any]) -> None:
        """Save access token to file.

        Args:
            token_data: Token response from OAuth
        """
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)

            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')

            self.logger.info("Saved TickTick OAuth token")

        except Exception as e:
            self.logger.error(f"Error saving token: {e}")

    def get_auth_url(self, redirect_uri: str = "http://localhost:8080/callback") -> str:
        """Get OAuth authorization URL.

        Args:
            redirect_uri: OAuth redirect URI

        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'scope': 'tasks:read tasks:write',
            'state': 'random_state_string',  # Should be random in production
            'redirect_uri': redirect_uri,
            'response_type': 'code'
        }

        url = f"{self.AUTH_URL}?{urlencode(params)}"
        return url

    def authorize(self, redirect_uri: str = "http://localhost:8080/callback") -> None:
        """Start OAuth authorization flow.

        Args:
            redirect_uri: OAuth redirect URI
        """
        auth_url = self.get_auth_url(redirect_uri)

        print("\n" + "="*60)
        print("TickTick OAuth Authorization")
        print("="*60)
        print("\n1. Opening browser for TickTick authorization...")
        print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
        print("2. Log in with your TickTick account (passkey/social login)")
        print("3. Authorize the application")
        print(f"4. Copy the 'code' parameter from the redirect URL")
        print("\nThe redirect URL will look like:")
        print(f"{redirect_uri}?code=AUTHORIZATION_CODE&state=...\n")

        # Open browser
        webbrowser.open(auth_url)

        # Get authorization code from user
        auth_code = input("\nPaste the authorization code here: ").strip()

        if auth_code:
            self.exchange_code_for_token(auth_code, redirect_uri)
        else:
            self.logger.error("No authorization code provided")

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> bool:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code
            redirect_uri: OAuth redirect URI

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
                'scope': 'tasks:read tasks:write'
            }

            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()
            self._save_token(token_data)

            print("\n✅ Successfully authenticated with TickTick!")
            return True

        except Exception as e:
            self.logger.error(f"Error exchanging code for token: {e}")
            print(f"\n❌ Authentication failed: {e}")
            return False

    def _api_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response data or None
        """
        if not self.access_token:
            self.logger.error("Not authenticated - run authorize() first")
            return None

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("Access token expired or invalid")
            else:
                self.logger.error(f"API request failed: {e}")
            return None

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects.

        Returns:
            List of project dictionaries
        """
        result = self._api_request('GET', '/project')
        return result if result else []

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from all projects.

        Returns:
            List of task dictionaries
        """
        all_tasks = []

        # Get all projects first
        projects = self.get_all_projects()

        # Get tasks from each project
        for project in projects:
            project_id = project.get('id')
            if not project_id:
                continue

            # Skip closed projects
            if project.get('closed', False):
                continue

            # Get project data (includes tasks)
            project_data = self._api_request('GET', f'/project/{project_id}/data')
            if project_data:
                tasks = project_data.get('tasks', [])
                all_tasks.extend(tasks)

        return all_tasks

    def _parse_ticktick_date(self, date_str: str) -> datetime:
        """Parse TickTick date format.

        Args:
            date_str: Date string from TickTick API

        Returns:
            Parsed datetime object
        """
        # TickTick returns dates like: 2026-11-11T23:00:00.000+0000
        # Python's fromisoformat needs: 2026-11-11T23:00:00.000+00:00
        # Also handle 'Z' suffix
        date_str = date_str.replace('Z', '+00:00')

        # Fix timezone format: +0000 -> +00:00
        if '+' in date_str and date_str[-5] in ['+', '-']:
            # Has timezone without colon
            date_str = date_str[:-2] + ':' + date_str[-2:]

        return datetime.fromisoformat(date_str)

    def get_today_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks due today (in local timezone).

        Returns:
            List of task dictionaries
        """
        all_tasks = self.get_all_tasks()
        now = datetime.now()
        today = now.date()

        today_tasks = []
        for task in all_tasks:
            due_date = task.get('dueDate')
            if due_date:
                # Parse the due date (returns timezone-aware datetime)
                task_datetime_utc = self._parse_ticktick_date(due_date)

                # Convert to local timezone
                # This ensures tasks scheduled for Saturday 00:00 local time
                # don't show up in Friday's briefing
                task_datetime_local = task_datetime_utc.astimezone()

                # Get the local date
                task_date_local = task_datetime_local.date()

                # Only include if the task's local date is today and not completed
                if task_date_local == today and task.get('status') == 0:
                    today_tasks.append(self._format_task(task))

        return today_tasks

    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get overdue tasks.

        Returns:
            List of task dictionaries
        """
        all_tasks = self.get_all_tasks()
        today = datetime.now().date()

        overdue = []
        for task in all_tasks:
            due_date = task.get('dueDate')
            if due_date:
                task_date = self._parse_ticktick_date(due_date).date()
                if task_date < today and task.get('status') == 0:
                    overdue.append(self._format_task(task))

        return overdue

    def get_task_statistics(self) -> Dict[str, int]:
        """Get task statistics.

        Returns:
            Dictionary with task stats
        """
        all_tasks = self.get_all_tasks()
        today = datetime.now().date()

        stats = {
            'total': len(all_tasks),
            'completed_today': 0,
            'overdue': 0,
            'due_today': 0,
            'high_priority': 0
        }

        for task in all_tasks:
            # Completed today
            completed_time = task.get('completedTime')
            if completed_time:
                completed_date = self._parse_ticktick_date(completed_time).date()
                if completed_date == today:
                    stats['completed_today'] += 1

            # Due today and overdue
            due_date = task.get('dueDate')
            if due_date and task.get('status') == 0:
                task_date = self._parse_ticktick_date(due_date).date()
                if task_date == today:
                    stats['due_today'] += 1
                elif task_date < today:
                    stats['overdue'] += 1

            # High priority
            if task.get('priority') == 5 and task.get('status') == 0:
                stats['high_priority'] += 1

        return stats

    def _format_task(self, task: Dict) -> Dict[str, Any]:
        """Format API task response.

        Args:
            task: Task from API

        Returns:
            Formatted task dictionary
        """
        formatted = {
            'id': task.get('id'),
            'title': task.get('title', 'Untitled'),
            'completed': task.get('status') == 2,
            'priority': task.get('priority', 0),
            'priority_name': self._priority_name(task.get('priority', 0))
        }

        if task.get('dueDate'):
            formatted['due_date'] = self._parse_ticktick_date(task['dueDate'])

        if task.get('tags'):
            formatted['tags'] = task.get('tags', [])

        return formatted

    def _priority_name(self, priority: int) -> str:
        """Convert priority number to name."""
        priority_map = {0: 'None', 1: 'Low', 3: 'Medium', 5: 'High'}
        return priority_map.get(priority, 'Unknown')

    def format_task_summary(self, task: Dict[str, Any]) -> str:
        """Format a task into a readable summary."""
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

    def create_task(
        self,
        title: str,
        project_id: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        content: Optional[str] = None,
        repeat_rule: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new task in TickTick.

        Args:
            title: Task title
            project_id: Project/list ID (optional)
            due_date: Due date/time (optional)
            priority: Priority level (0=None, 1=Low, 3=Medium, 5=High)
            tags: List of tags (optional)
            content: Task description/notes (optional)
            repeat_rule: Recurrence rule in RRULE format (optional)
                        Example: "FREQ=DAILY;BYDAY=MO,TU,WE,TH,SA" for daily except Fri/Sun

        Returns:
            Created task data or None if failed
        """
        if not self.access_token:
            self.logger.error("Not authenticated - run authorize() first")
            return None

        task_data = {
            'title': title,
            'priority': priority
        }

        if project_id:
            task_data['projectId'] = project_id

        if due_date:
            # TickTick expects due date in ISO format with timezone (UTC)
            # Format: "2025-11-25T23:00:00.000+0000"
            if due_date.tzinfo is None:
                # If no timezone, treat as UTC
                from datetime import timezone
                due_date = due_date.replace(tzinfo=timezone.utc)

            # Format with milliseconds and timezone
            task_data['dueDate'] = due_date.strftime('%Y-%m-%dT%H:%M:%S.000%z')

        if tags:
            task_data['tags'] = tags

        if content:
            task_data['content'] = content

        if repeat_rule:
            # TickTick uses 'repeat' field for recurrence rules
            task_data['repeat'] = repeat_rule

        result = self._api_request('POST', '/task', json=task_data)

        if result:
            self.logger.info(f"Created task: {title}")
            return result
        else:
            self.logger.error(f"Failed to create task: {title}")
            return None

    def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a project/list by name.

        Args:
            name: Project name to search for

        Returns:
            Project data or None if not found
        """
        projects = self.get_all_projects()

        for project in projects:
            if project.get('name', '').lower() == name.lower():
                return project

        return None

    def create_project(self, name: str, color: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new project/list.

        Args:
            name: Project name
            color: Project color (optional)

        Returns:
            Created project data or None if failed
        """
        if not self.access_token:
            self.logger.error("Not authenticated - run authorize() first")
            return None

        project_data = {'name': name}

        if color:
            project_data['color'] = color

        result = self._api_request('POST', '/project', json=project_data)

        if result:
            self.logger.info(f"Created project: {name}")
            return result
        else:
            self.logger.error(f"Failed to create project: {name}")
            return None

    def task_exists(self, title: str, project_id: Optional[str] = None) -> bool:
        """Check if a task with the given title already exists.

        Args:
            title: Task title to search for
            project_id: Optional project ID to narrow search

        Returns:
            True if task exists, False otherwise
        """
        all_tasks = self.get_all_tasks()

        for task in all_tasks:
            # Check if titles match (case-insensitive)
            if task.get('title', '').lower() == title.lower():
                # If project_id specified, also check project match
                if project_id:
                    if task.get('projectId') == project_id:
                        return True
                else:
                    return True

        return False
