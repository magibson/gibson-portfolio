#!/usr/bin/env python3
"""
Package Tracker - Scans Gmail for shipping notifications and extracts tracking info
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import re
import json
import os

# Gmail configuration  
GMAIL_USER = "msgibson103@gmail.com"
GMAIL_APP_PASSWORD = "txcvsqymhbezkfwz"
IMAP_SERVER = "imap.gmail.com"

# Tracking number patterns
TRACKING_PATTERNS = {
    'ups': [
        r'1Z[A-Z0-9]{16}',  # UPS standard
    ],
    'fedex': [
        r'\b\d{12}\b',  # FedEx Express
        r'\b\d{15}\b',  # FedEx Ground
        r'\b\d{20}\b',  # FedEx Door Tag
    ],
    'usps': [
        r'\b9[0-9]{21}\b',  # USPS Tracking
        r'\b[A-Z]{2}\d{9}US\b',  # International
    ],
    'amazon': [
        r'TBA\d{12}',  # Amazon Logistics
    ],
}

# Sender patterns
SENDER_PATTERNS = {
    'ups': ['ups.com', 'ups-my-choice'],
    'fedex': ['fedex.com'],
    'usps': ['usps.com', 'informeddelivery'],
    'amazon': ['amazon.com', 'amazon.co'],
    'dhl': ['dhl.com'],
}

def connect_imap():
    """Connect to Gmail IMAP"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        return mail
    except Exception as e:
        print(f"IMAP connection failed: {e}")
        return None

def decode_mime_header(header):
    """Decode a MIME header"""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            result += part
    return result

def get_email_body(msg):
    """Extract text body from email message"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
            elif content_type == "text/html":
                try:
                    body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())
    return body

def extract_tracking_numbers(text, carrier=None):
    """Extract tracking numbers from text"""
    found = []
    patterns = TRACKING_PATTERNS if carrier is None else {carrier: TRACKING_PATTERNS.get(carrier, [])}
    
    for c, pats in patterns.items():
        for pat in pats:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                found.append({'carrier': c, 'tracking': m.upper()})
    
    return found

def identify_carrier(from_addr, subject):
    """Identify carrier from email sender/subject"""
    text = f"{from_addr} {subject}".lower()
    for carrier, patterns in SENDER_PATTERNS.items():
        for p in patterns:
            if p in text:
                return carrier
    return None

def scan_for_packages(days=14):
    """Scan Gmail for shipping notifications"""
    mail = connect_imap()
    if not mail:
        return []
    
    packages = []
    seen_items = set()  # Track by subject to avoid duplicates
    
    try:
        mail.select('INBOX')
        
        # Search for shipping-related emails
        queries = [
            'FROM "ups.com"',
            'FROM "fedex.com"', 
            'FROM "usps.com"',
            'FROM "amazon.com" SUBJECT "shipped"',
            'FROM "amazon.com" SUBJECT "delivered"',
            'FROM "amazon.com" SUBJECT "arriving"',
            'FROM "amazon.com" SUBJECT "out for delivery"',
            'SUBJECT "tracking number"',
            'SUBJECT "has shipped"',
            'SUBJECT "out for delivery"',
        ]
        
        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        
        all_email_ids = set()
        for query in queries:
            try:
                result, data = mail.search(None, f'({query} SINCE {since_date})')
                if result == 'OK' and data[0]:
                    all_email_ids.update(data[0].split())
            except:
                pass
        
        print(f"Found {len(all_email_ids)} potential shipping emails")
        
        for email_id in list(all_email_ids)[:50]:  # Limit to 50 emails
            try:
                result, data = mail.fetch(email_id, '(RFC822)')
                if result != 'OK':
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                from_addr = decode_mime_header(msg.get('From', ''))
                subject = decode_mime_header(msg.get('Subject', ''))
                date_str = msg.get('Date', '')
                
                # Try to parse date
                email_date = datetime.now()
                try:
                    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S']:
                        try:
                            email_date = datetime.strptime(date_str[:31].strip(), fmt)
                            break
                        except:
                            pass
                except:
                    pass
                
                # Get body
                body = get_email_body(msg)
                full_text = f"{subject} {body}"
                
                # Identify carrier
                carrier = identify_carrier(from_addr, subject)
                
                # Determine status from subject
                status = 'In Transit'
                subject_lower = subject.lower()
                if 'delivered' in subject_lower:
                    status = 'Delivered'
                elif 'out for delivery' in subject_lower:
                    status = 'Out for Delivery'
                elif 'shipped' in subject_lower or 'on its way' in subject_lower:
                    status = 'Shipped'
                elif 'arriving' in subject_lower:
                    status = 'Arriving Soon'
                
                # Extract tracking numbers
                tracking_nums = extract_tracking_numbers(full_text, carrier)
                
                if tracking_nums:
                    # Has tracking number
                    for t in tracking_nums:
                        if t['tracking'] not in seen_items:
                            seen_items.add(t['tracking'])
                            packages.append({
                                'carrier': t['carrier'].upper(),
                                'tracking': t['tracking'],
                                'status': status,
                                'description': extract_item_name(subject),
                                'date': email_date.strftime('%Y-%m-%d'),
                                'last_updated': datetime.now().isoformat()
                            })
                else:
                    # No tracking number - still capture as package (common for Amazon)
                    item_key = f"{subject[:50]}_{email_date.strftime('%Y-%m-%d')}"
                    if item_key not in seen_items and status in ['Shipped', 'Out for Delivery', 'Arriving Soon']:
                        seen_items.add(item_key)
                        packages.append({
                            'carrier': carrier.upper() if carrier else 'AMAZON',
                            'tracking': None,
                            'status': status,
                            'description': extract_item_name(subject),
                            'date': email_date.strftime('%Y-%m-%d'),
                            'last_updated': datetime.now().isoformat()
                        })
                
            except Exception as e:
                print(f"Error processing email: {e}")
                continue
        
        mail.logout()
        
    except Exception as e:
        print(f"Error scanning emails: {e}")
    
    # Sort by date, most recent first
    packages.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Remove delivered packages older than 2 days
    cutoff = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    packages = [p for p in packages if p['status'] != 'Delivered' or p.get('date', '') > cutoff]
    
    return packages

def extract_item_name(subject):
    """Extract item name from email subject"""
    # Remove common prefixes
    for prefix in ['Shipped:', 'Delivered:', 'Arriving:', 'Out for delivery:']:
        if subject.startswith(prefix):
            subject = subject[len(prefix):].strip()
    
    # Clean up the text
    subject = subject.replace('"', '').strip()
    
    # Truncate if too long
    if len(subject) > 50:
        subject = subject[:47] + '...'
    
    return subject

def save_packages(packages, filepath='packages.json'):
    """Save packages to JSON file"""
    with open(filepath, 'w') as f:
        json.dump({
            'packages': packages,
            'last_scan': datetime.now().isoformat(),
            'count': len(packages)
        }, f, indent=2)
    print(f"Saved {len(packages)} packages to {filepath}")

if __name__ == '__main__':
    print("Scanning Gmail for packages...")
    packages = scan_for_packages(days=14)
    
    print(f"\nFound {len(packages)} packages:")
    for p in packages:
        tracking = p['tracking'][:20] + '...' if p['tracking'] else 'No tracking'
        print(f"  [{p['carrier']}] {tracking} - {p['status']} - {p.get('description', '')[:30]}")
    
    save_packages(packages, 'data/packages.json')
