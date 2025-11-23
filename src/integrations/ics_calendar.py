"""ICS calendar integration for Outlook/Office 365 calendars."""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from icalendar import Calendar
import recurring_ical_events

from ..utils.config import get_config
from ..utils.logger import get_logger


class ICSCalendarIntegration:
    """Handles ICS calendar feeds from Outlook/Office 365."""

    def __init__(self, ics_url: str):
        """Initialize ICS calendar integration.

        Args:
            ics_url: URL to ICS calendar feed (webcal:// or https://)
        """
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Convert webcal:// to https://
        if ics_url.startswith('webcal://'):
            ics_url = 'https://' + ics_url[9:]

        self.ics_url = ics_url

    def fetch_calendar(self) -> Optional[Calendar]:
        """Fetch ICS calendar from URL.

        Returns:
            Calendar object or None if fetch fails
        """
        try:
            response = requests.get(self.ics_url, timeout=10)
            response.raise_for_status()

            calendar = Calendar.from_ical(response.content)
            self.logger.info(f"Fetched ICS calendar from {self.ics_url}")
            return calendar

        except Exception as e:
            self.logger.error(f"Error fetching ICS calendar: {e}")
            return None

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get events for a specific date.

        Args:
            target_date: Date to query

        Returns:
            List of event dictionaries
        """
        calendar = self.fetch_calendar()
        if not calendar:
            return []

        try:
            # Use recurring_ical_events to handle recurring events
            start_date = datetime.combine(target_date, datetime.min.time())
            end_date = datetime.combine(target_date, datetime.max.time())

            events = recurring_ical_events.of(calendar).between(start_date, end_date)

            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                if formatted_event:
                    formatted_events.append(formatted_event)

            self.logger.info(f"Found {len(formatted_events)} events for {target_date}")
            return formatted_events

        except Exception as e:
            self.logger.error(f"Error parsing ICS events: {e}")
            return []

    def get_todays_events(self) -> List[Dict[str, Any]]:
        """Get events for today.

        Returns:
            List of event dictionaries
        """
        return self.get_events_for_date(date.today())

    def _format_event(self, event) -> Optional[Dict[str, Any]]:
        """Format an ICS event to standard format.

        Args:
            event: ICS event component

        Returns:
            Formatted event dictionary
        """
        try:
            # Extract basic info
            summary = str(event.get('summary', 'Untitled'))
            location = str(event.get('location', '')) if event.get('location') else None
            description = str(event.get('description', '')) if event.get('description') else None

            # Extract start/end times
            dtstart = event.get('dtstart')
            dtend = event.get('dtend')

            start_dt = None
            end_dt = None

            if dtstart:
                if isinstance(dtstart.dt, datetime):
                    start_dt = dtstart.dt
                elif isinstance(dtstart.dt, date):
                    start_dt = datetime.combine(dtstart.dt, datetime.min.time())

            if dtend:
                if isinstance(dtend.dt, datetime):
                    end_dt = dtend.dt
                elif isinstance(dtend.dt, date):
                    end_dt = datetime.combine(dtend.dt, datetime.min.time())

            return {
                'summary': summary,
                'location': location,
                'description': description,
                'start': start_dt,
                'end': end_dt,
                'source': 'ics_calendar'
            }

        except Exception as e:
            self.logger.warning(f"Error formatting event: {e}")
            return None
