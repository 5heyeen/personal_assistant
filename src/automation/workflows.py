"""Automated workflows for personal assistant."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..integrations.notion import NotionIntegration
from ..integrations.google_calendar import GoogleCalendarIntegration
from ..integrations.imessage import iMessageIntegration
from ..integrations.ticktick import TickTickIntegration
from ..utils.config import get_config
from ..utils.logger import get_logger


class WorkflowEngine:
    """Executes automated workflows for the personal assistant."""

    def __init__(self):
        """Initialize workflow engine."""
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Initialize integrations
        self.notion = NotionIntegration()
        self.calendar = None
        self.imessage = None
        self.ticktick = None

        # Initialize TickTick if enabled
        if self.config.get('ticktick.enabled', False):
            try:
                self.ticktick = TickTickIntegration()
                if not self.ticktick.is_available():
                    self.logger.warning("TickTick credentials not configured")
                    self.ticktick = None
            except Exception as e:
                self.logger.warning(f"TickTick not available: {e}")

        # Initialize Google Calendar if enabled
        if self.config.google_calendar_enabled:
            try:
                self.calendar = GoogleCalendarIntegration()
            except Exception as e:
                self.logger.warning(f"Google Calendar not available: {e}")

        # Initialize iMessage if enabled
        if self.config.imessage_enabled:
            try:
                self.imessage = iMessageIntegration()
            except Exception as e:
                self.logger.warning(f"iMessage not available: {e}")

    def daily_briefing(self, send_via_imessage: bool = False, recipient: Optional[str] = None) -> str:
        """Generate and optionally send daily briefing.

        Args:
            send_via_imessage: Whether to send via iMessage
            recipient: iMessage recipient (required if send_via_imessage=True)

        Returns:
            Briefing text
        """
        self.logger.info("Generating daily briefing")

        briefing_parts = ["📅 Daily Briefing - {}".format(datetime.now().strftime("%A, %B %d, %Y"))]

        # Get today's calendar events
        if self.calendar:
            try:
                events = self.calendar.get_todays_events()
                if events:
                    briefing_parts.append("\n🗓️ Today's Schedule:")
                    for event in events:
                        summary = self.calendar.format_event_summary(event)
                        briefing_parts.append(f"  • {summary}")
                else:
                    briefing_parts.append("\n🗓️ No events scheduled for today")
            except Exception as e:
                self.logger.error(f"Error getting calendar events: {e}")
                briefing_parts.append("\n⚠️ Could not retrieve calendar events")

        # Get tasks from TickTick
        if self.ticktick and self.ticktick.is_available():
            try:
                today_tasks = self.ticktick.get_today_tasks()
                overdue_tasks = self.ticktick.get_overdue_tasks()
                stats = self.ticktick.get_task_statistics()

                briefing_parts.append("\n✅ Tasks:")
                if overdue_tasks:
                    briefing_parts.append(f"  ⚠️ {len(overdue_tasks)} overdue task(s)")
                    for task in overdue_tasks[:3]:  # Show first 3
                        briefing_parts.append(f"    - {self.ticktick.format_task_summary(task)}")

                if today_tasks:
                    briefing_parts.append(f"  📋 {len(today_tasks)} task(s) due today")
                    for task in today_tasks[:5]:  # Show first 5
                        briefing_parts.append(f"    - {self.ticktick.format_task_summary(task)}")
                else:
                    briefing_parts.append("  ✨ No tasks due today")

                if stats.get('high_priority', 0) > 0:
                    briefing_parts.append(f"  🔴 {stats['high_priority']} high priority task(s)")

            except Exception as e:
                self.logger.error(f"Error getting TickTick tasks: {e}")
                briefing_parts.append("\n✅ Tasks: (Error loading from TickTick)")
        else:
            briefing_parts.append("\n✅ Tasks: (Configure TickTick credentials)")

        briefing_parts.append("\n🍽️ Meals: (Configure meal planning database)")

        briefing = "\n".join(briefing_parts)

        # Send via iMessage if requested
        if send_via_imessage and self.imessage and recipient:
            try:
                self.imessage.send_message(recipient, briefing)
                self.logger.info(f"Sent daily briefing to {recipient}")
            except Exception as e:
                self.logger.error(f"Error sending briefing: {e}")

        return briefing

    def weekly_review(self) -> str:
        """Generate weekly review and planning.

        Returns:
            Weekly review text
        """
        self.logger.info("Generating weekly review")

        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)

        review_parts = [
            f"📊 Weekly Review - Week of {week_start.strftime('%B %d, %Y')}"
        ]

        # Get week's events
        if self.calendar:
            try:
                events = self.calendar.get_events(
                    time_min=week_start,
                    time_max=week_end
                )
                review_parts.append(f"\n📅 This week: {len(events)} events")
            except Exception as e:
                self.logger.error(f"Error getting weekly events: {e}")

        # Get upcoming week
        next_week_start = week_end
        next_week_end = next_week_start + timedelta(days=7)

        if self.calendar:
            try:
                upcoming = self.calendar.get_events(
                    time_min=next_week_start,
                    time_max=next_week_end
                )
                review_parts.append(f"📅 Next week: {len(upcoming)} events scheduled")
            except Exception as e:
                self.logger.error(f"Error getting next week events: {e}")

        review_parts.append("\n💡 Add task completion stats by connecting task database")

        return "\n".join(review_parts)

    def advance_preparation_check(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Check for events requiring advance preparation.

        Args:
            days_ahead: How many days ahead to check

        Returns:
            List of events needing preparation
        """
        self.logger.info(f"Checking for events needing preparation ({days_ahead} days ahead)")

        if not self.calendar:
            self.logger.warning("Calendar not available for preparation check")
            return []

        lead_times = self.config.get('adhd_support.lead_times', {})

        events_needing_prep = []

        try:
            # Get upcoming events
            now = datetime.utcnow()
            end_time = now + timedelta(days=days_ahead)
            events = self.calendar.get_events(time_min=now, time_max=end_time)

            for event in events:
                summary = event.get('summary', '').lower()
                start = event.get('start', {})

                if 'dateTime' in start:
                    start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    days_until = (start_time - datetime.now().astimezone()).days

                    # Check if event needs preparation based on keywords
                    if any(keyword in summary for keyword in ['birthday', 'bday']):
                        if days_until <= lead_times.get('birthdays_days', 14):
                            events_needing_prep.append({
                                'event': event,
                                'type': 'birthday',
                                'days_until': days_until,
                                'prep_needed': 'Gift shopping/planning'
                            })

                    elif any(keyword in summary for keyword in ['travel', 'trip', 'flight']):
                        if days_until <= lead_times.get('travel_days', 30):
                            events_needing_prep.append({
                                'event': event,
                                'type': 'travel',
                                'days_until': days_until,
                                'prep_needed': 'Booking, packing, arrangements'
                            })

                    elif any(keyword in summary for keyword in ['doctor', 'dentist', 'medical', 'appointment']):
                        if days_until <= lead_times.get('medical_appointments_days', 3):
                            events_needing_prep.append({
                                'event': event,
                                'type': 'medical',
                                'days_until': days_until,
                                'prep_needed': 'Insurance, forms, questions'
                            })

            self.logger.info(f"Found {len(events_needing_prep)} events needing preparation")
            return events_needing_prep

        except Exception as e:
            self.logger.error(f"Error in preparation check: {e}")
            return []

    def send_preparation_reminders(self, recipient: Optional[str] = None) -> None:
        """Send preparation reminders via iMessage.

        Args:
            recipient: iMessage recipient
        """
        if not self.imessage or not recipient:
            self.logger.warning("iMessage or recipient not configured for reminders")
            return

        events = self.advance_preparation_check()

        if not events:
            self.logger.info("No preparation reminders to send")
            return

        message_parts = ["⏰ Advance Preparation Reminders:"]

        for item in events:
            event = item['event']
            summary = event.get('summary', 'Event')
            days = item['days_until']
            prep = item['prep_needed']

            message_parts.append(f"\n• {summary} in {days} days")
            message_parts.append(f"  Prep needed: {prep}")

        message = "\n".join(message_parts)

        try:
            self.imessage.send_message(recipient, message)
            self.logger.info(f"Sent preparation reminders to {recipient}")
        except Exception as e:
            self.logger.error(f"Error sending reminders: {e}")

    def playdate_friday_reminder(self, recipient: Optional[str] = None) -> str:
        """Generate Friday playdate planning reminder.

        Args:
            recipient: Optional iMessage recipient

        Returns:
            Reminder message
        """
        self.logger.info("Generating playdate Friday reminder")

        message = """🎮 Weekend Playdate Planning

It's Friday! Time to plan weekend playdates.

Ideas to consider:
• Check weather for outdoor activities
• Review upcoming week schedule
• Coordinate with other parents
• Plan activities/snacks

Reply with playdate plans or 'skip' to dismiss."""

        if self.imessage and recipient:
            try:
                self.imessage.send_message(recipient, message)
                self.logger.info(f"Sent playdate reminder to {recipient}")
            except Exception as e:
                self.logger.error(f"Error sending playdate reminder: {e}")

        return message


def main():
    """Main entry point for workflow testing."""
    import argparse

    parser = argparse.ArgumentParser(description='Run personal assistant workflows')
    parser.add_argument('--task', choices=['daily', 'weekly', 'prep_check'], required=True)
    parser.add_argument('--recipient', help='iMessage recipient for notifications')

    args = parser.parse_args()

    engine = WorkflowEngine()

    if args.task == 'daily':
        briefing = engine.daily_briefing(
            send_via_imessage=bool(args.recipient),
            recipient=args.recipient
        )
        print(briefing)

    elif args.task == 'weekly':
        review = engine.weekly_review()
        print(review)

    elif args.task == 'prep_check':
        events = engine.advance_preparation_check()
        print(f"Found {len(events)} events needing preparation:")
        for item in events:
            print(f"  - {item['event']['summary']}: {item['prep_needed']} ({item['days_until']} days)")


if __name__ == '__main__':
    main()
