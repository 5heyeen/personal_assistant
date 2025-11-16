# TickTick Integration Setup

Your Personal Assistant now integrates with TickTick for task management!

## Features

✅ **Task Retrieval**:
- Today's tasks in daily briefing
- Overdue tasks with warnings
- Upcoming tasks (next 7 days)
- Tasks by priority (High/Medium/Low)
- Tasks by tags

✅ **Task Management**:
- Create new tasks
- Mark tasks as completed
- Task statistics (completed today, overdue, etc.)

✅ **Daily Briefing Integration**:
- Automatic inclusion in morning briefing
- Priority highlighting (🔴 High, 🟡 Medium, 🔵 Low)
- Overdue task warnings

## Quick Setup

### 1. Add Your TickTick Credentials

Edit `.env` file:
```bash
# TickTick credentials
TICKTICK_USERNAME=your_email@example.com
TICKTICK_PASSWORD=your_ticktick_password
```

Replace with your actual TickTick login credentials.

### 2. Install TickTick Library

```bash
pip install ticktick-py
```

### 3. Test Connection

```bash
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.') / 'src'))

from src.integrations.ticktick import TickTickIntegration

ticktick = TickTickIntegration()
if ticktick.is_available():
    print('✓ TickTick connected!')
    stats = ticktick.get_task_statistics()
    print(f'  Total tasks: {stats[\"total\"]}')
    print(f'  Due today: {stats[\"due_today\"]}')
    print(f'  Overdue: {stats[\"overdue\"]}')
else:
    print('✗ TickTick not available')
"
```

## Daily Briefing Example

Once configured, your daily briefing will include:

```
📅 Daily Briefing - Monday, November 17, 2025

🗓️ Today's Schedule:
  • Team Meeting - 10:00 AM
  • Lunch with Sarah - 12:30 PM

✅ Tasks:
  ⚠️ 2 overdue task(s)
    - 🔴 Finish project proposal
    - 🟡 Review pull request #123
  📋 4 task(s) due today
    - 🔴 Submit expense report (due 5:00 PM)
    - 🟡 Call dentist (due 3:00 PM)
    - 🔵 Buy groceries
    - Review meeting notes
  🔴 3 high priority task(s)

🍽️ Meals: (Configure meal planning database)
```

## Available Features

### Get Today's Tasks
```python
from src.integrations.ticktick import TickTickIntegration

ticktick = TickTickIntegration()
tasks = ticktick.get_today_tasks()

for task in tasks:
    print(ticktick.format_task_summary(task))
```

### Get Overdue Tasks
```python
overdue = ticktick.get_overdue_tasks()
print(f"You have {len(overdue)} overdue tasks")
```

### Get Upcoming Tasks
```python
# Next 7 days
upcoming = ticktick.get_upcoming_tasks(days=7)
```

### Get High Priority Tasks
```python
# Priority levels: 0=None, 1=Low, 3=Medium, 5=High
high_priority = ticktick.get_tasks_by_priority(priority=5)
```

### Get Tasks by Tag
```python
work_tasks = ticktick.get_tasks_by_tag('work')
```

### Create a Task
```python
from datetime import datetime, timedelta

# Create task due tomorrow at 2 PM
due_date = datetime.now() + timedelta(days=1)
due_date = due_date.replace(hour=14, minute=0)

task = ticktick.create_task(
    title="Call client",
    due_date=due_date,
    priority=5,  # High priority
    tags=['work', 'urgent'],
    content="Discuss project timeline"
)
```

### Complete a Task
```python
ticktick.complete_task(task_id="task-id-here")
```

### Get Statistics
```python
stats = ticktick.get_task_statistics()
print(f"Completed today: {stats['completed_today']}")
print(f"Overdue: {stats['overdue']}")
print(f"Due today: {stats['due_today']}")
print(f"High priority: {stats['high_priority']}")
```

## Priority Indicators

Tasks in briefings use emoji indicators:
- 🔴 **High priority** (level 5)
- 🟡 **Medium priority** (level 3)
- 🔵 **Low priority** (level 1)
- No indicator = No priority set

## Automation Ideas

### Morning Routine
```python
# Included automatically in daily briefing
python3 src/automation/workflows.py --task daily
```

### Weekly Review
The weekly review will show:
- Tasks completed this week
- Tasks due next week
- Overdue task trends

### Custom Workflows

Create custom workflows in `src/automation/workflows.py`:

```python
def weekly_task_review(self) -> str:
    """Generate weekly task review."""
    if not self.ticktick:
        return "TickTick not configured"

    # Get tasks from the week
    stats = self.ticktick.get_task_statistics()
    upcoming = self.ticktick.get_upcoming_tasks(days=7)

    review = [
        f"📊 Weekly Task Review",
        f"",
        f"This week:",
        f"  ✅ Completed: {stats['completed_today']} tasks",
        f"  ⚠️ Overdue: {stats['overdue']} tasks",
        f"",
        f"Next week:",
        f"  📋 {len(upcoming)} tasks scheduled"
    ]

    return "\n".join(review)
```

## Troubleshooting

### "TickTick not available"
- Check credentials in `.env` are correct
- Ensure `ticktick-py` is installed: `pip install ticktick-py`
- Verify TickTick account is active

### "ticktick-py library not installed"
```bash
pip install ticktick-py
```

### Authentication errors
- Verify your email and password are correct
- Check if two-factor authentication is enabled (may need app-specific password)
- Try logging into TickTick web interface to verify credentials

### No tasks showing up
- Make sure you have tasks in TickTick
- Check task due dates are set
- Verify tasks are not in a specific project/list that's not being queried

## Security Notes

- Your TickTick password is stored in `.env` (not committed to git)
- The `.env` file is in `.gitignore` for security
- Never commit or share your `.env` file
- Consider using an app-specific password if available

## Integration with Other Features

### iMessage Notifications
Send task summary via iMessage:
```python
engine = WorkflowEngine()
briefing = engine.daily_briefing(
    send_via_imessage=True,
    recipient="+1234567890"
)
```

### Scheduled Reminders
Tasks are automatically included in scheduled daily briefings (7 AM by default).

### Voice Commands
Once message monitor is active, you can ask:
- "What are my tasks today?"
- "Show overdue tasks"
- "Daily schedule" (includes tasks + calendar)

## Next Steps

1. ✅ Add your credentials to `.env`
2. ✅ Install ticktick-py
3. ✅ Test the connection
4. ✅ Try a daily briefing
5. ✅ Customize workflows as needed

---

**Documentation**: https://github.com/lazeroffmichael/ticktick-py
**TickTick Web**: https://ticktick.com
