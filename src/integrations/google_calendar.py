"""Google Calendar integration for personal assistant."""

import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.config import get_config
from ..utils.logger import get_logger


# Scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarIntegration:
    """Handles Google Calendar API interactions."""

    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """Initialize Google Calendar integration.

        Args:
            credentials_file: Path to credentials.json
            token_file: Path to token.json
        """
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Set default paths
        if credentials_file is None:
            credentials_file = self.config.base_dir / self.config.get(
                'google_calendar.credentials_file', 'credentials.json'
            )
        if token_file is None:
            token_file = self.config.base_dir / self.config.get(
                'google_calendar.token_file', 'token.json'
            )

        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.calendar_id = self.config.get('google_calendar.calendar_id', 'primary')

        # Authenticate and build service
        self.service = self._build_service()

    def _build_service(self):
        """Build Google Calendar API service with authentication."""
        creds = None

        # Load token if it exists
        if self.token_file.exists():
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Refreshing Google Calendar credentials")
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise FileNotFoundError(
                        f"Google Calendar credentials not found at {self.credentials_file}. "
                        "Please download credentials.json from Google Cloud Console."
                    )

                self.logger.info("Initiating Google Calendar OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
                self.logger.info(f"Saved credentials to {self.token_file}")

        # Build service
        try:
            service = build('calendar', 'v3', credentials=creds)
            self.logger.info("Successfully connected to Google Calendar API")
            return service
        except Exception as e:
            self.logger.error(f"Error building Google Calendar service: {e}")
            raise

    def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 100,
        single_events: bool = True,
        order_by: str = 'startTime'
    ) -> List[Dict[str, Any]]:
        """Get calendar events within a time range.

        Args:
            time_min: Start of time range (defaults to now)
            time_max: End of time range
            max_results: Maximum number of events to return
            single_events: Expand recurring events
            order_by: How to order results ('startTime' or 'updated')

        Returns:
            List of event dictionaries
        """
        try:
            if time_min is None:
                time_min = datetime.utcnow()

            params = {
                'calendarId': self.calendar_id,
                'timeMin': time_min.isoformat() + 'Z',
                'maxResults': max_results,
                'singleEvents': single_events,
                'orderBy': order_by
            }

            if time_max:
                params['timeMax'] = time_max.isoformat() + 'Z'

            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])

            self.logger.debug(f"Retrieved {len(events)} events")
            return events

        except HttpError as error:
            self.logger.error(f"Google Calendar API error: {error}")
            raise

    def get_todays_events(self) -> List[Dict[str, Any]]:
        """Get all events for today.

        Returns:
            List of today's events
        """
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return self.get_events(time_min=start_of_day, time_max=end_of_day)

    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        end_time = now + timedelta(days=days)

        return self.get_events(time_min=now, time_max=end_time)

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            reminders: Reminder settings

        Returns:
            Created event data
        """
        try:
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC'
                }
            }

            if description:
                event['description'] = description

            if location:
                event['location'] = location

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            if reminders:
                event['reminders'] = reminders
            else:
                # Default reminders
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30}
                    ]
                }

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            self.logger.info(f"Created event: {summary} at {start_time}")
            return created_event

        except HttpError as error:
            self.logger.error(f"Error creating event: {error}")
            raise

    def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing calendar event.

        Args:
            event_id: Event ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated event data
        """
        try:
            # Get current event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            # Apply updates
            event.update(updates)

            # Update event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            self.logger.info(f"Updated event: {event_id}")
            return updated_event

        except HttpError as error:
            self.logger.error(f"Error updating event: {error}")
            raise

    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event.

        Args:
            event_id: Event ID to delete
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            self.logger.info(f"Deleted event: {event_id}")

        except HttpError as error:
            self.logger.error(f"Error deleting event: {error}")
            raise

    def search_events(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for events by query string.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of matching events
        """
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            self.logger.debug(f"Found {len(events)} events matching '{query}'")
            return events

        except HttpError as error:
            self.logger.error(f"Error searching events: {error}")
            raise

    def get_free_busy(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get free/busy information for calendars.

        Args:
            time_min: Start of time range
            time_max: End of time range
            calendar_ids: List of calendar IDs (defaults to primary)

        Returns:
            Free/busy data
        """
        try:
            if calendar_ids is None:
                calendar_ids = [self.calendar_id]

            body = {
                'timeMin': time_min.isoformat() + 'Z',
                'timeMax': time_max.isoformat() + 'Z',
                'items': [{'id': cal_id} for cal_id in calendar_ids]
            }

            result = self.service.freebusy().query(body=body).execute()
            self.logger.debug("Retrieved free/busy information")
            return result

        except HttpError as error:
            self.logger.error(f"Error getting free/busy: {error}")
            raise

    def format_event_summary(self, event: Dict[str, Any]) -> str:
        """Format an event into a readable summary.

        Args:
            event: Event dictionary

        Returns:
            Formatted event summary
        """
        summary = event.get('summary', 'No title')

        # Parse start time
        start = event.get('start', {})
        if 'dateTime' in start:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            time_str = start_time.strftime('%I:%M %p')
        elif 'date' in start:
            time_str = 'All day'
        else:
            time_str = 'Unknown time'

        # Get location if available
        location = event.get('location', '')
        location_str = f" at {location}" if location else ""

        return f"{summary} - {time_str}{location_str}"
