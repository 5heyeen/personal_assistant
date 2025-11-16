#!/usr/bin/env python3
"""Setup and verification script for Personal Assistant."""

import os
import sys
from pathlib import Path
import subprocess


def check_python_version():
    """Check Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (3.9+ required)")
        return False


def check_env_file():
    """Check if .env file exists."""
    print("\n📝 Checking .env file...")
    env_file = Path(".env")
    if env_file.exists():
        print("   ✓ .env file exists")
        with open(env_file) as f:
            content = f.read()
            if "NOTION_TOKEN" in content:
                print("   ✓ NOTION_TOKEN found")
                return True
            else:
                print("   ✗ NOTION_TOKEN not found in .env")
                return False
    else:
        print("   ✗ .env file not found")
        return False


def check_dependencies():
    """Check if dependencies are installed."""
    print("\n📦 Checking dependencies...")
    try:
        import requests
        import yaml
        import notion_client
        import google.auth
        print("   ✓ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"   ✗ Missing dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        return False


def check_imessage_access():
    """Check if iMessage database is accessible."""
    print("\n💬 Checking iMessage access...")
    db_path = Path.home() / "Library" / "Messages" / "chat.db"

    if not db_path.exists():
        print("   ✗ Messages database not found")
        return False

    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM message LIMIT 1")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"   ✓ Can read Messages database ({count} messages)")
        return True
    except Exception as e:
        print(f"   ✗ Cannot access Messages database: {e}")
        print("   → Grant Full Disk Access to Terminal in System Preferences")
        return False


def check_google_credentials():
    """Check for Google Calendar credentials."""
    print("\n📅 Checking Google Calendar credentials...")
    creds_file = Path("credentials.json")

    if creds_file.exists():
        print("   ✓ credentials.json found")
        return True
    else:
        print("   ⚠ credentials.json not found")
        print("   → Download from Google Cloud Console if you want Calendar integration")
        return False


def check_notion_access():
    """Check Notion API access."""
    print("\n📝 Checking Notion access...")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        token = os.getenv('NOTION_TOKEN')
        if not token:
            print("   ✗ NOTION_TOKEN not set in environment")
            return False

        import requests
        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28'
        }

        # Try to access the assistant page
        import yaml
        with open('config/settings.yaml') as f:
            config = yaml.safe_load(f)

        page_id = config['notion']['assistant_page_id']
        response = requests.get(
            f'https://api.notion.com/v1/pages/{page_id}',
            headers=headers
        )

        if response.status_code == 200:
            page = response.json()
            title = page['properties']['title']['title'][0]['plain_text']
            print(f"   ✓ Can access Notion page: '{title}'")
            return True
        elif response.status_code == 404:
            print("   ✗ Cannot access Personal Assistant page")
            print("   → Share the page with your Notion integration")
            return False
        else:
            print(f"   ✗ Notion API error: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ✗ Error checking Notion: {e}")
        return False


def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("   ✓ Dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("   ✗ Failed to install dependencies")
        return False


def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    dirs = ['logs', 'data']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"   ✓ {dir_name}/")
    return True


def main():
    """Run setup checks."""
    print("="*60)
    print("Personal Assistant Setup & Verification")
    print("="*60)

    checks = [
        ("Python version", check_python_version),
        ("Environment file", check_env_file),
        ("Dependencies", check_dependencies),
        ("iMessage access", check_imessage_access),
        ("Google credentials", check_google_credentials),
        ("Notion access", check_notion_access),
        ("Directories", create_directories),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"   ✗ Error running check: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("Setup Summary")
    print("="*60)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n{passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 Setup complete! You're ready to run the assistant.")
        print("\nNext steps:")
        print("1. python main.py --test  # Test configuration")
        print("2. python main.py --recipient YOUR_PHONE  # Run assistant")
    else:
        print("\n⚠️  Some checks failed. See SETUP.md for detailed instructions.")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
