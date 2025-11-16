"""iMessage integration for personal assistant."""

import sqlite3
import subprocess
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from ..utils.config import get_config
from ..utils.logger import get_logger


class iMessageIntegration:
    """Handles iMessage reading and sending."""

    def __init__(self):
        """Initialize iMessage integration."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.db_path = self.config.imessage_database_path

        # Validate database exists
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"iMessage database not found at {self.db_path}. "
                "Ensure Full Disk Access is granted to Terminal."
            )

    def _connect_db(self) -> sqlite3.Connection:
        """Connect to iMessage database (read-only).

        Returns:
            SQLite connection
        """
        try:
            # Open in read-only mode
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"Error connecting to iMessage database: {e}")
            raise

    def get_recent_messages(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
        chat_id: Optional[str] = None
    ) -> List[Dict]:
        """Get recent messages from iMessage database.

        Args:
            limit: Maximum number of messages to retrieve
            since: Only get messages after this datetime
            chat_id: Optional chat ID to filter by

        Returns:
            List of message dictionaries
        """
        try:
            conn = self._connect_db()
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT
                    message.ROWID as id,
                    message.guid,
                    message.text,
                    message.handle_id,
                    message.service,
                    message.date,
                    message.date_read,
                    message.date_delivered,
                    message.is_from_me,
                    message.is_read,
                    message.cache_has_attachments,
                    handle.id as sender,
                    chat.chat_identifier,
                    chat.display_name as chat_name,
                    chat.ROWID as chat_rowid
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                WHERE message.text IS NOT NULL
            """

            params = []

            if since:
                # Convert to Apple's timestamp (seconds since 2001-01-01)
                apple_epoch = datetime(2001, 1, 1)
                timestamp = int((since - apple_epoch).total_seconds())
                query += " AND message.date > ?"
                params.append(timestamp)

            if chat_id:
                query += " AND chat.ROWID = ?"
                params.append(chat_id)

            query += " ORDER BY message.date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                # Convert Apple timestamp to datetime
                apple_epoch = datetime(2001, 1, 1)
                date = apple_epoch + timedelta(seconds=row['date'] / 1_000_000_000)

                messages.append({
                    'id': row['id'],
                    'guid': row['guid'],
                    'text': row['text'],
                    'sender': row['sender'],
                    'chat_identifier': row['chat_identifier'],
                    'chat_name': row['chat_name'],
                    'chat_id': row['chat_rowid'],
                    'date': date,
                    'is_from_me': bool(row['is_from_me']),
                    'is_read': bool(row['is_read']),
                    'has_attachments': bool(row['cache_has_attachments']),
                    'service': row['service']
                })

            conn.close()
            self.logger.debug(f"Retrieved {len(messages)} messages")
            return messages

        except Exception as e:
            self.logger.error(f"Error retrieving messages: {e}")
            raise

    def get_chats(self, include_group_chats: bool = True) -> List[Dict]:
        """Get list of all chats.

        Args:
            include_group_chats: Include group chats in results

        Returns:
            List of chat dictionaries
        """
        try:
            conn = self._connect_db()
            cursor = conn.cursor()

            query = """
                SELECT
                    chat.ROWID as id,
                    chat.guid,
                    chat.chat_identifier,
                    chat.display_name,
                    chat.service_name,
                    COUNT(message.ROWID) as message_count
                FROM chat
                LEFT JOIN chat_message_join ON chat.ROWID = chat_message_join.chat_id
                LEFT JOIN message ON chat_message_join.message_id = message.ROWID
            """

            if not include_group_chats:
                query += " WHERE chat.chat_identifier NOT LIKE 'chat%'"

            query += " GROUP BY chat.ROWID ORDER BY MAX(message.date) DESC"

            cursor.execute(query)
            rows = cursor.fetchall()

            chats = []
            for row in rows:
                chats.append({
                    'id': row['id'],
                    'guid': row['guid'],
                    'identifier': row['chat_identifier'],
                    'display_name': row['display_name'],
                    'service': row['service_name'],
                    'message_count': row['message_count'],
                    'is_group': row['chat_identifier'].startswith('chat') if row['chat_identifier'] else False
                })

            conn.close()
            self.logger.debug(f"Retrieved {len(chats)} chats")
            return chats

        except Exception as e:
            self.logger.error(f"Error retrieving chats: {e}")
            raise

    def send_message(self, recipient: str, message: str) -> bool:
        """Send an iMessage using AppleScript.

        Args:
            recipient: Phone number or iMessage email
            message: Message text to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape quotes in message
            message = message.replace('"', '\\"').replace("'", "\\'")

            # AppleScript to send message
            script = f'''
            tell application "Messages"
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to participant "{recipient}" of targetService
                send "{message}" to targetBuddy
            end tell
            '''

            # Execute AppleScript
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"Sent message to {recipient}: {message[:50]}...")
                return True
            else:
                self.logger.error(f"Error sending message: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending message to {recipient}: {e}")
            return False

    def send_message_to_chat(self, chat_identifier: str, message: str) -> bool:
        """Send a message to a specific chat (including group chats).

        Args:
            chat_identifier: Chat identifier from database
            message: Message text to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # Escape quotes
            message = message.replace('"', '\\"').replace("'", "\\'")

            # AppleScript for chat
            script = f'''
            tell application "Messages"
                set targetChat to a reference to text chat id "{chat_identifier}"
                send "{message}" to targetChat
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"Sent message to chat {chat_identifier}: {message[:50]}...")
                return True
            else:
                self.logger.error(f"Error sending to chat: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending to chat {chat_identifier}: {e}")
            return False

    def get_unread_messages(self) -> List[Dict]:
        """Get all unread messages.

        Returns:
            List of unread message dictionaries
        """
        try:
            conn = self._connect_db()
            cursor = conn.cursor()

            query = """
                SELECT
                    message.ROWID as id,
                    message.guid,
                    message.text,
                    message.date,
                    message.is_from_me,
                    handle.id as sender,
                    chat.chat_identifier,
                    chat.display_name as chat_name
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                WHERE message.is_read = 0
                    AND message.is_from_me = 0
                    AND message.text IS NOT NULL
                ORDER BY message.date DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                apple_epoch = datetime(2001, 1, 1)
                date = apple_epoch + timedelta(seconds=row['date'] / 1_000_000_000)

                messages.append({
                    'id': row['id'],
                    'guid': row['guid'],
                    'text': row['text'],
                    'sender': row['sender'],
                    'chat_identifier': row['chat_identifier'],
                    'chat_name': row['chat_name'],
                    'date': date
                })

            conn.close()
            self.logger.debug(f"Found {len(messages)} unread messages")
            return messages

        except Exception as e:
            self.logger.error(f"Error retrieving unread messages: {e}")
            raise

    def search_messages(self, keyword: str, limit: int = 100) -> List[Dict]:
        """Search messages for a keyword.

        Args:
            keyword: Keyword to search for
            limit: Maximum number of results

        Returns:
            List of matching messages
        """
        try:
            conn = self._connect_db()
            cursor = conn.cursor()

            query = """
                SELECT
                    message.ROWID as id,
                    message.text,
                    message.date,
                    message.is_from_me,
                    handle.id as sender,
                    chat.chat_identifier,
                    chat.display_name as chat_name
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                WHERE message.text LIKE ?
                ORDER BY message.date DESC
                LIMIT ?
            """

            cursor.execute(query, (f'%{keyword}%', limit))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                apple_epoch = datetime(2001, 1, 1)
                date = apple_epoch + timedelta(seconds=row['date'] / 1_000_000_000)

                messages.append({
                    'id': row['id'],
                    'text': row['text'],
                    'sender': row['sender'],
                    'chat_identifier': row['chat_identifier'],
                    'chat_name': row['chat_name'],
                    'date': date,
                    'is_from_me': bool(row['is_from_me'])
                })

            conn.close()
            self.logger.debug(f"Found {len(messages)} messages matching '{keyword}'")
            return messages

        except Exception as e:
            self.logger.error(f"Error searching messages: {e}")
            raise
