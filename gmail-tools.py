#!/usr/bin/env python3
"""
Gmail Integration for Matthew
Using IMAP/SMTP with app password
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import sys
import re

# Gmail configuration  
GMAIL_USER = "msgibson103@gmail.com"
GMAIL_APP_PASSWORD = "txcvsqymhbezkfwz"
DISPLAY_NAME = "Matt Gibson"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

def connect_imap():
    """Connect to Gmail IMAP"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        return mail
    except Exception as e:
        print(f"IMAP connection failed: {e}")
        return None

def get_recent_emails(hours=24, limit=10):
    """Get recent emails from the last N hours"""
    mail = connect_imap()
    if not mail:
        return []
    
    try:
        mail.select('INBOX')
        
        # Search for recent emails
        since_date = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")
        result, data = mail.search(None, f'SINCE {since_date}')
        
        if result != 'OK':
            return []
        
        email_ids = data[0].split()
        recent_emails = []
        
        # Get the most recent emails (up to limit)
        for email_id in email_ids[-limit:]:
            result, data = mail.fetch(email_id, '(RFC822)')
            if result == 'OK':
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract email details
                subject = msg.get('Subject', 'No Subject')
                sender = msg.get('From', 'Unknown Sender')
                date = msg.get('Date', 'Unknown Date')
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Clean up sender (extract just the name/email)
                sender_match = re.search(r'<(.+?)>', sender)
                if sender_match:
                    sender_email = sender_match.group(1)
                    sender_name = sender.split('<')[0].strip()
                    clean_sender = f"{sender_name} ({sender_email})" if sender_name else sender_email
                else:
                    clean_sender = sender
                
                recent_emails.append({
                    'subject': subject,
                    'sender': clean_sender,
                    'date': date,
                    'body': body[:200] + "..." if len(body) > 200 else body
                })
        
        mail.close()
        mail.logout()
        return recent_emails
        
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []

def check_unread_count():
    """Get count of unread emails"""
    mail = connect_imap()
    if not mail:
        return 0
    
    try:
        mail.select('INBOX')
        result, data = mail.search(None, 'UNSEEN')
        if result == 'OK':
            unread_count = len(data[0].split()) if data[0] else 0
        else:
            unread_count = 0
            
        mail.close()
        mail.logout()
        return unread_count
        
    except Exception as e:
        print(f"Error checking unread count: {e}")
        return 0

def get_inbox_summary():
    """Get inbox summary"""
    unread = check_unread_count()
    recent = get_recent_emails(hours=24, limit=5)
    
    summary = f"📧 **Gmail Summary**\n"
    summary += f"• **Unread messages:** {unread}\n"
    
    if recent:
        summary += f"• **Recent emails ({len(recent)}):**\n"
        for email in recent[:3]:  # Show top 3
            sender_short = email['sender'][:30] + "..." if len(email['sender']) > 30 else email['sender']
            subject_short = email['subject'][:40] + "..." if len(email['subject']) > 40 else email['subject']
            summary += f"  - **{sender_short}:** {subject_short}\n"
    else:
        summary += "• **No recent emails**\n"
    
    return summary

def search_emails(query, limit=10):
    """Search emails by subject or sender"""
    mail = connect_imap()
    if not mail:
        return []
    
    try:
        mail.select('INBOX')
        
        # Search by subject first
        result, data = mail.search(None, f'SUBJECT "{query}"')
        if result == 'OK' and data[0]:
            email_ids = data[0].split()
        else:
            # Try searching by sender
            result, data = mail.search(None, f'FROM "{query}"')
            if result == 'OK' and data[0]:
                email_ids = data[0].split()
            else:
                return []
        
        found_emails = []
        # Get most recent matches
        for email_id in email_ids[-limit:]:
            result, data = mail.fetch(email_id, '(RFC822)')
            if result == 'OK':
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                found_emails.append({
                    'subject': msg.get('Subject', 'No Subject'),
                    'sender': msg.get('From', 'Unknown'),
                    'date': msg.get('Date', 'Unknown')
                })
        
        mail.close()
        mail.logout()
        return found_emails
        
    except Exception as e:
        print(f"Search failed: {e}")
        return []

def test_connection():
    """Test Gmail connection"""
    print("Testing Gmail connection...")
    
    # Test IMAP
    mail = connect_imap()
    if mail:
        mail.logout()
        print("✅ IMAP connection successful")
        
        # Test getting unread count
        unread = check_unread_count()
        print(f"✅ Found {unread} unread emails")
        
        return True
    else:
        print("❌ IMAP connection failed")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 gmail-tools.py test        # Test connection")
        print("  python3 gmail-tools.py summary     # Get inbox summary")  
        print("  python3 gmail-tools.py unread      # Check unread count")
        print("  python3 gmail-tools.py recent      # Show recent emails")
        print("  python3 gmail-tools.py search <query>  # Search emails")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        test_connection()
    elif command == "summary":
        print(get_inbox_summary())
    elif command == "unread":
        count = check_unread_count()
        print(f"Unread emails: {count}")
    elif command == "recent":
        emails = get_recent_emails(hours=24, limit=10)
        if emails:
            print("Recent emails:")
            for email in emails:
                print(f"• {email['sender']}: {email['subject']}")
        else:
            print("No recent emails found")
    elif command == "search":
        if len(sys.argv) < 3:
            print("Need search query")
            sys.exit(1)
        query = sys.argv[2]
        results = search_emails(query)
        if results:
            print(f"Found {len(results)} emails matching '{query}':")
            for email in results:
                print(f"• {email['sender']}: {email['subject']}")
        else:
            print(f"No emails found matching '{query}'")
    else:
        print(f"Unknown command: {command}")