# Personal Assistant Setup Guide

Complete setup instructions for your Personal Assistant.

## Prerequisites

- macOS (for iMessage integration)
- Python 3.9 or higher
- Notion account with integration
- Google account (for Calendar integration)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Notion Integration Setup

### Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it "Personal Assistant"
4. Select your workspace
5. Copy the "Internal Integration Token"

### Share Pages with Integration

For each of these pages in Notion, you need to share them with your integration:

1. Open the page in Notion
2. Click "..." (three dots) in the top right
3. Go to "Connections" or "Add connections"
4. Select "Personal Assistant" integration
5. Confirm

**Pages to share:**
- Personal Assistant (main configuration page)
- Meal Planning database/page
- Memories page and all sub-pages:
  - Personal Topics
  - Work Topics
  - Finance & Investments
  - AI Usage
- Any task or calendar databases you create

### Configure Notion Token

Add your Notion token to the `.env` file:
```
NOTION_TOKEN=your_notion_integration_token_here
```

Replace `your_notion_integration_token_here` with the token you copied from the Notion integrations page.

## Step 3: iMessage Access Setup

### Grant Full Disk Access

1. Open **System Preferences** → **Security & Privacy**
2. Click the **Privacy** tab
3. Select **Full Disk Access** from the left sidebar
4. Click the lock icon and enter your password
5. Click the "+" button
6. Add one of these:
   - `/Applications/Utilities/Terminal.app` (if running from Terminal)
   - Your Python interpreter (find with `which python3`)

### Verify Database Access

```bash
# Check if you can access the Messages database
ls -l ~/Library/Messages/chat.db
```

If you see "Permission denied", Full Disk Access is not properly configured.

## Step 4: Google Calendar Setup

### Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create a new project: "Personal Assistant"
3. Enable the Google Calendar API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

### Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "+ Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Personal Assistant"
5. Download the credentials JSON file
6. Save it as `credentials.json` in the project root

### First-Time Authorization

When you first run the assistant with Google Calendar enabled:

1. A browser window will open
2. Sign in to your Google account
3. Grant permissions to access your calendar
4. The token will be saved to `token.json`

## Step 5: Configuration

Edit `config/settings.yaml` to customize your assistant:

### Required Changes

```yaml
# Update these with your phone number/email for iMessage notifications
# Example: "+1234567890" or "your@email.com"
```

### Optional Customizations

- **Polling intervals**: How often to check for new messages
- **Automation times**: When to run daily/weekly briefings
- **Lead times**: How far in advance to remind for events
- **Timezone**: Set your local timezone

## Step 6: Test Your Setup

### Test Configuration

```bash
python main.py --test
```

This will verify that all configurations are loaded correctly.

### Test Individual Components

```bash
# Test Notion integration
python src/integrations/notion.py

# Test iMessage reading (requires Full Disk Access)
python src/integrations/imessage.py

# Test Google Calendar
python src/integrations/google_calendar.py
```

### Test Workflows

```bash
# Generate daily briefing
python src/automation/workflows.py --task daily

# Generate weekly review
python src/automation/workflows.py --task weekly

# Check preparation reminders
python src/automation/workflows.py --task prep_check
```

## Step 7: Running the Assistant

### Full Assistant (All Features)

```bash
python main.py --recipient "+1234567890"
```

Replace with your phone number or iMessage email.

### iMessage Monitor Only

```bash
python src/monitors/message_monitor.py
```

### Scheduler Only

```bash
python src/automation/scheduler.py
```

### Run as Background Service (macOS)

Create a Launch Agent to run automatically:

```bash
# Create launch agent plist
cat > ~/Library/LaunchAgents/com.personal.assistant.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.personal.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/personal_assistant/main.py</string>
        <string>--recipient</string>
        <string>YOUR_PHONE_NUMBER</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/personal_assistant/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/personal_assistant/logs/stderr.log</string>
</dict>
</plist>
EOF

# Load the agent
launchctl load ~/Library/LaunchAgents/com.personal.assistant.plist
```

## Troubleshooting

### "Permission denied" on Messages database

- Verify Full Disk Access is granted
- Restart Terminal after granting access
- Check with: `sqlite3 ~/Library/Messages/chat.db "SELECT COUNT(*) FROM message;"`

### "Could not find page" errors from Notion

- Ensure pages are shared with your integration
- Check the page IDs in `config/settings.yaml` match your Notion pages
- Verify the integration token is correct

### Google Calendar authentication fails

- Ensure `credentials.json` is in the project root
- Delete `token.json` and re-authenticate
- Check that Google Calendar API is enabled in Cloud Console

### Messages not being detected

- Check the polling interval in `config/settings.yaml`
- Verify activation keywords match what you're sending
- Check logs in `logs/assistant.log`

### No automated tasks running

- Verify `automation.enabled: true` in config
- Check system time is correct
- View scheduled jobs with `--test` flag

## Next Steps

1. **Share Referenced Pages**: Share all the Notion pages mentioned in your Personal Assistant configuration
2. **Create Databases**: Set up task, meal planning, and other databases in Notion
3. **Customize Workflows**: Edit `src/automation/workflows.py` to add custom automations
4. **Test iMessage**: Send yourself a message with "Mode: Personal Assistant" to test activation

## Security Notes

- Never commit `.env`, `credentials.json`, or `token.json` to git
- Keep your Notion integration token secure
- The Messages database contains all your iMessages - be cautious with access
- Review permissions granted to the Google Calendar integration

## Support

Check the logs at `logs/assistant.log` for detailed information about what the assistant is doing.
