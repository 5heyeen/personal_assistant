# Personal Assistant - Test Plan

Comprehensive testing guide to verify all functionality.

## Test Environment Setup

### Prerequisites
- [ ] Python 3.9+ installed
- [ ] macOS system (for iMessage testing)
- [ ] Notion workspace with integration
- [ ] Full Disk Access granted (for iMessage)
- [ ] Google Calendar credentials (optional)

### Setup Verification
```bash
python3 setup.py
```

Expected: All checks pass or show clear status for optional features.

---

## 1. Configuration Tests

### 1.1 Environment Variables
**Test**: Verify .env file loads correctly

```bash
python3 -c "from src.utils.config import get_config; c = get_config(); print(f'Token loaded: {bool(c.notion_token)}')"
```

**Expected**: `Token loaded: True`

**Validates**:
- ✅ .env file exists
- ✅ NOTION_TOKEN is loaded
- ✅ Environment variable loading works

### 1.2 YAML Configuration
**Test**: Verify settings.yaml loads

```bash
python3 -c "from src.utils.config import get_config; c = get_config(); print(f'Poll interval: {c.imessage_poll_interval}')"
```

**Expected**: `Poll interval: 30` (or your configured value)

**Validates**:
- ✅ YAML parsing works
- ✅ Config values accessible
- ✅ Dot notation access works

### 1.3 Config Test Mode
**Test**: Run test mode

```bash
python3 main.py --test
```

**Expected**: Shows all configuration values without errors

**Validates**:
- ✅ All configs load
- ✅ No import errors
- ✅ Application initializes

---

## 2. Notion Integration Tests

### 2.1 Basic Connectivity
**Test**: Connect to Notion API

```bash
python3 -c "
from src.integrations.notion import NotionIntegration
notion = NotionIntegration()
page = notion.get_page(notion.assistant_page_id)
print(f'Page title: {page[\"properties\"][\"title\"][\"title\"][0][\"plain_text\"]}')
"
```

**Expected**: `Page title: Personal Assistant`

**Validates**:
- ✅ Notion API authentication
- ✅ Page retrieval
- ✅ Token is valid

### 2.2 Read Page Content
**Test**: Fetch page blocks

```bash
python3 -c "
from src.integrations.notion import NotionIntegration
notion = NotionIntegration()
blocks = notion.get_page_content(notion.assistant_page_id)
print(f'Retrieved {len(blocks)} blocks')
"
```

**Expected**: `Retrieved N blocks` (where N > 0)

**Validates**:
- ✅ Block retrieval
- ✅ Page content access

### 2.3 Search Functionality
**Test**: Search Notion workspace

```bash
python3 -c "
from src.integrations.notion import NotionIntegration
notion = NotionIntegration()
results = notion.search('Personal Assistant')
print(f'Found {len(results)} results')
"
```

**Expected**: `Found N results` (at least 1)

**Validates**:
- ✅ Search API works
- ✅ Query processing

### 2.4 Add Memory (if pages shared)
**Test**: Add a test memory

```bash
python3 -c "
from src.integrations.notion import NotionIntegration
notion = NotionIntegration()
result = notion.add_memory('personal', 'Test memory from automated test')
print(f'Memory added: {bool(result)}')
"
```

**Expected**: `Memory added: True` or warning if page not shared

**Validates**:
- ✅ Block appending
- ✅ Memory categorization

---

## 3. iMessage Integration Tests

### 3.1 Database Access
**Test**: Verify Messages database is readable

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
print('✓ iMessage database accessible')
"
```

**Expected**: No errors, prints confirmation

**Validates**:
- ✅ Database exists
- ✅ Full Disk Access granted
- ✅ Read permissions

### 3.2 Read Recent Messages
**Test**: Fetch recent messages

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
messages = imsg.get_recent_messages(limit=10)
print(f'Retrieved {len(messages)} messages')
for msg in messages[:3]:
    print(f'  - {msg[\"sender\"]}: {msg[\"text\"][:50]}...')
"
```

**Expected**: Shows recent messages from your Messages app

**Validates**:
- ✅ SQLite query works
- ✅ Message parsing
- ✅ Timestamp conversion

