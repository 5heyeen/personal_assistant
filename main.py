#!/usr/bin/env python3
"""Main entry point for Personal Assistant."""

import argparse
import signal
import sys
import threading
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.utils.config import get_config
from src.utils.logger import setup_logger
from src.monitors.message_monitor import MessageMonitor
from src.automation.scheduler import TaskScheduler


class PersonalAssistant:
    """Main personal assistant application."""

    def __init__(self, imessage_recipient: str = None):
        """Initialize personal assistant.

        Args:
            imessage_recipient: Default iMessage recipient for notifications
        """
        # Setup logging
        self.logger = setup_logger('PersonalAssistant')
        self.logger.info("="*80)
        self.logger.info("Personal Assistant Starting")
        self.logger.info("="*80)

        self.config = get_config()
        self.imessage_recipient = imessage_recipient

        # Initialize components
        self.message_monitor = None
        self.scheduler = None
        self.running = False

    def start_message_monitor(self) -> None:
        """Start iMessage monitoring."""
        if not self.config.imessage_enabled:
            self.logger.info("iMessage monitoring is disabled in config")
            return

        try:
            self.logger.info("Starting iMessage monitor...")
            self.message_monitor = MessageMonitor()

            # Run in separate thread
            monitor_thread = threading.Thread(
                target=self.message_monitor.start_monitoring,
                daemon=True
            )
            monitor_thread.start()
            self.logger.info("iMessage monitor started")

        except Exception as e:
            self.logger.error(f"Failed to start iMessage monitor: {e}")

    def start_scheduler(self) -> None:
        """Start task scheduler."""
        if not self.config.automation_enabled:
            self.logger.info("Automation is disabled in config")
            return

        try:
            self.logger.info("Starting task scheduler...")
            self.scheduler = TaskScheduler()
            self.scheduler.load_schedules_from_config(
                imessage_recipient=self.imessage_recipient
            )
            self.scheduler.start(run_in_thread=True)
            self.logger.info("Task scheduler started")

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")

    def start(self) -> None:
        """Start all components."""
        self.running = True

        # Start message monitor
        self.start_message_monitor()

        # Start scheduler
        self.start_scheduler()

        self.logger.info("="*80)
        self.logger.info("Personal Assistant is running")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("="*80)

    def stop(self) -> None:
        """Stop all components."""
        self.logger.info("Shutting down Personal Assistant...")
        self.running = False

        if self.message_monitor:
            self.message_monitor.stop_monitoring()

        if self.scheduler:
            self.scheduler.stop()

        self.logger.info("Personal Assistant stopped")

    def run(self) -> None:
        """Run the personal assistant (blocking)."""
        self.start()

        try:
            # Keep main thread alive
            while self.running:
                signal.pause()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Personal Assistant - Notion, iMessage, and Google Calendar integration'
    )
    parser.add_argument(
        '--recipient',
        help='Default iMessage recipient for notifications (phone number or email)'
    )
    parser.add_argument(
        '--no-monitor',
        action='store_true',
        help='Disable iMessage monitoring'
    )
    parser.add_argument(
        '--no-scheduler',
        action='store_true',
        help='Disable task scheduler'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (load config and exit)'
    )

    args = parser.parse_args()

    # Create assistant instance
    assistant = PersonalAssistant(imessage_recipient=args.recipient)

    # Test mode
    if args.test:
        print("Configuration loaded successfully!")
        print(f"Notion page: {assistant.config.notion_assistant_page_id}")
        print(f"iMessage enabled: {assistant.config.imessage_enabled}")
        print(f"Calendar enabled: {assistant.config.google_calendar_enabled}")
        print(f"Automation enabled: {assistant.config.automation_enabled}")
        return

    # Override config based on arguments
    if args.no_monitor:
        assistant.config._config['imessage']['enabled'] = False

    if args.no_scheduler:
        assistant.config._config['automation']['enabled'] = False

    # Run assistant
    assistant.run()


if __name__ == '__main__':
    main()
