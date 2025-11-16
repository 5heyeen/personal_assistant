"""iMessage monitoring service."""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

from ..integrations.imessage import iMessageIntegration
from ..utils.config import get_config
from ..utils.logger import get_logger


class MessageMonitor:
    """Monitors iMessage for new messages and activation keywords."""

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize message monitor.

        Args:
            state_file: Path to state file for tracking processed messages
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.imessage = iMessageIntegration()

        # State file for tracking processed messages
        if state_file is None:
            state_file = self.config.state_file
        self.state_file = state_file
        self.state = self._load_state()

        # Activation keywords from config
        self.activation_keywords = self.config.get('imessage.activation_keywords', [])

        # Poll interval
        self.poll_interval = self.config.imessage_poll_interval

        # Running flag
        self.running = False

    def _load_state(self) -> Dict:
        """Load state from file.

        Returns:
            State dictionary
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.logger.info(f"Loaded state from {self.state_file}")
                    return state
            except Exception as e:
                self.logger.error(f"Error loading state: {e}")

        # Default state
        return {
            'last_message_id': 0,
            'processed_messages': [],
            'last_check': None
        }

    def _save_state(self) -> None:
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
            self.logger.debug("Saved state")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def check_for_new_messages(self) -> List[Dict]:
        """Check for new messages since last check.

        Returns:
            List of new messages
        """
        try:
            # Get last check time
            last_check = self.state.get('last_check')
            if last_check:
                since = datetime.fromisoformat(last_check)
            else:
                # First run - check last hour
                since = datetime.now() - timedelta(hours=1)

            # Get recent messages
            messages = self.imessage.get_recent_messages(limit=100, since=since)

            # Filter out already processed messages
            processed_ids = set(self.state.get('processed_messages', []))
            new_messages = [msg for msg in messages if msg['id'] not in processed_ids]

            # Filter out messages from self
            new_messages = [msg for msg in new_messages if not msg['is_from_me']]

            # Update state
            if messages:
                latest_id = max(msg['id'] for msg in messages)
                self.state['last_message_id'] = latest_id

            for msg in new_messages:
                processed_ids.add(msg['id'])

            # Keep only recent processed messages (last 1000)
            self.state['processed_messages'] = list(processed_ids)[-1000:]
            self.state['last_check'] = datetime.now().isoformat()
            self._save_state()

            if new_messages:
                self.logger.info(f"Found {len(new_messages)} new message(s)")

            return new_messages

        except Exception as e:
            self.logger.error(f"Error checking for new messages: {e}")
            return []

    def check_for_activation_keywords(self, messages: List[Dict]) -> List[Dict]:
        """Check if any messages contain activation keywords.

        Args:
            messages: List of messages to check

        Returns:
            List of messages with activation keywords
        """
        activated_messages = []

        for msg in messages:
            text = msg.get('text', '').lower()

            for keyword in self.activation_keywords:
                if keyword.lower() in text:
                    self.logger.info(f"Activation keyword '{keyword}' detected in message from {msg.get('sender')}")
                    msg['activation_keyword'] = keyword
                    activated_messages.append(msg)
                    break

        return activated_messages

    def handle_activated_message(self, message: Dict) -> None:
        """Handle a message that triggered activation.

        Args:
            message: Message dictionary with activation keyword
        """
        keyword = message.get('activation_keyword', '')
        sender = message.get('sender', 'Unknown')
        text = message.get('text', '')

        self.logger.info(f"Handling activated message from {sender}: {text[:50]}...")

        # TODO: This is where you would integrate with the agent logic
        # For now, just log it
        # Future: Call agent to process the request

    def start_monitoring(self) -> None:
        """Start monitoring iMessages in a loop."""
        self.logger.info("Starting iMessage monitor...")
        self.running = True

        try:
            while self.running:
                # Check for new messages
                new_messages = self.check_for_new_messages()

                # Check for activation keywords
                if new_messages:
                    activated = self.check_for_activation_keywords(new_messages)

                    for msg in activated:
                        self.handle_activated_message(msg)

                # Sleep before next check
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            self.logger.info("Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
        finally:
            self.running = False
            self._save_state()

    def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        self.logger.info("Stopping iMessage monitor...")
        self.running = False


def main():
    """Main entry point for message monitor."""
    monitor = MessageMonitor()
    monitor.start_monitoring()


if __name__ == '__main__':
    main()
