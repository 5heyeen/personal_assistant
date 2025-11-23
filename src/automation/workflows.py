"""Automated workflows for personal assistant."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..integrations.notion import NotionIntegration
from ..integrations.google_calendar import GoogleCalendarIntegration
from ..integrations.imessage import iMessageIntegration
from ..integrations.ticktick import TickTickIntegration
from ..integrations.ticktick_oauth import TickTickOAuth
from ..integrations.meal_planning import MealPlanningIntegration
from ..integrations.ics_calendar import ICSCalendarIntegration
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
        self.meal_planning = None
        self.work_calendar = None

        # Initialize TickTick if enabled (try OAuth first, then password)
        if self.config.get('ticktick.enabled', False):
            try:
                # Try OAuth first (for passkey/social login users)
                self.ticktick = TickTickOAuth()
                if not self.ticktick.is_available():
                    self.logger.info("TickTick OAuth not available, trying password auth...")
                    # Fall back to password authentication
                    self.ticktick = TickTickIntegration()
                    if not self.ticktick.is_available():
                        self.logger.warning("TickTick credentials not configured")
                        self.ticktick = None
                else:
                    self.logger.info("Using TickTick OAuth authentication")
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

        # Initialize meal planning
        try:
            self.meal_planning = MealPlanningIntegration()
            if not self.meal_planning.is_available():
                self.logger.info("Meal planning database not configured")
                self.meal_planning = None
        except Exception as e:
            self.logger.warning(f"Meal planning not available: {e}")

        # Initialize work calendar (ICS feed)
        work_ics_url = self.config.get('personal.work_ics_url')
        if work_ics_url:
            try:
                self.work_calendar = ICSCalendarIntegration(work_ics_url)
                self.logger.info("Initialized work calendar integration")
            except Exception as e:
                self.logger.warning(f"Work calendar not available: {e}")

    def daily_briefing(self, send_via_imessage: bool = False, recipient: Optional[str] = None) -> str:
        """Generate and optionally send daily briefing.

        Args:
            send_via_imessage: Whether to send via iMessage
            recipient: iMessage recipient (required if send_via_imessage=True)

        Returns:
            Briefing text
        """
        self.logger.info("Generating daily briefing")

        # Get personalization from config
        greeting_name = self.config.get('personal.greeting_name', 'there')
        location = {
            'latitude': self.config.get('personal.location.latitude', 59.9139),
            'longitude': self.config.get('personal.location.longitude', 10.7522)
        }

        briefing_parts = [f"Hello {greeting_name}!"]

        # Weather section
        try:
            from ..integrations.weather import WeatherIntegration
            weather = WeatherIntegration(
                latitude=location.get('latitude', 59.9139),
                longitude=location.get('longitude', 10.7522)
            )
            forecast = weather.get_today_forecast()

            if forecast:
                # Compact weather summary on one line
                temp_min = int(forecast.get('temp_min', 0))
                temp_max = int(forecast.get('temp_max', 0))
                rain_summary = weather.format_rain_summary(forecast)

                weather_line = f"☀️ {temp_min}-{temp_max}°C"
                if rain_summary:
                    weather_line += f", 💧 {rain_summary}"

                briefing_parts.append(weather_line)

                # Weather advice
                temp_advice = weather.get_temperature_advice(forecast)
                if temp_advice:
                    for advice in temp_advice:
                        briefing_parts.append(advice)

                if rain_summary:
                    briefing_parts.append(f"Expect some rain around {rain_summary} - bring an umbrella! ☂️")
        except Exception as e:
            self.logger.warning(f"Weather not available: {e}")
            briefing_parts.append("☀️ Weather unavailable")

        # Get calendar events first (needed for reminders)
        all_events = []
        family_events = []
        reminder_events = []

        if self.calendar:
            try:
                # Get events from personal calendar
                personal_events = self.calendar.get_todays_events()
                all_events.extend(personal_events)

                # Get events from family calendar
                family_calendar_id = self.config.get('personal.family_calendar_id')
                if family_calendar_id:
                    try:
                        now = datetime.utcnow()
                        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                        end_of_day = start_of_day + timedelta(days=1)

                        family_events = self.calendar.get_events(
                            time_min=start_of_day,
                            time_max=end_of_day,
                            calendar_id=family_calendar_id
                        )

                        # Extract reminders from family calendar
                        for event in family_events:
                            summary = event.get('summary', '')
                            # Check if it's a reminder (starts with Max:, Ella:, or Husk!)
                            if any(summary.startswith(prefix) for prefix in ['Max:', 'Ella:', 'Husk!']):
                                reminder_events.append(event)
                            else:
                                # Regular event
                                all_events.append(event)

                    except Exception as e:
                        self.logger.warning(f"Could not get family calendar events: {e}")

            except Exception as e:
                self.logger.error(f"Error getting calendar events: {e}")

        # Get work calendar events (ICS feed)
        if self.work_calendar:
            try:
                from datetime import date
                work_events = self.work_calendar.get_events_for_date(date.today())

                # Convert ICS events to Google Calendar format for consistent display
                for event in work_events:
                    formatted_event = {
                        'summary': event.get('summary', 'Untitled'),
                        'location': event.get('location'),
                        'description': event.get('description')
                    }

                    # Format start/end times
                    start_dt = event.get('start')
                    end_dt = event.get('end')

                    if start_dt:
                        if isinstance(start_dt, datetime):
                            formatted_event['start'] = {'dateTime': start_dt.isoformat()}
                        else:
                            formatted_event['start'] = {'date': start_dt.isoformat()}

                    if end_dt:
                        if isinstance(end_dt, datetime):
                            formatted_event['end'] = {'dateTime': end_dt.isoformat()}
                        else:
                            formatted_event['end'] = {'date': end_dt.isoformat()}

                    all_events.append(formatted_event)

                self.logger.info(f"Added {len(work_events)} work calendar events")
            except Exception as e:
                self.logger.warning(f"Could not get work calendar events: {e}")

        # Reminders section
        briefing_parts.append("\n🔔 REMINDERS:")
        if reminder_events:
            for reminder in reminder_events:
                summary = reminder.get('summary', '')
                briefing_parts.append(f"- {summary}")
        else:
            briefing_parts.append("- No reminders for today")

        # Calendar events section
        briefing_parts.append("\n📅 YOUR DAY AHEAD:")

        if self.calendar:
            try:
                # Get rain warnings for events
                rain_warnings = {}
                try:
                    if forecast:
                        rain_warnings = weather.get_rain_warnings_for_events(forecast, all_events)
                except:
                    pass

                if all_events:
                    # Sort events by start time
                    sorted_events = sorted(all_events, key=lambda e: e.get('start', {}).get('dateTime', ''))

                    for event in sorted_events:
                        start = event.get('start', {})
                        end = event.get('end', {})
                        summary = event.get('summary', 'Untitled')
                        location_str = event.get('location', '')

                        # Parse datetime
                        start_time = None
                        end_time = None
                        is_all_day = False

                        if 'dateTime' in start:
                            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        elif 'date' in start:
                            is_all_day = True

                        if 'dateTime' in end:
                            end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))

                        # Determine if indoor/outdoor
                        indoor_outdoor = ""
                        if location_str:
                            if any(word in location_str.lower() for word in ['indoor', 'office', 'room', 'building']):
                                indoor_outdoor = " (indoors)"
                            elif any(word in location_str.lower() for word in ['outdoor', 'park', 'field', 'rødtangen']):
                                indoor_outdoor = " (outdoors)"
                        else:
                            indoor_outdoor = " (indoors)"

                        # Format time
                        time_str = ""
                        if is_all_day:
                            time_str = "All day"
                        elif start_time and end_time:
                            time_str = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                        elif start_time:
                            time_str = start_time.strftime('%H:%M')

                        # Build event line
                        event_line = f"{time_str} {summary}"
                        if location_str:
                            event_line += f" at {location_str}"
                        event_line += indoor_outdoor

                        # Add rain warning if applicable
                        if summary in rain_warnings:
                            event_line += f": **{rain_warnings[summary]}** Light rain expected"

                        briefing_parts.append(event_line)
                else:
                    briefing_parts.append("No events scheduled for today")

            except Exception as e:
                self.logger.error(f"Error getting calendar events: {e}")
                briefing_parts.append("⚠️ Could not retrieve calendar events")

        # Extract Magnus-specific events from family calendar
        magnus_events = []
        for event in family_events:
            summary = event.get('summary', '').lower()
            # Only look for events with "magnus" in the name
            if 'magnus' in summary:
                magnus_events.append(event)

        # Format Magnus's schedule (only show if there are events)
        if magnus_events:
            magnus_lines = []
            for event in magnus_events:
                start = event.get('start', {})
                end = event.get('end', {})
                summary = event.get('summary', '')

                start_time = None
                end_time = None
                if 'dateTime' in start:
                    start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                if 'dateTime' in end:
                    end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))

                if start_time and end_time:
                    time_str = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                    magnus_lines.append(f"{summary} {time_str}")

            if magnus_lines:
                briefing_parts.append("\nMagnus: " + ", ".join(magnus_lines))

        # Meals section
        briefing_parts.append("\n🍽️ Meals:")
        if self.meal_planning:
            try:
                todays_meals = self.meal_planning.get_todays_meals()
                if todays_meals:
                    for meal in todays_meals:
                        meal_summary = self.meal_planning.format_meal_summary(meal)
                        briefing_parts.append(f"  • {meal_summary}")
                else:
                    briefing_parts.append("  No meals planned for today")
            except Exception as e:
                self.logger.error(f"Error getting meals: {e}")
                briefing_parts.append("  (Error loading meal plan)")
        else:
            briefing_parts.append("  (Configure meal planning database)")

        # Tasks section - show individual tasks with inline status
        if self.ticktick and self.ticktick.is_available():
            try:
                today_tasks = self.ticktick.get_today_tasks()
                overdue_tasks = self.ticktick.get_overdue_tasks()

                briefing_parts.append("\n✅ Tasks:")

                # Show today's high priority tasks first
                priority_tasks = []
                for task in today_tasks:
                    if task.get('priority', 0) == 5:  # High priority
                        priority_tasks.append(task)

                for task in priority_tasks[:2]:  # Top 2 high priority
                    title = task.get('title', 'Untitled')
                    due_time = ""
                    if 'due_date' in task:
                        due_time = f" (due today {task['due_date'].strftime('%H:%M')})"
                    briefing_parts.append(f"  🔴 {title}{due_time}")

                # Show some overdue tasks
                for task in overdue_tasks[:3]:
                    title = task.get('title', 'Untitled')
                    briefing_parts.append(f"  - {title} (overdue)")

                # Show remaining today tasks
                shown_titles = {t.get('title') for t in priority_tasks[:2]}
                for task in today_tasks[:3]:
                    title = task.get('title', 'Untitled')
                    if title not in shown_titles:
                        due_time = ""
                        if 'due_date' in task:
                            due_time = f" (due today {task['due_date'].strftime('%H:%M')})"
                        briefing_parts.append(f"  - {title}{due_time}")

            except Exception as e:
                self.logger.error(f"Error getting TickTick tasks: {e}")
                briefing_parts.append("\n✅ Tasks: (Error loading from TickTick)")
        else:
            briefing_parts.append("\n✅ Tasks: (Configure TickTick credentials)")

        briefing = "\n".join(briefing_parts)

        # Send via iMessage if requested
        if send_via_imessage and self.imessage and recipient:
            try:
                self.imessage.send_message(recipient, briefing)
                self.logger.info(f"Sent daily briefing to {recipient}")
            except Exception as e:
                self.logger.error(f"Error sending briefing: {e}")

        return briefing

    def weekly_briefing(self, send_via_imessage: bool = False, recipient: Optional[str] = None) -> str:
        """Generate and optionally send weekly briefing.

        Args:
            send_via_imessage: Whether to send via iMessage
            recipient: iMessage recipient (required if send_via_imessage=True)

        Returns:
            Briefing text
        """
        self.logger.info("Generating weekly briefing")

        briefing_parts = ["Hello gorgeous,", "🗓️ HERE'S YOUR WEEK AHEAD:"]

        # Get events for the next 7 days
        from datetime import date
        today = date.today()

        # Collect events by day
        events_by_day = {}

        for day_offset in range(7):
            target_date = today + timedelta(days=day_offset)
            events_by_day[target_date] = []

            # Get personal calendar events
            if self.calendar:
                try:
                    start_of_day = datetime.combine(target_date, datetime.min.time())
                    end_of_day = start_of_day + timedelta(days=1)

                    personal_events = self.calendar.get_events(
                        time_min=start_of_day,
                        time_max=end_of_day
                    )
                    events_by_day[target_date].extend(personal_events)

                    # Get family calendar events
                    family_calendar_id = self.config.get('personal.family_calendar_id')
                    if family_calendar_id:
                        family_events = self.calendar.get_events(
                            time_min=start_of_day,
                            time_max=end_of_day,
                            calendar_id=family_calendar_id
                        )
                        # Filter out reminders (Max:, Ella:, Husk!)
                        for event in family_events:
                            summary = event.get('summary', '')
                            if not any(summary.startswith(prefix) for prefix in ['Max:', 'Ella:', 'Husk!']):
                                events_by_day[target_date].append(event)

                except Exception as e:
                    self.logger.warning(f"Error getting calendar events for {target_date}: {e}")

            # Get work calendar events
            if self.work_calendar:
                try:
                    work_events = self.work_calendar.get_events_for_date(target_date)

                    # Convert to standard format
                    for event in work_events:
                        formatted_event = {
                            'summary': event.get('summary', 'Untitled'),
                            'location': event.get('location'),
                            'start': {},
                            'end': {}
                        }

                        start_dt = event.get('start')
                        end_dt = event.get('end')

                        if start_dt and isinstance(start_dt, datetime):
                            formatted_event['start']['dateTime'] = start_dt.isoformat()
                        if end_dt and isinstance(end_dt, datetime):
                            formatted_event['end']['dateTime'] = end_dt.isoformat()

                        events_by_day[target_date].append(formatted_event)

                except Exception as e:
                    self.logger.warning(f"Error getting work events for {target_date}: {e}")

        # Format the weekly briefing
        for target_date in sorted(events_by_day.keys()):
            events = events_by_day[target_date]

            if events:
                # Day header
                day_name = target_date.strftime('%A')
                day_num = int(target_date.strftime('%d'))
                month_abbr = target_date.strftime('%b')

                # Get ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
                if 10 <= day_num % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day_num % 10, 'th')

                briefing_parts.append(f"\n{day_name} {day_num}{suffix} {month_abbr}:")

                # Sort events by start time
                sorted_events = sorted(
                    events,
                    key=lambda e: e.get('start', {}).get('dateTime', e.get('start', {}).get('date', ''))
                )

                # Cross-reference: If we see "Privat avtale", find matching Google Calendar event
                # Create a map of time -> event name from non-work events
                time_to_event_map = {}
                for event in sorted_events:
                    summary = event.get('summary', '')
                    start = event.get('start', {})
                    source = event.get('source', '')

                    # Only map non-"Privat avtale" events
                    if summary != 'Privat avtale' and 'dateTime' in start:
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        # Use hour+minute as key for matching
                        time_key = (start_time.hour, start_time.minute)
                        if time_key not in time_to_event_map:
                            time_to_event_map[time_key] = summary

                for event in sorted_events:
                    summary = event.get('summary', 'Untitled')
                    start = event.get('start', {})
                    end = event.get('end', {})

                    # Skip events starting with "Sheyeen: "
                    if summary.startswith('Sheyeen: '):
                        continue

                    # Parse times
                    if 'dateTime' in start and 'dateTime' in end:
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))

                        # Cross-reference "Privat avtale" with Google Calendar
                        display_summary = summary
                        if summary == 'Privat avtale':
                            time_key = (start_time.hour, start_time.minute)
                            if time_key in time_to_event_map:
                                display_summary = time_to_event_map[time_key]
                                # Skip if we already have this event from Google Calendar
                                continue

                        time_str = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                        briefing_parts.append(f"{time_str} {display_summary}")
                    elif 'dateTime' in start:
                        start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                        briefing_parts.append(f"{start_time.strftime('%H:%M')} {summary}")
                    else:
                        # Skip all-day events starting with Max/Ella prefixes
                        if any(summary.startswith(prefix) for prefix in ['Max: ', 'Ella: ', 'Max & Ella: ']):
                            continue
                        briefing_parts.append(f"All day: {summary}")

        briefing = "\n".join(briefing_parts)

        # Send via iMessage if requested
        if send_via_imessage and self.imessage and recipient:
            try:
                self.imessage.send_message(recipient, briefing)
                self.logger.info(f"Sent weekly briefing to {recipient}")
            except Exception as e:
                self.logger.error(f"Error sending weekly briefing: {e}")

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
