#!/usr/bin/env python3
"""Run daily briefing and send via iMessage."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.automation.workflows import WorkflowEngine
from src.integrations.imessage import iMessageIntegration
from src.workflows.school_plan_processor import SchoolPlanProcessor
from src.utils.logger import get_logger

def main():
    logger = get_logger(__name__)

    try:
        # Check for new school plans (scan past 7 days)
        try:
            logger.info("Checking for new school plans in messages...")
            school_processor = SchoolPlanProcessor()
            results = school_processor.process_recent_messages(
                sender="Sheyeen Liew",
                hours_back=168  # 7 days
            )

            if results['images_processed'] > 0:
                logger.info(f"Processed {results['images_processed']} school plan images")
                logger.info(f"Added {results['homework_added']} homework tasks, {results['events_added']} events")
            else:
                logger.info("No new school plans found")

        except Exception as e:
            logger.warning(f"Could not check for school plans: {e}")

        # Initialize workflow engine
        engine = WorkflowEngine()

        # Generate daily briefing
        briefing = engine.daily_briefing()

        # Save to file
        output_dir = Path(__file__).parent / 'data' / 'briefings'
        output_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        output_file = output_dir / f'briefing_{today}.txt'

        with open(output_file, 'w') as f:
            f.write(briefing)

        logger.info(f"Daily briefing saved to {output_file}")
        print(f"✅ Briefing saved to {output_file}")

        # Try to send via iMessage (if available and configured)
        try:
            imessage = iMessageIntegration()
            if imessage.is_available():
                RECIPIENT = "+4740516916"  # Your phone number
                if imessage.send_message(RECIPIENT, briefing):
                    logger.info(f"Sent briefing via iMessage to {RECIPIENT}")
                    print(f"📱 Briefing sent via iMessage to {RECIPIENT}")
                else:
                    logger.warning("Failed to send iMessage")
                    print("⚠️  Failed to send iMessage")
            else:
                logger.info("iMessage not available (needs Full Disk Access)")
                print("ℹ️  iMessage not available - briefing saved to file only")
        except Exception as e:
            logger.warning(f"Could not initialize iMessage: {e}")
            print(f"⚠️  iMessage unavailable: {e}")

        print("\n" + briefing)

    except Exception as e:
        logger.error(f"Error generating daily briefing: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
