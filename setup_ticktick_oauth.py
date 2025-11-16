#!/usr/bin/env python3
"""Setup script for TickTick OAuth authentication."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.integrations.ticktick_oauth import TickTickOAuth

def main():
    print("="*60)
    print("TickTick OAuth Setup")
    print("="*60)
    print("\nBefore starting, you need:")
    print("1. TickTick Developer credentials")
    print("2. Visit: https://developer.ticktick.com/")
    print("3. Create an application")
    print("4. Get Client ID and Client Secret")
    print("\nThen add to .env:")
    print("  TICKTICK_CLIENT_ID=your_client_id")
    print("  TICKTICK_CLIENT_SECRET=your_client_secret")
    print("\n" + "="*60)

    input("\nPress Enter when ready to continue...")

    # Initialize OAuth client
    oauth = TickTickOAuth()

    if not oauth.client_id or not oauth.client_secret:
        print("\n❌ Error: Client ID and Secret not found in .env")
        print("\nAdd these to your .env file:")
        print("TICKTICK_CLIENT_ID=your_client_id_here")
        print("TICKTICK_CLIENT_SECRET=your_client_secret_here")
        return

    # Check if already authenticated
    if oauth.is_available():
        print("\n✅ Already authenticated with TickTick!")
        print("\nTesting connection...")

        stats = oauth.get_task_statistics()
        print(f"\nTask Statistics:")
        print(f"  Total tasks: {stats.get('total', 0)}")
        print(f"  Due today: {stats.get('due_today', 0)}")
        print(f"  Overdue: {stats.get('overdue', 0)}")
        print(f"  High priority: {stats.get('high_priority', 0)}")

        reauth = input("\nRe-authenticate? (y/n): ").strip().lower()
        if reauth != 'y':
            return

    # Start OAuth flow
    print("\nStarting OAuth authorization...")
    oauth.authorize()

    # Test connection
    if oauth.is_available():
        print("\n✅ Setup complete!")
        print("\nYou can now use TickTick in your Personal Assistant.")
        print("\nTest with: python3 test_workflows.py")
    else:
        print("\n❌ Setup failed. Please try again.")

if __name__ == '__main__':
    main()
