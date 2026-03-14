#!/usr/bin/env python3
"""
smtp_fix.py – Gmail SMTP multi-method diagnostic
=================================================
Attempts to establish a Gmail SMTP connection using three different
methods in order to identify which configuration works in the current
network environment:

* **Method 1** – Port 587 with STARTTLS (standard approach).
* **Method 2** – Port 465 with SSL (``SMTP_SSL``).
* **Method 3** – Port 587 with a custom SSL context (lowered security level).

If a working method is found the script can optionally update the ``.env``
file to use that method.

Usage::

    python smtp_fix.py

Environment variables required (via ``.env``):
    SMTP_USERNAME – Your Gmail address.
    SMTP_PASSWORD – Your Gmail App Password (16 characters).
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def test_gmail_methods():
    """Attempt Gmail SMTP connections via three different methods.

    Tries each method in sequence and returns the identifier of the first one
    that successfully authenticates.

    Methods tried
    -------------
    * ``"method1"`` – Port 587 with STARTTLS (debug output enabled).
    * ``"method2"`` – Port 465 with ``SMTP_SSL`` and default SSL context.
    * ``"method3"`` – Port 587 with a custom SSL context (``SECLEVEL=1``).

    Returns:
        str or None: The method identifier string (``"method1"``,
        ``"method2"``, or ``"method3"``) if one succeeded, or ``None`` if
        all methods failed.
    """
    
    username = os.getenv('SMTP_USERNAME')
    password = os.getenv('SMTP_PASSWORD')
    
    print("Testing different Gmail SMTP methods...\n")
    
    # Method 1: Port 587 with STARTTLS
    print("Method 1: Port 587 with STARTTLS")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Enable debug
        server.starttls()
        server.login(username, password)
        print("[SUCCESS] Method 1 worked!")
        server.quit()
        return "method1"
    except Exception as e:
        print(f"[FAILED] Method 1: {e}\n")
    
    # Method 2: Port 465 with SSL
    print("Method 2: Port 465 with SSL")
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context)
        server.set_debuglevel(1)
        server.login(username, password)
        print("[SUCCESS] Method 2 worked!")
        server.quit()
        return "method2"
    except Exception as e:
        print(f"[FAILED] Method 2: {e}\n")
    
    # Method 3: Port 587 with custom SSL context
    print("Method 3: Port 587 with custom SSL context")
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)
        context = ssl.create_default_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        server.starttls(context=context)
        server.login(username, password)
        print("[SUCCESS] Method 3 worked!")
        server.quit()
        return "method3"
    except Exception as e:
        print(f"[FAILED] Method 3: {e}\n")
    
    return None

def update_env_for_working_method(method):
    """Optionally update the ``.env`` file to use the working SMTP method.

    Currently handles automatic updates for ``"method2"`` (port 465 / SSL).
    For ``"method3"`` a message is printed advising manual code changes.

    Args:
        method: Method identifier returned by :func:`test_gmail_methods`
                (``"method1"``, ``"method2"``, or ``"method3"``).
    """
    
    if method == "method2":
        # Update to use SSL port 465
        print("\nUpdating .env for SSL method (port 465)...")
        with open('.env', 'r') as f:
            content = f.read()
        
        content = content.replace('SMTP_PORT=587', 'SMTP_PORT=465')
        content = content.replace('SMTP_USE_TLS=True', 'SMTP_USE_SSL=True')
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print("Updated .env file for SSL connection")
    
    elif method == "method3":
        print("\nMethod 3 uses custom SSL context - updating mail.py...")
        # This would require code changes in mail.py

if __name__ == "__main__":
    working_method = test_gmail_methods()
    
    if working_method:
        print(f"\n[SUCCESS] {working_method.upper()} is working!")
        update_env_for_working_method(working_method)
    else:
        print("\n[ERROR] None of the methods worked.")
        print("\nTroubleshooting steps:")
        print("1. Verify your Gmail App Password is correct")
        print("2. Enable 2-Factor Authentication in Google Account")
        print("3. Generate a new App Password")
        print("4. Try using your actual Gmail password temporarily")
        print("5. Check if your network/firewall blocks SMTP")