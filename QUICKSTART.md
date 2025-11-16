# Quick Start Guide

Get your Personal Assistant running in 5 minutes!

## ⚡ Fast Track Setup

### 1. Verify Setup (1 min)

```bash
python3 setup.py
```

This checks:
- ✅ Python version
- ✅ Dependencies
- ✅ Notion connection
- ⚠️ iMessage access
- ⚠️ Google Calendar

### 2. Grant iMessage Access (2 min)

**macOS System Preferences:**
1. Open **System Preferences** → **Security & Privacy**
2. Click **Privacy** tab
3. Select **Full Disk Access**
4. Click **🔒** and unlock
5. Click **+** and add **Terminal.app**
6. Restart Terminal

**Verify:**
```bash
sqlite3 ~/Library/Messages/chat.db "SELECT COUNT(*) FROM message LIMIT 1"
```

Should show a number (your message count).

### 3. Share Notion Pages (2 min)

For each page listed below:
1. Open page in Notion
2. Click **...** (top right)
3. Click **Connections**
4. Add your integration

**Required pages:**
- ✅ Personal Assistant (already shared)
- ⏳ Meal Planning
- ⏳ Memories & sub-pages
- ⏳ Task databases

### 4. Test Run

```bash
# Test configuration
python3 main.py --test

# Run daily briefing (no iMessage)
python3 src/automation/workflows.py --task daily

# Full assistant (replace with your number)
python3 main.py --recipient "+1234567890"
```

## 🎯 What Works Right Now

### ✅ Fully Working
- Notion API integration
- Configuration management
- Logging system
- Project structure

### ⚠️ Needs Setup
- **iMessage**: Requires Full Disk Access
- **Google Calendar**: Needs credentials.json
- **Notion Pages**: Need to be shared

### 📋 Optional Setup
- Google Calendar credentials
- Additional Notion databases

## 💬 Test iMessage Monitoring

Once Full Disk Access is granted:

```bash
# Start monitor
python3 src/monitors/message_monitor.py
```

**Send yourself**: "Mode: Personal Assistant"

The monitor should detect the activation keyword!

## 🔄 Run as Background Service

### Option 1: Terminal Session
```bash
nohup python3 main.py --recipient "+1234567890" &
```

### Option 2: tmux
```bash
tmux new -s assistant
python3 main.py --recipient "+1234567890"
# Ctrl+B then D to detach
```

### Option 3: macOS Launch Agent
See `SETUP.md` for Launch Agent configuration.

## 🎨 Customize Your Assistant

### Change Automation Times

Edit `config/settings.yaml`:

```yaml
automation:
  daily_briefing:
    time: "07:00"  # Your preferred morning time

  weekly_review:
    day: "Sunday"
    time: "18:00"  # Your preferred review time
```

### Add Activation Keywords

Edit `config/settings.yaml`:

```yaml
imessage:
  activation_keywords:
    - "Mode: Personal Assistant"
    - "hey assistant"
    - "schedule check"
    # Add your own!
```

### Adjust Polling Frequency

Edit `config/settings.yaml`:

```yaml
imessage:
  poll_interval_seconds: 30  # Check every 30 seconds
```

## 📊 View Logs

```bash
# Follow logs in real-time
tail -f logs/assistant.log

# View all logs
cat logs/assistant.log

# Search for errors
grep ERROR logs/assistant.log
```

## 🐛 Troubleshooting

### "Permission denied" on Messages database
```bash
# Check permissions
ls -l ~/Library/Messages/chat.db

# If denied → Grant Full Disk Access to Terminal
```

### "Could not find page" from Notion
```bash
# Verify page is shared
python3 fetch_notion_page.py

# Share page in Notion UI
```

### No messages detected
```bash
# Check state file
cat data/state.json

# Delete and restart
rm data/state.json
python3 src/monitors/message_monitor.py
```

### Automation not running
```bash
# Test scheduler
python3 src/automation/scheduler.py

# Check system time
date

# Verify config
python3 main.py --test
```

## 🚀 Next Steps

1. **Share remaining Notion pages** - See SETUP.md
2. **Create task databases** - Organize your tasks in Notion
3. **Set up meal planning** - Create meal database
4. **Add Google Calendar** - Download credentials.json
5. **Customize workflows** - Edit `src/automation/workflows.py`

## 📚 Documentation

- **README.md** - Project overview
- **SETUP.md** - Detailed setup instructions
- **PROJECT_SUMMARY.md** - Technical details
- **This file** - Quick start!

## 🆘 Common Commands

```bash
# Verify setup
python3 setup.py

# Test configuration
python3 main.py --test

# Run daily briefing
python3 src/automation/workflows.py --task daily

# Run weekly review
python3 src/automation/workflows.py --task weekly

# Check preparation reminders
python3 src/automation/workflows.py --task prep_check

# Start message monitor
python3 src/monitors/message_monitor.py

# Start full assistant
python3 main.py --recipient "+1234567890"

# Monitor only (no scheduler)
python3 main.py --no-scheduler --recipient "+1234567890"

# Scheduler only (no monitor)
python3 main.py --no-monitor
```

## 💡 Pro Tips

1. **Start with monitor only** - Test iMessage integration first
2. **Use test mode** - Verify config before running
3. **Check logs** - Tail logs to see what's happening
4. **Small iterations** - Test one feature at a time
5. **Backup your .env** - Keep Notion token safe

---

**Ready to go?** Run `python3 main.py --test` to verify everything is set up!
