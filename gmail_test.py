#!/usr/bin/env python3
"""
gmail_test.py – Minimal Gmail send test
========================================
Sends a single test email using the SMTP credentials stored in the ``.env``
file to verify that authentication and delivery are working.

Usage::

    python gmail_test.py

Environment variables required (via ``.env``):
    SMTP_USERNAME – Your Gmail address.
    SMTP_PASSWORD – Your Gmail App Password (16 characters).
"""

import smtplib
import ssl
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def test_gmail_simple():
    """Send a minimal test email via Gmail SMTP using credentials from ``.env``.

    Connects to ``smtp.gmail.com:587`` with STARTTLS, authenticates, sends a
    plain-text test message to ``caran1024@gmail.com``, and prints the result.

    Environment variables used:
        SMTP_USERNAME – Gmail sender address.
        SMTP_PASSWORD – Gmail App Password.
    """
    
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD') 
    
    print(f"Testing Gmail with:")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    try:
        # Simple approach
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)
        server.ehlo('gmail.com')  # Use gmail.com as FQDN
        server.starttls()
        server.ehlo('gmail.com')  # EHLO again after STARTTLS
        
        print("Attempting login...")
        server.login(username, password)
        print("LOGIN SUCCESS!")
        
        # Send test email
        msg = MIMEText("Test email from Python!")
        msg['Subject'] = 'Python Test Email'
        msg['From'] = username
        msg['To'] = 'caran1024@gmail.com'
        
        server.send_message(msg)
        print("EMAIL SENT SUCCESSFULLY!")
        
        server.quit()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gmail_simple()