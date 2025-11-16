"""Scheduler for automated tasks."""

import schedule
import time
import threading
from typing import Callable, Optional

from ..utils.config import get_config
from ..utils.logger import get_logger
from .workflows import WorkflowEngine


class TaskScheduler:
    """Schedules and runs automated tasks."""

    def __init__(self):
        """Initialize task scheduler."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.workflow_engine = WorkflowEngine()
        self.running = False
        self.thread = None

    def schedule_daily_briefing(self, time_str: str, recipient: Optional[str] = None) -> None:
        """Schedule daily briefing.

        Args:
            time_str: Time in HH:MM format
            recipient: Optional iMessage recipient
        """
        def job():
            self.logger.info("Running scheduled daily briefing")
            self.workflow_engine.daily_briefing(
                send_via_imessage=bool(recipient),
                recipient=recipient
            )

        schedule.every().day.at(time_str).do(job)
        self.logger.info(f"Scheduled daily briefing at {time_str}")

    def schedule_weekly_review(self, day: str, time_str: str) -> None:
        """Schedule weekly review.

        Args:
            day: Day of week (e.g., 'Sunday')
            time_str: Time in HH:MM format
        """
        def job():
            self.logger.info("Running scheduled weekly review")
            review = self.workflow_engine.weekly_review()
            self.logger.info(f"Weekly review:\n{review}")

        # Get the schedule day method
        day_lower = day.lower()
        if hasattr(schedule.every(), day_lower):
            getattr(schedule.every(), day_lower).at(time_str).do(job)
            self.logger.info(f"Scheduled weekly review on {day} at {time_str}")

    def schedule_playdate_reminder(self, day: str, time_str: str, recipient: Optional[str] = None) -> None:
        """Schedule playdate Friday reminder.

        Args:
            day: Day of week (typically 'Friday')
            time_str: Time in HH:MM format
            recipient: Optional iMessage recipient
        """
        def job():
            self.logger.info("Running scheduled playdate reminder")
            self.workflow_engine.playdate_friday_reminder(recipient=recipient)

        day_lower = day.lower()
        if hasattr(schedule.every(), day_lower):
            getattr(schedule.every(), day_lower).at(time_str).do(job)
            self.logger.info(f"Scheduled playdate reminder on {day} at {time_str}")

    def schedule_preparation_check(self, day: str, time_str: str, recipient: Optional[str] = None) -> None:
        """Schedule advance preparation check.

        Args:
            day: Day of week
            time_str: Time in HH:MM format
            recipient: Optional iMessage recipient
        """
        def job():
            self.logger.info("Running scheduled preparation check")
            self.workflow_engine.send_preparation_reminders(recipient=recipient)

        day_lower = day.lower()
        if hasattr(schedule.every(), day_lower):
            getattr(schedule.every(), day_lower).at(time_str).do(job)
            self.logger.info(f"Scheduled preparation check on {day} at {time_str}")

    def load_schedules_from_config(self, imessage_recipient: Optional[str] = None) -> None:
        """Load all schedules from configuration.

        Args:
            imessage_recipient: Default iMessage recipient for notifications
        """
        self.logger.info("Loading schedules from configuration")

        # Daily briefing
        if self.config.get('automation.daily_briefing.enabled'):
            time_str = self.config.get('automation.daily_briefing.time', '07:00')
            self.schedule_daily_briefing(time_str, recipient=imessage_recipient)

        # Weekly review
        if self.config.get('automation.weekly_review.enabled'):
            day = self.config.get('automation.weekly_review.day', 'Sunday')
            time_str = self.config.get('automation.weekly_review.time', '18:00')
            self.schedule_weekly_review(day, time_str)

        # Playdate reminder
        if self.config.get('automation.playdate_reminder.enabled'):
            day = self.config.get('automation.playdate_reminder.day', 'Friday')
            time_str = self.config.get('automation.playdate_reminder.time', '14:00')
            self.schedule_playdate_reminder(day, time_str, recipient=imessage_recipient)

        # Show all scheduled jobs
        self.logger.info(f"Loaded {len(schedule.jobs)} scheduled job(s)")

    def run_pending(self) -> None:
        """Run all pending scheduled tasks."""
        schedule.run_pending()

    def start(self, run_in_thread: bool = True) -> None:
        """Start the scheduler.

        Args:
            run_in_thread: Run scheduler in a background thread
        """
        self.logger.info("Starting scheduler...")
        self.running = True

        def run_loop():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        if run_in_thread:
            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
            self.logger.info("Scheduler started in background thread")
        else:
            run_loop()

    def stop(self) -> None:
        """Stop the scheduler."""
        self.logger.info("Stopping scheduler...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def clear_all(self) -> None:
        """Clear all scheduled jobs."""
        schedule.clear()
        self.logger.info("Cleared all scheduled jobs")


def main():
    """Main entry point for scheduler testing."""
    scheduler = TaskScheduler()
    scheduler.load_schedules_from_config()

    print("Scheduled jobs:")
    for job in schedule.jobs:
        print(f"  - {job}")

    print("\nRunning scheduler (Ctrl+C to stop)...")
    try:
        scheduler.start(run_in_thread=False)
    except KeyboardInterrupt:
        print("\nScheduler stopped")


if __name__ == '__main__':
    main()
