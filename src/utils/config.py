"""Configuration management for personal assistant."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv


class Config:
    """Configuration manager for the personal assistant."""

    def __init__(self, config_path: str = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. Defaults to config/settings.yaml
        """
        # Load environment variables
        load_dotenv()

        # Determine paths
        self.base_dir = Path(__file__).parent.parent.parent
        if config_path is None:
            config_path = self.base_dir / "config" / "settings.yaml"
        else:
            config_path = Path(config_path)

        # Load configuration
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., 'notion.token_env_var')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config = Config()
            >>> config.get('imessage.poll_interval_seconds')
            30
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_env(self, env_var: str, default: Any = None) -> Any:
        """Get environment variable.

        Args:
            env_var: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value or default
        """
        return os.getenv(env_var, default)

    @property
    def notion_token(self) -> str:
        """Get Notion API token from environment."""
        env_var = self.get('notion.token_env_var', 'NOTION_TOKEN')
        token = self.get_env(env_var)
        if not token:
            raise ValueError(f"Notion token not found in environment variable: {env_var}")
        return token

    @property
    def notion_assistant_page_id(self) -> str:
        """Get Personal Assistant page ID."""
        return self.get('notion.assistant_page_id')

    @property
    def imessage_enabled(self) -> bool:
        """Check if iMessage monitoring is enabled."""
        return self.get('imessage.enabled', False)

    @property
    def imessage_database_path(self) -> Path:
        """Get iMessage database path."""
        path = self.get('imessage.database_path', '~/Library/Messages/chat.db')
        return Path(path).expanduser()

    @property
    def imessage_poll_interval(self) -> int:
        """Get iMessage poll interval in seconds."""
        return self.get('imessage.poll_interval_seconds', 30)

    @property
    def google_calendar_enabled(self) -> bool:
        """Check if Google Calendar integration is enabled."""
        return self.get('google_calendar.enabled', False)

    @property
    def automation_enabled(self) -> bool:
        """Check if automation is enabled."""
        return self.get('automation.enabled', False)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get('logging.level', 'INFO')

    @property
    def log_file(self) -> Path:
        """Get log file path."""
        return self.base_dir / self.get('logging.file', 'logs/assistant.log')

    @property
    def state_file(self) -> Path:
        """Get state file path."""
        return self.base_dir / self.get('state.file', 'data/state.json')

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.get(key)

    def __repr__(self) -> str:
        """String representation."""
        return f"Config(base_dir={self.base_dir})"


# Global config instance
_config = None


def get_config(config_path: str = None) -> Config:
    """Get or create global config instance.

    Args:
        config_path: Path to config file

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