### 3.3 Get Chats
**Test**: List all chats

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
chats = imsg.get_chats()
print(f'Found {len(chats)} chat(s)')
for chat in chats[:5]:
    print(f'  - {chat[\"display_name\"] or chat[\"identifier\"]}: {chat[\"message_count\"]} messages')
"
```

**Expected**: Lists your iMessage conversations

**Validates**:
- ✅ Chat enumeration
- ✅ Group chat detection
- ✅ Message counting

### 3.4 Search Messages
**Test**: Search for keyword

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
results = imsg.search_messages('hello', limit=5)
print(f'Found {len(results)} messages containing \"hello\"')
"
```

**Expected**: Shows messages matching the keyword

**Validates**:
- ✅ Full-text search
- ✅ Result limiting

### 3.5 Send Test Message
**Test**: Send message to yourself

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
# Replace with your number/email
success = imsg.send_message('+1234567890', 'Test message from Personal Assistant')
print(f'Message sent: {success}')
"
```

**Expected**: `Message sent: True` and you receive the message

**Validates**:
- ✅ AppleScript execution
- ✅ Message sending
- ✅ Messages.app integration

---

## 4. Google Calendar Tests

### 4.1 Authentication
**Test**: OAuth flow (first time only)

```bash
python3 -c "
from src.integrations.google_calendar import GoogleCalendarIntegration
cal = GoogleCalendarIntegration()
print('✓ Google Calendar authenticated')
"
```

**Expected**: Opens browser for OAuth (first time) or uses cached token

**Validates**:
- ✅ OAuth flow
- ✅ Token caching
- ✅ API access

### 4.2 Get Today's Events
**Test**: Fetch today's calendar

```bash
python3 -c "
from src.integrations.google_calendar import GoogleCalendarIntegration
cal = GoogleCalendarIntegration()
events = cal.get_todays_events()
print(f'Today: {len(events)} event(s)')
for event in events:
    print(f'  - {cal.format_event_summary(event)}')
"
```

**Expected**: Lists today's calendar events

**Validates**:
- ✅ Event retrieval
- ✅ Time filtering
- ✅ Event formatting

### 4.3 Get Upcoming Week
**Test**: Fetch next 7 days

```bash
python3 -c "
from src.integrations.google_calendar import GoogleCalendarIntegration
cal = GoogleCalendarIntegration()
events = cal.get_upcoming_events(days=7)
print(f'Next 7 days: {len(events)} event(s)')
"
```

**Expected**: Shows upcoming events

**Validates**:
- ✅ Date range queries
- ✅ Future event filtering

### 4.4 Create Test Event
**Test**: Create and delete an event

```bash
python3 -c "
from src.integrations.google_calendar import GoogleCalendarIntegration
from datetime import datetime, timedelta
cal = GoogleCalendarIntegration()
start = datetime.utcnow() + timedelta(days=1, hours=2)
end = start + timedelta(hours=1)
event = cal.create_event('Test Event - DELETE ME', start, end, description='Automated test event')
print(f'Created event: {event[\"id\"]}')
cal.delete_event(event['id'])
print('✓ Event deleted')
"
```

**Expected**: Creates and deletes test event

**Validates**:
- ✅ Event creation
- ✅ Event deletion
- ✅ Write permissions

---

## 5. Message Monitor Tests

### 5.1 Monitor Initialization
**Test**: Initialize monitor

```bash
python3 -c "
from src.monitors.message_monitor import MessageMonitor
monitor = MessageMonitor()
print(f'Monitor initialized')
print(f'Activation keywords: {len(monitor.activation_keywords)}')
"
```

**Expected**: Monitor initializes without errors

**Validates**:
- ✅ State file creation
- ✅ Configuration loading
- ✅ Keyword loading

### 5.2 Check for New Messages
**Test**: Manual message check

```bash
python3 -c "
from src.monitors.message_monitor import MessageMonitor
monitor = MessageMonitor()
new_messages = monitor.check_for_new_messages()
print(f'New messages: {len(new_messages)}')
"
```

**Expected**: Shows count of new messages since last check

**Validates**:
- ✅ Message polling
- ✅ State tracking
- ✅ Deduplication

### 5.3 Keyword Detection
**Test**: Test keyword activation

1. Send yourself: "Mode: Personal Assistant test"
2. Run:
```bash
python3 -c "
from src.monitors.message_monitor import MessageMonitor
monitor = MessageMonitor()
new_messages = monitor.check_for_new_messages()
activated = monitor.check_for_activation_keywords(new_messages)
print(f'Activated messages: {len(activated)}')
for msg in activated:
    print(f'  Keyword: {msg.get(\"activation_keyword\")}')
