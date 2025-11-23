#!/usr/bin/env python3
"""Run weekly briefing and send via iMessage."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.automation.workflows import WorkflowEngine
from src.integrations.imessage import iMessageIntegration
from src.utils.logger import get_logger

def main():
    logger = get_logger(__name__)

    try:
        # Initialize workflow engine
        engine = WorkflowEngine()

        # Generate weekly briefing
        briefing = engine.weekly_briefing()

        # Save to file
        output_dir = Path(__file__).parent / 'data' / 'briefings'
        output_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        output_file = output_dir / f'weekly_briefing_{today}.txt'

        with open(output_file, 'w') as f:
            f.write(briefing)

        logger.info(f"Weekly briefing saved to {output_file}")
        print(f"✅ Weekly briefing saved to {output_file}")

        # Try to send via iMessage (if available and configured)
        try:
            imessage = iMessageIntegration()
            if imessage.is_available():
                RECIPIENT = "+4740516916"  # Your phone number
                if imessage.send_message(RECIPIENT, briefing):
                    logger.info(f"Sent weekly briefing via iMessage to {RECIPIENT}")
                    print(f"📱 Weekly briefing sent via iMessage to {RECIPIENT}")
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
        logger.error(f"Error generating weekly briefing: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
