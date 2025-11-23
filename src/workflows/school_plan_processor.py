"""Workflow for processing school weekly plans from iMessages."""

import re
import os
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from pathlib import Path
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

from ..integrations.imessage import iMessageIntegration
from ..integrations.ticktick_oauth import TickTickOAuth
from ..integrations.google_calendar import GoogleCalendarIntegration
from ..integrations.school_plan_scanner import SchoolPlanScanner
from ..utils.config import get_config
from ..utils.logger import get_logger


class SchoolPlanProcessor:
    """Processes school weekly plans from iMessages."""

    def __init__(self):
        """Initialize school plan processor."""
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Initialize integrations
        self.imessage = iMessageIntegration()
        self.ticktick = TickTickOAuth()
        self.calendar = GoogleCalendarIntegration()
        self.scanner = SchoolPlanScanner()

        # Check availability
        if not self.imessage.is_available():
            self.logger.warning("iMessage not available")

        if not self.ticktick.is_available():
            self.logger.warning("TickTick not available")

    def process_recent_messages(
        self,
        sender: str = "Sheyeen Liew",
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """Process recent messages from sender for school plans.

        Args:
            sender: Sender to search for (default: Sheyeen Liew)
            hours_back: How many hours back to search

        Returns:
            Dictionary with processing results
        """
        results = {
            'messages_checked': 0,
            'images_processed': 0,
            'homework_added': 0,
            'events_added': 0,
            'reminders_sent': 0,
            'errors': []
        }

        try:
            # Get messages with attachments from sender
            since = datetime.now() - timedelta(hours=hours_back)
            attachments = self.imessage.get_message_attachments(
                sender=sender,
                since=since,
                limit=20
            )

            results['messages_checked'] = len(attachments)
            self.logger.info(f"Found {len(attachments)} messages from {sender} with attachments")

            # Track processed attachments to avoid duplicates
            processed_paths = set()

            for attachment in attachments:
                attachment_path = attachment.get('attachment_path')
                if not attachment_path or attachment_path in processed_paths:
                    continue

                # Only process PDF and image files
                mime_type = attachment.get('mime_type', '')
                if not (mime_type.startswith('image/') or mime_type == 'application/pdf'):
                    continue

                # Check if filename contains "ukeplan" (case insensitive)
                filename = Path(attachment_path).name.lower()
                if 'ukeplan' not in filename:
                    continue

                # Extract child name and week from filename
                # Expected format: "Ukeplan uke 48.pdf" or similar
                child_name = self._extract_child_from_filename(filename)
                if not child_name:
                    # Default to Max if not found
                    child_name = "Max"

                # Determine week start date
                week_start = self._determine_week_start(attachment.get('date'))

                try:
                    self.logger.info(f"Processing school plan: {filename}")
                    msg_results = self.process_image_file(
                        attachment_path,
                        child_name,
                        week_start
                    )

                    results['images_processed'] += 1
                    results['homework_added'] += msg_results.get('homework_added', 0)
                    results['events_added'] += msg_results.get('events_added', 0)
                    results['reminders_sent'] += msg_results.get('reminders_sent', 0)

                    processed_paths.add(attachment_path)

                except Exception as e:
                    error_msg = f"Error processing {filename}: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error retrieving messages: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    def _extract_child_from_filename(self, filename: str) -> Optional[str]:
        """Extract child name from filename.

        Args:
            filename: Filename to parse

        Returns:
            Child name (Max or Ella) or None
        """
        filename_lower = filename.lower()
        if 'max' in filename_lower:
            return "Max"
        elif 'ella' in filename_lower:
            return "Ella"
        return None

    def _determine_week_start(self, message_date: datetime) -> date:
        """Determine the Monday of the week from message date.

        Args:
            message_date: Date the message was received

        Returns:
            Monday of the current/next week
        """
        if not message_date:
            message_date = datetime.now()

        # Get the Monday of the current week
        days_since_monday = message_date.weekday()
        week_start = message_date.date() - timedelta(days=days_since_monday)

        # If it's late in the week (Thu-Sun), assume it's for next week
        if message_date.weekday() >= 3:  # Thursday or later
            week_start += timedelta(days=7)

        return week_start

    def process_image_file(
        self,
        image_path: str,
        child_name: str,
        week_start_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Process a school plan image file.

        Args:
            image_path: Path to image file
            child_name: Name of child (Max, Ella)
            week_start_date: Starting Monday of the week (optional)

        Returns:
            Processing results
        """
        results = {
            'homework_added': 0,
            'events_added': 0,
            'reminders_sent': 0,
            'errors': []
        }

        added_items = {
            'homework': [],
            'events': []
        }

        try:
            # Extract text from image using OCR
            self.logger.info(f"Extracting text from {image_path}")
            text = self._extract_text_from_image(image_path)

            if not text:
                raise ValueError("No text extracted from image")

            self.logger.debug(f"Extracted text:\n{text}")

            # Parse homework items
            homework_items = self.scanner.extract_homework_from_text(
                text, child_name, week_start_date
            )
            self.logger.info(f"Found {len(homework_items)} homework items")

            # Parse events
            events = self.scanner.extract_events_from_text(text, child_name)
            self.logger.info(f"Found {len(events)} events")

            # Add homework to TickTick
            for item in homework_items:
                try:
                    task_title = self.scanner.format_task_title(item)
                    self._add_homework_to_ticktick(item)
                    results['homework_added'] += 1

                    # Add title with full description for SMS (truncate at 100 chars if needed)
                    description = item.get('description', '')
                    if len(description) > 100:
                        desc_snippet = description[:100] + '...'
                    else:
                        desc_snippet = description

                    sms_summary = f"{task_title} - {desc_snippet}" if desc_snippet else task_title
                    added_items['homework'].append(sms_summary)
                except Exception as e:
                    error_msg = f"Error adding homework: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)

            # Add events to calendars
            for event in events:
                try:
                    child = event.get('child', '')
                    event_title = self._format_event_title(event)
                    date_text = event.get('date_text', '')
                    hour = event.get('hour', 8)
                    minute = event.get('minute', 0)

                    self._add_event_to_calendars(event)
                    results['events_added'] += 1

                    # Add clean event name with day, date, and time for SMS
                    event_date = self._parse_norwegian_date(date_text)
                    if event_date:
                        # Get day of week in Norwegian
                        day_names = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']
                        day_name = day_names[event_date.weekday()]
                        time_str = f"{hour:02d}:{minute:02d}"
                        event_summary = f"{event_title} ({day_name} {date_text} kl. {time_str})"
                    else:
                        event_summary = f"{event_title} ({date_text})"

                    added_items['events'].append(event_summary)
                except Exception as e:
                    error_msg = f"Error adding event: {e}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)

            # Send single summary SMS
            if added_items['homework'] or added_items['events']:
                self._send_summary_sms(child_name, week_start_date, added_items)
                results['reminders_sent'] = 1

        except Exception as e:
            error_msg = f"Error processing image {image_path}: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    def _extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image or PDF using OCR.

        Args:
            image_path: Path to image or PDF file

        Returns:
            Extracted text with sections separated
        """
        try:
            # Check if it's a PDF
            if image_path.lower().endswith('.pdf'):
                return self._extract_text_from_pdf(image_path)

            # Open image
            image = Image.open(image_path)

            # Extract text from two-column layout
            return self._extract_text_two_column(image)

        except Exception as e:
            self.logger.error(f"Error extracting text from {image_path}: {e}")
            raise

    def _extract_text_two_column(self, image: Image.Image) -> str:
        """Extract text from two-column layout (Mine lekser | Beskjeder).

        Args:
            image: PIL Image object

        Returns:
            Text with sections marked
        """
        try:
            width, height = image.size
            mid_x = width // 2

            # Split into left and right columns
            left_column = image.crop((0, 0, mid_x, height))
            right_column = image.crop((mid_x, 0, width, height))

            # OCR each column separately
            left_text = pytesseract.image_to_string(
                left_column,
                lang='nor+eng',
                config='--psm 6'
            ).strip()

            right_text = pytesseract.image_to_string(
                right_column,
                lang='nor+eng',
                config='--psm 6'
            ).strip()

            # Mark sections clearly
            combined_text = f"=== MINE LEKSER ===\n{left_text}\n\n=== BESKJEDER ===\n{right_text}"

            return combined_text

        except Exception as e:
            self.logger.error(f"Error extracting two-column text: {e}")
            # Fall back to single-column extraction
            return pytesseract.image_to_string(
                image,
                lang='nor+eng',
                config='--psm 6'
            ).strip()

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using OCR.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text from all pages
        """
        try:
            self.logger.info(f"Converting PDF to images: {pdf_path}")

            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)

            all_text = []
            for i, image in enumerate(images):
                self.logger.debug(f"Processing page {i+1}/{len(images)}")

                # Use two-column extraction for each page
                text = self._extract_text_two_column(image)
                all_text.append(text)

            # Combine all pages
            combined_text = '\n\n=== PAGE BREAK ===\n\n'.join(all_text)
            return combined_text

        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise

    def _add_homework_to_ticktick(self, item: Dict[str, Any]) -> None:
        """Add homework item to TickTick.

        Args:
            item: Homework item dictionary
        """
        if not self.ticktick.is_available():
            raise ValueError("TickTick not available")

        # Find or create "Homework" project
        project = self.ticktick.find_project_by_name("Homework")
        if not project:
            project = self.ticktick.create_project("Homework")

        if not project:
            raise ValueError("Could not find or create Homework project")

        project_id = project.get('id')

        # Format task title
        task_title = self.scanner.format_task_title(item)

        # Check for duplicates (check both title and due date)
        due_date = item.get('due_date')
        if self._task_exists_with_due_date(task_title, project_id, due_date):
            self.logger.info(f"Task already exists, skipping: {task_title} (due {due_date})")
            return

        # Get due date
        due_date = item.get('due_date')
        if due_date and isinstance(due_date, date):
            # Convert date to datetime at 23:00
            due_datetime = datetime.combine(due_date, datetime.min.time())
            due_datetime = due_datetime.replace(hour=23, minute=0)
        else:
            due_datetime = None

        # Create task with description in content field
        content = None
        if item['type'] == 'homework':
            content = item.get('description', '')

        # Check if this is a Norsk task - make it recurring
        repeat_rule = None
        if item['type'] == 'homework' and 'norsk' in item.get('subject', '').lower():
            # Recur daily except Friday and Sunday (Mon, Tue, Wed, Thu, Sat)
            repeat_rule = "FREQ=DAILY;BYDAY=MO,TU,WE,TH,SA"

        self.ticktick.create_task(
            title=task_title,
            project_id=project_id,
            due_date=due_datetime,
            priority=0,
            content=content,
            repeat_rule=repeat_rule
        )

        self.logger.info(f"Added to TickTick: {task_title}")

    def _task_exists_with_due_date(
        self,
        title: str,
        project_id: str,
        due_date: Optional[date]
    ) -> bool:
        """Check if task exists with specific title and due date.

        Args:
            title: Task title
            project_id: Project ID
            due_date: Due date to check

        Returns:
            True if task exists with same title and due date
        """
        all_tasks = self.ticktick.get_all_tasks()

        for task in all_tasks:
            if task.get('title', '').lower() == title.lower():
                if task.get('projectId') == project_id:
                    # Check due date
                    task_due = task.get('dueDate')
                    if due_date and task_due:
                        task_date = self.ticktick._parse_ticktick_date(task_due).date()
                        if task_date == due_date:
                            return True
                    elif not due_date and not task_due:
                        return True

        return False

    def _format_event_title(self, event: Dict[str, Any]) -> str:
        """Format event title from event data.

        Args:
            event: Event dictionary

        Returns:
            Formatted event title like "Max: Juleavslutning"
        """
        child = event.get('child', '')
        description = event.get('description', '')

        # Extract event name - skip bullet points and special characters
        words = description.split()
        event_name = None

        for word in words:
            # Skip bullet points and short special characters
            if len(word) <= 2 or word in ['¢', '•', '*', '-', '·']:
                continue
            # Skip common Norwegian words that aren't event names
            if word.lower() in ['blir', 'er', 'på', 'i', 'kl.', 'klokken']:
                continue
            # Found the event name
            event_name = word.rstrip('en')  # Remove -en suffix
            break

        if not event_name:
            # Fallback - use first word longer than 2 chars
            for word in words:
                if len(word) > 2:
                    event_name = word.rstrip('en')
                    break

        if not event_name:
            event_name = "Event"

        return f"{child}: {event_name}"

    def _add_event_to_calendars(self, event: Dict[str, Any]) -> None:
        """Add event to Handeliew events Google Calendar.

        Args:
            event: Event dictionary
        """
        # Extract event details
        date_text = event.get('date_text', '')
        hour = event.get('hour', 8)
        minute = event.get('minute', 0)

        # Parse Norwegian date
        event_date = self._parse_norwegian_date(date_text)
        if not event_date:
            self.logger.warning(f"Could not parse date: {date_text}")
            return

        # Get event title
        event_title = self._format_event_title(event)

        # Create datetime
        start_datetime = datetime.combine(event_date, datetime.min.time())
        start_datetime = start_datetime.replace(hour=hour, minute=minute)
        end_datetime = start_datetime + timedelta(hours=1)  # Default 1hr

        # Get "Handeliew events" calendar ID
        handeliew_calendar_id = self._get_handeliew_calendar_id()
        if not handeliew_calendar_id:
            self.logger.error("Could not find 'Handeliew events' calendar")
            return

        # Check if event already exists in this calendar
        if self._event_exists_in_calendar(event_title, start_datetime, handeliew_calendar_id):
            self.logger.info(f"Event already exists, skipping: {event_title}")
            return

        # Add to Handeliew events Google Calendar
        if self.calendar.is_available():
            calendar_event = {
                'summary': event_title,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Oslo',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Oslo',
                },
            }

            self.calendar.create_event(event_data=calendar_event, calendar_id=handeliew_calendar_id)
            self.logger.info(f"Added event to Handeliew events calendar: {event_title}")

    def _parse_norwegian_date(self, date_text: str) -> Optional[date]:
        """Parse Norwegian date like '9.desember' or '9 des'.

        Args:
            date_text: Date text in Norwegian

        Returns:
            Parsed date or None
        """
        import re

        # Norwegian month names
        months = {
            'januar': 1, 'jan': 1,
            'februar': 2, 'feb': 2,
            'mars': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'mai': 5,
            'juni': 6, 'jun': 6,
            'juli': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'oktober': 10, 'okt': 10,
            'november': 11, 'nov': 11,
            'desember': 12, 'des': 12
        }

        # Extract day and month
        match = re.search(r'(\d{1,2})[\.\s]+(\w+)', date_text, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()

            if month_str in months:
                month = months[month_str]
                # Use current year or next year if month has passed
                today = date.today()
                year = today.year
                try:
                    event_date = date(year, month, day)
                    # If date is in the past, use next year
                    if event_date < today:
                        event_date = date(year + 1, month, day)
                    return event_date
                except ValueError:
                    pass

        return None

    def _get_handeliew_calendar_id(self) -> Optional[str]:
        """Get the calendar ID for 'Handeliew events' calendar.

        Returns:
            Calendar ID or None if not found
        """
        if not self.calendar.is_available():
            return None

        try:
            # Get all calendars
            calendars = self.calendar.service.calendarList().list().execute()

            # Find "Handeliew events" calendar
            for calendar in calendars.get('items', []):
                if calendar.get('summary', '').lower() == 'handeliew events':
                    return calendar.get('id')

            self.logger.warning("Could not find 'Handeliew events' calendar")
            return None

        except Exception as e:
            self.logger.error(f"Error finding Handeliew events calendar: {e}")
            return None

    def _event_exists_in_calendar(
        self,
        event_title: str,
        start_datetime: datetime,
        calendar_id: str
    ) -> bool:
        """Check if event already exists in specific calendar.

        Args:
            event_title: Event title
            start_datetime: Event start time
            calendar_id: Calendar ID to check

        Returns:
            True if event exists
        """
        if not self.calendar.is_available():
            return False

        # Get events for that day
        start_of_day = datetime.combine(start_datetime.date(), datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)

        try:
            events = self.calendar.service.events().list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True
            ).execute()

            for event in events.get('items', []):
                if event.get('summary', '').lower() == event_title.lower():
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking for existing event: {e}")
            return False

    def _send_summary_sms(
        self,
        child_name: str,
        week_start_date: Optional[date],
        added_items: Dict[str, list]
    ) -> None:
        """Send summary SMS with all added items.

        Args:
            child_name: Name of child
            week_start_date: Week start date
            added_items: Dictionary with homework, prep, and events lists
        """
        if not self.imessage.is_available():
            return

        # Determine week number
        if week_start_date:
            week_num = week_start_date.isocalendar()[1]
        else:
            week_num = date.today().isocalendar()[1]

        # Build message
        message_lines = [f"Added from {child_name}'s Ukeplan Week {week_num}"]
        message_lines.append("")  # Blank line

        # Add homework items (deduplicate)
        homework_unique = list(set(added_items['homework']))
        if homework_unique:
            message_lines.append("Homework:")
            for hw in homework_unique:
                message_lines.append(f"• {hw}")

        # Add events
        if added_items['events']:
            if homework_unique:
                message_lines.append("")  # Blank line
            message_lines.append("Events:")
            for event in added_items['events']:
                message_lines.append(f"• {event}")

        message = "\n".join(message_lines)

        # Send to configured recipient
        recipient = self.config.get('personal.phone', '+4740516916')
        self.imessage.send_message(recipient, message)

        self.logger.info(f"Sent summary SMS:\n{message}")
