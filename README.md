# Personal Assistant

An intelligent personal assistant that integrates with Notion, iMessage, and Google Calendar to help manage all aspects of daily life with ADHD-aware support.

## Features

- **Notion Integration**: Read and update data from your Notion workspace
- **TickTick Integration**: Task management with daily briefings, overdue tracking, and priority filtering
- **iMessage Automation**: Monitor messages and send automated responses
- **Google Calendar Sync**: Manage calendar events and reminders
- **ADHD-Aware Support**: Time-blindness helpers, executive function support
- **Proactive Behaviors**: Meal planning, playdate scheduling, advance preparation reminders
- **Memory Management**: Organize learnings across personal, work, finance, and AI domains

## Project Structure

```
personal_assistant/
├── src/
│   ├── integrations/
│   │   ├── notion.py          # Notion API integration
│   │   ├── imessage.py        # iMessage monitoring and sending
│   │   └── google_calendar.py # Google Calendar integration
│   ├── agents/
│   │   ├── base_agent.py      # Base agent class
│   │   └── personal_assistant.py  # Main personal assistant logic
│   ├── monitors/
│   │   └── message_monitor.py # iMessage monitoring service
│   ├── automation/
│   │   ├── scheduler.py       # Task scheduler
│   │   └── workflows.py       # Automated workflows
│   └── utils/
│       ├── config.py          # Configuration management
│       └── logger.py          # Logging utilities
├── config/
│   └── settings.yaml          # Configuration settings
├── data/
│   └── state.json            # Persistent state storage
├── logs/                      # Application logs
├── .env                       # Environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

### 1. Notion Integration

1. Create a Notion integration: https://www.notion.so/my-integrations
2. Copy the integration token to `.env` as `NOTION_TOKEN`
3. Share these pages with your integration:
   - Personal Assistant page
   - All referenced memory pages
   - Meal planning database
   - Calendar databases
   - Task databases

### 2. TickTick Setup (Optional but Recommended)

1. Add your TickTick credentials to `.env`:
   ```
   TICKTICK_USERNAME=your_email@example.com
   TICKTICK_PASSWORD=your_password
   ```
2. Install TickTick library:
   ```bash
   pip install ticktick-py
   ```
3. See [TICKTICK_SETUP.md](TICKTICK_SETUP.md) for detailed setup

### 3. iMessage Access

1. Grant Full Disk Access to Terminal:
   - System Preferences → Security & Privacy → Privacy → Full Disk Access
   - Add Terminal.app or your Python interpreter
2. The Messages database is at `~/Library/Messages/chat.db`

### 4. Google Calendar API (Optional)

1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create OAuth 2.0 credentials
4. Download and save as `credentials.json`
5. First run will prompt for authorization

## Usage

### Running the Assistant

```bash
# Start the message monitor
python src/monitors/message_monitor.py

# Run one-time tasks
python src/automation/workflows.py --task daily_schedule

# Start the full assistant (with all automations)
python main.py
```

### Configuration

Edit `config/settings.yaml` to customize:
- Monitoring intervals
- Notification preferences
- Automation triggers
- Keywords for activation

## Development

### Requirements

- Python 3.9+
- macOS (for iMessage integration)
- Notion account with integration
- Google Calendar API credentials

### Install Dependencies

```bash
pip install -r requirements.txt
```

## License

Private use only
