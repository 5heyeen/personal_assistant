#!/usr/bin/env python3
"""Quick test script for workflows."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.automation.workflows import WorkflowEngine

# Test workflow engine
print("Testing Workflow Engine...")
engine = WorkflowEngine()

print("\n1. Testing Daily Briefing:")
print("-" * 60)
briefing = engine.daily_briefing(send_via_imessage=False)
print(briefing)

print("\n2. Testing Weekly Review:")
print("-" * 60)
review = engine.weekly_review()
print(review)

print("\n3. Testing Preparation Check:")
print("-" * 60)
events = engine.advance_preparation_check(days_ahead=30)
print(f"Found {len(events)} events needing preparation")
for item in events[:5]:  # Show first 5
    event = item['event']
    print(f"  - {event.get('summary', 'No title')}: {item['prep_needed']} ({item['days_until']} days)")

print("\n✅ All workflow tests passed!")
