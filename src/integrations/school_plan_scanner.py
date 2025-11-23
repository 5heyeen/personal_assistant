"""School plan scanner for extracting homework and events from iMessage Ukeplan images."""

import re
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..utils.config import get_config
from ..utils.logger import get_logger


class SchoolPlanScanner:
    """Scans iMessages for school weekly plans and extracts homework/events."""

    def __init__(self):
        """Initialize school plan scanner."""
        self.config = get_config()
        self.logger = get_logger(__name__)

    def extract_homework_from_text(
        self,
        text: str,
        child_name: str,
        week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Extract homework items from Ukeplan text.

        Args:
            text: OCR text from Ukeplan image
            child_name: Name of child (Max, Ella)
            week_start_date: Starting Monday of the week

        Returns:
            List of homework task dictionaries
        """
        homework_items = []

        # If no week start provided, use next Monday
        if week_start_date is None:
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            week_start_date = today + timedelta(days=days_until_monday)

        # Extract only from "MINE LEKSER" section
        mine_lekser_text = self._extract_section(text, "MINE LEKSER")
        if not mine_lekser_text:
            # Fall back to full text if section markers not found
            mine_lekser_text = text

        lines = mine_lekser_text.split('\n')
        current_subject = None
        current_desc_lines = []

        # Stop words that indicate we've left the homework section
        stop_patterns = [
            r'^\s*[*¢•]\s*',  # Bullet points (usually in Beskjeder)
            r'ukens?\s+m[åa]l',  # Ukens mål section
            r'^\s*===',  # Section markers
            r'^\s*Gr\.\d+:',  # Grade groupings (bottom left box)
            r'^\s*TSO:',  # Schedule codes (bottom left box)
            r'^\s*[A-Z]{2,3}\s*$',  # Short codes like "LL", "TSO", "WWW"
            r'gymtøy',  # PE equipment mentions
            r'^\s*\d+\s*$',  # Standalone numbers
            r'=\s*\|',  # Box borders/separators
            r'^[A-Z][a-zæøå]+:\s+Jeg\s+(vet|kan|kjenner)',  # Ukens mål statements like "Norsk: Jeg vet..."
            r'^\s*[EWwgN]\s*\|',  # Column markers
        ]

        # Homework subjects
        subjects = ['Norsk', 'Norwegian', 'Matematikk', 'Matte', 'Math', 'Musikk',
                   'Music', 'Engelsk', 'English', 'Lesing', 'Reading']
        subject_pattern = r'^(' + '|'.join(subjects) + r'):\s*(.*)$'

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check if this line should stop current subject
            should_stop = False
            for stop_pat in stop_patterns:
                if re.search(stop_pat, line, re.IGNORECASE):
                    should_stop = True
                    break

            if should_stop:
                # Save current subject if we have one
                if current_subject and current_desc_lines:
                    task_desc = ' '.join(current_desc_lines)
                    if len(task_desc) >= 10:
                        due_dates = self._determine_due_dates(current_subject, task_desc, week_start_date)
                        for due_date in due_dates:
                            homework_items.append({
                                'child': child_name,
                                'subject': current_subject,
                                'description': task_desc,
                                'due_date': due_date,
                                'type': 'homework'
                            })
                # Reset
                current_subject = None
                current_desc_lines = []
                continue

            # Check if this is a new subject
            subject_match = re.match(subject_pattern, line, re.IGNORECASE)
            if subject_match:
                # Save previous subject if exists
                if current_subject and current_desc_lines:
                    task_desc = ' '.join(current_desc_lines)
                    if len(task_desc) >= 10:
                        due_dates = self._determine_due_dates(current_subject, task_desc, week_start_date)
                        for due_date in due_dates:
                            homework_items.append({
                                'child': child_name,
                                'subject': current_subject,
                                'description': task_desc,
                                'due_date': due_date,
                                'type': 'homework'
                            })

                # Start new subject
                current_subject = subject_match.group(1).strip()
                rest_of_line = subject_match.group(2).strip()
                current_desc_lines = [rest_of_line] if rest_of_line else []
            elif current_subject:
                # Continue current subject description
                # Skip very short lines or numbers only (likely OCR noise)
                if len(line) > 2 and not line.isdigit():
                    current_desc_lines.append(line)

        # Don't forget the last subject
        if current_subject and current_desc_lines:
            task_desc = ' '.join(current_desc_lines)
            if len(task_desc) >= 10:
                due_dates = self._determine_due_dates(current_subject, task_desc, week_start_date)
                for due_date in due_dates:
                    homework_items.append({
                        'child': child_name,
                        'subject': current_subject,
                        'description': task_desc,
                        'due_date': due_date,
                        'type': 'homework'
                    })

        return homework_items

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract text from a specific section.

        Args:
            text: Full OCR text
            section_name: Section name to extract (e.g., "MINE LEKSER")

        Returns:
            Text from that section only
        """
        # Look for section markers like "=== MINE LEKSER ==="
        pattern = f"===\\s*{section_name}\\s*===(.*?)(?:===|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()

        # Fall back to finding the section name and taking everything until next section
        pattern = f"{section_name}(.*?)(?:===|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()

        return ""

    def _determine_due_dates(
        self,
        subject: str,
        description: str,
        week_start: date
    ) -> List[date]:
        """Determine due dates based on subject and description.

        Args:
            subject: Subject name
            description: Task description
            week_start: Monday of the week

        Returns:
            List of due dates
        """
        due_dates = []

        # Default patterns based on examples
        # Norsk: Usually Mon-Thu (0-3)
        # Matematikk: Usually Monday (0)
        # Musikk: Usually Tuesday (1)
        # Reading/Lesing: Usually Tue-Wed (1-2)

        subject_lower = subject.lower()

        if 'norsk' in subject_lower:
            # Due Tuesday
            due_dates = [week_start + timedelta(days=1)]  # Tuesday only
        elif 'matematikk' in subject_lower or 'matte' in subject_lower:
            # Due Monday
            due_dates = [week_start]
        elif 'musikk' in subject_lower:
            # Due Tuesday
            due_dates = [week_start + timedelta(days=1)]
        elif 'lesing' in subject_lower or 'reading' in subject_lower:
            # Due Tue-Wed
            due_dates = [
                week_start + timedelta(days=1),  # Tuesday
                week_start + timedelta(days=2)   # Wednesday
            ]
        else:
            # Default to Monday
            due_dates = [week_start]

        return due_dates

    def extract_events_from_text(
        self,
        text: str,
        child_name: str
    ) -> List[Dict[str, Any]]:
        """Extract important events from Beskjeder section.

        Args:
            text: OCR text from Ukeplan image
            child_name: Name of child (Max, Ella)

        Returns:
            List of event dictionaries
        """
        events = []

        # Look for date patterns like "9.desember" or "9 des" or "tirsdag 9.desember"
        date_patterns = [
            r'(\d{1,2})\.\s*(?:januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember)',
            r'(\d{1,2})\s+(?:jan|feb|mar|apr|mai|jun|jul|aug|sep|okt|nov|des)',
            r'(?:mandag|tirsdag|onsdag|torsdag|fredag|lørdag|søndag)\s+(\d{1,2})\.\s*(?:januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember)'
        ]

        # Look for time patterns like "kl. 08.30" or "08:30"
        time_pattern = r'kl\.\s*(\d{1,2})\.(\d{2})|(\d{1,2}):(\d{2})'

        # Extract events
        lines = text.split('\n')
        for line in lines:
            # Skip if line is too short
            if len(line.strip()) < 10:
                continue

            # Check for date
            date_match = None
            for pattern in date_patterns:
                date_match = re.search(pattern, line, re.IGNORECASE)
                if date_match:
                    break

            if date_match:
                # Found a date, extract event details
                event_text = line.strip()

                # Extract time if present
                time_match = re.search(time_pattern, line)
                hour = 8  # Default time
                minute = 0

                if time_match:
                    if time_match.group(1):  # kl. format
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                    else:  # : format
                        hour = int(time_match.group(3))
                        minute = int(time_match.group(4))

                events.append({
                    'child': child_name,
                    'description': event_text,
                    'date_text': date_match.group(0),
                    'hour': hour,
                    'minute': minute,
                    'type': 'event'
                })

        return events

    def extract_preparation_items(
        self,
        text: str,
        child_name: str,
        week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Extract preparation items that need reminders.

        Args:
            text: OCR text from Ukeplan image
            child_name: Name of child
            week_start_date: Starting Monday of the week

        Returns:
            List of preparation item dictionaries
        """
        prep_items = []

        if week_start_date is None:
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            week_start_date = today + timedelta(days=days_until_monday)

        # Extract from "BESKJEDER" section
        beskjeder_text = self._extract_section(text, "BESKJEDER")
        if not beskjeder_text:
            # Fall back to full text
            beskjeder_text = text

        # Look for "Ta med" or "Husk" or "Send med" patterns
        prep_patterns = [
            r'(?:Ta med|Husk|Send med)[\s:]+(.+?)(?:\n|$)',
            r'(?:må være|skal ha med|trenger)[\s:]+(.+?)(?:\n|$)'
        ]

        for pattern in prep_patterns:
            matches = re.finditer(pattern, beskjeder_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                item_desc = match.group(1).strip()

                # Try to determine due date from context
                # Default to Thursday (common for weekly items)
                due_date = week_start_date + timedelta(days=3)  # Thursday

                prep_items.append({
                    'child': child_name,
                    'description': item_desc,
                    'due_date': due_date,
                    'type': 'preparation',
                    'needs_reminder': True
                })

        return prep_items

    def format_task_title(self, item: Dict[str, Any]) -> str:
        """Format task title for TickTick.

        Args:
            item: Task dictionary

        Returns:
            Formatted task title
        """
        child = item.get('child', '')

        if item['type'] == 'homework':
            subject = item.get('subject', '')
            return f"{child}: {subject}"
        elif item['type'] == 'preparation':
            desc = item.get('description', '')
            return f"{child}: {desc}"
        else:
            return f"{child}: {item.get('description', '')}"
