#!/usr/bin/env python3
"""
Google Calendar & Gmail API Integration
OAuth 2.0 flow with manual implementation
"""

import json
import requests
import urllib.parse
import webbrowser
import sys
from datetime import datetime, timedelta
import secrets

CREDENTIALS_FILE = "google-credentials.json"
TOKEN_FILE = "google-tokens.json"
REDIRECT_URI = "http://localhost:8080"

def load_credentials():
    """Load Google OAuth credentials"""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
            return creds['installed']
    except FileNotFoundError:
        print("❌ google-credentials.json not found")
        return None

def save_tokens(tokens):
    """Save OAuth tokens"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def load_tokens():
    """Load saved tokens"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_auth_url():
    """Generate Google OAuth authorization URL"""
    creds = load_credentials()
    if not creds:
        return None
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    # Define scopes - what we want access to
    scopes = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ]
    
    params = {
        'client_id': creds['client_id'],
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(scopes),
        'response_type': 'code',
        'access_type': 'offline',  # Get refresh token
        'state': state,
        'prompt': 'consent'  # Force consent screen to get refresh token
    }
    
    auth_url = f"{creds['auth_uri']}?" + urllib.parse.urlencode(params)
    
    return auth_url, state

def exchange_code_for_tokens(auth_code):
    """Exchange authorization code for access tokens"""
    creds = load_credentials()
    if not creds:
        return None
    
    data = {
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    
    response = requests.post(creds['token_uri'], data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        tokens['created_at'] = datetime.now().isoformat()
        save_tokens(tokens)
        return tokens
    else:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def refresh_access_token():
    """Use refresh token to get new access token"""
    tokens = load_tokens()
    creds = load_credentials()
    
    if not tokens or 'refresh_token' not in tokens:
        return None
    
    data = {
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token'
    }
    
    response = requests.post(creds['token_uri'], data=data)
    
    if response.status_code == 200:
        new_tokens = response.json()
        # Keep the refresh token from original response
        if 'refresh_token' not in new_tokens:
            new_tokens['refresh_token'] = tokens['refresh_token']
        new_tokens['created_at'] = datetime.now().isoformat()
        save_tokens(new_tokens)
        return new_tokens
    else:
        print(f"❌ Token refresh failed: {response.status_code}")
        return None

def get_valid_access_token():
    """Get a valid access token, refreshing if needed"""
    tokens = load_tokens()
    
    if not tokens:
        print("❌ No tokens found. Run: python3 google-api.py auth")
        return None
    
    # Check if token is expired (tokens expire in 1 hour)
    if 'expires_in' in tokens and 'created_at' in tokens:
        created_at = datetime.fromisoformat(tokens['created_at'])
        expires_in = tokens['expires_in']
        if datetime.now() > created_at + timedelta(seconds=expires_in - 60):  # 1min buffer
            print("🔄 Access token expired, refreshing...")
            new_tokens = refresh_access_token()
            if new_tokens:
                return new_tokens['access_token']
            else:
                print("❌ Failed to refresh token. Re-authenticate needed.")
                return None
    
    return tokens.get('access_token')

def google_api_request(endpoint, params=None):
    """Make authenticated request to Google API"""
    access_token = get_valid_access_token()
    if not access_token:
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        print("❌ Authentication failed. Try refreshing token or re-authenticate.")
        return None
    else:
        print(f"❌ API request failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def get_calendar_events(days_ahead=7):
    """Get upcoming calendar events"""
    now = datetime.now()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
    
    params = {
        'timeMin': time_min,
        'timeMax': time_max,
        'maxResults': 20,
        'singleEvents': True,
        'orderBy': 'startTime'
    }
    
    endpoint = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    return google_api_request(endpoint, params)

def get_gmail_messages(query='is:unread', max_results=10):
    """Get Gmail messages"""
    params = {
        'q': query,
        'maxResults': max_results
    }
    
    endpoint = 'https://www.googleapis.com/gmail/v1/users/me/messages'
    return google_api_request(endpoint, params)

def get_gmail_message(message_id):
    """Get specific Gmail message details"""
    endpoint = f'https://www.googleapis.com/gmail/v1/users/me/messages/{message_id}'
    return google_api_request(endpoint)

def get_user_profile():
    """Get basic Gmail profile info to test connection"""
    endpoint = 'https://www.googleapis.com/gmail/v1/users/me/profile'
    return google_api_request(endpoint)

def send_email(to, subject, body, attachments=None):
    """Send an email via Gmail API"""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import os
    
    access_token = get_valid_access_token()
    if not access_token:
        return None
    
    # Create message
    if attachments:
        message = MIMEMultipart()
        message.attach(MIMEText(body, 'plain'))
        
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(filepath)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                message.attach(part)
    else:
        message = MIMEText(body, 'plain')
    
    message['to'] = to
    message['subject'] = subject
    
    # Encode message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    # Send via API
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        'https://www.googleapis.com/gmail/v1/users/me/messages/send',
        headers=headers,
        json={'raw': raw}
    )
    
    if response.status_code == 200:
        print(f"✅ Email sent to {to}")
        return response.json()
    else:
        print(f"❌ Failed to send email: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def calendar_summary():
    """Get upcoming calendar events summary"""
    events_data = get_calendar_events()
    
    if not events_data:
        return "❌ Could not access calendar"
    
    events = events_data.get('items', [])
    
    if not events:
        return "📅 **No upcoming events in the next 7 days**"
    
    summary = f"📅 **Upcoming Events ({len(events)}):**\n"
    
    for event in events[:5]:  # Show first 5
        start = event.get('start', {})
        if 'date' in start:
            # All-day event
            date_str = start['date']
            time_str = "All day"
        else:
            # Timed event
            start_time = datetime.fromisoformat(start.get('dateTime', '').replace('Z', '+00:00'))
            date_str = start_time.strftime('%b %d')
            time_str = start_time.strftime('%I:%M %p')
        
        title = event.get('summary', 'No title')
        summary += f"• **{date_str} {time_str}:** {title}\n"
    
    return summary

def gmail_summary():
    """Get Gmail unread messages summary"""
    messages_data = get_gmail_messages('is:unread')
    
    if not messages_data:
        return "❌ Could not access Gmail"
    
    messages = messages_data.get('messages', [])
    
    if not messages:
        return "📧 **No unread messages**"
    
    summary = f"📧 **Unread Messages ({len(messages)}):**\n"
    
    # Get details for first few messages
    for i, msg in enumerate(messages[:3]):
        msg_details = get_gmail_message(msg['id'])
        if msg_details:
            headers = {h['name']: h['value'] for h in msg_details.get('payload', {}).get('headers', [])}
            sender = headers.get('From', 'Unknown sender')[:40]
            subject = headers.get('Subject', 'No subject')[:50]
            summary += f"• **{sender}:** {subject}\n"
        
        if i >= 2:  # Limit to 3 for brevity
            break
    
    if len(messages) > 3:
        summary += f"• ... and {len(messages) - 3} more\n"
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📅 Google API Integration")
        print("Commands:")
        print("  python3 google-api.py auth           # Get authorization URL")
        print("  python3 google-api.py setup <code>   # Complete setup with auth code")
        print("  python3 google-api.py test           # Test connection")
        print("  python3 google-api.py calendar       # Show upcoming events")
        print("  python3 google-api.py gmail          # Show unread emails")
        print("  python3 google-api.py summary        # Combined summary")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "auth":
        auth_url, state = get_auth_url()
        if auth_url:
            print("🔐 Google Authorization Required")
            print(f"Visit this URL: {auth_url}")
            print("\nAfter authorizing, you'll be redirected to localhost (which will fail).")
            print("Copy the 'code=' parameter from the URL and run:")
            print("  python3 google-api.py setup <code>")
        
    elif command == "setup":
        if len(sys.argv) < 3:
            print("❌ Need authorization code")
            sys.exit(1)
        
        auth_code = sys.argv[2]
        tokens = exchange_code_for_tokens(auth_code)
        
        if tokens:
            print("✅ Tokens saved successfully!")
            
            # Test connection
            profile = get_user_profile()
            if profile:
                print(f"🎉 Connected! Email: {profile.get('emailAddress', 'Connected successfully')}")
            
    elif command == "test":
        profile = get_user_profile()
        if profile:
            print(f"✅ Connected! Email: {profile.get('emailAddress', 'Connected successfully')}")
        else:
            print("❌ Connection failed")
    
    elif command == "calendar":
        print(calendar_summary())
    
    elif command == "gmail":
        print(gmail_summary())
    
    elif command == "summary":
        print(calendar_summary())
        print()
        print(gmail_summary())
    
    else:
        print(f"❌ Unknown command: {command}")