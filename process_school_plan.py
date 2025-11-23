#!/usr/bin/env python3
"""Process school weekly plan image and add homework/events."""

import sys
import argparse
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.workflows.school_plan_processor import SchoolPlanProcessor
from src.utils.logger import get_logger


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process school weekly plan image',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process Max's Ukeplan for this week
  python3 process_school_plan.py ukeplan_max.jpg --child Max

  # Process Ella's Ukeplan for next week (starting Monday)
  python3 process_school_plan.py ukeplan_ella.jpg --child Ella --next-week

  # Process with custom week start date
  python3 process_school_plan.py ukeplan_max.jpg --child Max --date 2025-11-24
        '''
    )

    parser.add_argument(
        'image',
        help='Path to school plan image file'
    )

    parser.add_argument(
        '--child',
        required=True,
        choices=['Max', 'Ella'],
        help='Child name (Max or Ella)'
    )

    parser.add_argument(
        '--date',
        help='Week start date (Monday) in YYYY-MM-DD format'
    )

    parser.add_argument(
        '--next-week',
        action='store_true',
        help='Use next Monday as week start'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )

    args = parser.parse_args()

    logger = get_logger(__name__)

    # Determine week start date
    week_start = None
    if args.date:
        week_start = date.fromisoformat(args.date)
    elif args.next_week:
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        week_start = today + timedelta(days=days_until_monday)
    else:
        # Use current week's Monday
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)

    # Check image file exists
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"❌ Error: Image file not found: {args.image}")
        sys.exit(1)

    print(f"\n📚 Processing School Plan")
    print(f"{'='*50}")
    print(f"Image: {args.image}")
    print(f"Child: {args.child}")
    print(f"Week starting: {week_start.strftime('%A, %d %B %Y')}")
    print(f"{'='*50}\n")

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    try:
        # Initialize processor
        processor = SchoolPlanProcessor()

        # Process the image
        results = processor.process_image_file(
            str(image_path),
            args.child,
            week_start
        )

        # Display results
        print(f"\n✅ Processing Complete!")
        print(f"{'='*50}")
        print(f"Homework items added: {results['homework_added']}")
        print(f"Events added: {results['events_added']}")
        print(f"Reminders sent: {results['reminders_sent']}")

        if results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"  - {error}")

        print(f"{'='*50}\n")

    except Exception as e:
        logger.error(f"Error processing school plan: {e}")
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
