# TickTick OAuth Setup (for Passkey/Social Login Users)

If you log into TickTick using passkey, Apple ID, Google, or other social login methods, you need to use OAuth authentication instead of username/password.

## Step 1: Create TickTick Developer Application

### 1.1 Visit TickTick Developer Portal
Go to: **https://developer.ticktick.com/**

### 1.2 Create New Application
1. Click "Create Application" or "New App"
2. Fill in application details:
   - **Name**: Personal Assistant
   - **Description**: Personal task management assistant
   - **Redirect URI**: `http://localhost:8080/callback`

### 1.3 Get Credentials
After creating the app, you'll receive:
- **Client ID**: A long string (looks like: `xxx_xxxxxxxxxxxx`)
- **Client Secret**: Another long string

**Save these** - you'll need them next!

## Step 2: Configure Credentials

Add your OAuth credentials to `.env`:

```bash
# TickTick OAuth (for passkey/social login users)
TICKTICK_CLIENT_ID=your_client_id_here
TICKTICK_CLIENT_SECRET=your_client_secret_here
```

## Step 3: Run OAuth Setup

```bash
python3 setup_ticktick_oauth.py
```

This will:
1. Check your credentials
2. Open your browser to TickTick
3. Ask you to authorize the app
4. Save your access token locally

### What Happens:

1. **Browser Opens**: You'll see TickTick authorization page
2. **Log In**: Use your passkey/social login (Apple ID, Google, etc.)
3. **Authorize**: Click "Allow" to grant access
4. **Redirect**: Browser redirects to `http://localhost:8080/callback?code=...`
5. **Copy Code**: Copy the `code=XXXXXX` part from the URL
6. **Paste**: Paste it back in the terminal

### Example:
```
Redirect URL: http://localhost:8080/callback?code=abc123xyz&state=...

Copy this part: abc123xyz
```

## Step 4: Test Integration

```bash
python3 test_workflows.py
```

You should now see your TickTick tasks in the daily briefing!

## Troubleshooting

### "Could not find page" Error
- Make sure your Developer app is approved
- Check redirect URI is exactly: `http://localhost:8080/callback`

### "Invalid Client" Error
- Verify Client ID and Secret in `.env` are correct
- Check for extra spaces or quotes

### Authorization Code Expired
- The code expires quickly - paste it immediately
- If expired, run `python3 setup_ticktick_oauth.py` again

### Browser Doesn't Open
The script will print the auth URL. Copy and paste it into your browser manually:
```
https://ticktick.com/oauth/authorize?client_id=...
```

## Token Storage

Your access token is stored in:
```
data/ticktick_token.json
```

This file is in `.gitignore` and won't be committed to git.

## Security Notes

- **Never share** your Client Secret
- **Never commit** `ticktick_token.json` to git
- Token is stored locally and encrypted in transit
- You can revoke access anytime at https://developer.ticktick.com/

## Re-authentication

If your token expires or you want to re-authenticate:

```bash
# Delete token
rm data/ticktick_token.json

# Re-run setup
python3 setup_ticktick_oauth.py
```

## Scopes

The app requests these permissions:
- `tasks:read` - Read your tasks
- `tasks:write` - Create and update tasks

## Alternative: Using TickTick API Directly

If you prefer not to use OAuth, you can:
1. Create an app-specific password in TickTick (if available)
2. Use the username/password integration instead (see `TICKTICK_SETUP.md`)

---

**Need help?** Check the TickTick Developer documentation: https://developer.ticktick.com/docs
