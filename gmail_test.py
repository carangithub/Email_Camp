#!/usr/bin/env python3
"""
Test Gmail with the exact same credentials from .env
"""

import smtplib
import ssl
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def test_gmail_simple():
    """Simple Gmail test"""
    
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