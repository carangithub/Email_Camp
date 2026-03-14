#!/usr/bin/env python3
"""
smtp_test.py – Step-by-step SMTP connection diagnostic
=======================================================
Tests the SMTP configuration stored in ``.env`` through four progressive
stages:

1. Basic TCP connection to the SMTP server.
2. STARTTLS negotiation.
3. Authentication with the configured credentials.
4. Sending a test email to the configured sender address (self-send).

Run this script when you need to diagnose SMTP connectivity or
authentication problems::

    python smtp_test.py

Environment variables required (via ``.env``):
    SMTP_SERVER   – SMTP server hostname (default ``smtp.gmail.com``).
    SMTP_PORT     – SMTP server port (default ``587``).
    SMTP_USERNAME – SMTP login username.
    SMTP_PASSWORD – SMTP password or App Password.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def test_smtp_connection():
    """Run a four-stage SMTP connectivity and authentication test.

    Stages
    ------
    1. Basic TCP connection – verifies the server is reachable on the
       configured port.
    2. TLS upgrade – verifies STARTTLS can be established.
    3. Authentication – verifies the configured credentials are accepted.
    4. Email send – sends a self-addressed test message to confirm end-to-end
       delivery.

    Prints ``[OK]`` or ``[ERROR]`` for each stage. Aborts on the first
    failure and prints possible remediation steps.
    """
    
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    
    print("=" * 60)
    print("GMAIL SMTP CONNECTION TEST")
    print("=" * 60)
    print(f"Server: {smtp_server}")
    print(f"Port: {smtp_port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    print()
    
    # Test 1: Basic connection
    print("1. Testing basic SMTP connection...")
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        print("[OK] Connected to SMTP server")
        server.quit()
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    # Test 2: TLS connection
    print("\n2. Testing TLS connection...")
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        context = ssl.create_default_context()
        server.starttls(context=context)
        print("[OK] TLS connection established")
        server.quit()
    except Exception as e:
        print(f"[ERROR] TLS failed: {e}")
        return
    
    # Test 3: Authentication
    print("\n3. Testing authentication...")
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.login(username, password)
        print("[OK] Authentication successful")
        server.quit()
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        print("\nPossible solutions:")
        print("1. Enable 2-Factor Authentication in Google Account")
        print("2. Generate App Password for Mail")
        print("3. Use the 16-character App Password (not your regular password)")
        print("4. Check if 'Less secure app access' is enabled (not recommended)")
        return
    
    # Test 4: Send test email
    print("\n4. Testing email send...")
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.login(username, password)
        
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = username  # Send to self for testing
        msg['Subject'] = "SMTP Test - Email Campaign Manager"
        
        body = """
        This is a test email from your Email Campaign Manager.
        
        If you receive this email, your SMTP configuration is working correctly!
        
        Test performed at: """ + str(os.popen('date /t && time /t').read().strip())
        
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        server.quit()
        
        print("[OK] Test email sent successfully!")
        print(f"Check your inbox at {username}")
        
    except Exception as e:
        print(f"[ERROR] Failed to send test email: {e}")
    
    print("\n" + "=" * 60)
    print("SMTP TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_smtp_connection()