"
```

**Expected**: Detects "Mode: Personal Assistant" keyword

**Validates**:
- ✅ Keyword matching
- ✅ Case-insensitive detection
- ✅ Activation flagging

### 5.4 Monitor Loop (Manual)
**Test**: Run monitor for 60 seconds

```bash
timeout 60 python3 src/monitors/message_monitor.py
```

**Action**: Send yourself a test message with an activation keyword

**Expected**: Monitor detects and logs the message

**Validates**:
- ✅ Polling loop
- ✅ Real-time detection
- ✅ Graceful shutdown

---

## 6. Workflow Tests

### 6.1 Daily Briefing
**Test**: Generate daily briefing

```bash
python3 src/automation/workflows.py --task daily
```

**Expected**: Outputs formatted daily briefing

**Validates**:
- ✅ Calendar integration
- ✅ Text formatting
- ✅ Workflow logic

### 6.2 Weekly Review
**Test**: Generate weekly review

```bash
python3 src/automation/workflows.py --task weekly
```

**Expected**: Shows weekly summary

**Validates**:
- ✅ Date calculations
- ✅ Event aggregation
- ✅ Summary generation

### 6.3 Preparation Check
**Test**: Find events needing prep

```bash
python3 src/automation/workflows.py --task prep_check
```

**Expected**: Lists upcoming events with preparation needs

**Validates**:
- ✅ Keyword detection (birthday, travel, etc.)
- ✅ Lead time calculations
- ✅ Event categorization

### 6.4 Send Briefing via iMessage
**Test**: Send briefing to yourself

```bash
python3 src/automation/workflows.py --task daily --recipient "+1234567890"
```

**Expected**: Receives iMessage with daily briefing

**Validates**:
- ✅ End-to-end workflow
- ✅ iMessage delivery
- ✅ Integration between components

---

## 7. Scheduler Tests

### 7.1 Load Schedules
**Test**: Load from config

```bash
python3 -c "
from src.automation.scheduler import TaskScheduler
scheduler = TaskScheduler()
scheduler.load_schedules_from_config()
import schedule
print(f'Loaded {len(schedule.jobs)} job(s)')
for job in schedule.jobs:
    print(f'  - {job}')
"
```

**Expected**: Lists scheduled jobs from config

**Validates**:
- ✅ Config parsing
- ✅ Schedule creation
- ✅ Job registration

### 7.2 Run Pending Jobs
**Test**: Manually trigger pending

```bash
python3 -c "
from src.automation.scheduler import TaskScheduler
scheduler = TaskScheduler()
scheduler.load_schedules_from_config()
scheduler.run_pending()
print('✓ Pending jobs checked')
"
```

**Expected**: Executes if any jobs are due

**Validates**:
- ✅ Job execution
- ✅ Timing logic

---

## 8. Integration Tests

### 8.1 Full Application Start
**Test**: Start in test mode

```bash
python3 main.py --test
```

**Expected**: Shows all component status

**Validates**:
- ✅ All modules load
- ✅ No import errors
- ✅ Configuration complete

### 8.2 Monitor + Scheduler
**Test**: Run both components

```bash
# In one terminal (run for 2 minutes)
timeout 120 python3 main.py --recipient "+1234567890"

