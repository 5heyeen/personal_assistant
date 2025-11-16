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

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks.

        Returns:
            List of task dictionaries
        """
        result = self._api_request('GET', '/task')
        return result if result else []

    def get_today_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks due today.

        Returns:
            List of task dictionaries
        """
        all_tasks = self.get_all_tasks()
        today = datetime.now().date()

        today_tasks = []
        for task in all_tasks:
            due_date = task.get('dueDate')
            if due_date:
                task_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
                if task_date == today and task.get('status') == 0:  # 0 = not completed
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
                task_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
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
                completed_date = datetime.fromisoformat(completed_time.replace('Z', '+00:00')).date()
                if completed_date == today:
                    stats['completed_today'] += 1

            # Due today and overdue
            due_date = task.get('dueDate')
            if due_date and task.get('status') == 0:
                task_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
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
            formatted['due_date'] = datetime.fromisoformat(task['dueDate'].replace('Z', '+00:00'))

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