# In another terminal, send test message
# Send: "Mode: Personal Assistant"
```

**Expected**: Monitor detects message, scheduler runs in background

**Validates**:
- ✅ Multi-threading
- ✅ Component coordination
- ✅ Graceful shutdown

### 8.3 End-to-End: Keyword → Notion
**Test**: Message triggers Notion memory

1. Modify message handler to add memory:
```python
# Edit src/monitors/message_monitor.py
# In handle_activated_message(), add:
from src.integrations.notion import NotionIntegration
notion = NotionIntegration()
notion.add_memory('personal', f'Activated by: {text}')
```

2. Send activation message
3. Check Notion personal memories page

**Expected**: New memory entry appears

**Validates**:
- ✅ iMessage → Notion pipeline
- ✅ Full integration flow

---

## 9. Error Handling Tests

### 9.1 Missing .env
**Test**: Rename .env temporarily

```bash
mv .env .env.bak
python3 main.py --test
mv .env.bak .env
```

**Expected**: Clear error about missing NOTION_TOKEN

**Validates**:
- ✅ Error messages
- ✅ Graceful failure

### 9.2 Invalid Notion Token
**Test**: Use invalid token

```bash
NOTION_TOKEN=invalid python3 -c "
from src.integrations.notion import NotionIntegration
try:
    notion = NotionIntegration()
    notion.get_page('123')
except Exception as e:
    print(f'✓ Caught error: {type(e).__name__}')
"
```

**Expected**: Catches and reports API error

**Validates**:
- ✅ API error handling
- ✅ Exception catching

### 9.3 iMessage Without Permissions
**Test**: (If Full Disk Access not granted)

```bash
python3 -c "
from src.integrations.imessage import iMessageIntegration
try:
    imsg = iMessageIntegration()
except Exception as e:
    print(f'✓ Expected error: {e}')
"
```

**Expected**: FileNotFoundError or permission error

**Validates**:
- ✅ Permission checking
- ✅ Helpful error messages

---

## 10. Performance Tests

### 10.1 Message Query Speed
**Test**: Time message retrieval

```bash
python3 -c "
import time
from src.integrations.imessage import iMessageIntegration
imsg = iMessageIntegration()
start = time.time()
messages = imsg.get_recent_messages(limit=1000)
elapsed = time.time() - start
print(f'Retrieved {len(messages)} messages in {elapsed:.2f}s')
"
```

**Expected**: < 1 second for 1000 messages

**Validates**:
- ✅ Query performance
- ✅ Database efficiency

### 10.2 Monitor Overhead
**Test**: CPU usage during monitoring

```bash
# Start monitor
python3 src/monitors/message_monitor.py &
PID=$!

# Watch CPU for 60 seconds
sleep 60 && kill $PID
```

**Expected**: Low CPU usage (< 5% average)

**Validates**:
- ✅ Efficient polling
- ✅ Resource usage

---

## Test Results Checklist

### Core Functionality
- [ ] Configuration loads from YAML and .env
- [ ] Notion API connects and retrieves pages
- [ ] iMessage database is accessible
- [ ] Messages can be read and sent
- [ ] Google Calendar (if enabled) authenticates
- [ ] Calendar events can be retrieved

### Monitoring
- [ ] Message monitor initializes
- [ ] New messages are detected
- [ ] Activation keywords trigger correctly
- [ ] State is persisted between runs

### Automation
- [ ] Daily briefing generates
- [ ] Weekly review works
- [ ] Preparation check identifies events
- [ ] Scheduler loads jobs from config
- [ ] Jobs execute at scheduled times

### Integration
- [ ] All components start together
- [ ] Monitor and scheduler run concurrently
- [ ] Messages can trigger Notion updates
- [ ] iMessage notifications are delivered

### Error Handling
- [ ] Missing config files handled gracefully
- [ ] API errors are caught and logged
- [ ] Permission issues show helpful messages
- [ ] Application shuts down cleanly

---

## Continuous Testing

### Daily Smoke Test
```bash
# Quick verification
python3 setup.py && python3 main.py --test
```

### Weekly Full Test
Run all sections of this test plan to ensure nothing broke.

### Before Deployment
- [ ] Run full test suite
- [ ] Test on clean environment
- [ ] Verify all documentation is current

---

## Test Automation (Future)

Consider adding:
- Unit tests with pytest
- Integration test suite
- CI/CD pipeline
- Mock objects for external APIs
- Test coverage reporting

---

**Last Updated**: November 16, 2025
